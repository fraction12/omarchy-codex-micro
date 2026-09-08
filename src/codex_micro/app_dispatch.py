"""User-session app routing. No device grabs, root service, or shell evaluation."""
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import time
from .native import EVDEV
from .routing import trigger,held_action

KEYS={name:code for code,name in EVDEV.items()}
KEYS.update({'KC_VOLU':115,'KC_VOLD':114,'KC_MUTE':113,'KC_BRIU':225,'KC_BRID':224,'KC_MPLY':164,'KC_MNXT':163,'KC_MPRV':165,'KC_MSTP':166})
MODS={'CTRL':29,'SHIFT':42,'ALT':56,'SUPER':125}
SOCKET=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))/'omarchy-codex-micro-actions.sock'


def query(command):
    return json.loads(subprocess.check_output(['hyprctl',command,'-j'],text=True,timeout=2))


def app_options():
    try:clients=query('clients')
    except (OSError,ValueError,subprocess.SubprocessError):return []
    classes=sorted({w['class'] for w in clients if w.get('class')},key=str.casefold)
    return [{'value':c,'label':c,'description':c} for c in classes]


def focus_app(app):
    # Our editor must relinquish its layer-shell keyboard focus first.
    subprocess.run(['omarchy-shell','shell','hide','fraction12.codex-micro'],check=True,capture_output=True,timeout=2)
    overlay=subprocess.check_output(['hyprctl','repl','for _, l in ipairs(hl.get_layers()) do if l.mapped and l.interactivity > 0 then return true end end; return false'],text=True,timeout=2).strip()
    if overlay!='false':raise ValueError('Close the open desktop panel first; input was not sent')
    active=query('activewindow')
    if active.get('class')==app:return active['address']
    matches=[w for w in query('clients') if w.get('class')==app]
    if not matches:raise ValueError('Open '+app+' first; input was not sent')
    window=min(matches,key=lambda w:w.get('focusHistoryID',9999))
    address=window['address']
    subprocess.run(['hyprctl','dispatch','hl.dsp.focus({ window = '+json.dumps('address:'+address)+' })'],check=True,capture_output=True,timeout=2)
    deadline=time.monotonic()+.75
    while time.monotonic()<deadline:
        current=query('activewindow')
        if current.get('address')==address and current.get('class')==app:return address
        time.sleep(.015)
    raise ValueError('Could not focus '+app+'; input was not sent')


def key_down(key):
    # Numeric Lua input is an XKB keycode, independent of layout symbols.
    # F13, for example, is XF86Tools in the Micro's active keymap.
    code=KEYS['KC_'+key]+8
    return subprocess.check_output(['hyprctl','repl','return hl.is_key_down('+str(code)+')'],text=True,timeout=2).strip()=='true'


def modifiers_clear():
    expression=' or '.join('hl.is_key_down('+json.dumps(k)+')' for k in ('Control_L','Shift_L','Alt_L','Super_L','Control_R','Shift_R','Alt_R','Super_R'))
    deadline=time.monotonic()+.5
    while time.monotonic()<deadline:
        result=subprocess.check_output(['hyprctl','repl','return '+expression],text=True,timeout=2).strip()
        if result=='false':return
        if result!='true':raise ValueError('Cannot verify released modifiers; input was not sent')
        time.sleep(.01)
    raise ValueError('Release keyboard modifiers and try again')


class Keyboard:
    """Linux uinput keyboard; its lifetime owns all synthetic key releases."""
    def __init__(self):
        self.fd=os.open('/dev/uinput',os.O_WRONLY|os.O_NONBLOCK)
        self.down=set()
        try:
            fcntl.ioctl(self.fd,0x40045564,1)  # UI_SET_EVBIT(EV_KEY)
            for code in sorted(set(KEYS.values())|set(MODS.values())):fcntl.ioctl(self.fd,0x40045565,code)
            setup=struct.pack('HHHH80sI',3,0x1209,0xc0de,1,b'Omarchy Micro app actions',0)
            fcntl.ioctl(self.fd,0x405c5503,setup)  # UI_DEV_SETUP
            fcntl.ioctl(self.fd,0x5501)  # UI_DEV_CREATE
            deadline=time.monotonic()+2
            while time.monotonic()<deadline:
                if any(k['name']=='omarchy-micro-app-actions' for k in query('devices')['keyboards']):break
                time.sleep(.025)
            else:raise RuntimeError('The app-action keyboard was not recognized')
        except BaseException:
            os.close(self.fd);raise

    def event(self,code,value):
        os.write(self.fd,struct.pack('llHHi',0,0,1,code,value)+struct.pack('llHHi',0,0,0,0,0))
        if value:self.down.add(code)
        else:self.down.discard(code)

    def tap(self,action):
        codes=[MODS[m] for m in action.get('modifiers',[])]+[KEYS[action['key']]]
        try:
            for code in codes:self.event(code,1)
            time.sleep(.025)
        finally:
            for code in reversed(codes):self.event(code,0)

    def release_all(self):
        for code in list(self.down):self.event(code,0)

    def close(self):
        try:
            self.release_all()
            time.sleep(.03)
        finally:
            fcntl.ioctl(self.fd,0x5502)
            os.close(self.fd)


