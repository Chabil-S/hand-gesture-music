import sys,tempfile,csv,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
import gesture_collector
from collect_thumb_focus import ThumbFocus

with tempfile.TemporaryDirectory() as temporary:
    gesture_collector.BASE=Path(temporary)
    collector=ThumbFocus();collector.root.withdraw();collector.root.update()
    assert collector.session is None and not collector.camera_running
    assert collector.splits==['train']*3 and collector.total==3
    assert collector.hand.get()=='ขวา' and [c[0] for c in collector.classes]==['previous']
    collector.session_init()
    session=collector.session
    for n in range(3):
        collector.samples=[['synthetic_test',i*.15,'Left',640,480,*([.2]*63)] for i in range(48)]
        collector.finish(True,'synthetic_test')
    manifest=json.loads((session/'session.json').read_text(encoding='utf-8'))
    assert manifest['round_splits']==['train']*3 and manifest['classes']==['previous']
    provenance=json.loads((session/'supplement_provenance.json').read_text(encoding='utf-8'))
    assert provenance['split_fixed_before_capture']=='train'
    clips=[json.loads(line) for line in (session/'clips.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(clips)==3 and all(c['accepted'] and c['split']=='train' and c['label']=='previous' for c in clips)
    for clip in clips:
        path=session/clip['csv'];assert hashlib.sha256(path.read_bytes()).hexdigest()==clip['sha256']
        with path.open(encoding='utf-8',newline='') as f:
            assert all(r['split']=='train' and r['label']=='previous' for r in csv.DictReader(f))
    assert collector.round==3 and 'ครบแล้ว' in collector.instruction.get()
    collector.new_hand();assert collector.hand.get()=='ขวา' and collector.round==3
    collector.close()
print('PASS: three right-thumb train-only clips, source provenance and hashes; no camera on initialization or hand switching')
