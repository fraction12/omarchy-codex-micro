import copy,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from codex_micro.app_dispatch import Dispatcher,focus_app
from codex_micro.model import validate_config,compile_keymap
from codex_micro.cli import binding_text
from codex_micro.routing import entries,trigger,held_action
from codex_micro.editor import device_actions
from test_model import original,config

class AppRoutingTests(unittest.TestCase):
    def setUp(self):
        enabled=patch('codex_micro.app_dispatch.plugin_enabled',return_value=True)
        enabled.start();self.addCleanup(enabled.stop)

    def focused_config(self):
        c=config();c['layers']['3']={'name':'T3','app':'t3code','bindings':{'key00':{'label':'Commands','action':{'kind':'key','key':'KC_K','modifiers':['CTRL']},'gestures':{'double':{'label':'Models','action':{'kind':'key','key':'KC_M','modifiers':['CTRL','SHIFT']}}}},'key10':{'label':'Talk','action':{'kind':'key','key':'KC_F9'}}}}
        return c

    def test_target_changes_are_device_changes(self):
        c=config();other=copy.deepcopy(c);other['layers']['3']['app']='t3code'
        self.assertNotEqual(device_actions(c),device_actions(other))

    def test_compilation_routes_gestures_and_keeps_held_ptt(self):
        c=self.focused_config();validate_config(c);result=compile_keymap(original(),c)
        layer=next(l for l in result['profiles'][0]['layers'] if l['id']==2)
        multi=next(m for m in result['multiActions'] if 'KA_M'+str(m['id'])==layer['layout']['keymap'][0][0])
        self.assertNotEqual(multi['kcOnTap'],multi['kcOnDoubleTap'])
        self.assertEqual(layer['layout']['keymap'][-1][0],trigger(c,'3','key10','single')[1])
        text=binding_text(c)
        self.assertIn('route 3 key00 double tap',text)
        self.assertIn('route 3 key10 single press',text)
        self.assertIn('route 3 key10 single release',text)
        self.assertIn('locked = true',text)

    def test_private_triggers_unique_across_layers_and_gestures(self):
        c=self.focused_config();c['layers']['2']=copy.deepcopy(c['layers']['3'])
        seen=set()
        from codex_micro.routing import CONTROLS,PRESS_CONTROLS
        for n in ('2','3'):
            for control in CONTROLS:
                for g in (('single','double','tap_hold') if control in PRESS_CONTROLS else ('single',)):
                    mods,key,_=trigger(c,n,control,g);value=(tuple(mods),key)
                    self.assertNotIn(value,seen);seen.add(value)

    def run_action(self,focus_error=None,phase='tap',control='key00'):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        path=Path(directory.name)/'config.json';path.write_text(json.dumps(self.focused_config()))
        keyboard=MagicMock();d=Dispatcher(keyboard,path)
        message={'layer':'3','control':control,'gesture':'single','phase':phase,'time':time.monotonic()}
        return d,keyboard,message

    def test_focus_before_input_and_skip_on_failure(self):
        d,k,m=self.run_action()
        order=[]
        with patch('codex_micro.app_dispatch.modifiers_clear'),patch('codex_micro.app_dispatch.focus_app',side_effect=lambda _:order.append('focus') or '0x1'),patch('codex_micro.app_dispatch.query',return_value={'address':'0x1'}):
            k.tap.side_effect=lambda _:order.append('input');d.handle(m)
        self.assertEqual(order,['focus','input'])
        k.reset_mock()
        with patch('codex_micro.app_dispatch.modifiers_clear'),patch('codex_micro.app_dispatch.focus_app',side_effect=ValueError('not open')):
            with self.assertRaises(ValueError):d.handle(m)
        k.tap.assert_not_called()

    def test_focus_race_and_expired_requests_never_send(self):
        d,k,m=self.run_action()
        with patch('codex_micro.app_dispatch.modifiers_clear'),patch('codex_micro.app_dispatch.focus_app',return_value='0x1'),patch('codex_micro.app_dispatch.query',return_value={'address':'0x2'}):
            with self.assertRaises(ValueError):d.handle(m)
        k.tap.assert_not_called()
        m['time']-=10;d.handle(m);k.tap.assert_not_called()

    def test_release_works_even_if_focus_or_config_changed(self):
        d,k,m=self.run_action(phase='press',control='key10')
        with patch('codex_micro.app_dispatch.modifiers_clear'),patch('codex_micro.app_dispatch.focus_app',return_value='0x1'),patch('codex_micro.app_dispatch.query',return_value={'address':'0x1'}),patch('codex_micro.app_dispatch.key_down',return_value=True):d.handle(m)
        k.event.assert_called_with(67,1)
        d.config_path.unlink();m['phase']='release'
        d.handle(m);k.event.assert_called_with(67,0);self.assertFalse(d.held)

    def test_release_before_press_does_not_leave_key_held(self):
        d,k,m=self.run_action(phase='press',control='key10')
        with patch('codex_micro.app_dispatch.key_down',return_value=False):d.handle(m)
        k.event.assert_not_called()

    def test_already_focused_does_not_dispatch_focus(self):
        with patch('codex_micro.app_dispatch.query',return_value={'address':'0x1','class':'t3code'}),patch('codex_micro.app_dispatch.subprocess.check_output',return_value='false'),patch('codex_micro.app_dispatch.subprocess.run') as run:
            self.assertEqual(focus_app('t3code'),'0x1')
            self.assertEqual(run.call_count,1) # Only dismiss our editor, no compositor focus.

    def test_missing_app_and_open_overlay_fail_closed(self):
        with patch('codex_micro.app_dispatch.query',side_effect=[{'class':'other'},[]]),patch('codex_micro.app_dispatch.subprocess.check_output',return_value='false'),patch('codex_micro.app_dispatch.subprocess.run'):
            with self.assertRaisesRegex(ValueError,'Open t3code'):focus_app('t3code')
        with patch('codex_micro.app_dispatch.subprocess.check_output',return_value='true'),patch('codex_micro.app_dispatch.subprocess.run'):
            with self.assertRaisesRegex(ValueError,'desktop panel'):focus_app('t3code')

    def test_disabled_plugin_drops_input_but_allows_release(self):
        d,k,m=self.run_action()
        with patch('codex_micro.app_dispatch.plugin_enabled',return_value=False):d.handle(m)
        k.tap.assert_not_called()
        identity=('3','key10','single');d.held[identity]={'code':67,'physical':'F13','since':time.monotonic()}
        with patch('codex_micro.app_dispatch.key_down',return_value=False):d.expire_releases()
        k.event.assert_called_once_with(67,0)
        self.assertFalse(d.held)

    def test_shared_held_key_released_only_after_last_control(self):
        d,k,m=self.run_action()
        a=('2','key10','single');b=('3','key10','single')
        d.held={a:{'code':67},b:{'code':67}}
        d.release(a);k.event.assert_not_called()
        d.release(b);k.event.assert_called_once_with(67,0)

class HeldKeyIdentityTests(unittest.TestCase):
    def test_f13_hold_uses_xkb_code_even_when_symbol_is_xf86tools(self):
        from codex_micro.app_dispatch import key_down
        def compositor(argv,**kwargs):
            # Physical F13 is XKB 191; its active symbol is XF86Tools.
            return 'true\n' if argv[-1]=='return hl.is_key_down(191)' else 'false\n'
        with patch('codex_micro.app_dispatch.subprocess.check_output',side_effect=compositor):
            self.assertTrue(key_down('F13'))

    def test_all_private_hold_keys_use_physical_codes_and_read_release(self):
        from codex_micro.app_dispatch import key_down
        for number in range(13,25):
            with patch('codex_micro.app_dispatch.subprocess.check_output',return_value='false\n') as query:
                self.assertFalse(key_down('F'+str(number)))
                self.assertEqual(query.call_args.args[0][-1],f'return hl.is_key_down({191+number-13})')
