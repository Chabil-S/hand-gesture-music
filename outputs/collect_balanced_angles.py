"""Balanced four-pose, six-angle, train-only supplement for both hands."""
import json
from gesture_collector import Collector

ANGLES=[
 'ฝ่ามือเข้ากล้องตรง ๆ • มือระดับกลางภาพ ระยะประมาณ 40–60 ซม.',
 'หลังมือเข้ากล้องตรง ๆ • ใช้ระยะใกล้เคียงรอบแรก',
 'ฝ่ามือเข้ากล้อง แล้วหมุนซ้ายเล็กน้อยประมาณ 30 องศา • ไม่หันเป็นสันมือ',
 'ฝ่ามือเข้ากล้อง แล้วหมุนขวาเล็กน้อยประมาณ 30 องศา • ไม่หันเป็นสันมือ',
 'ฝ่ามือเข้ากล้อง • กระดกข้อมือเข้า/ออกเล็กน้อยประมาณ 20 องศา ช้า ๆ',
 'หลังมือเข้ากล้อง • เอียงซ้าย/ขวาเล็กน้อย ขยับระยะประมาณ 35–70 ซม. ช้า ๆ',
]

class BalancedAngles(Collector):
    def __init__(self):
        self.angle_mode=False
        super().__init__(initial_hand='ขวา')
        self.angle_mode=True;self.splits=['train']*len(ANGLES)
        self.total=len(self.classes)*len(self.splits)
        self.hand_menu.configure(state='disabled')
        self.progress.set(f'เก็บครบ 0/{self.total} ช่วง • ชุดฝึกหลายมุม')
        self.root.title('Hand Gesture Music — Balanced Angle Training')
        self.update_step()
    def update_step(self):
        super().update_step()
        if not self.angle_mode:return
        if self.round>=len(self.splits):
            if self.hand.get()=='ขวา':
                self.timer.set('มือขวาครบแล้ว • กดเริ่มชุดใหม่สำหรับอีกข้าง แล้วใช้มือซ้ายจริง')
            else:
                self.new_hand_button.pack_forget()
                self.timer.set('ส่งข้อความ “เก็บหลายมุมชุดใหม่ครบทั้งสองมือแล้ว” ในแชท')
            return
        pose=self.classes[self.gesture][0]
        specific={'toggle':'กำทั้งห้านิ้ว พับโป้งแนบกำมือ',
                  'previous':'ชูเฉพาะโป้ง กำอีกสี่นิ้ว',
                  'next':'ชูชี้–กลางเป็น V พับโป้ง นาง และก้อย',
                  'neutral':'เปลี่ยนแบมือ/ชี้นิ้วเดียว/มือผ่อนคลาย ตามตัวนับเวลา'}[pose]
        self.instruction.set(ANGLES[self.round]+'\n'+specific+'\nใช้มือ'+self.hand.get()+'จริง ให้เห็นทั้งมือ คงท่าตามป้าย')
    def new_hand(self):
        if self.hand.get()!='ขวา':return
        super().new_hand();self.hand_menu.configure(state='disabled')
    def session_init(self):
        creating=self.session is None
        super().session_init()
        if creating:
            path=self.session/'session.json'
            metadata=json.loads(path.read_text(encoding='utf-8'))
            metadata['angle_protocol']='balanced_six_angles_train_v1'
            # Finalize new-session metadata before the first captured row.
            path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
            (self.session/'supplement_provenance.json').write_text(json.dumps({
                'purpose':'balanced four-class multi-angle training supplement',
                'actual_hand_protocol':'right' if self.hand.get()=='ขวา' else 'left',
                'angle_plan':ANGLES,'split_fixed_before_capture':'train',
                'label_source':'user follows explicit per-pose prompts, no classifier labeling',
                'scope':'training only; new validation and test remain separate',
                'existing_raw_sources_unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':BalancedAngles().root.mainloop()
