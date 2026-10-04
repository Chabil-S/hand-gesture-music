"""Guided, local landmark collection. Labels come from the user, not a recognizer."""
import csv
import argparse
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
from tkinter import messagebox

import cv2
import mediapipe as mp
from PIL import Image, ImageTk

BASE = Path(__file__).resolve().parent
MODEL = BASE / 'assets' / 'hand_landmarker.task'
CLASSES = [
    ('toggle', 'เล่น / พัก', 'กำมือ', 'กำมือหนึ่งข้าง หันด้านนิ้วเข้ากล้อง'),
    ('next', 'เพลงถัดไป', 'ชูสองนิ้ว', 'ชูนิ้วชี้และนิ้วกลาง กางเป็นรูป V'),
    ('previous', 'เพลงก่อนหน้า', 'ชูนิ้วโป้ง', 'กำสี่นิ้วและชูนิ้วโป้งขึ้น'),
    ('neutral', 'ไม่สั่งงาน', 'ท่าอื่น', 'แบมือ / ชูนิ้วชี้ / มือผ่อนคลาย ตามข้อความ'),
]
SPLITS = ['train', 'train', 'train', 'validation', 'test']
EDGES = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
         (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),
         (15,16),(13,17),(0,17),(17,18),(18,19),(19,20)]
COORDS = [f'{axis}{i}' for i in range(21) for axis in 'xyz']
FONT = 'Leelawadee UI'

def now():
    return datetime.now(timezone(timedelta(hours=7))).isoformat()

