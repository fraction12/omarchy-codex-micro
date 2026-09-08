"""Strict user configuration and a preserving compiler for device keymap v1."""
import copy
import hashlib
from .native import actions_for, VALID_KEYS
import json
from dataclasses import dataclass

CONTROL_NAMES=tuple([f'key{i:02}' for i in range(13)]+['dial_left','dial_right','dial_press','stick_up','stick_right','stick_down','stick_left'])
GESTURE_CONTROLS=tuple(n for n in CONTROL_NAMES if n.startswith('key') or n=='dial_press')
PREFIX='Omarchy Micro / '

@dataclass(frozen=True)
class Binding:
    label: str
    action: dict


def exact(value, required, optional=()):
    if not isinstance(value,dict) or not set(required)<=value.keys() or value.keys()-set(required)-set(optional):
        raise ValueError(f'Expected fields {required}; optional {optional}')


def validate_config(config):
    exact(config,('version','profile','layers'),('$schema','quick_micro'))
    if 'quick_micro' in config and type(config['quick_micro']) is not bool:raise ValueError('quick_micro must be a boolean')
    if type(config['version']) is not int or config['version']!=1: raise ValueError('Unsupported config version')
    if type(config['profile']) is not int or config['profile']<0: raise ValueError('Invalid profile ID')
    if not isinstance(config['layers'],dict) or set(config['layers'])!={'2','3'}: raise ValueError('Only layers 2 and 3 may be configured')
    for number, layer in config['layers'].items():
        exact(layer,('name','bindings'),('app',))
        if 'app' in layer and (not isinstance(layer['app'],str) or not 1<=len(layer['app'])<=256 or any(ord(c)<32 for c in layer['app'])):raise ValueError('Invalid app window class')
        if not isinstance(layer['name'],str) or not 1<=len(layer['name'])<=40: raise ValueError('Invalid layer name')
        if not isinstance(layer['bindings'],dict) or layer['bindings'].keys()-set(CONTROL_NAMES): raise ValueError('Unknown control')
        for control,b in layer['bindings'].items():
            exact(b,('label','action'),('gestures',))
            gestures=b.get('gestures',{})
            exact(gestures,(),('double','tap_hold'))
            if 'gestures' in b and control not in GESTURE_CONTROLS: raise ValueError('Gestures require a key or dial press')
            for gesture in gestures.values():
                exact(gesture,('label','action'))
                if not isinstance(gesture['action'],dict) or gesture['action'].get('kind') not in ('keybind','key','noop'): raise ValueError('Gestures require a keyboard key or Omarchy shortcut')
                nested={'version':1,'profile':config['profile'],'layers':{'2':{'name':'Gesture','bindings':{control:gesture}},'3':{'name':'Unused','bindings':{}}}}
                validate_config(nested)
            if not isinstance(b['label'],str) or not 1<=len(b['label'])<=100 or any(ord(c)<32 for c in b['label']): raise ValueError('Invalid label')
            a=b['action']
            if not isinstance(a,dict): raise ValueError('Action must be an object')
            kind=a.get('kind')
            if kind=='noop': exact(a,('kind',))
            elif kind=='key':
                exact(a,('kind','key'),('modifiers',))
                if not isinstance(a['key'],str) or a['key'] not in VALID_KEYS: raise ValueError('Unsupported keyboard key')
                actions_for(a.get('modifiers',[]),a['key'])
            elif kind=='keybind':
                exact(a,('kind','binding','modifiers','key'))
                if not isinstance(a['binding'],str) or not a['binding']: raise ValueError('Missing native binding')
                actions_for(a['modifiers'],a['key'])
            elif kind=='exec':
                exact(a,('kind','argv'))
                argv=a['argv']
                if not isinstance(argv,list) or not argv or any(not isinstance(s,str) or '\0' in s for s in argv) or not argv[0]: raise ValueError('exec.argv must be a nonempty string array')
            elif kind=='focus':
                exact(a,('kind','direction'))
                if a['direction'] not in ('l','r','u','d'): raise ValueError('Invalid direction')
            elif kind=='workspace':
                exact(a,('kind','target'))
                if a['target'] not in ('e+1','e-1','previous') and not (isinstance(a['target'],str) and a['target'].isdigit() and 1<=int(a['target'])<=99): raise ValueError('Invalid workspace')
            elif kind=='volume':
                exact(a,('kind','delta'))
                if type(a['delta']) is not int or not -10<=a['delta']<=10 or a['delta']==0: raise ValueError('Volume delta must be -10..-1 or 1..10')
            elif kind=='herdr_workspace':
                exact(a,('kind','label'))
                if not isinstance(a['label'],str) or not a['label']: raise ValueError('Missing Herdr workspace label')
            else: raise ValueError(f'Unknown action kind: {kind}')
    from .routing import entries,trigger
    routed=list(entries(config))
    reserved={(tuple(sorted(mods)),key) for n,c,g,b in routed if b['action']['kind']!='noop' for mods,key,_ in [trigger(config,n,c,g)]}
    for _,_,_,binding in routed:
        action=binding['action']
        if action['kind'] in ('key','keybind') and (tuple(sorted(action.get('modifiers',[]))),action['key']) in reserved:
            raise ValueError('Shortcut conflicts with a private app-layer trigger')
    return config


