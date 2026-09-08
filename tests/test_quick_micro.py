import copy
import unittest
from test_model import original, config
from codex_micro.model import compile_keymap, check_preserved, validate_config
from codex_micro.editor import device_actions
from codex_micro.cli import binding_text

class QuickMicroTests(unittest.TestCase):
    def setup_map(self):
        a=original()
        a['profiles'][0]['layers'][0]['layout']['encoders']=[['KC_VOLU','KC_VOLD','KV_OAI_AG00']]
        c=config();c['quick_micro']=True
        c['layers']['3']['app']='t3code'
        for layer in c['layers'].values():
            layer['bindings']['dial_press']={'label':'Enter','action':{'kind':'key','key':'KC_ENT'},'gestures':{'double':{'label':'Backspace','action':{'kind':'key','key':'KC_BSPC'}},'tap_hold':{'label':'Tab','action':{'kind':'key','key':'KC_TAB'}}}}
        return a,c

    def test_every_layer_gets_same_global_double_without_app_route(self):
        a,c=self.setup_map();b=compile_keymap(a,c)
        doubles=[]
        for layer in b['profiles'][0]['layers']:
            code=layer['layout']['encoders'][0][2]
            multi=next(m for m in b['multiActions'] if code=='KA_M'+str(m['id']))
            doubles.append(multi['kcOnDoubleTap'])
        self.assertEqual(len(set(doubles)),1)
        macro=next(m for m in b['macros'] if doubles[0]=='KA_A'+str(m['id']))
        self.assertEqual([e['kc'] for e in macro['actions'] if e['act']==2],['KC_F24'])
        host=binding_text(c)
        self.assertIn('Quick Micro',host)
        self.assertIn('omarchy-shell shell toggle fraction12.codex-micro {}',host)
        self.assertNotIn('shell summon',host)
        self.assertNotIn('route 3 dial_press double',host)
        self.assertEqual(a['profiles'][1],b['profiles'][1])
        check_preserved(a,b,0)

    def test_disable_restores_original_dial_and_custom_double(self):
        a,c=self.setup_map();on=compile_keymap(a,c)
        self.assertEqual(on,compile_keymap(on,c))
        c['quick_micro']=False
        off=compile_keymap(on,c)
        self.assertEqual(off['profiles'][0]['layers'][0],a['profiles'][0]['layers'][0])
        reference=compile_keymap(a,c)
        # IDs may differ, but all generated resources converge on the next compile.
        self.assertEqual(off,compile_keymap(off,c))
        l=off['profiles'][0]['layers'][1]
        m=next(m for m in off['multiActions'] if 'KA_M'+str(m['id'])==l['layout']['encoders'][0][2])
        self.assertEqual(m['kcOnDoubleTap'],'KC_BSPC')
        self.assertEqual(m['kcOnTap'],'KC_ENT')
        self.assertEqual(m['kcOnTapHold'],'KC_TAB')
        self.assertNotIn('Quick Micro',binding_text(c))
        check_preserved(a,off,0)

    def test_toggle_is_typed_and_requires_device_save(self):
        a,c=self.setup_map();off=copy.deepcopy(c);off['quick_micro']=False
        self.assertNotEqual(device_actions(c),device_actions(off))
        c['quick_micro']='yes'
        with self.assertRaises(ValueError):validate_config(c)

    def test_protected_dial_and_other_codex_keys_cannot_silently_change(self):
        a,c=self.setup_map();b=compile_keymap(a,c)
        code=b['profiles'][0]['layers'][0]['layout']['encoders'][0][2]
        multi=next(m for m in b['multiActions'] if code=='KA_M'+str(m['id']))
        multi['kcOnTap']='KC_BSPC'
        with self.assertRaises(ValueError):check_preserved(a,b,0)
        b=compile_keymap(a,c)
        b['profiles'][0]['layers'][0]['layout']['keymap'][0][0]='KC_ENT'
        with self.assertRaises(ValueError):check_preserved(a,b,0)

    def test_foreign_dial_gestures_restore_and_repeated_toggles_are_bounded(self):
        a,c=self.setup_map()
        old={'id':90,'name':'Codex dial','color':None,'kcOnTap':'KV_OAI_ENC_CLK','kcOnHold':'KC_F9','kcOnDoubleTap':'KC_TAB','kcOnTapHold':'KC_ENT','tt':300}
        a['multiActions']=[old]
        a['profiles'][0]['layers'][0]['layout']['encoders'][0][2]='KA_M90'
        a['profiles'][0]['multiActionsUsed']=[90]
        b=a
        for i in range(100):
            c['quick_micro']=i%2==0
            b=compile_keymap(b,c)
            self.assertLess(len(b['multiActions']),12)
            self.assertLess(len(b['macros']),12)
        self.assertEqual(a['profiles'][0]['layers'][0],b['profiles'][0]['layers'][0])
        self.assertIn(old,b['multiActions'])
        check_preserved(a,b,0)
