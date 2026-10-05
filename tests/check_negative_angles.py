import sys,json,tempfile
from pathlib import Path
base=Path('D:/hand-gesture-music/outputs');sys.path.insert(0,str(base))
import gesture_collector
from collect_negative_angles import NegativeAngles
app=NegativeAngles();app.root.withdraw()
assert app.session is None and not app.camera_running
assert app.negative and app.classes[0][0]=='neutral' and len(app.classes)==1
assert app.splits==['train']*6 and app.total==6
for r in range(6):
    app.round=r;app.update_step();assert '12' in app.instruction.get()
app.round=6;app.update_step();app.new_hand()
assert app.hand.get()=='ซ้าย' and app.round==0
with tempfile.TemporaryDirectory() as temp:
    original=gesture_collector.BASE
    gesture_collector.BASE=Path(temp)
    try:
        app.session_init()
        m=json.loads((app.session/'session.json').read_text(encoding='utf-8'))
        assert m['round_splits']==['train']*6 and m['collection_kind']=='three_finger_negative'
        assert m['angle_protocol']=='three_finger_six_angles_train_v1'
        assert not list(app.session.glob('*.csv'))
    finally:gesture_collector.BASE=original
app.round=6;app.update_step();app.new_hand();assert app.hand.get()=='ซ้าย'
app.close()
print('PASS: six-angle train-only three-finger protocol, hand order, no automatic camera or capture')
