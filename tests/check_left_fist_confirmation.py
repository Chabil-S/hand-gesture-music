import sys,tempfile,json,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
import gesture_collector
from confirm_left_fist import ConfirmLeftFist
with tempfile.TemporaryDirectory() as temporary:
    gesture_collector.BASE=Path(temporary)
    c=ConfirmLeftFist();c.root.withdraw();c.root.update()
    assert c.session is None and not c.camera_running
    assert c.hand.get()=='ซ้าย' and c.splits==['validation'] and c.total==1
    assert [v[0] for v in c.classes]==['toggle']
    c.session_init()
    provenance=json.loads((c.session/'confirmation_provenance.json').read_text(encoding='utf-8'))
    assert provenance['split_fixed_before_capture']=='validation'
    assert provenance['frozen_model']=='20261005_163211'
    assert provenance['review_status']=='original clip unresolved; not excluded or relabeled'
    c.samples=[['synthetic_test',i*.15,'Right',640,480,*([.2]*63)] for i in range(48)]
    c.finish(True,'synthetic_test')
    clip=json.loads((c.session/'clips.jsonl').read_text(encoding='utf-8'))
    assert clip['accepted'] and clip['split']=='validation' and clip['label']=='toggle'
    with (c.session/clip['csv']).open(encoding='utf-8',newline='') as f:
        assert all(r['split']=='validation' and r['label']=='toggle' for r in csv.DictReader(f))
    c.new_hand();assert c.round==1 and c.hand.get()=='ซ้าย'
    c.close()
print('PASS: one left-fist validation clip, frozen-model provenance, unresolved source preserved, no camera on initialization')
