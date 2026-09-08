import copy
import unittest
from codex_micro.model import validate_config, compile_keymap, check_preserved, CONTROL_NAMES, key_actions, chord


def original():
    return {'version':1,'activeProfileId':0,'profiles':[{'id':0,'name':'Original','layers':[{'id':0,'name':'Codex','layout':{'keymap':[['KV_OAI_AG00']]},'unknown':42},{'id':1,'name':'Old'}], 'macrosUsed':[5]},{'id':1,'layers':[{'id':0,'name':'Other'}]}], 'macros':[{'id':5,'name':'Keep','actions':[]}],'multiActions':[], 'unknown':{'keep':True}}

def config():
    return {'version':1,'profile':0,'layers':{'2':{'name':'Desktop','bindings':{'key00':{'label':'Hello','action':{'kind':'exec','argv':['notify-send','Hello']}}}},'3':{'name':'Work','bindings':{}}}}

class ModelTests(unittest.TestCase):
    def test_protected_layer(self):
        c=config(); c['layers']['1']=c['layers']['2']
        with self.assertRaises(ValueError):validate_config(c)
    def test_unknown_action_rejected(self):
        c=config(); c['layers']['2']['bindings']['key00']['action']['kind']='shell'
        with self.assertRaises(ValueError):validate_config(c)
    def test_no_string_commands(self):
        c=config(); c['layers']['2']['bindings']['key00']['action']['argv']='echo wrong'
        with self.assertRaises(ValueError):validate_config(c)
    def test_preservation_and_idempotence(self):
        a=original(); frozen=copy.deepcopy(a)
        b=compile_keymap(a,config())
        self.assertEqual(a,frozen)
        self.assertEqual(a['profiles'][0]['layers'][0],b['profiles'][0]['layers'][0])
        self.assertEqual(a['profiles'][1],b['profiles'][1])
        check_preserved(a,b,0)
        self.assertEqual(b,compile_keymap(b,config()))
    def test_catches_out_of_scope_mutation(self):
        a=original(); b=compile_keymap(a,config()); b['profiles'][0]['layers'][0]['name']='Bad'
        with self.assertRaises(ValueError):check_preserved(a,b,0)
    def test_every_control_gets_unique_chord(self):
        c=config()
        for layer in c['layers'].values():
            layer['bindings']={n:{'label':n,'action':{'kind':'exec','argv':['true']}} for n in CONTROL_NAMES}
        b=compile_keymap(original(),c)
        macros=b['macros'][1:]
        self.assertEqual(len(macros),40)
        self.assertEqual(len({str(m['actions']) for m in macros}),40)
        for m in macros:
            self.assertEqual([a['act'] for a in m['actions']].count(2),1)

    def test_no_console_switch_shortcuts(self):
        for layer in (2, 3):
            for control in CONTROL_NAMES:
                actions = key_actions(layer, control)
                self.assertFalse(any(a['kc'] in ('KC_LALT', 'KC_RALT') for a in actions))
                tapped = [a['kc'] for a in actions if a['act'] == 2]
                self.assertTrue(all(k.startswith('KC_F') and 13 <= int(k[4:]) <= 24 for k in tapped))
                self.assertNotIn('ALT', chord(layer, control))

    def test_host_binds_use_physical_codes(self):
        # Linux XKB maps F13..F18 to XF86 names; symbolic F-key binds miss them.
        self.assertEqual(chord(2, 'dial_left'), 'SUPER + CTRL + code:194')
        self.assertEqual(chord(3, 'dial_right'), 'SUPER + CTRL + SHIFT + code:195')

    def test_native_volume_needs_no_macro(self):
        c=config();c['layers']['2']['bindings']['dial_right']={'label':'Volume up','action':{'kind':'keybind','binding':'XF86AudioRaiseVolume','modifiers':[],'key':'KC_VOLU'}}
        b=compile_keymap(original(),c)
        self.assertEqual(b['profiles'][0]['layers'][1]['layout']['encoders'][0][0],'KC_VOLU')
    def test_native_terminal_and_repeated_edits_preserve_codex(self):
        c=config();c['layers']['2']['bindings']['key00']['action']={'kind':'keybind','binding':'SUPER + RETURN','modifiers':['SUPER'],'key':'KC_ENT'}
        a=original();b=compile_keymap(a,c)
        self.assertEqual(b,compile_keymap(b,c))
        for i in range(280):
            c['layers']['2']['bindings']['key00']['action']['key']='KC_A' if i%2 else 'KC_B'
            b=compile_keymap(b,c)
        self.assertEqual(a['profiles'][0]['layers'][0],b['profiles'][0]['layers'][0])
        self.assertLess(len(b['macros']),5)
    def test_protected_layer_referenced_generated_macro_is_not_reclaimed(self):
        a=original(); a['macros'].append({'id':7,'name':'Omarchy Micro / P0 kept','actions':[]})
        a['profiles'][0]['layers'][0]['layout']['keymap']=[['KA_A7']]
        b=compile_keymap(a,config())
        self.assertIn(a['macros'][-1],b['macros'])

    def test_physical_joystick_up_is_three_quarter_turn(self):
        c=config()
        for name in ('stick_up','stick_down'):
            c['layers']['2']['bindings'][name]={'label':name,'action':{'kind':'keybind','binding':name,'modifiers':[],'key':'KC_UP' if name=='stick_up' else 'KC_DOWN'}}
        b=compile_keymap(original(),c)
        sectors=b['profiles'][0]['layers'][1]['layout']['joystick']['sectors']
        self.assertIn({'k':'KC_UP','a1':.625,'a2':.875},sectors)
        self.assertIn({'k':'KC_DOWN','a1':.125,'a2':.375},sectors)

    def test_physical_dial_order(self):
        c=config()
        for control,key in [('dial_left','KC_VOLD'),('dial_right','KC_VOLU'),('dial_press','KC_MUTE')]:
            c['layers']['2']['bindings'][control]={'label':control,'action':{'kind':'keybind','binding':control,'modifiers':[],'key':key}}
        b=compile_keymap(original(),c)
        self.assertEqual(b['profiles'][0]['layers'][1]['layout']['encoders'][0],['KC_VOLU','KC_VOLD','KC_MUTE'])

    def test_display_name_changes_do_not_change_device_layout(self):
        c=config();a=compile_keymap(original(),c)
        c['layers']['2']['name']='My custom name'
        c['layers']['3']['name']='Another name'
        self.assertEqual(a,compile_keymap(a,c))

