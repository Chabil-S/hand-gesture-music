import csv
import hashlib
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from gesture_collector import Collector, COORDS,CLASSES,SPLITS

class Dummy:
    def set(self,*args): pass
    def get(self): return 'ขวา'
    def configure(self,**kwargs): pass
    def pack(self,**kwargs): pass

c=Collector.__new__(Collector)
c.session=Path(tempfile.mkdtemp(prefix='storage_check_',dir=Path(__file__).parent))
c.round=0
c.gesture=0
c.accepted=0
c.classes=CLASSES;c.splits=SPLITS;c.total=20;c.negative=False
for name in ['title','instruction','timer','progress','cancel_button','record_button','hand','new_hand_button']:
    setattr(c,name,Dummy())
c.samples=[['fixture',i/8,'Right',640,480,*([0.1]*len(COORDS))] for i in range(60)]
c.finish(False,'test_rejected')
assert (c.round,c.gesture,c.accepted)==(0,0,0)
first_file=next(c.session.glob('*.csv'))
first_hash=hashlib.sha256(first_file.read_bytes()).hexdigest()
for _ in range(20): c.finish(True,'test_complete')
assert (c.round,c.gesture,c.accepted)==(5,0,20)
entries=[json.loads(line) for line in (c.session/'clips.jsonl').read_text().splitlines()]
assert len(entries)==21 and not entries[0]['accepted']
by_round={}
for entry in entries:
    by_round.setdefault(entry['round_id'],set()).add(entry['split'])
    assert hashlib.sha256((c.session/entry['csv']).read_bytes()).hexdigest()==entry['sha256']
    with (c.session/entry['csv']).open(newline='') as file:
        rows=list(csv.reader(file))
    assert len(rows)==61 and all(len(row)==73 for row in rows)
assert by_round=={1:{'train'},2:{'train'},3:{'train'},4:{'validation'},5:{'test'}}
assert hashlib.sha256(first_file.read_bytes()).hexdigest()==first_hash
print('PASS: schema, rejected capture, immutable clips, 20-step progression, disjoint round splits')
c.session=Path(tempfile.mkdtemp(prefix='negative_storage_check_',dir=Path(__file__).parent))
c.round=0;c.gesture=0;c.accepted=0;c.negative=True
c.classes=[('neutral','neutral','three fingers','')];c.splits=['train','validation','test'];c.total=3
for _ in range(3):c.finish(True,'negative_test')
entries=[json.loads(line) for line in (c.session/'clips.jsonl').read_text().splitlines()]
assert c.accepted==3 and c.round==3
assert [(e['split'],e['label']) for e in entries]==[('train','neutral'),('validation','neutral'),('test','neutral')]
print('PASS: supplemental three-finger data uses three separate rounds and retains neutral label')
