"""Local paired live evaluation. No media-control imports or commands."""
import hashlib
import json
import math
import queue
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tkinter as tk
import joblib
from PIL import Image, ImageTk
from gesture_collector import Collector, FONT
from gesture_features import features, GestureGate
from control_runtime import ActiveHand

BASE = Path(__file__).resolve().parent
NAMES = {'toggle':'กำมือ • เล่น/พัก','next':'V ชี้–กลาง พับโป้ง • ถัดไป',
         'previous':'ชูโป้ง พับสี่นิ้ว • ก่อนหน้า','neutral':'แบมือ • ไม่สั่งงาน',
         'three_finger':'ชูโป้ง–ชี้–กลาง • ไม่สั่งงาน','uncertain':'ยังไม่แน่ใจ','no_hand':'ไม่พบมือ'}
VARIANTS = [('old_060','รุ่นเก่า • 0.60','20261004_171415',.6),
            ('new_080','รุ่นใหม่ • 0.80','20261004_221121',.8),
            ('new_060','รุ่นใหม่ • 0.60','20261004_221121',.6)]
TRIALS = [(hand, pose) for hand in ('right','left') for pose in ('toggle','next','previous','neutral','three_finger')]

class Branch:
    def __init__(self, model, threshold, config):
        self.model=model; self.threshold=threshold
        self.config=config
        self.reset()
    def reset(self):
        self.gate=GestureGate(self.config['hold_seconds'],self.config['release_seconds'],self.config['max_frame_gap_seconds'])
        self.gate.latched=True
        self.selector=ActiveHand(); self.count=0
    def update(self, frame):
        classified=[]
        for hand in frame.get('hands',[]):
            value=dict(hand); value.update(label='uncertain',score=0.,raw_label='uncertain')
            try:
                p=self.model.predict_proba([features(hand['coords'],frame['w'],frame['h'])])[0]
                i=int(p.argmax()); value.update(score=float(p[i]),raw_label=str(self.model.classes_[i]))
                value['label']=value['raw_label'] if value['score']>=self.threshold else 'uncertain'
            except ValueError: pass
            classified.append(value)
        active, changed, reason=self.selector.select(classified,frame['t'],not self.gate.latched)
        if changed:
            latched=self.gate.latched; self.gate.reset(); self.gate.latched=latched
        chosen=classified[active] if active is not None else {'label':'uncertain' if reason=='conflict' else 'no_hand','score':0.,'raw_label':None}
        command=self.gate.update(chosen['label'],frame['t'])
        if command: self.count+=1
        return {'label':chosen['label'],'raw_label':chosen['raw_label'],'score':chosen['score'],
                'active_index':active,'selection_reason':reason,'latched':self.gate.latched,
                'candidate':self.gate.candidate,'command':command,'command_count':self.count}

def phase_at(elapsed):
    if elapsed < 3: return 'prepare',None
    if elapsed < 7: return 'hold',1
    if elapsed < 10: return 'release',1
    if elapsed < 14: return 'hold',2
    if elapsed < 17: return 'release',2
    return 'done',None

