import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from repair_validation_v import RepairV
c=RepairV();c.root.withdraw();c.root.update()
assert c.hand.get()=='ซ้าย'
assert str(c.hand_menu['state'])=='disabled'
assert c.splits==['validation'] and c.total==1 and c.classes[0][0]=='next'
assert c.session is None and len(c.classes)==1
c.round=1;c.update_step();c.root.update()
assert not c.new_hand_button.winfo_ismapped()
assert 'แก้ไขครบ' in c.timer.get()
c.new_hand();assert c.hand.get()=='ซ้าย' and c.round==1
c.close()
print('PASS: one left V validation clip, no recording on open, no hand switch, explicit completion instructions')
