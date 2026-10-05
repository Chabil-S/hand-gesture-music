import sys,tempfile,csv,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
import gesture_collector
from collect_fist_contrast import FistContrast
with tempfile.TemporaryDirectory() as temporary:
    gesture_collector.BASE=Path(temporary)
    c=FistContrast();c.root.withdraw();c.root.update()
    assert c.session is None and not c.camera_running
    assert c.splits==['train']*3 and [v[0] for v in c.classes]==['toggle']
    sessions=[]
    for hand in ['ขวา','ซ้าย']:
        assert c.hand.get()==hand
        c.session_init();sessions.append(c.session)
        for n in range(3):
            c.samples=[['synthetic_test',i*.15,'Left',640,480,*([.2]*63)] for i in range(48)]
            c.finish(True,'synthetic_test')
        meta=json.loads((c.session/'session.json').read_text(encoding='utf-8'))
        assert meta['declared_hand']==hand and meta['round_splits']==['train']*3 and meta['classes']==['toggle']
        clips=[json.loads(s) for s in (c.session/'clips.jsonl').read_text(encoding='utf-8').splitlines()]
        assert len(clips)==3
        for clip in clips:
            path=c.session/clip['csv']
            assert clip['split']=='train' and clip['label']=='toggle' and clip['accepted']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==clip['sha256']
            with path.open(encoding='utf-8',newline='') as f:
                assert all(r['split']=='train' and r['label']=='toggle' for r in csv.DictReader(f))
        if hand=='ขวา':c.new_hand();assert c.round==0 and c.session is None
    assert sessions[0]!=sessions[1]
    assert 'ทั้งสองข้าง' in c.instruction.get()
    c.new_hand();assert c.round==3 and c.hand.get()=='ซ้าย'
    c.close()
print('PASS: right then left fist-only train sessions, fixed splits and preserved hashes, no recording on initialization')
