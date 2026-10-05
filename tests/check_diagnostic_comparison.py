import sys,json,subprocess,tempfile
from pathlib import Path
base=Path(__file__).resolve().parents[1]/'outputs'
sys.path.insert(0,str(base))
from live_comparison import ComparisonApp
active=(base/'latest_model.json').read_bytes()
history=(base/'evaluation_history.json').read_bytes()
directory=base/json.loads((base/'data/latest_diagnostic.json').read_text())['directory']
config=json.loads((directory/'selection_frozen.json').read_text(encoding='utf-8'))
assert config['eligible_for_activation'] is False and config['test_evaluated'] is False
assert config['revision_validation']['event_integrity_passed']
app=ComparisonApp('latest-diagnostic');app.root.withdraw();app.root.update()
assert 'candidate' in app.branches
assert app.branches['candidate'].threshold==config['threshold']
app.close()
result=subprocess.run([sys.executable,str(base/'train_gestures.py'),'--diagnostic-only','--activate'],capture_output=True)
assert result.returncode==2 and b'cannot be activated' in result.stderr
assert (base/'latest_model.json').read_bytes()==active
assert (base/'evaluation_history.json').read_bytes()==history
import gesture_music_app
saved_base=gesture_music_app.BASE
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);(root/'models/diagnostic').mkdir(parents=True)
    (root/'latest_model.json').write_text(json.dumps({'directory':'models/diagnostic'}))
    (root/'models/diagnostic/selection_frozen.json').write_text(json.dumps({'eligible_for_activation':False}))
    gesture_music_app.BASE=root
    try:
        try:gesture_music_app.LiveApp()
        except RuntimeError as error:assert 'ควบคุมเพลง' in str(error)
        else:raise AssertionError('Music controller accepted diagnostic artifact')
    finally:gesture_music_app.BASE=saved_base
print('PASS: real diagnostic model loads for comparison, activation flags rejected, production pointer and test history unchanged')
