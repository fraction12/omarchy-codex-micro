import unittest
from codex_micro.transport import frames, Decoder

class FramingTests(unittest.TestCase):
    def test_multiframe_unicode_roundtrip(self):
        value = {'id':'micro-test', 'result': 'héllo'*60}
        decoder = Decoder()
        result=[]
        for frame in frames(value):
            self.assertEqual(len(frame),64)
            result.extend(decoder.feed(frame))
        self.assertEqual(result,[value])
    def test_ignores_keyboard_and_debug(self):
        d=Decoder()
        self.assertEqual(d.feed(bytes([1])*64),[])
        self.assertEqual(d.feed(bytes([6,1,2,65,10])+bytes(59)),[])

class DiscoveryTests(unittest.TestCase):
    def test_usb_and_bluetooth_only_match_micro_identity(self):
        from codex_micro.transport import devices
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for i,bus in enumerate(('0003','0005','0006')):
                node=root/f'hidraw{i}'/'device';node.mkdir(parents=True)
                (node/'uevent').write_text(f'HID_ID={bus}:0000303A:00008360\nHID_NAME=Codex Micro\nHID_UNIQ=test-{i}\n')
            self.assertEqual([d['transport'] for d in devices(root)],['usb','bluetooth'])

class BluetoothPacingTests(unittest.TestCase):
    def test_bluetooth_paces_every_report(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from codex_micro.transport import Device
        d=Device.__new__(Device);d.fd=123;d.identity={'transport':'bluetooth'};d.decoder=Decoder()
        reply=next(frames({'id':'omicro-test','result':True}))
        with patch('codex_micro.transport.uuid.uuid4',return_value=SimpleNamespace(hex='test')),patch('codex_micro.transport.os.write',side_effect=lambda fd,data:len(data)) as write,patch('codex_micro.transport.select.select',return_value=([123],[],[])),patch('codex_micro.transport.os.read',return_value=reply),patch('codex_micro.transport.time.sleep') as sleep:
            self.assertTrue(d.call('test',{'data':'x'*300}))
            self.assertGreater(write.call_count,1)
            self.assertEqual(sum(c.args==(.04,) for c in sleep.call_args_list),write.call_count)
