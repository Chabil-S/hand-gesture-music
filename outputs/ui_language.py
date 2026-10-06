"""Small Thai/English UI catalog; media metadata is deliberately left untouched."""
import json
import re
import tkinter as tk

EN = {
    'เริ่มควบคุมแล้ว · ปล่อยมือ':'Gestures enabled · release hand',
    'พักการควบคุมแล้ว · ปล่อยมือ':'Gestures paused · release hand',
    'ค้างจีบหรือกางปลายนิ้ว แล้วขยับเพื่อปรับเสียง':'Hold closed or open fingertips, then move to adjust volume',
    'ขยับนิ้วเพื่อปรับเสียง':'Move to adjust volume', 'ค้างจีบเพื่อเริ่ม':'Hold pinch to start',
    'ค้างจีบ 0.45 วินาที · พับอีกสามนิ้ว':'Hold pinch 0.45 s · fold the other fingers',
    'เอามือออกเพื่อจบ':'Lower hand to finish',
    'ทดลองท่าเพิ่มเติม':'Try extra gestures', 'ท่าเพิ่มเติม · รุ่นทดลอง':'Extra gestures · experimental',
    'ยังต้องลองกับมือจริง · ปิดทุกครั้งที่เปิดโปรแกรม':'Live hand testing needed · off on each launch',
    'โหมดจีบปรับเสียง Apple Music':'Pinch mode for Apple Music volume',
    'พับกลาง–นาง–ก้อย · ค้างจีบหรือกาง 0.45 วินาที':'Fold the other three fingers · hold closed or open for 0.45 s',
    'กางเพิ่ม · หุบลด · ท่าเปลี่ยนเพลงพักในโหมดนี้':'Open to raise · close to lower · track gestures are paused',
    'แบมือค้างเพื่อพัก / เริ่มควบคุม':'Hold an open palm to pause / enable gestures',
    'แบทั้งห้านิ้ว 1.2 วินาที แล้วปล่อย':'Spread all five fingers for 1.2 s, then release',
    'ตรวจท่านี้ได้ระหว่างพัก ถ้ากล้องยังเปิดอยู่':'Works while paused if the camera stays open',
    'ใช้ค่าแล้วกลับโหมดดูผล · กดเริ่มควบคุมเพื่อส่งคำสั่งจริง':'Apply to preview · enable gestures for real commands',
    'ใช้โหมดทดลอง':'Apply experimental mode',
    'โหมดปรับเสียงปิดอยู่':'Volume mode is off', 'กำลังอ่านระดับเสียง…':'Reading volume…',
    'เสียง Apple Music · —':'Apple Music volume · —',
    'เสียง Apple Music · ยังอ่านไม่ได้':'Apple Music volume · unavailable',
    'โหมดปรับเสียง · ท่าเปลี่ยนเพลงพักอยู่':'Volume mode · track gestures paused',
    'กลับโหมดท่าเพลงแล้ว':'Track gesture mode restored',
    'ปล่อยมือก่อนแบมืออีกครั้ง':'Release before another palm hold',
    'กางเพิ่ม · หุบลด · เอามือออกเพื่อจบ':'Open to raise · close to lower · lower hand to finish',
    'ดูผลจีบ · ยังไม่ปรับเสียง':'Pinch preview · volume unchanged',
    'ค้างปลายนิ้วเพื่อเริ่มปรับเสียง':'Hold your fingertips to start',
    'จีบหรือกางชี้–โป้ง · พับอีกสามนิ้ว':'Close or open thumb–index · fold the other fingers',
    'ดูผลจีบ · เพิ่มเสียง':'Pinch preview · raise volume', 'ดูผลจีบ · ลดเสียง':'Pinch preview · lower volume',
    'ปรับเสียงด้วยนิ้ว':'Pinch volume', 'รอท่าจีบ':'Waiting for a pinch', 'แบมือ':'Open palm',
    'โหมดจีบ · ควบคุมเสียง':'Pinch · volume control', 'โหมดจีบ · ดูผล':'Pinch · preview',
    'ปล่อยมือ แล้วทำท่าถัดไป':'Release, then make the next gesture.',
    'ค้างท่า = 1 คำสั่ง':'One hold = one command',
    'มุมมอง':'VIEWS', 'จับท่าทาง':'Gestures', 'กำลังฟัง':'Now playing', 'ตั้งค่า':'Settings',
    'เพลงของคุณ ในจังหวะของมือ':'Your music, at your fingertips',
    'อ่านสถานะ Apple Music':'Refresh Apple Music', 'เห็นท่า เห็นคำสั่ง':'Gesture control',
    'ภาพจากกล้อง':'Camera preview', 'กล้อง':'Camera', 'เปิดกล้อง':'Open camera', 'ปิดกล้อง':'Close camera',
    'เปิดกล้องเพื่อลองท่า':'Open the camera to try gestures', 'รอท่ามือ':'Waiting for a hand',
    'เริ่มควบคุมเพลง':'Enable gestures', 'พักการควบคุม':'Pause gestures',
    'กำมือ':'Fist', 'V ชี้–กลาง พับโป้ง':'V sign · thumb folded', 'ชูโป้ง':'Thumbs up',
    'เล่น / พัก':'Play / pause', 'ถัดไป':'Next', 'ก่อนหน้า':'Previous',
    'ท่าที่ตรวจพบ':'Detected gesture', 'คะแนนโมเดล':'Model confidence',
    'พร้อมรับท่า':'Ready for a gesture', 'ปล่อยมือก่อนออกคำสั่งใหม่':'Release before the next gesture',
    'ปล่อยมือก่อนคำสั่งใหม่':'Release before the next gesture', 'ค้างมือไม่สั่งซ้ำ':'One command per held pose',
    'กำลังควบคุมด้วยมือ':'Gesture control is on', 'โหมดดูผล':'Preview mode',
    'โหมดดูผล · ยังไม่ส่งคำสั่งมือ':'Preview · commands off',
    'ดูหน้ากำลังฟัง':'Open player', 'ยังไม่มีเพลงที่กำลังฟัง':'No track playing',
    'เปิด Apple Music แล้วเริ่มเพลง':'Open Apple Music and start a track',
    'ยังไม่ได้เชื่อมต่อ':'Not connected', 'ยังไม่มีภาพปกจาก Apple Music':'No artwork available from Apple Music',
    'กำลังเล่น':'Playing', 'พักเพลง':'Paused', 'หยุดเล่น':'Stopped', 'ยังไม่ได้เล่นเพลง':'Not playing',
    'ไม่มีข้อมูลระยะเวลาเพลง':'Track duration is unavailable',
    'ปุ่มเพลงสั่งงานทันที · โหมดดูผลใช้กับท่ามือ':'Player buttons act immediately · preview applies to gestures',
    'สลับมุมมองได้โดยไม่หยุดรับท่า':'Switch views without interrupting gestures',
    'ขยายกล้องและดูผล':'Open camera view', 'ปรับให้เข้ากับมือคุณ':'Make it feel right',
    'คะแนนขั้นต่ำรับท่า (%)':'Minimum confidence (%)',
    'สูงขึ้น: รับเฉพาะท่าที่มั่นใจมากขึ้น · ต่ำลง: รับท่าได้ง่ายขึ้น':'Higher: stricter confidence · Lower: easier to trigger',
    'รับง่ายขึ้น':'Easier to trigger', 'เข้มงวดขึ้น':'More selective',
    'จังหวะการออกคำสั่ง':'Gesture timing', 'เวลาค้างท่า':'Hold time', 'เวลาปล่อยมือ':'Release time',
    'วินาที · ค้างก่อนส่งคำสั่ง':'Seconds to hold before sending',
    'วินาที · เว้นก่อนรับท่าใหม่':'Seconds to release before a new gesture',
    'ช่วงภาพขาดที่ยอมรับ (วินาที)':'Maximum frame gap (seconds)',
    'เว้นเกินนี้จะเริ่มนับเวลาค้างท่าใหม่':'Longer gaps restart the hold timer',
    'การตั้งค่าเพิ่มเติม':'Advanced settings',
    'บันทึกแล้วกลับโหมดดูผล เพื่อให้ลองท่าก่อนเปิดควบคุมเพลง':'Saving returns to preview so you can try the new settings',
    'บันทึกและใช้ค่า':'Save settings', 'คืนค่าที่รุ่นเคยทดสอบ':'Restore model defaults',
    'ยังไม่ได้เปลี่ยนค่า':'Settings not saved', 'ทุกค่าต้องเป็นตัวเลขปกติ':'All values must be finite numbers',
    'คะแนนรับท่าต้องมากกว่า 0 และไม่เกิน 100%':'Confidence must be greater than 0 and at most 100%',
    'เวลาทั้งหมดต้องมากกว่า 0 วินาที':'All timing values must be greater than zero',
    'Apple Music · เชื่อมต่อแล้ว':'Apple Music · connected',
    'เปิด Apple Music และเริ่มเพลงเพื่อเชื่อมต่อ':'Open Apple Music and play a track to connect',
    'อ่าน Apple Music ไม่ได้ · ลองเปิดเพลงแล้วอ่านสถานะอีกครั้ง':'Cannot read Apple Music. Start a track and refresh.',
    'ยังไม่มีชื่อเพลง':'Untitled track', 'ไม่ระบุศิลปิน':'Unknown artist',
    'ไม่สั่งงาน':'No command', 'ยังไม่แน่ใจ':'Uncertain', 'ไม่พบมือ':'No hand detected',
    'กล้องยังไม่เปิด':'Camera is off', 'กล้องปิด':'Camera is off', 'กล้องมีปัญหา':'Camera unavailable',
    'กำลังเปิดกล้อง…':'Opening camera…',
    'กำลังปิดกล้องเดิม · รอสักครู่แล้วเปิดอีกครั้ง':'Closing the camera. Wait a moment before reopening.',
    'โหมดดูผล • ยังไม่ส่งคำสั่งเพลง':'Preview mode · no gesture commands',
    'โหมดดูผล • กล้องปิด':'Preview mode · camera off',
    'โหมดดูผล • ใช้ค่ารับท่าที่ปรับเอง':'Preview mode · custom settings',
    'บันทึกค่ารับท่าแล้ว • ลองในโหมดดูผลก่อนกดเริ่มควบคุมเพลง':'Settings saved. Try gestures in preview, then enable control.',
    'ควบคุมเพลงอยู่ • เอามือออกก่อนเริ่ม':'Gesture control enabled · release your hand first',
    'ลองทั้งสามท่าได้โดยไม่เปลี่ยนเพลง':'Try all three gestures without changing the music',
    'คิวเต็ม • คำสั่งนี้ยังไม่ถูกส่ง กรุณารอแล้วปล่อยท่าก่อนลองใหม่':'Command queue is full. Wait, release, and try again.',
    'กำลังอ่าน Apple Music…':'Reading Apple Music…',
    'ยังรับท่าปล่อยมือและท่าถัดไปได้':'Release and the next gesture can still be detected',
    'กล้องมีปัญหา • หยุดส่งเพลงแล้ว':'Camera unavailable · gesture commands paused',
    'สองมือสั่งต่างกัน • รอให้เหลือท่าคำสั่งเดียว':'Conflicting gestures. Show only one command.',
    'รอมือสั่งงานกลับมา':'Waiting for the active hand',
    'โหมดดูผล • ไม่ส่งเพลง':'Preview mode · no command sent',
    'เอามือออก แล้วลองท่าถัดไป':'Release your hand, then try the next gesture',
    'ปล่อยท่าก่อน: เอามือออก หรือทำท่าไม่สั่งงาน':'Release first: lower your hand or show a neutral pose',
    'ค้างมือหรือเปลี่ยนท่าคำสั่งทันทีจะไม่สั่งซ้ำ':'Holding or immediately switching command poses will not repeat a command',
    'รอภาพกล้องใหม่':'Waiting for camera frames', 'ส่งคำสั่งไม่สำเร็จ':'Command failed',
    'เปิด Apple Music และเริ่มเพลงไว้':'Open Apple Music and start a track',
    'อ่านสถานะแล้ว':'Status refreshed', 'ตรวจพบผลคำสั่งแล้ว':'Command confirmed',
    'ยังไม่ยืนยันผล โปรดดูเครื่องเล่น':'Result not confirmed. Check the player.',
    'กำมือ = เล่น/พัก':'Fist = play/pause', 'V ชี้–กลาง พับโป้ง = ถัดไป':'V sign, thumb folded = next',
    'นิ้วโป้ง = ก่อนหน้า':'Thumbs up = previous',
    'เปิดกล้องไม่ได้ ปิดแอปอื่นที่ใช้กล้องและตรวจสิทธิ์กล้องใน Windows':'Cannot open camera. Close other camera apps and check Windows camera permissions.',
    'อ่านภาพกล้องไม่ได้ กรุณาปิดแล้วเปิดหน้ากล้องใหม่':'Cannot read camera frames. Close and reopen the camera.',
}

