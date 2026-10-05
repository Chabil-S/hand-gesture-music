import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from thumb_focus_comparison import create_app,FOCUS_TRIALS,FROZEN_CANDIDATE
import live_comparison
assert FOCUS_TRIALS==[('right','previous'),('right','neutral'),('right','three_finger'),('left','previous'),('left','neutral'),('left','three_finger')]
app=create_app();app.root.withdraw();app.root.update()
assert live_comparison.TRIALS==FOCUS_TRIALS
assert app.model_info['candidate']['directory']==FROZEN_CANDIDATE
assert app.model_info['candidate']['sha256']=='dbec648f66640af1e9783c5053e897983ed2c677d8d7b722aad9b81c15b58e64'
assert not app.camera_running and app.session is None
assert app.branches['candidate'].threshold==.6
app.close()
print('PASS: six paired thumb/neutral/three-finger trials, frozen artifact and unchanged gate, no capture on initialization')
