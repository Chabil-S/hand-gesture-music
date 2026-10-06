"""Mixed real-app command sequences; synthetic geometry, no music/volume writes."""
import sys,time,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
import gesture_music_app as live
from ui_language import Localizer
from gesture_options import load_options

with patch.object(live,'Localizer',lambda path:Localizer(None,'th')), \
     patch.object(live,'load_options',lambda path:{'volume_enabled':True,'palm_enabled':True}), \
     patch.object(live.MusicDisplay,'start',lambda self:None), \
     patch.object(live.VolumeWorker,'start',lambda self:None):
    app=live.LiveApp()
app.log=lambda event:None
ui=app.ui;app.root.update()
assert app.volume_enabled and app.palm_enabled and not app.armed
assert all(not group.winfo_manager() for group in ui.volume_groups)
config=dict(app.runtime_settings)
app.camera_running=True;app.last_frame=time.monotonic()
ui.set_music({'connected':True,'title':'Test track','artist':'Artist','status':'PLAYING'})
music=[];volume=[]
app.request=lambda action:music.append(action)
app.volume.submit=lambda delta=None:volume.append(delta)
app.volume_available=True

class Model:
    classes_=np.array(['neutral','toggle','next','previous'])
    labels=[]
    def predict_proba(self,X):
        scores=np.zeros(4);scores[list(self.classes_).index(self.labels.pop(0))]=1.
        return np.array([scores])
app.model=Model()
clock=0.
def pinch(distance):return {'pinch_pose':True,'open_palm':False,'aperture':distance}
palm={'pinch_pose':False,'open_palm':True,'aperture':2.}
def feed(hands):
    global clock
    clock+=.05
    app.model.labels=[label for x,label,sample in hands]
    shapes={round(x,3):sample for x,label,sample in hands}
    data=[]
    for x,label,sample in hands:
        points=np.zeros((21,3));points[:,0]=x;points[:,1]=.5
        points[9,1]=.6;points[5,0]=x-.08;points[17,0]=x+.08
        data.append({'coords':points.reshape(-1).tolist()})
    frame={'t':clock,'w':640,'h':480,'count':len(data),'hands':data,'rgb':np.zeros((480,640,3),dtype=np.uint8)}
    with patch.object(live,'geometry',lambda coords,*args:shapes[round(coords[0],3)]):
        app.frames.put(frame)
        with patch.object(app.root,'after',lambda *args:None):app.poll()
def hold(label,sample=None,frames=15):
    for i in range(frames):feed([(.3,label,sample)])
def release():
    for i in range(11):feed([])

# A first palm following a startup release can enable control, without a second release cycle.
release();hold('toggle',palm,28)
assert app.armed and not music and app.palm_feedback['state']=='confirmed'
release();hold('toggle',frames=30)
assert music==['toggle']
release();hold('next',frames=18)
assert music==['toggle','next']
release();hold('toggle',pinch(.15),12)  # classifier intentionally wrong: geometry reserves pinch
assert app.pinch.active and music==['toggle','next']
for i in range(45):hold('toggle',pinch(.15+i*.05),1)
assert any(delta is not None and delta>0 for delta in volume)
assert app.pinch.active and not any(action=='toggle' for action in music[1:])
before=len(volume)
for i in range(45):hold('toggle',pinch(2.35-i*.045),1)
assert any(delta is not None and delta<0 for delta in volume[before:])
assert all(abs(delta)<=.03 for delta in volume if delta is not None)

# Closing into a fist cannot immediately toggle playback; release makes song gestures available.
hold('toggle',frames=25)
assert music==['toggle','next']
release();hold('previous',frames=18)
assert music==['toggle','next','previous_track']

# A held song command also needs release before beginning a pinch.
before=len(volume);hold('toggle',pinch(.15),15)
assert app.pinch_feedback['state']=='release' and not app.pinch.active
assert not any(delta is not None for delta in volume[before:])
release();hold('toggle',pinch(2.35),12)
assert app.pinch.active
for i in range(20):hold('toggle',pinch(2.35-i*.05),1)
assert any(delta is not None and delta<0 for delta in volume[before:])