class ComparisonApp(Collector):
    def __init__(self):
        self.root=tk.Tk(); self.root.title('Hand Gesture Music — Paired Comparison')
        self.root.geometry('1220x800'); self.root.minsize(1080,740); self.root.configure(bg='#101827')
        self.frames=queue.Queue(maxsize=1); self.stop=threading.Event(); self.camera_running=False
        self.index=0; self.running=False; self.started=None; self.session=None; self.stream=None
        self.trial_rows=[]; self.manifest=None; self.last_frame=None; self.stale_sent=False; self.trial_file=None
        self.branches={}; self.cards={}; self.model_info={}
        loaded={}
        for key,title,stamp,threshold in VARIANTS:
            directory=BASE/'models'/stamp
            if stamp not in loaded: loaded[stamp]=joblib.load(directory/'gesture_model.joblib')
            config=json.loads((directory/'selection_frozen.json').read_text(encoding='utf-8'))
            self.branches[key]=Branch(loaded[stamp],threshold,config)
            self.model_info[key]={'directory':stamp,'threshold':threshold,
                'sha256':hashlib.sha256((directory/'gesture_model.joblib').read_bytes()).hexdigest(),
                'gate':{k:config[k] for k in ('hold_seconds','release_seconds','max_frame_gap_seconds')}}
        tk.Label(self.root,text='เทียบสองรุ่นจากมือชุดเดียวกัน',font=(FONT,24,'bold'),bg='#101827',fg='white').pack(anchor='w',padx=24,pady=(16,4))
        tk.Label(self.root,text='คำสั่งจำลอง • บันทึกพิกัดในเครื่อง • ไม่เปลี่ยนเพลง • ใช้ท่าและมุมแบบที่คุณใช้งานจริง',font=(FONT,12),bg='#101827',fg='#93c5fd').pack(anchor='w',padx=24)
        body=tk.Frame(self.root,bg='#101827'); body.pack(fill='both',expand=True,padx=24,pady=12)
        left=tk.Frame(body,bg='#101827'); left.pack(side='left',fill='both',expand=True,padx=(0,20))
        self.video=tk.Label(left,text='เปิดกล้อง แล้วกดเริ่มช่วงทดสอบ\nทำตามข้อความนับถอยหลัง',font=(FONT,17),bg='#1e293b',fg='white'); self.video.pack(fill='both',expand=True)
        self.detection=tk.StringVar(value='กล้องยังไม่เปิด')
        tk.Label(left,textvariable=self.detection,font=(FONT,12),bg='#101827',fg='#67e8f9').pack(anchor='w',pady=6)
        right=tk.Frame(body,bg='#1e293b',width=400,padx=16,pady=12); right.pack(side='right',fill='y'); right.pack_propagate(False)
        self.instruction=tk.StringVar(); self.timer=tk.StringVar(value='ช่วงละ 17 วินาที • ทำท่า 2 ครั้ง สลับแบมือ')
        self.progress=tk.StringVar(value='ยังไม่บันทึก'); self.feedback=tk.StringVar(value='ปิดหน้าควบคุมเพลงเดิมก่อนเปิดกล้อง')
        for variable,size,color in [(self.instruction,17,'white'),(self.timer,15,'#67e8f9'),(self.progress,11,'#cbd5e1')]:
            tk.Label(right,textvariable=variable,font=(FONT,size),bg='#1e293b',fg=color,wraplength=360,justify='left').pack(anchor='w',pady=(0,10))
        for key,title,_,_ in VARIANTS:
            tk.Label(right,text=title,font=(FONT,13,'bold'),bg='#1e293b',fg='#93c5fd').pack(anchor='w')
            variable=tk.StringVar(value='รอภาพกล้อง'); self.cards[key]=variable
            tk.Label(right,textvariable=variable,font=(FONT,12),bg='#1e293b',fg='white',wraplength=360,justify='left').pack(anchor='w',pady=(0,12))
        self.open_button=self.button(right,'เปิดกล้อง',self.open_camera)
        self.record_button=self.button(right,'เริ่มช่วงทดสอบ',self.record); self.record_button.configure(state='disabled')
        tk.Label(right,textvariable=self.feedback,font=(FONT,11),bg='#1e293b',fg='#cbd5e1',wraplength=360,justify='left').pack(anchor='w',pady=6)
        self.update_instruction(); self.root.protocol('WM_DELETE_WINDOW',self.close); self.root.after(40,self.poll)
    def update_instruction(self):
        if self.index>=len(TRIALS):
            self.instruction.set('ทดสอบครบแล้ว • แจ้งว่า “ทดสอบครบแล้ว”'); self.record_button.configure(state='disabled')
            return
        hand,pose=TRIALS[self.index]
        self.instruction.set(f'ช่วง {self.index+1}/10 • มือ'+('ขวา' if hand=='right' else 'ซ้าย')+'\n'+NAMES[pose])
    def record(self):
        if self.running or self.index>=len(TRIALS): return
        if self.last_frame is None or time.monotonic()-self.last_frame>.3:
            self.feedback.set('รอภาพกล้องสดก่อนเริ่ม'); return
        if self.session is None:
            ident=datetime.now(timezone(timedelta(hours=7))).strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
            self.session=BASE/'data'/'live_comparison'/ident; self.session.mkdir(parents=True,exist_ok=False)
            self.manifest={'session_id':ident,'purpose':'paired diagnostic, not training data',
                'models':self.model_info,'trial_plan':TRIALS,'trials':[],
                'label_caveat':'hand/pose are instructed intent, not verified frame-level ground truth; user transition delay is included',
                'camera_pipeline':'same mirrored camera frames, independent ActiveHand and GestureGate branches',
                'saved_media':'landmarks only, no images/audio','complete':False}
        for branch in self.branches.values(): branch.reset()
        self.trial_rows=[]; self.trial_file=f'trial_{self.index+1:02}_{uuid.uuid4().hex[:8]}.jsonl'
        self.stream=(self.session/self.trial_file).open('x',encoding='utf-8')
        self.started=time.monotonic(); self.running=True; self.record_button.configure(state='disabled')
        self.feedback.set('ขยับมุมตามที่ใช้จริง • ใช้มือตามป้าย • อีกข้างอยู่ในภาพได้แต่ไม่ทำคำสั่งแข่งกัน')
        self.write_manifest()
    def write_manifest(self):
        (self.session/'session.json').write_text(json.dumps(self.manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    def finish(self,complete):
        if not self.running:return
        self.stream.close(); self.stream=None; self.running=False
        hand,pose=TRIALS[self.index]
        counts={key:sum(r['branches'][key]['command'] is not None for r in self.trial_rows) for key in self.branches}
        self.manifest['trials'].append({'trial':self.index+1,'hand':hand,'pose':pose,'complete':complete,
            'frame_count':len(self.trial_rows),'command_counts':counts,'file':self.trial_file})
        if complete:self.index+=1
        self.manifest['complete']=self.index==len(TRIALS)
        self.write_manifest(); self.update_instruction()
        self.progress.set(f'บันทึกครบแล้ว {self.index}/10 ช่วง')
        self.feedback.set('บันทึกช่วงนี้แล้ว • กดเริ่มช่วงถัดไปเมื่อพร้อม' if self.index<len(TRIALS) else 'ข้อมูลอยู่ในเครื่องแล้ว • ส่งข้อความ “ทดสอบครบแล้ว”')
        self.record_button.configure(state='normal' if self.camera_running and self.index<len(TRIALS) else 'disabled')
        if not complete:self.feedback.set('ช่วงนี้หยุดก่อนครบ • ข้อมูลเดิมยังอยู่ • เปิดกล้องและลองช่วงเดิมอีกครั้ง')
    def poll(self):
        current=time.monotonic()
        if self.running:
            elapsed=current-self.started; phase,cycle=phase_at(elapsed)
            if phase=='done': self.finish(True)
            else:
                end={'prepare':3,'hold':7 if cycle==1 else 14,'release':10 if cycle==1 else 17}[phase]
                self.timer.set(('แบมือให้เห็นในกล้อง • เตรียม' if phase=='prepare' else 'ทำท่าตามป้าย • ครั้ง '+str(cycle) if phase=='hold' else 'ปล่อยท่า • แบมือให้เห็นในกล้อง')+f'\nอีก {max(1,math.ceil(end-elapsed))} วินาที')
        try:
            frame=self.frames.get_nowait()
            if 'error' in frame:
                self.detection.set(frame['error']); self.camera_running=False; self.last_frame=None
                self.open_button.configure(state='normal'); self.record_button.configure(state='disabled'); self.finish(False)
            else:
                self.last_frame=current; self.stale_sent=False
                results={key:branch.update(frame) for key,branch in self.branches.items()}
                for key,value in results.items():
                    self.cards[key].set(NAMES.get(value['label'],value['label'])+f' • คะแนน {value["score"]:.2f}\n'+('รอปล่อยท่า' if value['latched'] else 'พร้อมรับ / กำลังยืนยันท่า')+f' • คำสั่งจำลอง {value["command_count"]} ครั้ง')
                picture=Image.fromarray(frame['rgb']); picture.thumbnail((max(320,self.video.winfo_width()),max(240,self.video.winfo_height())))
                self.photo=ImageTk.PhotoImage(picture); self.video.configure(image=self.photo,text='')
                self.detection.set(f'พบ {frame["count"]} มือ • ทุกโมเดลได้รับภาพเดียวกัน')
                if not self.running and self.index<len(TRIALS): self.record_button.configure(state='normal')
                if self.running:
                    elapsed=frame['t']-self.started
                    if elapsed>=0:
                        phase,cycle=phase_at(elapsed)
                        row={'elapsed':elapsed,'phase':phase,'cycle':cycle,'trial':self.index+1,'hand_intent':TRIALS[self.index][0],
                            'pose_intent':TRIALS[self.index][1],'w':frame['w'],'h':frame['h'],'hands':frame['hands'],'branches':results}
                        self.stream.write(json.dumps(row,ensure_ascii=False)+'\n'); self.trial_rows.append(row)
        except queue.Empty:pass
        if self.last_frame is not None and current-self.last_frame>.3 and not self.stale_sent:
            for branch in self.branches.values():branch.gate.update('uncertain',current)
            self.stale_sent=True; self.detection.set('ภาพกล้องค้าง • การเปรียบเทียบช่วงนี้หยุดแล้ว')
            if self.running:self.finish(False)
        self.root.after(40,self.poll)
    def close(self):
        self.finish(False); self.stop.set(); self.root.destroy()

if __name__=='__main__': ComparisonApp().root.mainloop()
