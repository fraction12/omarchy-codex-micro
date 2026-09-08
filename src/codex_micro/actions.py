"""Host actions use argument vectors; never shell-evaluate configuration text."""
import json
import os
import subprocess
from pathlib import Path


def argv_for(action):
    kind=action['kind']
    if kind=='noop': return None
    if kind=='exec':
        return [str(Path(a).expanduser()) if a.startswith('~/') else a for a in action['argv']]
    if kind=='focus': return ['hyprctl','dispatch','hl.dsp.focus({ direction = '+json.dumps(action['direction'])+' })']
    if kind=='workspace':return ['hyprctl','dispatch','hl.dsp.focus({ workspace = '+json.dumps(action['target'])+' })']
    if kind=='volume':return ['wpctl','set-volume','-l','1.0','@DEFAULT_AUDIO_SINK@',f'{abs(action["delta"])}%'+('+' if action['delta']>0 else '-')]
    if kind=='herdr_workspace':
        # Explicit local default server: strip inherited pane targeting variables.
        env={k:v for k,v in os.environ.items() if not k.startswith('HERDR_')}
        data=json.loads(subprocess.check_output(['herdr','workspace','list'],env=env,text=True,timeout=5))
        matches=[w for w in data['result']['workspaces'] if w.get('label')==action['label']]
        if len(matches)!=1: raise ValueError('Herdr workspace label is missing or ambiguous')
        return ['herdr','workspace','focus',matches[0]['workspace_id']]
    raise ValueError('Unsupported action')


def execute(action):
    argv=argv_for(action)
    if argv is None:return {'action':'noop'}
    env={k:v for k,v in os.environ.items() if not k.startswith('HERDR_')}
    # UI launchers may remain alive; inherit no pipe from Quickshell.
    subprocess.Popen(argv,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    return {'started':argv}
