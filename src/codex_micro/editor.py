"""Versioned config edits and verified device/host updates from the popup."""
import json
import fcntl
import uuid
import os
import subprocess
from pathlib import Path
from .model import validate_config,compile_keymap
from .native import catalog,keyboard_options,configured_chord_options
from .storage import read_files,backup,verified_write,sha,STATE
from .transport import Device


def editor_state(path):
    raw=path.read_bytes()
    result={'config':validate_config(json.loads(raw)),'revision':sha(raw)}
    try: result.update(catalog())
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        result.update({'options':[],'omitted':[],'catalog_error':str(error)})
    from .app_dispatch import app_options
    result['apps']=app_options()
    result['previous_layers']=previous_layer_bindings(result['config'])
    result['options']=keyboard_options()+configured_chord_options(result['config'])+result['options']
    return result


def atomic_write(path,raw):
    temp=path.with_name('.'+path.name+f'.{os.getpid()}.tmp')
    try:
        temp.write_bytes(raw);temp.replace(path)
    finally:temp.unlink(missing_ok=True)


def device_actions(config):
    return {'quick_micro':config.get('quick_micro',False),'profile':config['profile'],'layers':{n:{'app':layer.get('app'), 'bindings':{k:{'single':b['action'],**{g:v['action'] for g,v in b.get('gestures',{}).items() if v['action']['kind']!='noop'}} for k,b in layer['bindings'].items()}} for n,layer in config['layers'].items()}}


def save_config(path,request):
    # Serialize local edits as well as USB saves. Names/labels never need USB.
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/'config.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        before=path.read_bytes()
        if sha(before)!=request['expected_sha256']:raise ValueError('Config changed elsewhere. Reopen the popup to reload it.')
        config=validate_config(request['config'])
        previous=json.loads(before)
        if config['profile']!=previous['profile']:raise ValueError('The popup cannot change the device profile')
        if device_actions(config)==device_actions(previous):
            raw=(json.dumps(config,indent=2,ensure_ascii=False)+'\n').encode()
            if raw!=before:
                directory=STATE/'config-backups';directory.mkdir(exist_ok=True)
                snapshot=directory/(uuid.uuid4().hex+'.json')
                snapshot.write_bytes(before);snapshot.chmod(0o600)
                atomic_write(path,raw)
            return {'saved':True,'config':config,'revision':sha(raw),'device_changed':False,'previous_layers':previous_layer_bindings(config)}
        result=save_device_config(path,request)
        result['previous_layers']=previous_layer_bindings(result['config'])
        return result


def save_device_config(path,request):
    from .cli import binding_text
    config=validate_config(request['config'])
    if any(layer.get('app') for layer in config['layers'].values()) and not os.access('/dev/uinput',os.W_OK):
        raise ValueError('App focus requires user-session access to /dev/uinput')
    options=catalog()['options']
    from .routing import entries,trigger
    reserved={(tuple(sorted(mods)),key) for n,c,g,b in entries(config) if b['action']['kind']!='noop' for mods,key,_ in [trigger(config,n,c,g)]}
    if config.get('quick_micro'):
        from .quick_micro import MODIFIERS,KEY
        reserved.add((tuple(sorted(MODIFIERS)),KEY))
    for option in options:
        action=option['action']
        if (tuple(sorted(action.get('modifiers',[]))),action.get('key')) in reserved:
            raise ValueError('App focus trigger conflicts with '+option.get('description',option['value']))
    validate_release_bindings(config,options)
    available={o['value']:o['action'] for o in options}
    for layer in config['layers'].values():
        for b in layer['bindings'].values():
            for entry in [b,*b.get('gestures',{}).values()]:
                a=entry['action']
                if a['kind']=='keybind' and available.get(a['binding'])!=a:
                    raise ValueError('Shortcut changed or no longer exists: '+a['binding']+'; refresh the picker')
    with Device() as device:
        before_config=path.read_bytes()
        if sha(before_config)!=request['expected_sha256']: raise ValueError('Config changed elsewhere. Reload the popup before saving.')
        if config['profile']!=json.loads(before_config)['profile']:raise ValueError('The popup cannot change the device profile')
        status=device.call('device.status')
        if status['version']!='0.6.2':raise ValueError('Unsupported device firmware')
        before=read_files(device)
        candidate=json.dumps(compile_keymap(json.loads(before['keymap.json']),config),separators=(',',':'),ensure_ascii=False).encode()
        destination=backup(device,status,before)
        (destination/'mappings.json').write_bytes(before_config)
        host=Path.home()/'.config/hypr/codex-micro.lua'
        before_host=host.read_bytes()
        (destination/'codex-micro.lua').write_bytes(before_host)
        changed_device=False
        try:
            if candidate!=before['keymap.json']:
                verified_write(device,before,candidate);changed_device=True
            # A user editing the source during the USB transfer wins over this save.
            if path.read_bytes()!=before_config:raise ValueError('Config changed during upload')
            atomic_write(path,(json.dumps(config,indent=2,ensure_ascii=False)+'\n').encode())
            atomic_write(host,binding_text(config).encode())
            subprocess.run(['hyprctl','reload'],check=True,capture_output=True)
            errors=subprocess.check_output(['hyprctl','configerrors'],text=True).strip()
            if errors:raise ValueError(errors)
        except Exception as error:
            # Preserve any concurrent external edit instead of overwriting it.
            current=path.read_bytes()
            if json.loads(current)==config:atomic_write(path,before_config)
            atomic_write(host,before_host)
            subprocess.run(['hyprctl','reload'],capture_output=True)
            if changed_device:
                try:verified_write(device,read_files(device),before['keymap.json'])
                except Exception as rollback:raise RuntimeError(f'{error}; rollback failed: {rollback}; backup: {destination}') from error
            raise
        return {'saved':True,'config':config,'revision':sha(path.read_bytes()),'device_sha256':sha(candidate),'backup':str(destination)}


def validate_release_bindings(config,options):
    """A tap branch releases immediately, so cannot drive press/release actions."""
    release_chords={(o['action']['key'],tuple(sorted(o['action']['modifiers']))) for o in options if o.get('requiresRelease')}
    for layer in config['layers'].values():
        for control,b in layer['bindings'].items():
            gestures=b.get('gestures',{})
            for gesture,entry in [('single',b),*gestures.items()]:
                a=entry['action']
                if a['kind'] not in ('key','keybind'):continue
                if (a['key'],tuple(sorted(a.get('modifiers',[])))) not in release_chords:continue
                if not (control.startswith('key') or control=='dial_press'):
                    raise ValueError('Push-to-talk requires a key or dial press')
                if gesture=='double':
                    raise ValueError('Use Single or Click + hold for push-to-talk')
                if a.get('modifiers'):
                    raise ValueError('This release shortcut needs a held chord, which the Micro cannot encode')


def previous_layer_bindings(config):
    """Find each layer's last different saved key setup in existing backups."""
    paths=list((STATE/'backups').glob('*/mappings.json'))+list((STATE/'config-backups').glob('*.json'))
    paths.sort(key=lambda p:p.stat().st_mtime_ns,reverse=True)
    result={}
    for path in paths:
        try:
            previous=validate_config(json.loads(path.read_bytes()))
        except (OSError,ValueError,KeyError,TypeError):
            continue
        if previous['profile']!=config['profile']:continue
        for number in ('2','3'):
            bindings=previous['layers'][number]['bindings']
            if number not in result and bindings!=config['layers'][number]['bindings']:
                result[number]=bindings
        if len(result)==2:break
    return result
