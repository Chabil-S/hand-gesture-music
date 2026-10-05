"""Collect only the left V validation clip quarantined after user label review."""
import json
from gesture_collector import Collector,CLASSES

class RepairV(Collector):
    def __init__(self):
        self.repair_mode=False
        super().__init__(initial_hand='ซ้าย',wide_angles=True)
        self.repair_mode=True;self.classes=[CLASSES[1]];self.splits=['validation'];self.total=1
        self.hand_menu.configure(state='disabled')
        self.progress.set('เก็บใหม่เฉพาะ V มือซ้าย • 0/1 ช่วง')
        self.root.title('Hand Gesture Music — Repair Left V')
        self.update_step()
    def update_step(self):
        super().update_step()
        if not self.repair_mode:return
        if self.round>=len(self.splits):
            self.new_hand_button.pack_forget()
            self.instruction.set('V มือซ้ายบันทึกครบแล้ว • ไม่ต้องเก็บท่าอื่นซ้ำ')
            self.timer.set('ส่งข้อความ “เก็บ V แก้ไขครบแล้ว” ในแชท')
        else:
            self.instruction.set('ใช้มือซ้าย ชูชี้–กลางเป็น V พับโป้ง\nคง V ตลอด 12 วินาที\nสลับหน้ามือ/หลังมือและมุมที่ใช้จริงช้า ๆ')
    def new_hand(self):return
    def session_init(self):
        creating=self.session is None
        super().session_init()
        if creating:
            (self.session/'repair_provenance.json').write_text(json.dumps({
                'replaces_quarantined_input':'20261005_145512_ec3901ad/r04_next_a93e3486.csv',
                'split_fixed_before_capture':'validation','purpose':'replace mislabeled validation V, not test or training',
                'actual_hand_protocol':'left','raw_sources_unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':RepairV().root.mainloop()