PATTERNS = [
    (r'แบมือ ([\d.]+) วินาที · ปล่อย ([\d.]+) วินาที',r'Palm \1 s · release \2 s'),
    (r'ค้างจีบ ([\d.]+) วินาที · พับอีกสามนิ้ว',r'Hold pinch \1 s · fold the other fingers'),
    (r'แบมือค้าง ([\d.]+) / ([\d.]+) วินาที',r'Open palm \1 / \2 s'),
    (r'เสียง Apple Music (\d+%) · ปิดเสียง',r'Apple Music volume \1 · muted'),
    (r'เสียง Apple Music (\d+%)',r'Apple Music volume \1'),
    (r'คะแนนขั้นต่ำรับท่า ([\d.]+%)',r'Minimum confidence: \1'),
    (r'เวลาปล่อยมือ ([\d.]+) วินาที',r'Release time: \1 s'),
    (r'ค้าง ([\d.]+) วินาที · ปล่อย ([\d.]+) วินาที',r'Hold \1 s · release \2 s'),
    (r'ค้าง ([\d.]+) วินาที • ปล่อย ([\d.]+) วินาที • ค้างมือไม่สั่งซ้ำ',r'Hold \1 s · release \2 s · no repeat while held'),
    (r'ค้างท่า ([\d.]+) / ([\d.]+) วินาที',r'Hold \1 / \2 s'),
    (r'เอามือออกอย่างน้อย ([\d.]+) วินาที แล้วทำท่าคำสั่ง',r'Release for at least \1 s, then show a command gesture'),
    (r'รับคำสั่งแล้ว • รอส่ง/ตรวจ (\d+) คำสั่ง',r'Command received · \1 pending'),
    (r'พบ (\d+) มือ • รับจากมือกรอบสีเขียว',r'\1 hand(s) detected · green frame is active'),
]