class Collector:
    def __init__(self, initial_hand='ขวา', negative=False):
        self.negative=negative
        self.classes=[('neutral','ไม่สั่งงาน','ชูสามนิ้ว','ชูโป้ง ชี้ กลาง พร้อมกัน คงท่าและพลิกหน้ามือ/หลังมือช้า ๆ')] if negative else CLASSES
        self.splits=['train','validation','test'] if negative else SPLITS
        self.total=len(self.classes)*len(self.splits)
        self.root = tk.Tk()
        self.root.title('Hand Gesture Music — Data Collection')
        self.root.geometry('1120x710')
        self.root.minsize(1000, 650)
        self.root.configure(bg='#101827')
        self.frames = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.camera_running = False
        self.latest = None
        self.round = 0
        self.gesture = 0
        self.phase = 'idle'
        self.samples = []
        self.clip_start = 0
        self.last_sample = 0
        self.last_frame_sampled = -1
        self.session = None
        self.accepted = 0
        self.seen = set()
        self.title = tk.StringVar()
        self.instruction = tk.StringVar()
        self.progress = tk.StringVar(value=f'เก็บครบ 0 / {self.total} ช่วง • ยังไม่ได้บันทึกข้อมูล')
        self.detection = tk.StringVar(value='กล้องยังไม่เปิด')
        self.timer = tk.StringVar(value='ลองท่าให้เห็นจุดบนมือก่อนบันทึก')
        self.hand = tk.StringVar(value=initial_hand)
        tk.Label(self.root,text='เก็บข้อมูลท่ามือของคุณ',font=(FONT,24,'bold'),
                 bg='#101827',fg='white').pack(anchor='w',padx=28,pady=(20,2))
        tk.Label(self.root,text='ขั้นที่ 2 • เตรียมตัวอย่างสำหรับฝึกโมเดล',font=(FONT,13),
                 bg='#101827',fg='#93c5fd').pack(anchor='w',padx=28)
        body=tk.Frame(self.root,bg='#101827')
        body.pack(fill='both',expand=True,padx=28,pady=16)
        left=tk.Frame(body,bg='#101827')
        left.pack(side='left',fill='both',expand=True,padx=(0,22))
        self.video=tk.Label(left,text='กด “เปิดกล้อง”\nใช้มือข้างเดียวและให้เห็นทั้งมือ',
                            font=(FONT,17),bg='#1e293b',fg='#cbd5e1')
        self.video.pack(fill='both',expand=True)
        tk.Label(left,textvariable=self.detection,font=(FONT,12),bg='#101827',
                 fg='#67e8f9').pack(anchor='w',pady=(10,0))
        tk.Label(left,text='ภาพเป็นกระจก • บันทึกเฉพาะพิกัดมือ • ไม่ส่งคำสั่งเพลง',
                 font=(FONT,11),bg='#101827',fg='#94a3b8').pack(anchor='w',pady=(4,0))
        right=tk.Frame(body,bg='#1e293b',width=330,padx=20,pady=16)
        right.pack(side='right',fill='y')
        right.pack_propagate(False)
        self.label(right,self.title,16,'#f1f5f9',bold=True)
        self.label(right,self.instruction,13,'#cbd5e1')
        self.label(right,self.timer,15,'#93c5fd',bold=True)
        self.label(right,self.progress,11,'#cbd5e1')
        opts=tk.Frame(right,bg='#1e293b')
        opts.pack(fill='x',pady=(8,12))
        tk.Label(opts,text='ใช้มือข้างเดิมตลอด: ',font=(FONT,11),bg='#1e293b',fg='white').pack(side='left')
        self.hand_menu=tk.OptionMenu(opts,self.hand,'ขวา','ซ้าย')
        self.hand_menu.configure(font=(FONT,11),bg='#334155',fg='white',relief='flat')
        self.hand_menu.pack(side='left')
        self.open_button=self.button(right,'เปิดกล้อง',self.open_camera)
        self.record_button=self.button(right,'บันทึกท่านี้ (12 วินาที)',self.record)
        self.record_button.configure(state='disabled')
        self.cancel_button=self.button(right,'ยกเลิกช่วงนี้',self.cancel,color='#475569')
        self.cancel_button.configure(state='disabled')
        self.new_hand_button=self.button(right,'เริ่มชุดใหม่สำหรับอีกข้าง',self.new_hand,color='#0f766e')
        self.new_hand_button.pack_forget()
        self.update_step()
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        self.root.after(40,self.poll)

    def label(self,parent,var,size,color,bold=False):
        tk.Label(parent,textvariable=var,font=(FONT,size,'bold' if bold else 'normal'),
                 bg='#1e293b',fg=color,justify='left',wraplength=288).pack(anchor='w',pady=(0,14))

    def button(self,parent,text,command,color='#2563eb'):
        result=tk.Button(parent,text=text,command=command,font=(FONT,12),bg=color,fg='white',
                         activebackground=color,activeforeground='white',relief='flat',pady=10)
        result.pack(fill='x',pady=(0,8))
        return result

    def update_step(self):
        if self.round>=len(self.splits):
            self.title.set('เก็บข้อมูลครบแล้ว')
            self.instruction.set('ขั้นต่อไป: ตรวจข้อมูล แล้วฝึกและเลือกโมเดล')
            self.record_button.configure(state='disabled')
            self.timer.set('เก็บอีกข้างด้วยปุ่มด้านล่าง เมื่อครบทั้งสองข้างให้แจ้งในแชท' if self.negative else 'ส่งข้อความ “เก็บครบแล้ว” ในแชท')
            self.new_hand_button.pack(fill='x',pady=(0,8))
            return
        purpose={'train':'ชุดฝึก','validation':'ชุดเลือกโมเดล','test':'ชุดทดสอบท้ายงาน'}[self.splits[self.round]]
        _,action,pose,hint=self.classes[self.gesture]
        self.title.set(f'มือ{self.hand.get()} • รอบ {self.round+1}/{len(self.splits)}\n{purpose} • {action} — {pose}')
        self.instruction.set(hint+'\nขยับระยะและมุมเล็กน้อยขณะคงท่าเดิม')

    def new_hand(self):
        if self.phase!='idle' or self.round<len(self.splits): return
        self.hand.set('ซ้าย' if self.hand.get()=='ขวา' else 'ขวา')
        self.session=None
        self.round=0
        self.gesture=0
        self.accepted=0
        self.hand_menu.configure(state='normal')
        self.new_hand_button.pack_forget()
        self.record_button.configure(state='normal' if self.camera_running else 'disabled')
        self.progress.set(f'เก็บครบ 0 / {self.total} ช่วง • ชุดเดิมยังอยู่ครบ')
        self.timer.set('เปลี่ยนมือจริง แล้วลองท่าก่อนบันทึก')
        self.update_step()

    def open_camera(self):
        if self.camera_running:
            return
        self.camera_running=True
        self.open_button.configure(state='disabled')
        self.detection.set('กำลังเปิดกล้องและตัวตรวจมือ…')
        threading.Thread(target=self.camera_worker,daemon=True).start()

    def push(self,value):
        try:
            self.frames.put_nowait(value)
        except queue.Full:
            try: self.frames.get_nowait()
            except queue.Empty: pass
            try: self.frames.put_nowait(value)
            except queue.Full: pass

    def camera_worker(self):
        cap=None
        detector=None
        try:
            cap=cv2.VideoCapture(0,cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                cap=cv2.VideoCapture(0)
            if not cap.isOpened():
                raise RuntimeError('เปิดกล้องไม่ได้ ปิดแอปอื่นที่ใช้กล้องและตรวจสิทธิ์กล้องใน Windows')
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
            options=mp.tasks.vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_hands=2,min_hand_detection_confidence=0.6,
                min_hand_presence_confidence=0.6,min_tracking_confidence=0.6)
            detector=mp.tasks.vision.HandLandmarker.create_from_options(options)
            timestamp=-1
            while not self.stop.is_set():
                ok,frame=cap.read()
                if not ok:
                    raise RuntimeError('อ่านภาพกล้องไม่ได้ กรุณาปิดแล้วเปิดหน้ากล้องใหม่')
                frame=cv2.flip(frame,1)
                rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                timestamp=max(timestamp+1,int(time.monotonic()*1000))
                result=detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb),timestamp)
                h,w=frame.shape[:2]
                for points in result.hand_landmarks:
                    xy=[(int(p.x*w),int(p.y*h)) for p in points]
                    for a,b in EDGES: cv2.line(rgb,xy[a],xy[b],(67,220,200),2)
                    for p in xy: cv2.circle(rgb,p,4,(245,205,75),-1)
                hands=[]
                for index,points in enumerate(result.hand_landmarks):
                    coordinates=[v for p in points for v in (p.x,p.y,p.z)]
                    if all(math.isfinite(v) for v in coordinates):
                        category=result.handedness[index][0]
                        hands.append({'coords':coordinates,'handedness':category.category_name,
                                      'handedness_score':category.score})
                values=None
                handedness=''
                if len(result.hand_landmarks)==1:
                    values=[v for p in result.hand_landmarks[0] for v in (p.x,p.y,p.z)]
                    handedness=result.handedness[0][0].category_name
                    if not all(math.isfinite(v) for v in values): values=None
                self.push({'rgb':rgb,'coords':values,'hands':hands,'count':len(result.hand_landmarks),
                           'handedness':handedness,'w':w,'h':h,'t':time.monotonic()})
        except Exception as error:
            self.push({'error':str(error)})
        finally:
            if cap is not None: cap.release()
            if detector is not None: detector.close()

    def session_init(self):
        if self.session is not None: return
        ident=datetime.now(timezone(timedelta(hours=7))).strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
        self.session=BASE/'data'/'raw'/ident
        self.session.mkdir(parents=True,exist_ok=False)
        metadata={'session_id':ident,'participant':'user_01','declared_hand':self.hand.get(),
                  'created':now(),'round_splits':self.splits,'classes':[x[0] for x in self.classes],
                  'collection_kind':'three_finger_negative' if self.negative else 'base_four_classes',
                  'mirrored':True,'landmarker_sha256':hashlib.sha256(MODEL.read_bytes()).hexdigest(),
                  'record_seconds':12,'sample_interval_seconds':0.125,
                  'minimum_samples':48,'stores_images':False,
                  'split_unit':'session_id + round_id','frame_split_allowed':False}
        with (self.session/'session.json').open('x',encoding='utf-8') as file:
            json.dump(metadata,file,ensure_ascii=False,indent=2)
        self.hand_menu.configure(state='disabled')

    def record(self):
        if self.round>=len(self.splits) or self.phase!='idle': return
        if not self.latest or self.latest.get('coords') is None or time.monotonic()-self.latest['t']>0.5:
            messagebox.showinfo('เตรียมมือ','ให้เห็นมือเพียงข้างเดียวและจุดบนมือก่อนกดบันทึก')
            return
        self.session_init()
        self.samples=[]
        self.seen=set()
        self.phase='countdown'
        self.clip_start=time.monotonic()+3
        self.last_sample=0
        self.last_frame_sampled=-1
        self.record_button.configure(state='disabled')
        self.cancel_button.configure(state='normal')

    def cancel(self):
        if self.phase=='idle': return
        self.finish(False,'cancelled_by_user')

    def finish(self,accepted,reason):
        label=self.classes[self.gesture][0]
        clip_id=f'r{self.round+1:02d}_{label}_{uuid.uuid4().hex[:8]}'
        path=self.session/(clip_id+'.csv')
        with path.open('x',encoding='utf-8',newline='') as file:
            writer=csv.writer(file)
            writer.writerow(['session_id','round_id','split','label','clip_id','timestamp',
                             'elapsed_seconds','handedness','width','height',*COORDS])
            for sample in self.samples:
                writer.writerow([self.session.name,self.round+1,self.splits[self.round],label,clip_id,*sample])
        entry={'clip_id':clip_id,'round_id':self.round+1,'split':self.splits[self.round],
               'label':label,'samples':len(self.samples),'accepted':accepted,'reason':reason,
               'completed':now(),'csv':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        with (self.session/'clips.jsonl').open('a',encoding='utf-8') as file:
            file.write(json.dumps(entry,ensure_ascii=False)+'\n')
        self.phase='idle'
        self.cancel_button.configure(state='disabled')
        self.record_button.configure(state='normal')
        if accepted:
            self.accepted+=1
            self.gesture+=1
            self.timer.set(f'บันทึกแล้ว {len(self.samples)} ตัวอย่าง • เตรียมท่าถัดไป')
            if self.gesture==len(self.classes):
                self.gesture=0
                self.round+=1
                if self.round<len(self.splits):
                    self.timer.set('จบรอบแล้ว • วางมือลงและเปลี่ยนระยะเล็กน้อยก่อนเริ่มรอบใหม่')
        else:
            self.timer.set(f'ช่วงนี้ยังไม่ใช้ฝึก ({len(self.samples)} ตัวอย่าง) • ลองบันทึกท่าเดิมใหม่')
        self.progress.set(f'เก็บครบ {self.accepted} / {self.total} ช่วง • บันทึกไว้ในเครื่องแล้ว')
        self.update_step()

    def poll(self):
        try:
            frame=self.frames.get_nowait()
            if 'error' in frame:
                self.detection.set(frame['error'])
                self.camera_running=False
                self.latest=None
                self.open_button.configure(state='normal')
                if self.phase!='idle': self.finish(False,'camera_error')
                self.record_button.configure(state='disabled')
            else:
                self.latest=frame
                size=(max(320,self.video.winfo_width()),max(240,self.video.winfo_height()))
                picture=Image.fromarray(frame['rgb'])
                picture.thumbnail(size,Image.Resampling.LANCZOS)
                self.photo=ImageTk.PhotoImage(picture)
                self.video.configure(image=self.photo,text='')
                count=frame['count']
                self.detection.set('พบมือ 1 ข้าง • พร้อมเก็บพิกัด' if count==1 else
                                   'ไม่พบมือ • ไม่นำเฟรมนี้ไปฝึก' if count==0 else 'พบหลายมือ • ให้ใช้เพียงข้างเดียว')
                if self.phase=='idle' and self.round<len(self.splits): self.record_button.configure(state='normal')
        except queue.Empty:
            pass
        current=time.monotonic()
        if self.phase=='countdown':
            self.timer.set(f'เตรียมท่า… {max(1,math.ceil(self.clip_start-current))}')
            if current>=self.clip_start: self.phase='recording'
        if self.phase=='recording':
            elapsed=current-self.clip_start
            if elapsed>=12:
                enough=len(self.samples)>=48
                neutral_ok=self.negative or self.gesture!=3 or self.seen=={0,1,2}
                self.finish(enough and neutral_ok,'complete' if enough and neutral_ok else 'too_few_valid_samples_or_missing_neutral_segment')
            else:
                stage=min(2,int(elapsed//4))
                hint='ชูโป้ง ชี้ กลาง • พลิกมือช้า ๆ โดยคงสามนิ้ว' if self.negative else ['แบมือ กางนิ้ว','ชูนิ้วชี้เพียงนิ้วเดียว','มือผ่อนคลาย นิ้วงอเล็กน้อย'][stage] if self.gesture==3 else 'คงท่าเดิม ขยับมุม/ระยะเล็กน้อย'
                self.timer.set(f'กำลังบันทึก • อีก {math.ceil(12-elapsed)} วินาที\n{hint}\nได้ {len(self.samples)} ตัวอย่าง')
                f=self.latest
                if f and f.get('coords') is not None and f['t']!=self.last_frame_sampled and current-f['t']<0.3 and current-self.last_sample>=0.125:
                    self.last_sample=current
                    self.last_frame_sampled=f['t']
                    self.samples.append([now(),round(elapsed,4),f['handedness'],f['w'],f['h'],*f['coords']])
                    self.seen.add(stage)
        self.root.after(40,self.poll)

    def close(self):
        if self.phase!='idle': self.finish(False,'window_closed_during_capture')
        self.stop.set()
        self.root.destroy()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--hand',choices=['right','left'],default='right')
    parser.add_argument('--negative',action='store_true')
    options=parser.parse_args()
    Collector('ซ้าย' if options.hand=='left' else 'ขวา',options.negative).root.mainloop()
