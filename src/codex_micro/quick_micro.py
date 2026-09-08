"""Reversible dial-double overlay, including the otherwise protected Codex layer."""
import copy
from .native import actions_for

MODIFIERS=['CTRL','SHIFT']
KEY='KC_F24'
COMBO='CTRL + SHIFT + code:202'


def prefix(profile):return f'Omarchy Micro / P{profile} quick dial '


def payload(keymap,code):
    if code.startswith('KA_M'):
        found=next((m for m in keymap.get('multiActions',[]) if code=='KA_M'+str(m['id'])),None)
        if found is None:raise ValueError('Dial references a missing multi-action')
        return {k:v for k,v in found.items() if k not in ('id','name')}
    return {'color':None,'kcOnTap':code,'kcOnHold':code,'kcOnDoubleTap':'KC_NONE','kcOnTapHold':'KC_NONE','tt':250}


def unwrap(keymap,profile):
    """Restore only overlays whose complete payload still matches our original."""
    target=next(p for p in keymap['profiles'] if p['id']==profile)
    for layer in target['layers']:
        encoders=layer.get('layout',{}).get('encoders',[])
        if not encoders or len(encoders[0])!=3:continue
        code=encoders[0][2]
        wrapper=next((m for m in keymap.get('multiActions',[]) if code=='KA_M'+str(m['id']) and m.get('name','').startswith(prefix(profile))),None)
        if wrapper is None:continue
        original=wrapper['name'][len(prefix(profile)):]
        if original==code:raise ValueError('Invalid Quick Micro overlay')
        expected=payload(keymap,original)
        macro=next((m for m in keymap.get('macros',[]) if wrapper.get('kcOnDoubleTap')=='KA_A'+str(m['id'])),None)
        if macro is None or macro.get('actions')!=actions_for(MODIFIERS,KEY):raise ValueError('Quick Micro shortcut changed on device')
        expected['kcOnDoubleTap']=wrapper['kcOnDoubleTap']
        if {k:v for k,v in wrapper.items() if k not in ('id','name')}!=expected:raise ValueError('Quick Micro dial changed on device')
        encoders[0][2]=original


def wrap(keymap,profile):
    target=next(p for p in keymap['profiles'] if p['id']==profile)
    macros=keymap.setdefault('macros',[])
    multis=keymap.setdefault('multiActions',[])
    def allocate(items):
        available=next((i for i in range(256) if i not in {m['id'] for m in items}),None)
        if available is None:raise ValueError('Quick Micro action ID limit reached')
        return available
    name=prefix(profile)+'shortcut'
    macro=next((m for m in macros if m.get('name')==name and m.get('actions')==actions_for(MODIFIERS,KEY)),None)
    if macro is None:
        macro={'id':allocate(macros),'name':name,'color':None,'actions':actions_for(MODIFIERS,KEY)}
        macros.append(macro)
    target['macrosUsed']=sorted(set(target.get('macrosUsed',[]))|{macro['id']})
    for layer in target['layers']:
        encoders=layer.get('layout',{}).get('encoders',[])
        if not encoders or len(encoders[0])!=3:raise ValueError('Quick Micro needs a dial in every layer')
        original=encoders[0][2]
        fields=copy.deepcopy(payload(keymap,original))
        fields['kcOnDoubleTap']='KA_A'+str(macro['id'])
        name=prefix(profile)+original
        wrapper=next((m for m in multis if m.get('name')==name and {k:v for k,v in m.items() if k not in ('id','name')}==fields),None)
        if wrapper is None:
            wrapper={'id':allocate(multis),'name':name,**fields};multis.append(wrapper)
        encoders[0][2]='KA_M'+str(wrapper['id'])
        target['multiActionsUsed']=sorted(set(target.get('multiActionsUsed',[]))|{wrapper['id']})
