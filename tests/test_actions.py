import unittest
from codex_micro.actions import argv_for

class ActionCommandTests(unittest.TestCase):
    def test_focus_uses_supported_lua_dispatch_command(self):
        self.assertEqual(argv_for({'kind':'focus','direction':'l'}),['hyprctl','dispatch','hl.dsp.focus({ direction = "l" })'])
    def test_workspace_uses_supported_lua_dispatch_command(self):
        self.assertEqual(argv_for({'kind':'workspace','target':'previous'}),['hyprctl','dispatch','hl.dsp.focus({ workspace = "previous" })'])
