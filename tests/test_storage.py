import unittest
from unittest.mock import patch
from codex_micro.storage import verified_write

class TransactionTests(unittest.TestCase):
    def test_stale_read_prevents_write(self):
        with patch('codex_micro.storage.read_files',return_value={'changed':b'x'}), patch('codex_micro.storage.write_keymap') as write:
            with self.assertRaises(ValueError): verified_write(None,{'keymap.json':b'a'},b'b')
            write.assert_not_called()
    def test_readback_failure_rolls_back(self):
        before={'keymap.json':b'a','smart_actions.json':b's'}
        wrong={'keymap.json':b'bad','smart_actions.json':b's'}
        with patch('codex_micro.storage.read_files',side_effect=[before,wrong,wrong,before]), patch('codex_micro.storage.write_keymap') as write:
            with self.assertRaisesRegex(RuntimeError,'verified restored'):verified_write(None,before,b'b')
            self.assertEqual([c.args[1] for c in write.call_args_list],[b'b',b'a'])
    def test_success_preserves_smart_actions(self):
        before={'keymap.json':b'a','smart_actions.json':b's'}
        after={'keymap.json':b'b','smart_actions.json':b's'}
        with patch('codex_micro.storage.read_files',side_effect=[before,after]), patch('codex_micro.storage.write_keymap'):
            self.assertEqual(verified_write(None,before,b'b'),after)