def shortcut(layer, control):
    index = CONTROL_NAMES.index(control)
    # Keep every macro away from Linux's Ctrl+Alt+F1..F12 VT switching.
    modifiers = ['SUPER'] + (['CTRL'] if index >= 10 else []) + (['SHIFT'] if layer == 3 else [])
    return modifiers, 13 + index % 10


def chord(layer,control):
    modifiers, key = shortcut(layer, control)
    # evdev KEY_F13=183; XKB/Hyprland keycodes add 8.
    return ' + '.join(modifiers + [f'code:{191 + key - 13}'])


def key_actions(layer,control):
    names, key = shortcut(layer, control)
    codes = {'SUPER':'KC_LGUI', 'CTRL':'KC_LCTL', 'SHIFT':'KC_LSFT'}
    modifiers = [codes[name] for name in names]
    return ([{'kc':k,'delay':0,'act':1} for k in modifiers]
            +[{'kc':f'KC_F{key}','delay':0,'act':2}]
            +[{'kc':k,'delay':0,'act':0} for k in reversed(modifiers)])


def profile_of(keymap,profile):
    if keymap.get('version')!=1 or not isinstance(keymap.get('profiles'),list): raise ValueError('Unsupported device keymap')
    found=[p for p in keymap['profiles'] if p.get('id')==profile]
    if len(found)!=1: raise ValueError('Target profile missing or ambiguous')
    if len({p.get('id') for p in keymap['profiles']})!=len(keymap['profiles']): raise ValueError('Duplicate profile IDs')
    layers=found[0].get('layers',[])
    if len({l.get('id') for l in layers})!=len(layers) or not any(l.get('id')==0 for l in layers): raise ValueError('Missing protected layer or duplicate layers')
    return found[0]


def compile_keymap(original,config):
    validate_config(config)
    result=copy.deepcopy(original)
    profile=profile_of(result,config['profile'])
    from .quick_micro import unwrap,wrap
    unwrap(result,config['profile'])
    multi_reclaim=reclaimable_multi_actions(result,config['profile'])
    result['multiActions']=[m for m in result.get('multiActions',[]) if m['id'] not in multi_reclaim]
    if 'multiActionsUsed' in profile: profile['multiActionsUsed']=[i for i in profile['multiActionsUsed'] if i not in multi_reclaim]
    reclaim=reclaimable_macros(result,config['profile'])
    result['macros']=[m for m in result.get('macros',[]) if m['id'] not in reclaim]
    profile['macrosUsed']=[i for i in profile.get('macrosUsed',[]) if i not in reclaim]
    macros=result.setdefault('macros',[])
    if len({m['id'] for m in macros})!=len(macros): raise ValueError('Duplicate macro IDs')
    occupied={m['id'] for m in macros}
    used=set(profile.get('macrosUsed',[]))
    multis=result.setdefault('multiActions',[])
    if len({m['id'] for m in multis})!=len(multis): raise ValueError('Duplicate multi-action IDs')
    multi_used=set(profile.get('multiActionsUsed',[]))

    def compile_action(action,number,control,gesture='single'):
        if action['kind']=='noop': return 'KC_NONE'
        if config['layers'][str(number)].get('app'):
            from .routing import trigger
            mods,key,held=trigger(config,number,control,gesture)
            if held:return key
            actions=actions_for(mods,key)
        elif action['kind'] in ('key','keybind'):
            if not action.get('modifiers'): return action['key']
            actions=actions_for(action['modifiers'],action['key'])
        else: actions=key_actions(number,control)
        digest=hashlib.sha256(json.dumps(actions,sort_keys=True).encode()).hexdigest()[:16]
        name=f'{PREFIX}P{config["profile"]} shortcut {digest}'
        matching=[m for m in macros if m.get('name')==name and m.get('actions')==actions]
        if matching: macro=matching[0]
        else:
            next_id=next((i for i in range(256) if i not in occupied),None)
            if next_id is None: raise ValueError('Macro ID limit reached')
            macro={'id':next_id,'name':name,'color':None,'actions':actions}
            occupied.add(next_id); macros.append(macro)
        used.add(macro['id'])
        return 'KA_A'+str(macro['id'])

    for number,layer_config in config['layers'].items():
        number=int(number)
        mapped={}
        for control in CONTROL_NAMES:
            binding=layer_config['bindings'].get(control,{'action':{'kind':'noop'}})
            mapped[control]=compile_action(binding['action'],number,control)
            gestures=binding.get('gestures',{})
            if not any(b['action']['kind']!='noop' for b in gestures.values()): continue
            branches={field:compile_action(gestures.get(g,{'action':{'kind':'noop'}})['action'],number,control,g)
                      for g,field in [('double','kcOnDoubleTap'),('tap_hold','kcOnTapHold')]}
            payload={'kcOnTap':mapped[control],'kcOnHold':mapped[control],**branches,'tt':250}
            name=f'{PREFIX}P{config["profile"]} gesture '+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16]
            matching=[m for m in multis if m.get('name')==name and all(m.get(k)==v for k,v in payload.items())]
            if matching: multi=matching[0]
            else:
                next_id=next((i for i in range(256) if i not in {m['id'] for m in multis}),None)
                if next_id is None: raise ValueError('Multi-action ID limit reached')
                multi={'id':next_id,'name':name,'color':None,**payload}
                multis.append(multi)
            mapped[control]='KA_M'+str(multi['id']);multi_used.add(multi['id'])
        existing=next((l for l in profile['layers'] if l['id']==number-1),None)
        layer=existing if existing is not None else {'id':number-1}
        if existing is None: profile['layers'].append(layer)
        layer.setdefault('name',f'Layer {number}')
        # Physical device verified: up .75, left .5, down .25, right 0.
        layer['layout']={'keymap':[[mapped[f'key{i:02}'] for i in row] for row in [[0,1],[2,3,4,5],[6,7,8,9],[10,11,12]]],
                         'encoders':[[mapped[n] for n in ('dial_right','dial_left','dial_press')]],
                         'joystick':{'type':'RADIAL','sectors':[{'k':mapped[n],'a1':a,'a2':b} for n,a,b in [('stick_up',.625,.875),('stick_left',.375,.625),('stick_down',.125,.375),('stick_right',.875,.125)]]}}
    profile['macrosUsed']=sorted(used)
    if multi_used or 'multiActionsUsed' in profile: profile['multiActionsUsed']=sorted(multi_used)
    if config.get('quick_micro'):wrap(result,config['profile'])
    check_preserved(original,result,config['profile'])
    return result


