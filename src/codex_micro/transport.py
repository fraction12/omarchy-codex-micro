"""Linux hidraw transport for Micro USB/Bluetooth RPC; never grabs keyboard input."""
import json
import fcntl
import os
import select
import time
import uuid
from pathlib import Path


class DeviceBusy(RuntimeError):
    """Another client owns the device; connection health is unknown."""


def frames(value):
    raw = (json.dumps(value, separators=(',', ':'), ensure_ascii=False)+'\r\n').encode()
    for offset in range(0, len(raw), 61):
        chunk = raw[offset:offset+61]
        yield bytes([6, 2, len(chunk)]) + chunk + bytes(61-len(chunk))


class Decoder:
    def __init__(self):
        self.buffer = b''

    def feed(self, packet):
        if len(packet) < 3 or packet[0:2] != bytes([6, 2]):
            return []
        size = packet[2]
        if size > 61 or len(packet) < size+3:
            raise ValueError('Invalid Micro HID report')
        self.buffer += packet[3:3+size]
        if len(self.buffer) > 4*1024*1024:
            raise ValueError('Micro response exceeds limit')
        values=[]
        while b'\n' in self.buffer:
            line,self.buffer=self.buffer.split(b'\n',1)
            if line.strip():
                values.append(json.loads(line))
        return values


def devices(sysfs=Path("/sys/class/hidraw")):
    result=[]
    for node in sorted(sysfs.glob('hidraw*')):
        try:
            uevent=(node/'device/uevent').read_text()
        except FileNotFoundError:
            continue  # Device disappeared during enumeration.
        attrs=dict(line.split('=',1) for line in uevent.splitlines() if '=' in line)
        transport={'0003:0000303A:00008360':'usb','0005:0000303A:00008360':'bluetooth'}.get(attrs.get('HID_ID','').upper())
        if transport is None: continue
        result.append({'path':'/dev/'+node.name,'name':attrs.get('HID_NAME'), 'serial':attrs.get('HID_UNIQ'), 'transport':transport})
    return result


class Device:
    def __init__(self):
        found=devices()
        if len(found)!=1:
            raise RuntimeError(f'Expected exactly one Codex Micro, found {len(found)}')
        self.identity=found[0]
        lock_dir=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))
        self.lock=os.open(lock_dir/'omarchy-codex-micro.lock',os.O_CREAT|os.O_RDWR,0o600)
        try:
            try:
                fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise DeviceBusy("Micro connection is busy") from error
            for process in Path('/proc').glob('[0-9]*'):
                if process.name==str(os.getpid()): continue
                try:
                    if process.stat().st_uid!=os.getuid(): continue
                    for handle in (process/'fd').iterdir():
                        try: target=os.readlink(handle)
                        except OSError: continue
                        if target==self.identity['path']:
                            raise DeviceBusy(f'Micro is in use by PID {process.name}; close its device connection before configuration')
                except (PermissionError,FileNotFoundError,ProcessLookupError): continue
            self.fd=os.open(self.identity['path'],os.O_RDWR|os.O_NONBLOCK)
        except BaseException:
            os.close(self.lock)
            raise
        self.decoder=Decoder()

    def close(self):
        os.close(self.fd)
        os.close(self.lock)

    def __enter__(self): return self
    def __exit__(self,*args): self.close()

    def call(self, method, params=None, timeout=8):
        request={'jsonrpc':'2.0','id':'omicro-'+uuid.uuid4().hex[:12],'method':method}
        if params is not None: request['params']=params
        for frame in frames(request):
            if os.write(self.fd,frame)!=64: raise IOError('Short HID write')
            # BLE HID writes are queued by BlueZ; bursting a whole JSON request
            # can drop reports before the next connection interval.
            if self.identity['transport']=='bluetooth': time.sleep(.04)
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if not select.select([self.fd],[],[],max(0,deadline-time.monotonic()))[0]: break
            raw=os.read(self.fd,4096)
            if not raw: raise IOError('Micro disconnected')
            for message in self.decoder.feed(raw):
                if message.get('id')!=request['id']: continue
                if 'error' in message: raise RuntimeError(str(message['error']))
                time.sleep(.05)
                return message.get('result')
        raise TimeoutError(f'Micro did not answer {method}')
