"""Private device triggers for layers whose input must first focus an app."""
from .native import MOD_KEYS

GESTURES=('single','double','tap_hold')
CONTROLS=tuple([f'key{i:02}' for i in range(13)]+['dial_left','dial_right','dial_press','stick_up','stick_right','stick_down','stick_left'])
PRESS_CONTROLS=tuple([f'key{i:02}' for i in range(13)]+['dial_press'])


def entries(config):
    for number,layer in config['layers'].items():
        if not layer.get('app'):continue
        for control,binding in layer['bindings'].items():
            yield number,control,'single',binding
            for gesture,entry in binding.get('gestures',{}).items():
                if config.get('quick_micro') and control=='dial_press' and gesture=='double':continue
                yield number,control,gesture,entry


def held_action(action):
    # F9 is the stock Omarchy press/release dictation shortcut.
    return action['kind'] in ('key','keybind') and action['key']=='KC_F9' and not action.get('modifiers')


def trigger(config,layer,control,gesture):
    held=sorted((n,c,g) for n,c,g,b in entries(config) if held_action(b['action']))
    identity=(str(layer),control,gesture)
    if identity in held:
        if len(held)>12:raise ValueError('At most 12 push-to-talk bindings can use app focus')
        return [],'KC_F'+str(13+held.index(identity)),True
    offset=CONTROLS.index(control) if gesture=='single' else 20+(0 if gesture=='double' else 14)+PRESS_CONTROLS.index(control)
    index=(int(layer)-2)*48+offset
    bank=index//12
    return ['ALT']+[m for bit,m in ((1,'SUPER'),(2,'CTRL'),(4,'SHIFT')) if bank&bit], 'KC_F'+str(13+index%12),False


def combo(mods,key):
    return ' + '.join(mods+['code:'+str(191+int(key[4:])-13)])
