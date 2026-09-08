"""Discover live Omarchy shortcuts and encode them as device HID keys."""
import ctypes as C
import json
import re
import subprocess

MODS = {64: 'SUPER', 4: 'CTRL', 8: 'ALT', 1: 'SHIFT'}
MOD_KEYS = {'SUPER':'KC_LGUI', 'CTRL':'KC_LCTL', 'ALT':'KC_LALT', 'SHIFT':'KC_LSFT'}
# Linux evdev positions -> firmware key names. XKB keycodes add eight.
EVDEV = {}
for start, names in [(2,'1 2 3 4 5 6 7 8 9 0'),(16,'Q W E R T Y U I O P'),(30,'A S D F G H J K L'),(44,'Z X C V B N M')]:
    EVDEV.update({start+i:'KC_'+n for i,n in enumerate(names.split())})
EVDEV.update({1:'KC_ESC',12:'KC_MINS',13:'KC_EQL',14:'KC_BSPC',15:'KC_TAB',26:'KC_LBRC',27:'KC_RBRC',28:'KC_ENT',39:'KC_SCLN',40:'KC_QUOT',41:'KC_GRV',43:'KC_BSLS',51:'KC_COMM',52:'KC_DOT',53:'KC_SLSH',55:'KC_PAST',57:'KC_SPC',58:'KC_CAPS',69:'KC_NUM',70:'KC_SCRL',71:'KC_P7',72:'KC_P8',73:'KC_P9',74:'KC_PMNS',75:'KC_P4',76:'KC_P5',77:'KC_P6',78:'KC_PPLS',79:'KC_P1',80:'KC_P2',81:'KC_P3',82:'KC_P0',83:'KC_PDOT',96:'KC_PENT',98:'KC_PSLS',99:'KC_PSCR',102:'KC_HOME',103:'KC_UP',104:'KC_PGUP',105:'KC_LEFT',106:'KC_RGHT',107:'KC_END',108:'KC_DOWN',109:'KC_PGDN',110:'KC_INS',111:'KC_DEL',119:'KC_PAUS'})
EVDEV.update({59+i:'KC_F'+str(i+1) for i in range(10)})
EVDEV.update({87:'KC_F11',88:'KC_F12'})
EVDEV.update({183+i:'KC_F'+str(i+13) for i in range(12)})
MEDIA = {'XF86AudioRaiseVolume':'KC_VOLU','XF86AudioLowerVolume':'KC_VOLD','XF86AudioMute':'KC_MUTE','XF86AudioMicMute':'KC_F20','XF86MonBrightnessUp':'KC_BRIU','XF86MonBrightnessDown':'KC_BRID','XF86AudioPlay':'KC_MPLY','XF86AudioPause':'KC_MPLY','XF86AudioNext':'KC_MNXT','XF86AudioPrev':'KC_MPRV','XF86AudioStop':'KC_MSTP'}
VALID_KEYS = set(EVDEV.values()) | set(MEDIA.values())


def key_symbols(keyboard):
    """Use the Micro's configured XKB layout, rather than assuming US letters."""
    lib=C.CDLL('libxkbcommon.so.0')
    class Names(C.Structure):
        _fields_=[(n,C.c_char_p) for n in ('rules','model','layout','variant','options')]
    lib.xkb_context_new.argtypes=[C.c_int]; lib.xkb_context_new.restype=C.c_void_p
    lib.xkb_keymap_new_from_names.argtypes=[C.c_void_p,C.POINTER(Names),C.c_int]; lib.xkb_keymap_new_from_names.restype=C.c_void_p
    lib.xkb_keymap_key_get_syms_by_level.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.POINTER(C.c_uint))]
    lib.xkb_keysym_get_name.argtypes=[C.c_uint,C.c_char_p,C.c_size_t]
    lib.xkb_keymap_unref.argtypes=[C.c_void_p];lib.xkb_context_unref.argtypes=[C.c_void_p]
    ctx=lib.xkb_context_new(0)
    names=Names(*[(keyboard.get(n) or '').encode() or None for n,_ in Names._fields_])
    km=lib.xkb_keymap_new_from_names(ctx,C.byref(names),0)
    if not km:
        lib.xkb_context_unref(ctx)
        raise ValueError('Cannot read the Micro keyboard layout')
    result={}
    try:
        for code,kc in EVDEV.items():
            syms=C.POINTER(C.c_uint)()
            count=lib.xkb_keymap_key_get_syms_by_level(km,code+8,keyboard.get('active_layout_index',0),0,C.byref(syms))
            for i in range(count):
                buf=C.create_string_buffer(128);lib.xkb_keysym_get_name(syms[i],buf,128)
                result.setdefault(buf.value.decode().upper(),kc)
        result.update({name.upper():kc for name,kc in MEDIA.items()})
        return result
    finally:
        lib.xkb_keymap_unref(km);lib.xkb_context_unref(ctx)


def actions_for(modifiers,key):
    if not isinstance(modifiers,list) or len(modifiers)!=len(set(modifiers)) or any(m not in MOD_KEYS for m in modifiers):
        raise ValueError('Invalid shortcut modifiers')
    if key not in VALID_KEYS: raise ValueError('Unsupported firmware key')
    if 'CTRL' in modifiers and 'ALT' in modifiers and re.fullmatch(r'KC_F(?:[1-9]|1[0-2])',key):
        raise ValueError('Virtual-console shortcuts cannot be assigned')
    keys=[MOD_KEYS[m] for m in modifiers]
    return ([{'kc':k,'delay':0,'act':1} for k in keys] + [{'kc':key,'delay':0,'act':2}] + [{'kc':k,'delay':0,'act':0} for k in reversed(keys)])


