import json,runpy,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_model import config

ROOT=Path(__file__).resolve().parents[1]

class HostSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name);self.base=self.home/'.config/hypr';self.base.mkdir(parents=True)
        self.bindings=self.base/'bindings.lua';self.bindings.write_text('-- user bindings\n')
        self.local=self.home/'mappings.json';self.local.write_text(json.dumps(config()))
        self.generated=self.base/'codex-micro.lua'
        self.link=self.home/'.config/omarchy/plugins/fraction12.codex-micro'
        self.calls=[];self.fail_command=None;self.api='true\n'
    def run_script(self,name):
        def run(argv,**kwargs):
            self.calls.append(argv)
            if self.fail_command and self.fail_command(argv):raise subprocess.CalledProcessError(1,argv)
            return subprocess.CompletedProcess(argv,0,stdout=self.api,stderr='')
        def output(argv,**kwargs):
            if argv[1]=='binds':return '[]'
            if argv[1]=='configerrors':return ''
            return self.api
        with patch('pathlib.Path.home',return_value=self.home),patch('codex_micro.cli.CONFIG',self.local),patch('codex_micro.storage.STATE',self.home/'state'),patch('shutil.which',return_value='/bin/tool'),patch('subprocess.run',side_effect=run),patch('subprocess.check_output',side_effect=output):
            runpy.run_path(str(ROOT/'scripts'/name),run_name='__main__')
    def test_enable_failure_rolls_back_host_and_new_link(self):
        self.fail_command=lambda a:a[:3]==['omarchy','plugin','enable']
        with self.assertRaises(subprocess.CalledProcessError):self.run_script('install')
        self.assertEqual(self.bindings.read_text(),'-- user bindings\n')
        self.assertFalse(self.generated.exists())
        self.assertFalse(self.link.is_symlink())
    def test_missing_lua_api_fails_before_changes(self):
        self.api='false\n'
        with self.assertRaises(SystemExit):self.run_script('install')
        self.assertFalse(self.link.is_symlink())
    def test_uninstall_foreign_generated_file_refuses_before_mutation(self):
        self.generated.write_text('-- owned by someone else\n')
        with self.assertRaises(SystemExit):self.run_script('uninstall')
        self.assertEqual(self.calls,[])
        self.assertEqual(self.bindings.read_text(),'-- user bindings\n')
    def test_install_update_uninstall_preserves_personal_mapping(self):
        before=self.local.read_bytes()
        self.run_script('install');self.run_script('install')
        self.assertEqual(self.bindings.read_text().count('dofile('),1)
        self.assertEqual(self.local.read_bytes(),before)
        self.run_script('uninstall')
        self.assertFalse(self.generated.exists());self.assertFalse(self.link.is_symlink())
        self.assertEqual(self.local.read_bytes(),before)
