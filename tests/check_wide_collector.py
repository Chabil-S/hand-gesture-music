import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from gesture_collector import Collector, SPLITS
for negative in (False, True):
    c=Collector(negative=negative,wide_angles=True)
    c.root.withdraw();c.root.update()
    assert c.splits==SPLITS
    assert c.total==(5 if negative else 20)
    assert c.session is None
    assert c.wide_angles
    for index in range(5):
        c.round=index;c.update_step()
        assert 'สามนิ้ว' not in c.instruction.get() if not negative else True
    c.round=5;c.update_step()
    assert 'อีกข้าง' in c.timer.get()
    c.new_hand();assert c.hand.get()=='ซ้าย' and c.round==0
    c.close()
print('PASS: both positive and negative angle protocols, complete rounds, hand switch, no recording on initialization')
