import sys,json,tempfile,time
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[1]/'outputs';sys.path.insert(0,str(BASE))
from live_settings import validate_settings,load_settings,save_settings
import gesture_music_app as live

settings={'threshold':.95,'hold_seconds':.6,'release_seconds':.35,'max_frame_gap_seconds':.3}
for key,bad in [('threshold',1.01),('threshold',0),('hold_seconds',0),('release_seconds',-1),('max_frame_gap_seconds',float('nan'))]:
    try:validate_settings(dict(settings,**{key:bad}))
    except ValueError:pass
    else:raise AssertionError((key,bad))
with tempfile.TemporaryDirectory() as temp:
    path=Path(temp)/'live_settings.json'
    assert load_settings(path,settings)==settings
    save_settings(path,settings);assert load_settings(path,dict(settings,threshold=.8))==settings
app=live.LiveApp();app.root.withdraw()
assert app.config['threshold']==.95 and app.frozen_config['threshold']==.8
assert not app.camera_running and not app.armed
frozen_dir=BASE/json.loads((BASE/'latest_model.json').read_text())['directory']
frozen=(frozen_dir/'selection_frozen.json').read_bytes()
class Scores:
    classes_=np.array(['neutral','previous'])
    score=.9
    def predict_proba(self,X):return np.array([[1-self.score,self.score]])
app.model=Scores()
coords=[v for i in range(21) for v in (.2+i*.015,.2+i*.01,0)]
for score,expected in [(.9,None),(.97,'previous')]:
    app.model.score=score;app.gate.reset();app.hand_selector.reset()
    app.frames.put({'t':time.monotonic(),'w':640,'h':480,'count':1,'hands':[{'coords':coords}],'rgb':np.zeros((480,640,3),dtype=np.uint8)})
    app.poll();assert app.gate.candidate==expected,(score,app.gate.candidate)
with tempfile.TemporaryDirectory() as temp:
    original=live.BASE;live.BASE=Path(temp)
    try:
        app.armed=True;epoch=app.music.epoch
        app.apply_runtime_settings(dict(settings,threshold=.85,hold_seconds=.8,release_seconds=.5))
        assert not app.armed and app.music.epoch>epoch
        assert app.gate.hold==.8 and app.gate.release==.5 and app.gate.candidate is None
        assert json.loads((Path(temp)/'live_settings.json').read_text())['threshold']==.85
    finally:live.BASE=original
assert (frozen_dir/'selection_frozen.json').read_bytes()==frozen
app.close()
print('PASS: 95% truly rejects score 90% and accepts 97%; saved overrides persist; apply pauses control and resets gate; frozen model stays intact')