class GestureTests(unittest.TestCase):
    def gesture_config(self):
        c=config()
        c['layers']['2']['bindings']['key00']['gestures']={
            'double':{'label':'Mute','action':{'kind':'keybind','binding':'Mute','modifiers':[],'key':'KC_MUTE'}},
            'tap_hold':{'label':'Terminal','action':{'kind':'keybind','binding':'Terminal','modifiers':['SUPER'],'key':'KC_ENT'}}}
        return c

    def test_native_gesture_branches_and_preservation(self):
        c=self.gesture_config();a=original();b=compile_keymap(a,c)
        m=b['multiActions'][0]
        self.assertEqual(b['profiles'][0]['layers'][1]['layout']['keymap'][0][0],f"KA_M{m['id']}")
        self.assertEqual(m['kcOnDoubleTap'],'KC_MUTE')
        self.assertEqual(m['tt'],250)
        self.assertEqual(m['kcOnHold'],m['kcOnTap'])
        self.assertTrue(m['kcOnTapHold'].startswith('KA_A'))
        self.assertTrue(m['kcOnHold'].startswith('KA_A'))
        self.assertTrue(m['kcOnTap'].startswith('KA_A'))
        self.assertEqual(b,compile_keymap(b,c))
        check_preserved(a,b,0)

    def test_repeated_gesture_edits_and_removal_reclaim_resources(self):
        c=self.gesture_config();a=original();b=a
        for i in range(280):
            c['layers']['2']['bindings']['key00']['gestures']['tap_hold']['action']['key']='KC_A' if i%2 else 'KC_B'
            b=compile_keymap(b,c)
        self.assertEqual(len(b['multiActions']),1)
        self.assertLessEqual(len(b['macros']),3)
        del c['layers']['2']['bindings']['key00']['gestures']
        b=compile_keymap(b,c)
        self.assertEqual(b['multiActions'],[])
        self.assertEqual(len(b['macros']),2)
        check_preserved(a,b,0)

    def test_protected_multi_and_its_macro_survive(self):
        c=self.gesture_config();a=compile_keymap(original(),c)
        m=copy.deepcopy(a['multiActions'][0])
        a['profiles'][0]['layers'][0]['layout']['keymap']=[[f"KA_M{m['id']}"]]
        b=compile_keymap(a,config())
        self.assertIn(m,b['multiActions'])
        ids={x['id'] for x in b['macros']}
        self.assertIn(int(m['kcOnTap'][4:]),ids)
        self.assertIn(int(m['kcOnHold'][4:]),ids)
        check_preserved(a,b,0)

    def test_gestures_reject_rotation_and_custom_commands(self):
        c=self.gesture_config();c['layers']['2']['bindings']['dial_left']=c['layers']['2']['bindings'].pop('key00')
        with self.assertRaises(ValueError):validate_config(c)
        c=self.gesture_config();c['layers']['2']['bindings']['key00']['gestures']['tap_hold']['action']={'kind':'exec','argv':['true']}
        with self.assertRaises(ValueError):validate_config(c)

    def test_gesture_actions_trigger_upload_but_labels_do_not(self):
        from codex_micro.editor import device_actions
        c=self.gesture_config();renamed=copy.deepcopy(c)
        renamed['layers']['2']['bindings']['key00']['gestures']['tap_hold']['label']='Renamed'
        self.assertEqual(device_actions(c),device_actions(renamed))
        renamed['layers']['2']['bindings']['key00']['gestures']['tap_hold']['action']['key']='KC_B'
        self.assertNotEqual(device_actions(c),device_actions(renamed))

