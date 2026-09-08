"""Exact-byte snapshots and verified single-file device transactions."""
import base64
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

STATE=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'omarchy-codex-micro'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def read_files(device):
    listing=device.call('fs.list',{'checksum':True})
    result={}
    for name in ('keymap.json','smart_actions.json'):
        metadata=next((x for x in listing if x['name']==name),None)
        if not metadata: raise ValueError(f'Missing device file {name}')
        chunks=[]
        size=metadata['size']
        if type(size) is not int or not 0<size<=1024*1024: raise ValueError('Device file size is invalid')
        for offset in range(0,size,1536):
            length=min(1536,size-offset)
            answer=device.call('fs.readbin',{'file':name,'offset':offset,'len':length})
            if not isinstance(answer,dict) or answer.get('total_size')!=size or answer.get('offset')!=offset:
                raise ValueError('Unexpected fs.readbin response')
            chunk=base64.b64decode(answer['data'],validate=True)
            if len(chunk)!=length:raise ValueError('Short device file read')
            chunks.append(chunk)
        raw=b''.join(chunks)
        if len(raw)!=metadata['size'] or hashlib.sha1(raw).hexdigest()!=metadata['checksum']:
            raise ValueError(f'Device file changed during read: {name}')
        json.loads(raw)
        result[name]=raw
    return result


def backup(device,status,files):
    path=STATE/'backups'/(time.strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8])
    path.mkdir(parents=True,mode=0o700)
    for name,raw in files.items():
        target=path/name
        with target.open('xb') as f: f.write(raw)
        target.chmod(0o600)
    metadata={'identity':device.identity,'status':status,'sha256':{n:sha(r) for n,r in files.items()}}
    (path/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (path/'manifest.json').chmod(0o600)
    return path


def write_keymap(device,raw):
    # Firmware 0.6.2 rejects fs.txbegin. Use the vendor single-file upload.
    # completed publishes the final chunk; caller backs up and verifies/rolls back.
    for offset in range(0,len(raw),1536):
        chunk=raw[offset:offset+1536]
        device.call('fs.writebin',{'file':'keymap.json','data':base64.b64encode(chunk).decode(),
                                 'append':True,'completed':offset+len(chunk)==len(raw),'offset':offset})


def verified_write(device,before,candidate):
    # Caller holds the plugin lock and has already made an immutable backup.
    if read_files(device)!=before: raise ValueError('Configuration changed after planning; not applied')
    try:
        write_keymap(device,candidate)
        after=read_files(device)
        if after['keymap.json']!=candidate or after['smart_actions.json']!=before['smart_actions.json']:
            raise ValueError('Device readback differs from expected configuration')
        return after
    except Exception as original_error:
        try:
            current=read_files(device)
            if current['keymap.json']!=before['keymap.json']:
                write_keymap(device,before['keymap.json'])
            if read_files(device)!=before: raise ValueError('Rollback readback mismatch')
        except Exception as rollback_error:
            raise RuntimeError(f'Apply failed: {original_error}; rollback not verified: {rollback_error}. Use the saved backup after reconnecting.') from original_error
        raise RuntimeError(f'Apply failed; original configuration verified restored: {original_error}') from original_error
