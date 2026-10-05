"""Six-angle three-finger train supplement, right then left, no model labeling."""
import json
from gesture_collector import Collector
from collect_balanced_angles import ANGLES

class NegativeAngles(Collector):
    def __init__(self):
        self.angle_mode=False
        super().__init__(initial_hand='ขวา',negative=True)
        self.angle_mode=True
        self.splits=['train']*len(ANGLES);self.total=len(ANGLES)
        self.hand_menu.configure(state='disabled')
        self.progress.set('สามนิ้วหลายมุม • 0/6 ช่วง')
        self.root.title('Hand Gesture Music — Three Finger Angle Training')
        self.update_step()
    def update_step(self):
        super().update_step()
        if not self.angle_mode:return
        if self.round>=len(self.splits):
            if self.hand.get()=='ขวา':
                self.timer.set('ขวาครบแล้ว • กดเริ่มชุดใหม่สำหรับอีกข้าง แล้วใช้มือซ้ายจริง')
            else:
                self.new_hand_button.pack_forget()
                self.timer.set('ส่งข้อความ “เก็บสามนิ้วหกมุมครบทั้งสองมือแล้ว” ในแชท')
            return
        self.instruction.set(ANGLES[self.round]+'\nชูโป้ง–ชี้–กลางพร้อมกัน พับนางและก้อย\nคงสามนิ้วตลอด 12 วินาที ใช้มือ'+self.hand.get()+'จริง')
    def new_hand(self):
        if self.hand.get()!='ขวา':return
        super().new_hand();self.hand_menu.configure(state='disabled')
    def session_init(self):
        creating=self.session is None
        super().session_init()
        if creating:
            path=self.session/'session.json'
            meta=json.loads(path.read_text(encoding='utf-8'))
            meta['angle_protocol']='three_finger_six_angles_train_v1'
            path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
            (self.session/'supplement_provenance.json').write_text(json.dumps({
                'purpose':'three-finger six-angle train-only supplement after weighting tradeoff',
                'actual_hand_protocol':'right' if self.hand.get()=='ขวา' else 'left',
                'angle_plan':ANGLES,'split_fixed_before_capture':'train',
                'label_source':'explicit three-finger prompts followed by user, no classifier labeling',
                'validation_and_test_policy':'training only; do not reassign to evaluation',
                'existing_raw_sources_unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':NegativeAngles().root.mainloop()
