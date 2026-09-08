"""Create user-owned mappings once; upgrades never replace them."""
import os
from .model import validate_config
import json


def initialize(path,defaults):
    if path.exists():return False
    raw=defaults.read_bytes()
    validate_config(json.loads(raw))
    path.parent.mkdir(parents=True,exist_ok=True)
    try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:return False
    with os.fdopen(fd,'wb') as stream:stream.write(raw)
    return True