def send(layer,control,gesture,phase):
    with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as s:
        s.settimeout(.2)
        s.sendto(json.dumps({'layer':layer,'control':control,'gesture':gesture,'phase':phase,'time':time.monotonic()}).encode(),str(SOCKET))


class Dispatcher:
    def __init__(self,keyboard,config_path):
        self.keyboard=keyboard;self.config_path=config_path;self.held={}

    def release(self,identity):
        held=self.held.pop(identity,None)
        if held and not any(h['code']==held['code'] for h in self.held.values()):self.keyboard.event(held['code'],0)

    def handle(self,message):
        from .model import validate_config
        from .actions import execute
        identity=(message['layer'],message['control'],message['gesture'])
        phase=message['phase']
        # Releases must work even after focus or mappings have changed.
        if phase=='release':self.release(identity);return
        if not plugin_enabled():return
        if phase not in ('tap','press') or time.monotonic()-message['time']>2:return
        config=validate_config(json.loads(self.config_path.read_bytes()))
        if config.get('quick_micro') and identity[1:] == ('dial_press','double'):return
        layer=config['layers'][identity[0]]
        if not layer.get('app'):return
        binding=layer['bindings'][identity[1]]
        entry=binding if identity[2]=='single' else binding.get('gestures',{}).get(identity[2],{'action':{'kind':'noop'}})
        action=entry['action']
        if action['kind']=='noop':return
        if phase=='press' and not held_action(action):return
        if phase=='tap' and held_action(action):return
        if phase=='press':
            _,physical,_=trigger(config,*identity)
            if identity in self.held or not key_down(physical[3:]):return
        modifiers_clear()
        address=focus_app(layer['app'])
        # Never fall through to a different app when focusing failed or raced.
        if query('activewindow').get('address')!=address:raise ValueError('Focus changed; input was not sent')
        if phase=='press':
            if not key_down(physical[3:]):return
            code=KEYS[action['key']]
            if not any(h['code']==code for h in self.held.values()):self.keyboard.event(code,1)
            self.held[identity]={'code':code,'physical':physical[3:],'since':time.monotonic()}
        elif action['kind'] in ('key','keybind'):self.keyboard.tap(action)
        else:execute(action)
        return {'handled':True,'layer':identity[0],'control':identity[1],'gesture':identity[2],'app':layer['app'],'time':time.time()}

    def expire_releases(self):
        for identity,held in list(self.held.items()):
            if time.monotonic()-held['since']>120 or not key_down(held['physical']):self.release(identity)


def plugin_enabled():
    settings=json.loads((Path.home()/'.config/omarchy/shell.json').read_bytes())
    plugin='fraction12.codex-micro'
    entries=list(settings.get('plugins',[]))
    for section in settings.get('bar',{}).get('layout',{}).values():
        if isinstance(section,list):entries.extend(section)
    return plugin not in settings.get('disabledPlugins',[]) and any((e.get('id') if isinstance(e,dict) else e)==plugin for e in entries)


def serve(config_path):
    lock=os.open(str(SOCKET)+'.lock',os.O_CREAT|os.O_RDWR,0o600)
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    keyboard=None
    try:
        keyboard=Keyboard();dispatch=Dispatcher(keyboard,config_path)
        with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as server:
            SOCKET.unlink(missing_ok=True);server.bind(str(SOCKET));SOCKET.chmod(0o600);server.settimeout(.25)
            def stop(*_):raise SystemExit
            signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
            print(json.dumps({'ready':True}),flush=True)
            last_notice=0
            while True:
                try:
                    try:
                        message=json.loads(server.recv(4096));result=dispatch.handle(message)
                        if result:
                            from .storage import STATE
                            STATE.mkdir(parents=True,exist_ok=True)
                            temp=STATE/'.last-app-action.tmp'
                            temp.write_text(json.dumps(result)+'\n');temp.chmod(0o600);temp.replace(STATE/'last-app-action.json')
                            print(json.dumps(result),flush=True)
                    except socket.timeout:pass
                    dispatch.expire_releases()
                except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as error:
                    keyboard.release_all();dispatch.held.clear()
                    print(json.dumps({'error':str(error)}),flush=True)
                    if time.monotonic()-last_notice>3:
                        subprocess.Popen(['notify-send','-a','Codex Micro','Action not sent',str(error)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                        last_notice=time.monotonic()
    finally:
        if keyboard:keyboard.close()
        SOCKET.unlink(missing_ok=True);os.close(lock)