def catalog():
    keyboards=json.loads(subprocess.check_output(['hyprctl','devices','-j'],text=True))['keyboards']
    keyboard=next((k for k in keyboards if 'codex-micro' in k['name']),None)
    if not keyboard: raise ValueError('Connect the Micro to read its keyboard layout')
    symbols=key_symbols(keyboard)
    raw=subprocess.check_output(['hyprctl','binds'],text=True)
    rows=[]
    for block in re.split(r'(?m)^bind',raw)[1:]:
        fields=dict(re.findall(r'^\t(\w+): ?(.*)$',block,re.M))
        flags=block.splitlines()[0]
        fields['flags']=flags;rows.append(fields)
    # The native menu repairs missing code: keys in this Hyprland Lua version.
    display=subprocess.check_output(['omarchy-menu-keybindings','--print'],text=True)
    fallback={}
    for line in display.splitlines():
        if '→' not in line:continue
        combos,desc=line.split('→',1)
        fallback.setdefault(desc.strip(),[]).extend(c.strip() for c in combos.split(' / '))
    options={}; omitted=[]
    for b in rows:
        desc=b.get('description','')
        if desc.startswith('Micro: ') or not desc or b.get('submap') or 'm' in b['flags'] or 'l' in b['flags'] and b.get('key','').startswith('mouse:'):continue
        mask=int(b.get('modmask',0));mods=[m for bit,m in MODS.items() if mask & bit]
        if mask & ~sum(MODS): omitted.append(desc);continue
        key=b.get('key','').split(' + ')[-1]
        if not key and int(b.get('keycode','0')):key='code:'+b['keycode']
        if not key:
            for combo in fallback.get(desc,[]):
                parts=combo.split(' + ')
                if len(parts)==2 and set(parts[0].split())==set(mods):key=parts[-1];break
        kc=EVDEV.get(int(key[5:])-8) if re.fullmatch(r'code:\d+',key) else symbols.get(key.upper())
        if not kc:omitted.append(desc);continue
        try: actions_for(mods,kc)
        except ValueError:omitted.append(desc);continue
        combo=' + '.join(mods+[key])
        # Release/start pairs share one physical shortcut; retain both descriptions.
        if combo in options:
            options[combo]['requiresRelease'] = options[combo].get('requiresRelease',False) or 'r' in b['flags']
            if desc not in options[combo]['description']: options[combo]['description']+=' / '+desc
            continue
        options[combo]={'requiresRelease':'r' in b['flags'],'value':combo,'label':desc+' · '+combo,'description':desc,'action':{'kind':'keybind','binding':combo,'modifiers':mods,'key':kc}}
    return {'options':display_options(list(options.values())),'omitted':sorted(set(omitted)), 'layout':keyboard['active_keymap']}


def display_options(options):
    from collections import Counter
    counts=Counter(o['description'].casefold() for o in options)
    return sorted([{**o,'label':o['description'] + (' · '+o['value'] if counts[o['description'].casefold()]>1 else '')} for o in options],key=lambda x:(x['description'].casefold(),x['value']))


def keyboard_options():
    names={'ENT':'Enter','BSPC':'Backspace','TAB':'Tab','ESC':'Escape','SPC':'Space',
           'DEL':'Delete','INS':'Insert','HOME':'Home','END':'End','PGUP':'Page Up','PGDN':'Page Down',
           'UP':'Up arrow','DOWN':'Down arrow','LEFT':'Left arrow','RGHT':'Right arrow',
           'CAPS':'Caps Lock','NUM':'Num Lock','SCRL':'Scroll Lock','PSCR':'Print Screen','PAUS':'Pause',
           'MINS':'Minus','EQL':'Equals','LBRC':'Left bracket','RBRC':'Right bracket',
           'BSLS':'Backslash','SCLN':'Semicolon','QUOT':'Quote','GRV':'Backtick','COMM':'Comma','DOT':'Period','SLSH':'Slash',
           'PENT':'Numpad Enter','PAST':'Numpad Multiply','PSLS':'Numpad Divide','PMNS':'Numpad Minus','PPLS':'Numpad Plus','PDOT':'Numpad Decimal',
           'VOLU':'Volume Up key','VOLD':'Volume Down key','MUTE':'Mute key','BRIU':'Brightness Up key','BRID':'Brightness Down key',
           'MPLY':'Play / Pause key','MNXT':'Next Track key','MPRV':'Previous Track key','MSTP':'Stop Media key'}
    names.update({'P'+str(i):'Numpad '+str(i) for i in range(10)})
    rows=[]
    for key in VALID_KEYS:
        name=names.get(key[3:],key[3:])
        rows.append({'value':'key:'+key,'label':name,'description':name,'action':{'kind':'key','key':key}})
    return sorted(rows,key=lambda o:o['label'].casefold())


def configured_chord_options(config):
    """Keep typed application chords selectable without claiming OS ownership."""
    options={}
    for layer in config['layers'].values():
        for binding in layer['bindings'].values():
            for entry in [binding,*binding.get('gestures',{}).values()]:
                action=entry['action']
                if action['kind']!='key' or not action.get('modifiers'):continue
                value='key:'+'+'.join(action['modifiers'])+':'+action['key']
                options.setdefault(value,{'value':value,'label':entry['label'],'description':entry['label'],'action':action})
    return list(options.values())
