"""One left-fist validation confirmation; disputed source remains unchanged."""
import json,hashlib
from gesture_collector import Collector,CLASSES,BASE

class ConfirmLeftFist(Collector):
    def __init__(self):
        self.confirmation_mode=False
        super().__init__(initial_hand='ซ้าย',wide_angles=True)
        self.confirmation_mode=True
        self.classes=[CLASSES[0]];self.splits=['validation'];self.total=1
        self.hand_menu.configure(state='disabled')
        self.progress.set('กำมือซ้ายสำหรับตรวจยืนยัน • 0/1 ช่วง')
        self.root.title('Hand Gesture Music — Confirm Left Fist')
        self.update_step()

    def update_step(self):
        super().update_step()
        if not self.confirmation_mode:return
        if self.round>=len(self.splits):
            self.new_hand_button.pack_forget()
            self.instruction.set('กำมือซ้ายสำหรับตรวจยืนยันบันทึกครบแล้ว')
            self.timer.set('ส่งข้อความ “เก็บกำมือซ้ายยืนยันครบแล้ว” ในแชท')
        else:
            self.instruction.set('ใช้มือซ้าย กำทั้งห้านิ้ว\nพับโป้งแนบกำมือ ไม่ชูโป้ง\nคงกำมือตลอด 12 วินาที\nพลิกหน้ามือ/หลังมือและเอียงช้า ๆ')

    def new_hand(self):return

    def session_init(self):
        creating=self.session is None
        super().session_init()
        if creating:
            (self.session/'confirmation_provenance.json').write_text(json.dumps({
                'purpose':'supplementary left-fist validation confirmation with a frozen diagnostic model',
                'review_of_input':'20261005_145512_ec3901ad/r04_toggle_70bd517c.csv',
                'review_status':'original clip unresolved; not excluded or relabeled',
                'user_statement':'จำไม่ได้ ต้องตรวจด้วยคลิปใหม่',
                'actual_hand_protocol':'left','split_fixed_before_capture':'validation',
                'frozen_model':'20261005_163211',
                'frozen_model_sha256':hashlib.sha256((BASE/'models/20261005_163211/gesture_model.joblib').read_bytes()).hexdigest(),
                'training_policy':'evaluate frozen model before any retraining; this clip is not training or test',
                'scope':'one gesture, one hand; not a complete independent acceptance test',
                'raw_sources_unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':ConfirmLeftFist().root.mainloop()
