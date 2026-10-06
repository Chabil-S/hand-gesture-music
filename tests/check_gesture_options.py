"""Default activation and separate, atomic persistence of gesture choices."""
import json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from gesture_options import load_options,save_options,validate_options

with tempfile.TemporaryDirectory() as temp:
    path=Path(temp)/'options.json'
    assert load_options(path)=={'volume_enabled':True,'palm_enabled':True}
    saved={'volume_enabled':False,'palm_enabled':True}
    assert save_options(path,saved)==saved and load_options(path)==saved
    assert not path.with_suffix('.tmp').exists()
    before=path.read_bytes()
    for invalid in ({'volume_enabled':1,'palm_enabled':True},{'volume_enabled':True},None):
        try:save_options(path,invalid);raise AssertionError('invalid options accepted')
        except ValueError:pass
        assert path.read_bytes()==before
    path.write_text('{bad json',encoding='utf-8')
    try:load_options(path);raise AssertionError('invalid JSON accepted')
    except ValueError:pass
print('PASS: enabled defaults, saved choices, strict booleans, atomic write and invalid-file handling')
