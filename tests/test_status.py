import errno
import unittest
from unittest.mock import patch
from codex_micro.cli import read_status
from codex_micro.transport import Device, DeviceBusy


class StatusTests(unittest.TestCase):
    def status_error(self, error):
        with patch('codex_micro.cli.devices', return_value=[{}]), patch('codex_micro.cli.Device', side_effect=error):
            return read_status()

    def test_busy_is_not_disconnected(self):
        self.assertEqual(self.status_error(DeviceBusy('busy')), {'status':'busy','connected':None})

    def test_missing_device_is_disconnected(self):
        with patch('codex_micro.cli.devices', return_value=[]):
            self.assertEqual(read_status(), {'status':'disconnected','connected':False})
        self.assertFalse(self.status_error(OSError(errno.ENODEV, 'removed'))['connected'])

    def test_timeout_is_unresponsive(self):
        result=self.status_error(TimeoutError('no reply'))
        self.assertEqual(result['status'], 'unresponsive')
        self.assertIsNone(result['connected'])

    def test_permission_and_io_errors_are_not_busy_or_disconnected(self):
        for error in (PermissionError('denied'), OSError(errno.EIO,'I/O error'), BlockingIOError('write queue full')):
            with self.subTest(error=error):
                result=self.status_error(error)
                self.assertEqual(result['status'],'unavailable')
                self.assertIsNone(result['connected'])

    def test_success_recovers(self):
        with patch('codex_micro.cli.devices',return_value=[{}]), patch('codex_micro.cli.Device') as factory:
            d=factory.return_value.__enter__.return_value
            d.identity={'transport':'bluetooth'}
            d.call.return_value={'battery':98}
            self.assertEqual(read_status(), {'status':'connected','connected':True,'battery':98,'device':d.identity})

    def test_only_lock_contention_becomes_device_busy_and_releases_fd(self):
        with patch('codex_micro.transport.devices',return_value=[{'path':'/dev/mock'}]), patch('codex_micro.transport.os.open',return_value=123), patch('codex_micro.transport.os.close') as close, patch('codex_micro.transport.fcntl.flock',side_effect=BlockingIOError(errno.EAGAIN,'busy')):
            with self.assertRaises(DeviceBusy): Device()
            close.assert_called_once_with(123)
