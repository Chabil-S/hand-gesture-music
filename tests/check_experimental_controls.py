"""Experimental opt-in, preview/control isolation and routing on the real Tk app."""
import sys
import time
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
import gesture_music_app as live
from ui_language import Localizer

with patch.object(live,'Localizer',lambda path:Localizer(None,'th')), \
     patch.object(live.MusicDisplay,'start',lambda self:None), \
     patch.object(live.VolumeWorker,'start',lambda self:None):
    app=live.LiveApp()
ui=app.ui;app.root.update()
app.log=lambda event:None
assert not app.volume_mode and not app.palm_enabled
assert all(not group.winfo_manager() for group in ui.volume_groups)
calls=[];app.volume.submit=lambda delta=None:calls.append(delta)
ui.set_music({'connected':True,'title':'Test','artist':'Artist','status':'PLAYING'})
app.camera_running=True;app.last_frame=time.monotonic()
config=dict(app.runtime_settings)
app.set_experimental(True,False)
assert not app.armed and app.runtime_settings==config and calls==[None]
sample=lambda a:{'pinch_pose':True,'aperture':a,'open_palm':False}
for i in range(11):assert app.process_dynamic(sample(.15),i*.05)
for i in range(16):app.process_dynamic(sample(.15+i*.025),.55+i*.05)
assert calls==[None]  # preview never changes actual volume
app.volume_available=True;app.toggle_control();assert app.armed
for i in range(11):app.process_dynamic(sample(.15),2+i*.05)
for i in range(16):app.process_dynamic(sample(.15+i*.025),2.55+i*.05)
assert any(d is not None and 0<d<=.03 for d in calls)
app.toggle_control();old=len(calls)
for i in range(11):app.process_dynamic(sample(.15),4+i*.05)
for i in range(16):app.process_dynamic(sample(.15+i*.025),4.55+i*.05)
assert len(calls)==old
app.set_experimental(False,True)
for i in range(9):app.process_dynamic(None,6+i*.05)
palm={'open_palm':True,'pinch_pose':False,'aperture':1}
for i in range(40):assert app.process_dynamic(palm,6.5+i*.05)
assert app.armed
for i in range(30):app.process_dynamic(palm,8.5+i*.05)
assert app.armed  # no repeated toggle while held
for i in range(9):app.process_dynamic(None,10+i*.05)
for i in range(40):app.process_dynamic(palm,10.5+i*.05)
assert not app.armed

# Palm priority must block a music command even if the trained classifier says fist.
class Model:
    classes_=np.array(['toggle'])
    def predict_proba(self,X):return np.array([[1.]])
app.model=Model();app.set_experimental(False,True)
app.armed=True;app.palm.reset(require_release=False)
app.hand_selector.wrist=np.array([.5,.5])
music=[];app.request=lambda action:music.append(action)
points=np.zeros((21,3));points[:,0]=.5;points[:,1]=.5;points[9,1]=.6;points[5,0]=.4;points[17,0]=.6
with patch.object(live,'geometry',lambda *args:palm):
    for i in range(22):
        app.frames.put({'t':20+i*.05,'w':640,'h':480,'count':1,'hands':[{'coords':points.reshape(-1).tolist()}],
                        'rgb':np.zeros((480,640,3),dtype=np.uint8)})
        app.poll()
assert not music

# Reusable dialog and both languages, including the hidden language shortcut.
for language in ('th','en'):
    app.root.locale.set_language(language,persist=False)
    for size in ('1080x820','1220x900'):
        app.root.geometry(size);ui.show('settings');ui.open_experimental();app.root.update()
        window=ui.experimental_window
        for child in window.winfo_children()[0].winfo_children():
            assert child.winfo_y()+child.winfo_height()<=child.master.winfo_height(),(language,child.winfo_class())
        window.withdraw()
        app.set_experimental(True,True);ui.show('camera');app.root.update()
        app.last_volume={'available':True,'level':.45,'muted':True}
        app.pinch.active=True
        app.volume_feedback.set('กางเพิ่ม · หุบลด · เอามือออกเพื่อจบ')
        ui.sync_controls();ui.render_gesture(0,time.monotonic());app.root.update()
        for group in ui.volume_groups:
            if group.winfo_viewable():
                assert group.winfo_rooty()+group.winfo_height()<=app.root.winfo_rooty()+app.root.winfo_height()
                assert group.winfo_y()+group.winfo_height()<=group.master.winfo_height()
        ui.show('music');app.root.update()
        assert ui.expand_camera_button.winfo_height()>=42,(language,size,ui.expand_camera_button.winfo_height(),ui.expand_camera_button.master.winfo_height(),app.pose.get(),app.volume_feedback.get())
        assert ui.expand_camera_button.winfo_y()+ui.expand_camera_button.winfo_height()<=ui.expand_camera_button.master.winfo_height()
        ui.toggle_language();app.root.update()
app.set_experimental(False,False);assert app.runtime_settings==config
app.close()
print('PASS: opt-in, preview isolation, bounded armed volume, palm pause/resume, no repeated toggle, routing priority, bilingual layout')
