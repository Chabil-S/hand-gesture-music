"""Live user-trained classifier with opt-in local music controls."""
import asyncio
import json
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from datetime import datetime, timezone, timedelta

import joblib
import cv2
from PIL import Image, ImageTk
from gesture_collector import Collector, FONT
from gesture_features import features, GestureGate, FEATURE_VERSION
from media_connection_probe import run
from control_runtime import ActiveHand,MusicQueue

BASE=Path(__file__).resolve().parent
NAMES={'neutral':'ไม่สั่งงาน','next':'ถัดไป','previous':'ก่อนหน้า','toggle':'เล่น / พัก',
       'uncertain':'ยังไม่แน่ใจ','no_hand':'ไม่พบมือ'}
LOG=BASE/'live_command_events.jsonl'

class LiveApp(Collector):
    def __init__(self):
        directory=BASE/json.loads((BASE/'latest_model.json').read_text(encoding='utf-8'))['directory']
        self.config=json.loads((directory/'selection_frozen.json').read_text(encoding='utf-8'))
        if self.config.get('eligible_for_activation') is False:
            raise RuntimeError('รุ่นนี้ใช้เปรียบเทียบกล้องเท่านั้น ยังไม่ผ่านเกณฑ์สำหรับควบคุมเพลง')
        if self.config['feature_version']!=FEATURE_VERSION: raise RuntimeError('Feature version mismatch')
        self.model=joblib.load(directory/'gesture_model.joblib')
        self.gate=GestureGate(self.config['hold_seconds'],self.config['release_seconds'],self.config['max_frame_gap_seconds'])
        self.frames=queue.Queue(maxsize=1)
        self.results=queue.Queue()
        self.music=MusicQueue(lambda action:asyncio.run(run(action)),self.results)
        self.hand_selector=ActiveHand()
        self.pending_count=0
        self.stop=threading.Event()
        self.camera_running=False
        self.armed=False
        self.busy=False
        self.last_frame=None
        self.last_prediction=None
        self.root=tk.Tk()
        self.root.title('Hand Gesture Music — Live Demo')
        self.root.geometry('1120x710')
        self.root.minsize(1000,650)
        self.root.configure(bg='#101827')
        self.pose=tk.StringVar(value='เปิดกล้องเพื่อลองท่า')
        target=self.config.get('acceptance_policy',{}).get('minimum_command_recall')
        policy_text=f' • เป้าหมายประเมินรุ่น {target:.0%}' if target is not None else ''
        self.score=tk.StringVar(value=f'คะแนนขั้นต่ำรับท่า {self.config["threshold"]:.0%}'+policy_text)
        self.detection=tk.StringVar(value='กล้องยังไม่เปิด')
        self.mode=tk.StringVar(value='โหมดดูผล • โมเดล '+directory.name)
        self.feedback=tk.StringVar(value='กำมือ = เล่น/พัก\nV ชี้–กลาง พับโป้ง = ถัดไป\nนิ้วโป้ง = ก่อนหน้า')
        tk.Label(self.root,text='ควบคุมเพลงด้วยท่าทางมือ',font=(FONT,24,'bold'),bg='#101827',fg='white').pack(anchor='w',padx=28,pady=(20,2))
        tk.Label(self.root,text='ขั้นที่ 3 • ทดลองโมเดลของคุณกับกล้องสด',font=(FONT,13),bg='#101827',fg='#93c5fd').pack(anchor='w',padx=28)
        body=tk.Frame(self.root,bg='#101827'); body.pack(fill='both',expand=True,padx=28,pady=16)
        left=tk.Frame(body,bg='#101827'); left.pack(side='left',fill='both',expand=True,padx=(0,22))
        self.video=tk.Label(left,text='กดเปิดกล้อง\nกรอบสีเขียวคือมือที่ระบบรับคำสั่ง',font=(FONT,17),bg='#1e293b',fg='#cbd5e1')
        self.video.pack(fill='both',expand=True)
        tk.Label(left,textvariable=self.detection,font=(FONT,12),bg='#101827',fg='#67e8f9').pack(anchor='w',pady=(8,0))
        tk.Label(left,text='คงท่า 0.6 วินาที • ค้างมือไม่สั่งซ้ำ • เอามือออกก่อนท่าถัดไป',font=(FONT,11),bg='#101827',fg='#94a3b8').pack(anchor='w',pady=(4,0))
        right=tk.Frame(body,bg='#1e293b',width=330,padx=20,pady=16);right.pack(side='right',fill='y');right.pack_propagate(False)
        for var,size,color in [(self.mode,13,'#93c5fd'),(self.pose,22,'white'),(self.score,11,'#94a3b8'),(self.feedback,13,'#e2e8f0')]:
            tk.Label(right,textvariable=var,font=(FONT,size),bg='#1e293b',fg=color,wraplength=288,justify='left').pack(anchor='w',pady=(0,16))
        self.open_button=self.button(right,'เปิดกล้อง',self.open_camera)
        self.control_button=self.button(right,'เริ่มควบคุมเพลง',self.toggle_control,color='#0f766e')
        self.control_button.configure(state='disabled')
        self.read_button=self.button(right,'อ่านสถานะ Apple Music',lambda:self.request('status'))
        tk.Label(right,text='เปิด Apple Music และคิวเพลงไว้\nโหมดดูผลใช้ลองท่าโดยไม่เปลี่ยนเพลง\nถ้าจุดผิด ให้ขยับมือหรือปรับแสง',font=(FONT,11),bg='#1e293b',fg='#94a3b8',justify='left').pack(anchor='w',pady=10)
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        self.root.after(40,self.poll)

    def open_camera(self):
        if self.camera_running:return
        self.camera_running=True
        self.open_button.configure(state='disabled')
        self.detection.set('กำลังเปิดกล้อง…')
        threading.Thread(target=self.camera_worker,daemon=True).start()

    def toggle_control(self):
        self.armed=not self.armed
        self.music.cancel_pending()
        self.hand_selector.reset()
        self.gate.reset()
        # Starting always requires a release, preventing the current pose from firing.
        self.gate.latched=self.armed
        self.control_button.configure(text='พักการควบคุม' if self.armed else 'เริ่มควบคุมเพลง')
        self.mode.set('ควบคุมเพลงอยู่ • เอามือออกก่อนเริ่ม' if self.armed else 'โหมดดูผล • ยังไม่ส่งคำสั่งเพลง')
        self.feedback.set('เอามือออกอย่างน้อย 0.35 วินาที แล้วทำท่าคำสั่ง' if self.armed else 'ลองทั้งสามท่าได้โดยไม่เปลี่ยนเพลง')

    def log(self,event):
        event['time']=datetime.now(timezone(timedelta(hours=7))).isoformat()
        event['model']=self.config['selected_model']
        with LOG.open('a',encoding='utf-8') as file:file.write(json.dumps(event,ensure_ascii=False)+'\n')

    def request(self,action):
        try:self.music.submit(action)
        except queue.Full:
            self.feedback.set('คิวเต็ม • คำสั่งนี้ยังไม่ถูกส่ง กรุณารอแล้วปล่อยท่าก่อนลองใหม่')
            self.log({'event':'queue_full','action':action})
            return
        self.pending_count+=1
        self.busy=True
        self.read_button.configure(state='disabled')
        self.feedback.set('กำลังอ่าน Apple Music…' if action=='status' else f'รับคำสั่งแล้ว • รอส่ง/ตรวจ {self.pending_count} คำสั่ง\nยังรับท่าปล่อยมือและท่าถัดไปได้')

    def poll(self):
        try:
            frame=self.frames.get_nowait()
            if 'error' in frame:
                self.detection.set(frame['error']);self.camera_running=False;self.armed=False
                self.mode.set('กล้องมีปัญหา • หยุดส่งเพลงแล้ว')
                self.control_button.configure(state='disabled',text='เริ่มควบคุมเพลง')
                self.music.cancel_pending()
                self.open_button.configure(state='normal');self.gate.reset()
            else:
                self.last_frame=time.monotonic()
                classified=[]
                for hand in frame.get('hands',[]):
                    prediction=dict(hand);prediction['label']='uncertain';prediction['score']=0
                    try:
                        vector=features(hand['coords'],frame['w'],frame['h'])
                        prob=self.model.predict_proba([vector])[0]
                        index=int(prob.argmax());prediction['score']=float(prob[index])
                        raw_label=str(self.model.classes_[index])
                        prediction['label']=raw_label if prediction['score']>=self.config['threshold'] else 'uncertain'
                    except ValueError:pass
                    classified.append(prediction)
                active,changed,reason=self.hand_selector.select(classified,frame['t'],not self.gate.latched)
                if changed:
                    # A different hand must complete its own confirmation period.
                    latched=self.gate.latched
                    self.gate.reset();self.gate.latched=latched
                if active is not None:
                    hand=classified[active];label=hand['label'];score=hand['score']
                    points=hand['coords'];xs=points[0::3];ys=points[1::3]
                    cv2.rectangle(frame['rgb'],(int(min(xs)*frame['w'])-10,int(min(ys)*frame['h'])-10),
                                  (int(max(xs)*frame['w'])+10,int(max(ys)*frame['h'])+10),(55,235,130),3)
                else:
                    label='uncertain' if reason=='conflict' else 'no_hand';score=0
                picture=Image.fromarray(frame['rgb'])
                picture.thumbnail((max(320,self.video.winfo_width()),max(240,self.video.winfo_height())),Image.Resampling.LANCZOS)
                self.photo=ImageTk.PhotoImage(picture);self.video.configure(image=self.photo,text='')
                self.control_button.configure(state='normal')
                self.pose.set(NAMES[label])
                target=self.config.get('acceptance_policy',{}).get('minimum_command_recall')
                policy_text=f' • เป้าหมายประเมินรุ่น {target:.0%}' if target is not None else ''
                self.score.set((f'คะแนนโมเดล {score:.2f} • คะแนนขั้นต่ำรับท่า {self.config["threshold"]:.0%}' if score else 'ยังไม่มีพิกัดมือที่ใช้จำแนกได้')+policy_text)
                self.detection.set('สองมือสั่งต่างกัน • รอให้เหลือท่าคำสั่งเดียว' if reason=='conflict'
                                   else f'พบ {frame["count"]} มือ • รับจากมือกรอบสีเขียว' if active is not None
                                   else 'รอมือสั่งงานกลับมา' if frame['count'] else 'ไม่พบมือ')
                command=self.gate.update(label,frame['t'])
                if command:
                    if self.armed:
                        self.log({'event':'gesture_confirmed','action':command,'score':score,'mode':'control'})
                        self.request('previous_track' if command=='previous' else command)
                    else:
                        self.feedback.set('ยืนยันท่า: '+NAMES[command]+'\nโหมดดูผล • ไม่ส่งเพลง\nเอามือออก แล้วลองท่าถัดไป')
                        self.log({'event':'gesture_confirmed','action':command,'score':score,'mode':'preview'})
                elif self.gate.latched and not self.busy and self.last_prediction!=label and label not in ('no_hand','neutral'):
                    self.feedback.set('ปล่อยท่าก่อน: เอามือออก หรือทำท่าไม่สั่งงาน\nค้างมือหรือเปลี่ยนท่าคำสั่งทันทีจะไม่สั่งซ้ำ')
                self.last_prediction=label
        except queue.Empty:pass
        if self.last_frame is not None and time.monotonic()-self.last_frame>0.3:
            self.gate.update('uncertain',time.monotonic())
            self.pose.set('รอภาพกล้องใหม่')
        try:
            action,result,error,epoch=self.results.get_nowait()
            self.pending_count=max(0,self.pending_count-1)
            self.busy=self.pending_count>0
            self.read_button.configure(state='disabled' if self.busy else 'normal')
            if epoch!=self.music.epoch:
                self.log({'event':'music_result_after_pause','action':action,'result':result,'error':error})
            elif error:
                self.feedback.set('ส่งคำสั่งไม่สำเร็จ\nเปิด Apple Music และเริ่มเพลงไว้\n'+error)
                self.log({'event':'music_result','action':action,'error':error,'success':False})
            else:
                state=result.get('after',result['before'])
                state_name={'PLAYING':'กำลังเล่น','PAUSED':'พักเพลง'}.get(state['status'],state['status'])
                success=result.get('observed_success')
                prefix='อ่านสถานะแล้ว' if action=='status' else 'ตรวจพบผลคำสั่งแล้ว' if success else 'ยังไม่ยืนยันผล โปรดดูเครื่องเล่น'
                self.feedback.set(prefix+'\n'+state['title']+'\n'+state_name)
                self.log({'event':'music_result','action':action,'success':success,'result':result})
        except queue.Empty:pass
        self.root.after(40,self.poll)

    def close(self):
        self.armed=False
        self.music.cancel_pending()
        self.stop.set()
        self.root.destroy()

if __name__=='__main__':LiveApp().root.mainloop()