# Pause stops both command kinds, while a deliberate palm can enable them again.
release();hold('toggle',palm,28)
assert not app.armed
before_music=list(music);before=len(volume)
release();hold('toggle',frames=18)
release();hold('toggle',pinch(.15),12)
for i in range(20):hold('toggle',pinch(.15+i*.03),1)
assert music==before_music and not any(delta is not None for delta in volume[before:])
release();hold('toggle',palm,28)
assert app.armed
release();hold('toggle',frames=18)
assert music==before_music+['toggle']

# Other neutral hands and changes of detection order preserve the active pinch.
release()
hold('neutral',pinch(.5),15)  # relaxed partial pinch never activates
assert not app.gate.latched and not app.pinch.active
before_music=list(music)
hold('toggle',frames=18)
assert music==before_music+['toggle']
release();hold('neutral',pinch(.15),3)
assert not app.gate.latched  # brief entry is also not a confirmed command
hold('toggle',frames=18)
assert music==before_music+['toggle','toggle']
release();hold('neutral',palm,3)
assert not app.gate.latched
hold('previous',frames=18)
assert music[-1]=='previous_track'

# Slow camera absence releases the latch; idle ticks alone never do so.
release();app.gate.reset();app.gate.latched=True
feed([])
release_started=app.gate.release_since
app.last_frame=time.monotonic()-1.
with patch.object(app.root,'after',lambda *args:None):app.poll()
assert app.gate.latched and app.gate.release_since==release_started
clock+=.4;feed([])
assert not app.gate.latched


release()
for i in range(13):feed([(.3,'neutral',pinch(.15)),(.8,'neutral',None)])
assert app.pinch.active
for i in range(12):feed([(.8,'neutral',None),(.3,'neutral',pinch(.15+i*.03))])
assert app.pinch.active
before_music=list(music);before=len(volume)
feed([(.3,'neutral',pinch(.8)),(.8,'next',None)])
assert not app.pinch.active and music==before_music
assert not any(delta is not None for delta in volume[before:])

# Independent options persist, without writing model thresholds or user preference files.
with tempfile.TemporaryDirectory() as temp:
    with patch.object(live,'BASE',Path(temp)):
        app.set_gesture_options(False,True)
        assert load_options(Path(temp)/'gesture_options.json')=={'volume_enabled':False,'palm_enabled':True}
    assert not app.volume_enabled and app.palm_enabled and not app.armed
assert app.runtime_settings==config
app.set_gesture_options(True,True,persist=False)

# Normal and active gesture surfaces, options dialog, both languages at minimum/default sizes.
for language in ('th','en'):
    app.root.locale.set_language(language,persist=False)
    for size in ('1080x820','1220x900'):
        app.root.geometry(size)
        for state in ('waiting','hold','active','release'):
            app.last_frame=time.monotonic()
            app.pinch_feedback={'state':state,'delta':None}
            app.pinch.active=state=='active'
            app.volume_feedback.set('กางเพิ่ม · หุบลด · เอามือออกเพื่อจบ')
            app.last_volume={'available':True,'level':.45,'muted':True}
            app.palm_feedback={'reserved':False,'progress':0.,'state':'waiting'}
            ui.sync_controls()
            for view in ('camera','music'):
                app.last_frame=time.monotonic();ui.show(view);app.root.update()
                for group in ui.volume_groups:
                    if group.winfo_viewable():
                        assert group.winfo_y()+group.winfo_height()<=group.master.winfo_height()
                if view=='music':assert ui.expand_camera_button.winfo_height()>=42
        ui.show('settings');ui.open_gesture_options();app.root.update()
        for child in ui.gesture_options_window.winfo_children()[0].winfo_children():
            assert child.winfo_y()+child.winfo_height()<=child.master.winfo_height()
        ui.gesture_options_window.withdraw()
app.close()
print('PASS: song/pinch/palm mixed sequences, release boundaries, preview and pause, multi-hand conflicts, persistence, bilingual layout')
