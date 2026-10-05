"""Train-only fist examples to contrast with the targeted thumb supplement."""
import json
from gesture_collector import Collector,CLASSES

class FistContrast(Collector):
    def __init__(self):
        self.contrast_mode=False
        super().__init__(initial_hand='ขวา',wide_angles=True)
        self.contrast_mode=True
        self.classes=[CLASSES[0]];self.splits=['train']*3;self.total=3
        self.hand_menu.configure(state='disabled')
        self.progress.set('กำมือขวา • ชุดฝึกเพิ่ม 0/3 ช่วง')
        self.root.title('Hand Gesture Music — Fist Contrast Training')
        self.update_step()

    def update_step(self):
        super().update_step()
        if not self.contrast_mode:return
        if self.round>=len(self.splits):
            if self.hand.get()=='ขวา':
                self.instruction.set('กำมือขวาครบแล้ว • กดเริ่มชุดใหม่สำหรับอีกข้าง แล้วใช้มือซ้าย')
                self.timer.set('เหลือกำมือซ้าย 3 ช่วง • ไม่ต้องเก็บท่าอื่น')
            else:
                self.new_hand_button.pack_forget()
                self.instruction.set('กำมือครบทั้งสองข้างแล้ว • เป็นชุดฝึกเพิ่มเติมเท่านั้น')
                self.timer.set('ส่งข้อความ “เก็บกำมือเพิ่มครบทั้งสองข้างแล้ว” ในแชท')
        else:
            angles=['หันฝ่ามือเข้ากล้อง เอียงซ้าย/ขวาช้า ๆ',
                    'หันหลังมือเข้ากล้อง เอียงซ้าย/ขวาช้า ๆ',
                    'พลิกหน้ามือ/หลังมือช้า ๆ ลองมุมเฉียงที่ใช้จริง']
            self.instruction.set('ใช้มือ'+self.hand.get()+' กำทั้งห้านิ้วตามปกติ\nโป้งพับแนบกำมือ ไม่ชูโป้ง\nคงกำมือตลอด 12 วินาที\n'+angles[self.round])

    def new_hand(self):
        if self.hand.get()!='ขวา':return
        super().new_hand()
        self.hand_menu.configure(state='disabled')

    def session_init(self):
        creating=self.session is None
        super().session_init()
        if creating:
            (self.session/'contrast_provenance.json').write_text(json.dumps({
                'purpose':'fist train-only contrast after thumb supplement improved thumb but reduced fist acceptance',
                'actual_hand_protocol':'right' if self.hand.get()=='ขวา' else 'left',
                'split_fixed_before_capture':'train',
                'reference_candidate':'20261005_161700',
                'reference_thumb_supplement':'20261005_161246_60241eef',
                'label_source':'user follows explicit fist-only prompt; no classifier labeling',
                'validation_and_test_policy':'do not reassign to validation or test',
                'raw_sources_unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':FistContrast().root.mainloop()
