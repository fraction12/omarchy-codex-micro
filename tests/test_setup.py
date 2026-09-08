import json,tempfile,unittest
from pathlib import Path
from codex_micro.configuration import initialize
from test_model import config

class SetupTests(unittest.TestCase):
    def test_first_install_creates_private_config_from_valid_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            default=Path(d)/'default.json';default.write_text(json.dumps(config()))
            target=Path(d)/'user'/'mappings.json'
            self.assertTrue(initialize(target,default))
            self.assertEqual(json.loads(target.read_text()),config())
            self.assertEqual(target.stat().st_mode & 0o777,0o600)
    def test_updates_preserve_existing_personal_config_exactly(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'mappings.json';original=b'personal content\n';target.write_bytes(original)
            self.assertFalse(initialize(target,Path(d)/'missing-default.json'))
            self.assertEqual(target.read_bytes(),original)
    def test_invalid_defaults_do_not_create_user_config(self):
        with tempfile.TemporaryDirectory() as d:
            default=Path(d)/'default.json';default.write_text('{}')
            target=Path(d)/'mappings.json'
            with self.assertRaises(ValueError):initialize(target,default)
            self.assertFalse(target.exists())
