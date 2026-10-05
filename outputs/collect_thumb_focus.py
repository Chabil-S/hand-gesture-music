"""Train-only right-thumb supplement; no classifier labels or test allocation."""
import json
from gesture_collector import Collector,CLASSES

class ThumbFocus(Collector):
    def __init__(self):
        self.focus_mode=False
        super().__init__(initial_hand='ขวา',wide_angles=True)
        self.focus_mode=True
        self.classes=[CLASSES[2]]
        self.splits=['train','train','train']
        self.total=3
        self.hand_menu.configure(state='disabled')
        self.progress.set('นิ้วโป้งขวา • ชุดฝึกเพิ่มเติม 0/3 ช่วง')
        self.root.title('Hand Gesture Music — Right Thumb Training')
        self.update_step()

    def update_step(self):
        super().update_step()
        if not self.focus_mode:return
        if self.round>=len(self.splits):
            self.new_hand_button.pack_forget()
            self.instruction.set('บันทึกนิ้วโป้งขวาครบแล้ว • เป็นชุดฝึกเพิ่มเติมเท่านั้น')
            self.timer.set('ส่งข้อความ “เก็บนิ้วโป้งขวาเพิ่มครบแล้ว” ในแชท')
        else:
            angles=['หันฝ่ามือเข้ากล้อง เอียงซ้าย/ขวาช้า ๆ',
                    'หันหลังมือเข้ากล้อง เอียงซ้าย/ขวาช้า ๆ',
                    'พลิกหน้ามือ/หลังมือช้า ๆ ลองมุมเฉียงที่เคยรับยาก']
            self.instruction.set('ใช้มือขวา กำสี่นิ้วและชูเฉพาะนิ้วโป้ง\nคงท่านี้ตลอด 12 วินาที\n'+angles[self.round]+
                                 '\nให้เห็นทั้งมือ ไม่ต้องเพิ่มนิ้วอื่น')

    def new_hand(self):return

    def session_init(self):
        creating=self.session is None
        super().session_init()
        if creating:
            (self.session/'supplement_provenance.json').write_text(json.dumps({
                'purpose':'targeted right-thumb train-only supplement after validation diagnosis',
                'actual_hand_protocol':'right','split_fixed_before_capture':'train',
                'reference_candidate':'20261005_153504',
                'reference_validation_clip':'20261005_144622_e13a21ee/r04_previous_f4f4c107.csv',
                'label_source':'user follows explicit thumb-only prompt; no classifier labeling',
                'validation_and_test_policy':'not an independent evaluation set; do not reassign to validation or test',
                'raw_sources_unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':ThumbFocus().root.mainloop()