class Localizer:
    def __init__(self,path=None,language=None):
        self.path=path
        self.language=language or 'th'
        self.callbacks=[]
        if path and language is None:
            try:self.language=json.loads(path.read_text(encoding='utf-8')).get('language','th')
            except (OSError,ValueError):pass
        if self.language not in ('th','en'):self.language='th'

    def text(self,source):
        if self.language=='th':return source
        if source in EN:return EN[source]
        if '\n' in source:return '\n'.join(self.text(line) for line in source.split('\n'))
        for pattern,replacement in PATTERNS:
            if re.fullmatch(pattern,source):return re.sub(pattern,replacement,source)
        if source.startswith('ยืนยันท่า: '):return 'Confirmed: '+self.text(source[len('ยืนยันท่า: '):])
        return source

    def bind(self,widget,source):
        def update():widget.configure(text=self.text(source))
        self.callbacks.append(update);update()

    def set_language(self,language,persist=True):
        if language not in ('th','en'):raise ValueError(language)
        if persist and self.path:
            temp=self.path.with_suffix('.tmp')
            temp.write_text(json.dumps({'language':language})+'\n',encoding='utf-8')
            temp.replace(self.path)
        self.language=language
        for callback in self.callbacks:callback()


class LocalizedVar(tk.StringVar):
    def __init__(self,*args,**kwargs):
        value=kwargs.pop('value','')
        super().__init__(*args,**kwargs)
        self.locale=self._root.locale
        self.source=value
        self.locale.callbacks.append(self.refresh)
        self.refresh()

    def set(self,value):
        self.source=str(value);self.refresh()

    def refresh(self):
        super().set(self.locale.text(self.source))
