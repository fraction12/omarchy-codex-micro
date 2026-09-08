import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from codex_micro.editor import save_config,save_device_config
from codex_micro.native import actions_for,key_symbols
from test_model import config

class EditorTests(unittest.TestCase):
    def test_stale_save_does_not_touch_device_files(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'config.json';raw=json.dumps(config()).encode();p.write_bytes(raw)
            device=MagicMock()
            with patch('codex_micro.editor.catalog',return_value={'options':[]}),patch('codex_micro.editor.Device',return_value=device):
                with self.assertRaisesRegex(ValueError,'changed elsewhere'):
                    save_config(p,{'config':config(),'expected_sha256':'stale'})
            device.__enter__.return_value.call.assert_not_called()
            self.assertEqual(p.read_bytes(),raw)
    def test_native_shortcut_no_longer_live_is_rejected(self):
        c=config();c['layers']['2']['bindings']['key00']['action']={'kind':'keybind','binding':'SUPER + RETURN','modifiers':['SUPER'],'key':'KC_ENT'}
        with patch('codex_micro.editor.catalog',return_value={'options':[]}):
            with self.assertRaisesRegex(ValueError,'no longer exists'):
                save_device_config(Path('/unused'),{'config':c,'expected_sha256':'unused'})
    def test_console_switch_is_rejected_for_native_shortcuts_too(self):
        with self.assertRaisesRegex(ValueError,'Virtual-console'):
            actions_for(['SUPER','CTRL','ALT'],'KC_F2')
    def test_linux_multimedia_names_resolve_to_their_physical_keys(self):
        symbols=key_symbols({'layout':'us'})
        self.assertEqual(symbols['XF86LAUNCH8'],'KC_F17')
        self.assertEqual(symbols['XF86AUDIORAISEVOLUME'],'KC_VOLU')
        self.assertEqual(symbols['RETURN'],'KC_ENT')

    def test_picker_shows_chords_only_for_duplicate_names(self):
        from codex_micro.native import display_options
        rows=display_options([{'description':'Terminal','value':'SUPER + RETURN'}, {'description':'Browser','value':'SUPER + SHIFT + RETURN'}, {'description':'Browser','value':'SUPER + SHIFT + B'}])
        self.assertEqual([r['label'] for r in rows if r['description']=='Terminal'],['Terminal'])
        self.assertTrue(all(' · SUPER' in r['label'] for r in rows if r['description']=='Browser'))

    def test_names_autosave_locally_without_device_or_catalog(self):
        from codex_micro.storage import sha
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'config.json';c=config();raw=json.dumps(c).encode();p.write_bytes(raw)
            c['layers']['2']['name']='Anything I want'
            with patch('codex_micro.editor.STATE',Path(folder)/'state'),patch('codex_micro.editor.Device') as device,patch('codex_micro.editor.catalog') as catalog:
                result=save_config(p,{'config':c,'expected_sha256':sha(raw)})
            device.assert_not_called();catalog.assert_not_called()
            self.assertFalse(result['device_changed'])
            self.assertEqual(json.loads(p.read_text())['layers']['2']['name'],'Anything I want')
            self.assertEqual(result['revision'],sha(p.read_bytes()))

    def test_offline_editor_still_loads_local_layer_names(self):
        from codex_micro.editor import editor_state
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'config.json';p.write_text(json.dumps(config()))
            with patch('codex_micro.editor.catalog',side_effect=ValueError('Disconnected')):
                result=editor_state(p)
            self.assertEqual(result['config']['layers']['2']['name'],'Desktop')
            self.assertTrue(any(o['value']=='key:KC_ENT' for o in result['options']))

class PushToTalkTests(unittest.TestCase):
    def test_release_shortcut_cannot_be_a_double_tap(self):
        from codex_micro.editor import validate_release_bindings
        c=config();action={'kind':'keybind','binding':'F9','modifiers':[],'key':'KC_F9'}
        options=[{'action':action,'requiresRelease':True}]
        c['layers']['2']['bindings']['key00']['gestures']={'double':{'label':'PTT','action':action}}
        with self.assertRaisesRegex(ValueError,r'Click \+ hold'): validate_release_bindings(c,options)
        c['layers']['2']['bindings']['key00']['gestures']={'tap_hold':{'label':'PTT','action':action}}
        validate_release_bindings(c,options)

    def test_single_ptt_remains_direct_without_gestures(self):
        from codex_micro.editor import validate_release_bindings
        c=config();action={'kind':'keybind','binding':'F9','modifiers':[],'key':'KC_F9'}
        options=[{'action':action,'requiresRelease':True}]
        c['layers']['2']['bindings']['key00']['action']=action
        validate_release_bindings(c,options)
        c['layers']['2']['bindings']['key00']['gestures']={'double':{'label':'Enter','action':{'kind':'key','key':'KC_ENT'}}}
        validate_release_bindings(c,options)

    def test_raw_key_cannot_bypass_release_handling(self):
        from codex_micro.editor import validate_release_bindings
        c=config();options=[{'action':{'kind':'keybind','binding':'F9','modifiers':[],'key':'KC_F9'},'requiresRelease':True}]
        c['layers']['2']['bindings']['key00']['gestures']={'double':{'label':'F9','action':{'kind':'key','key':'KC_F9'}}}
        with self.assertRaisesRegex(ValueError,r'Click \+ hold'):validate_release_bindings(c,options)

class SaveRoundTripTests(unittest.TestCase):
    def test_keyboard_gestures_save_and_reload_without_host_handlers(self):
        import base64,hashlib,copy
        from contextlib import ExitStack
        from codex_micro.model import compile_keymap
        from codex_micro.storage import sha
        from test_model import original
        class DeviceFiles:
            identity={'serial':'test-device'}
            def __init__(self,files):self.files=files;self.buffer=bytearray()
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def call(self,method,params=None):
                if method=='device.status':return {'version':'0.6.2'}
                if method=='fs.list':return [{'name':n,'size':len(raw),'checksum':hashlib.sha1(raw).hexdigest()} for n,raw in self.files.items()]
                if method=='fs.readbin':
                    raw=self.files[params['file']];offset=params['offset']
                    return {'total_size':len(raw),'offset':offset,'data':base64.b64encode(raw[offset:offset+params['len']]).decode()}
                if method=='fs.writebin':
                    if params['offset']==0:self.buffer=bytearray()
                    self.buffer.extend(base64.b64decode(params['data']))
                    if params['completed']:self.files[params['file']]=bytes(self.buffer)
                    return {}
                raise AssertionError(method)
        with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
            home=Path(folder);p=home/'mappings.json';old=config();p.write_text(json.dumps(old))
            host=home/'.config/hypr/codex-micro.lua';host.parent.mkdir(parents=True);host.write_text('-- previous')
            before=compile_keymap(original(),old)
            device=DeviceFiles({'keymap.json':json.dumps(before).encode(),'smart_actions.json':b'{}'})
            stack.enter_context(patch('codex_micro.editor.Device',return_value=device))
            stack.enter_context(patch('codex_micro.editor.catalog',return_value={'options':[]}))
            stack.enter_context(patch('codex_micro.editor.STATE',home/'state'))
            stack.enter_context(patch('codex_micro.storage.STATE',home/'state'))
            stack.enter_context(patch('codex_micro.editor.Path.home',return_value=home))
            stack.enter_context(patch('codex_micro.editor.subprocess.run'))
            stack.enter_context(patch('codex_micro.editor.subprocess.check_output',return_value=''))
            c=copy.deepcopy(old)
            c['layers']['2']['bindings']['key00']={'label':'Enter','action':{'kind':'key','key':'KC_ENT'},'gestures':{'double':{'label':'Backspace','action':{'kind':'key','key':'KC_BSPC'}},'tap_hold':{'label':'Space','action':{'kind':'key','key':'KC_SPC'}}}}
            result=save_config(p,{'config':c,'expected_sha256':sha(p.read_bytes())})
            self.assertTrue(result['saved']);self.assertEqual(json.loads(p.read_text()),c)
            self.assertEqual(json.loads(device.files['keymap.json']),compile_keymap(before,c))
            self.assertNotIn('o.bind(',host.read_text())
            self.assertEqual(device.files['smart_actions.json'],b'{}')
            c['layers']['2']['name']='Renamed'
            result=save_config(p,{'config':c,'expected_sha256':result['revision']})
            self.assertFalse(result['device_changed'])
            self.assertEqual(json.loads(p.read_text())['layers']['2']['bindings']['key00']['gestures']['double']['action']['key'],'KC_BSPC')

class LayerHistoryTests(unittest.TestCase):
    def test_previous_setup_is_independent_per_layer(self):
        import copy
        from codex_micro.editor import previous_layer_bindings
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder);(state/'backups/a').mkdir(parents=True)
            current=config();old=copy.deepcopy(current)
            old['layers']['2']['bindings']={}
            (state/'backups/a/mappings.json').write_text(json.dumps(old))
            with patch('codex_micro.editor.STATE',state):result=previous_layer_bindings(current)
            self.assertEqual(result,{'2':{}})

    def test_layer_name_change_is_not_a_previous_key_setup(self):
        from codex_micro.editor import previous_layer_bindings
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder);(state/'config-backups').mkdir()
            current=config();old=config();old['layers']['2']['name']='Old name'
            (state/'config-backups/a.json').write_text(json.dumps(old))
            with patch('codex_micro.editor.STATE',state):self.assertEqual(previous_layer_bindings(current),{})
