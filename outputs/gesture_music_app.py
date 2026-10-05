"""Live user-trained classifier with opt-in local music controls."""
import asyncio
import json
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime, timezone, timedelta

import joblib
import cv2
from gesture_collector import Collector
from gesture_features import features, GestureGate, FEATURE_VERSION
from media_connection_probe import run
from control_runtime import ActiveHand,MusicQueue
from live_settings import load_settings,save_settings,validate_settings
from music_ui import MusicUI
from music_display import MusicDisplay
from ui_language import Localizer, LocalizedVar

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
        self.frozen_config=dict(self.config)
        self.runtime_settings=load_settings(BASE/'live_settings.json',self.frozen_config)
        self.config.update(self.runtime_settings)
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
        self.root.locale=Localizer(BASE/'ui_preferences.json')
        self.camera_stop=threading.Event()
        self.camera_thread=None
        self.pose=LocalizedVar(value='รอท่ามือ')
        target=self.config.get('acceptance_policy',{}).get('minimum_command_recall')
        policy_text=f' • เป้าหมายประเมินรุ่น {target:.0%}' if target is not None else ''
        self.score=tk.StringVar(value=f'คะแนนขั้นต่ำรับท่า {self.config["threshold"]:.0%}'+policy_text)
        self.detection=LocalizedVar(value='กล้องยังไม่เปิด')
        self.mode=LocalizedVar(value='โหมดดูผล • ยังไม่ส่งคำสั่งเพลง')
        self.feedback=LocalizedVar(value='กำมือ = เล่น/พัก\nV ชี้–กลาง พับโป้ง = ถัดไป\nนิ้วโป้ง = ก่อนหน้า')
        self.timing_text=LocalizedVar()
        self.refresh_timing_text()
        self.ui=MusicUI(self)
        self.video=self.ui.video
        self.open_button=self.ui.open_button
        self.control_button=self.ui.control_button
        self.read_button=self.ui.read_button
        self.display=MusicDisplay(self.stop)
        self.display.start()
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        self.root.after(40,self.poll)

    def open_camera(self):
        if self.camera_running:return
        if self.camera_thread is not None and self.camera_thread.is_alive():
            self.feedback.set('กำลังปิดกล้องเดิม · รอสักครู่แล้วเปิดอีกครั้ง');return
        while not self.frames.empty():
            try:self.frames.get_nowait()
            except queue.Empty:break
        self.camera_stop.clear()
        self.camera_running=True
        self.detection.set('กำลังเปิดกล้อง…')
        self.ui.sync_controls()
        self.camera_thread=threading.Thread(target=lambda:Collector.camera_worker(self,self.camera_stop),daemon=True)
        self.camera_thread.start()

    def toggle_camera(self):
        if not self.camera_running:
            self.open_camera();return
        self.camera_running=False;self.armed=False;self.camera_stop.set()
        self.music.cancel_pending();self.gate.reset();self.hand_selector.reset()
        self.last_frame=None;self.last_prediction=None
        self.detection.set('กล้องปิด');self.pose.set('รอท่ามือ')
        self.mode.set('โหมดดูผล • กล้องปิด')
        self.ui.camera_off();self.ui.render_gesture(0,time.monotonic())

    def manual_request(self,action):
        if not self.busy and self.ui.music.get('connected'):
            self.request(action)

    def refresh_timing_text(self):
        self.timing_text.set(f'ค้าง {self.config["hold_seconds"]:g} วินาที • ปล่อย {self.config["release_seconds"]:g} วินาที • ค้างมือไม่สั่งซ้ำ')

    def apply_runtime_settings(self,values):
        checked=validate_settings(values)
        save_settings(BASE/'live_settings.json',checked)
        self.armed=False
        self.music.cancel_pending()
        self.hand_selector.reset()
        self.runtime_settings=checked
        self.config.update(checked)
        self.gate=GestureGate(checked['hold_seconds'],checked['release_seconds'],checked['max_frame_gap_seconds'])
        self.last_prediction=None
        self.control_button.configure(text='เริ่มควบคุมเพลง')
        self.mode.set('โหมดดูผล • ใช้ค่ารับท่าที่ปรับเอง')
        self.score.set(f'คะแนนขั้นต่ำรับท่า {checked["threshold"]:.0%} • ค่าขณะใช้งานแยกจากผลประเมินรุ่น')
        self.feedback.set('บันทึกค่ารับท่าแล้ว • ลองในโหมดดูผลก่อนกดเริ่มควบคุมเพลง')
        self.refresh_timing_text()
        self.ui.refresh_settings();self.ui.sync_controls()

    def open_settings(self):
        self.ui.show('settings')

    def toggle_control(self):
        if not self.camera_running or self.last_frame is None:return
        self.armed=not self.armed
        self.music.cancel_pending()
        self.hand_selector.reset()
        self.gate.reset()
        # Starting always requires a release, preventing the current pose from firing.
        self.gate.latched=self.armed
        self.control_button.configure(text='พักการควบคุม' if self.armed else 'เริ่มควบคุมเพลง')
        self.mode.set('ควบคุมเพลงอยู่ • เอามือออกก่อนเริ่ม' if self.armed else 'โหมดดูผล • ยังไม่ส่งคำสั่งเพลง')
        self.feedback.set(f'เอามือออกอย่างน้อย {self.config["release_seconds"]:g} วินาที แล้วทำท่าคำสั่ง' if self.armed else 'ลองทั้งสามท่าได้โดยไม่เปลี่ยนเพลง')

        self.ui.sync_controls()

    def log(self,event):
        event['time']=datetime.now(timezone(timedelta(hours=7))).isoformat()
        event['model']=self.config['selected_model']
        event['runtime_settings']=dict(self.runtime_settings)
        event['settings_match_frozen']=all(self.config[k]==self.frozen_config[k] for k in self.runtime_settings)
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
        self.ui.set_music(self.ui.music)
        self.feedback.set('กำลังอ่าน Apple Music…' if action=='status' else f'รับคำสั่งแล้ว • รอส่ง/ตรวจ {self.pending_count} คำสั่ง\nยังรับท่าปล่อยมือและท่าถัดไปได้')

    def poll(self):
        try:
            frame=self.frames.get_nowait()
            if self.camera_stop.is_set():raise queue.Empty
            if 'error' in frame:
                self.detection.set(frame['error']);self.camera_running=False;self.armed=False
                self.mode.set('กล้องมีปัญหา • หยุดส่งเพลงแล้ว')
                self.control_button.configure(state='disabled',text='เริ่มควบคุมเพลง')
                self.music.cancel_pending()
                self.open_button.configure(state='normal');self.gate.reset()
                self.last_frame=None;self.ui.camera_off()
                self.pose.set('กล้องมีปัญหา');self.ui.render_gesture(0,time.monotonic())
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
                self.ui.render_frame(frame['rgb']);self.ui.sync_controls()
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
                self.ui.render_gesture(score,frame['t'])
        except queue.Empty:pass
        if self.last_frame is not None and time.monotonic()-self.last_frame>self.config['max_frame_gap_seconds']:
            self.gate.update('uncertain',time.monotonic())
            self.pose.set('รอภาพกล้องใหม่')
            self.ui.render_gesture(0,time.monotonic())
        try:
            action,result,error,epoch=self.results.get_nowait()
            self.pending_count=max(0,self.pending_count-1)
            self.busy=self.pending_count>0
            self.read_button.configure(state='disabled' if self.busy else 'normal')
            self.ui.set_music(self.ui.music)
            self.display.refresh.set()
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
                self.feedback.set(prefix+'\n'+state_name)
                self.log({'event':'music_result','action':action,'success':success,'result':result})
        except queue.Empty:pass
        try:self.ui.set_music(self.display.results.get_nowait())
        except queue.Empty:pass
        self.root.after(40,self.poll)

    def close(self):
        self.armed=False
        self.music.cancel_pending()
        self.stop.set()
        self.camera_stop.set()
        self.root.destroy()

if __name__=='__main__':
    try:app=LiveApp()
    except (ValueError,OSError) as error:
        root=tk.Tk();root.withdraw()
        messagebox.showerror('เปิดโปรแกรมไม่สำเร็จ','ตรวจไฟล์ live_settings.json และไฟล์รุ่นที่ใช้\n'+str(error),parent=root)
        root.destroy()
    else:app.root.mainloop()