class KeyboardKeyTests(unittest.TestCase):
    def test_enter_backspace_and_hold_are_direct_keys(self):
        c=config();c['layers']['2']['bindings']['key00']={'label':'Enter','action':{'kind':'key','key':'KC_ENT'},'gestures':{'double':{'label':'Backspace','action':{'kind':'key','key':'KC_BSPC'}},'tap_hold':{'label':'F9','action':{'kind':'key','key':'KC_F9'}}}}
        a=compile_keymap(original(),c)
        m=a['multiActions'][0]
        self.assertEqual(m['kcOnTap'],'KC_ENT')
        self.assertEqual(m['kcOnDoubleTap'],'KC_BSPC')
        self.assertEqual(m['kcOnTapHold'],'KC_F9')
        self.assertEqual(m['kcOnHold'],'KC_ENT')
        self.assertEqual(len(a['macros']),1)
        check_preserved(original(),a,0)

    def test_unknown_raw_key_rejected(self):
        c=config();c['layers']['2']['bindings']['key00']['action']={'kind':'key','key':'KA_RESET'}
        with self.assertRaises(ValueError):validate_config(c)

class ClickHoldTests(unittest.TestCase):
    def test_click_hold_is_distinct_from_hold_and_double(self):
        c=config()
        c['layers']['2']['bindings']['key00']={'label':'Enter','action':{'kind':'key','key':'KC_ENT'},'gestures':{
            'double':{'label':'Backspace','action':{'kind':'key','key':'KC_BSPC'}},
            'tap_hold':{'label':'Tab','action':{'kind':'key','key':'KC_TAB'}}}}
        a=compile_keymap(original(),c);m=a['multiActions'][0]
        self.assertEqual(m['kcOnTap'],'KC_ENT')
        self.assertEqual(m['kcOnDoubleTap'],'KC_BSPC')
        self.assertEqual(m['kcOnHold'],'KC_ENT')
        self.assertEqual(m['kcOnTapHold'],'KC_TAB')
        self.assertEqual(a,compile_keymap(a,c))
        check_preserved(original(),a,0)

class InheritedHoldTests(unittest.TestCase):
    def test_long_press_inherits_single_with_other_gestures(self):
        for key in ('KC_ENT','KC_F9'):
            c=config();c['layers']['2']['bindings']['key00']={'label':'Single','action':{'kind':'key','key':key},'gestures':{'double':{'label':'Backspace','action':{'kind':'key','key':'KC_BSPC'}},'tap_hold':{'label':'Tab','action':{'kind':'key','key':'KC_TAB'}}}}
            result=compile_keymap(original(),c);m=result['multiActions'][0]
            self.assertEqual(m['kcOnHold'],key)
            self.assertEqual(m['kcOnTap'],key)
            self.assertEqual(m['kcOnTapHold'],'KC_TAB')

class ApplicationChordTests(unittest.TestCase):
    def test_chords_compile_to_balanced_macros_and_keep_plain_keys_direct(self):
        from codex_micro.native import actions_for, configured_chord_options
        c=config()
        binding={'label':'T3 commands','action':{'kind':'key','key':'KC_K','modifiers':['CTRL']},'gestures':{'double':{'label':'T3 models','action':{'kind':'key','key':'KC_M','modifiers':['CTRL','SHIFT']}}}}
        c['layers']['3']['bindings']={'key00':binding,'key12':{'label':'Enter','action':{'kind':'key','key':'KC_ENT'}}}
        validate_config(c)
        result=compile_keymap(original(),c)
        for mods,key in [(['CTRL'],'KC_K'),(['CTRL','SHIFT'],'KC_M')]:
            self.assertTrue(any(m['actions']==actions_for(mods,key) for m in result['macros']))
        self.assertEqual(result['profiles'][0]['layers'][-1]['layout']['keymap'][-1][-1],'KC_ENT')
        self.assertEqual([o['value'] for o in configured_chord_options(c)],['key:CTRL:KC_K','key:CTRL+SHIFT:KC_M'])
        check_preserved(original(),result,0)

    def test_chords_reject_invalid_modifiers_and_console_switches(self):
        c=config()
        for mods,key in [(['bad'],'KC_K'),(['CTRL','CTRL'],'KC_K'),(['CTRL','ALT'],'KC_F1')]:
            c['layers']['3']['bindings']={'key00':{'label':'Bad','action':{'kind':'key','key':key,'modifiers':mods}}}
            with self.assertRaises(ValueError):validate_config(c)