def reclaimable_multi_actions(keymap,profile):
    """Keep foreign actions and any owned action reachable from protected data."""
    import re
    owned={m['id']:m for m in keymap.get('multiActions',[]) if m.get('name','').startswith(f'{PREFIX}P{profile} ')}
    protected=copy.deepcopy(keymap)
    target=profile_of(protected,profile)
    target['layers']=[l for l in target['layers'] if l['id'] not in (1,2)]
    target.pop('multiActionsUsed',None)
    protected['multiActions']=[m for m in protected.get('multiActions',[]) if m['id'] not in owned]
    referenced={int(i) for i in re.findall(r'KA_M(\d+)',json.dumps(protected))}
    for p in protected['profiles']:
        if p['id']!=profile: referenced.update(p.get('multiActionsUsed',[]))
    # Group membership is protected even if no layer currently uses the action.
    for group in keymap.get('multiActionsGroups',[]): referenced.update(group.get('actionIds',[]))
    while True:
        expanded=referenced|{int(i) for mid in referenced if mid in owned for i in re.findall(r'KA_M(\d+)',json.dumps(owned[mid]))}
        if expanded==referenced: break
        referenced=expanded
    return set(owned)-referenced


def reclaimable_macros(keymap,profile):
    protected=copy.deepcopy(keymap)
    target=profile_of(protected,profile)
    target['layers']=[l for l in target['layers'] if l['id'] not in (1,2)]
    target.pop('macrosUsed',None)
    protected.pop('macros',None)
    text=json.dumps(protected)
    import re
    referenced={int(i) for i in re.findall(r'KA_A(\d+)',text)}
    for p in protected['profiles']:
        if p['id']!=profile: referenced.update(p.get('macrosUsed',[]))
    return {m['id'] for m in keymap.get('macros',[]) if m.get('name','').startswith(f'{PREFIX}P{profile} ') and m['id'] not in referenced}


def check_preserved(before,after,profile):
    def protected(value):
        result=copy.deepcopy(value)
        from .quick_micro import unwrap
        unwrap(result,profile)
        multi_reclaim=reclaimable_multi_actions(result,profile)
        result['multiActions']=[m for m in result.get('multiActions',[]) if m['id'] not in multi_reclaim]
        target=profile_of(result,profile)
        if 'multiActionsUsed' in target:
            target['multiActionsUsed']=[i for i in target['multiActionsUsed'] if i not in multi_reclaim]
            if not target['multiActionsUsed']: target.pop('multiActionsUsed')
        reclaim=reclaimable_macros(result,profile)
        p=profile_of(result,profile)
        p['layers']=[l for l in p['layers'] if l['id'] not in (1,2)]
        p['macrosUsed']=[i for i in p.get('macrosUsed',[]) if i not in reclaim]
        result['macros']=[m for m in result.get('macros',[]) if m['id'] not in reclaim]
        return result
    if protected(before)!=protected(after): raise ValueError('Change outside layers 2 and 3 or their private generated macros')
