"""Palm progress/confirmation in both views, with and without pinch mode."""
import sys,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
import gesture_music_app as live
from ui_language import Localizer

with patch.object(live,'Localizer',lambda path:Localizer(None,'th')), \
     patch.object(live.MusicDisplay,'start',lambda self:None), \
     patch.object(live.VolumeWorker,'start',lambda self:None):
    app=live.LiveApp()
app.log=lambda event:None
ui=app.ui;app.camera_running=True;app.last_frame=time.monotonic()
ui.set_music({'connected':True,'title':'Track','artist':'Artist','status':'PLAYING'})
app.root.geometry('1080x820');app.root.update()
palm={'open_palm':True,'pinch_pose':False,'aperture':2.}
for volume in (False,True):
    for language in ('th','en'):
        app.root.locale.set_language(language,persist=False)
        app.set_experimental(volume,True)
        app.process_dynamic(palm,0)
        assert app.palm_feedback['state']=='release' and app.palm_feedback['progress']==0
        for i in range(9):app.process_dynamic(None,.1+i*.05)
        for i in range(13):app.process_dynamic(palm,.6+i*.05)
        assert app.palm_feedback['state']=='holding'
        assert .45<=app.palm_feedback['progress']<=.55
        for view in ('camera','music'):
            app.last_frame=time.monotonic()
            ui.show(view);ui.sync_controls();ui.render_gesture(0,1.2);app.root.update()
            bar=ui.hold_bar if view=='camera' else ui.palm_bars[0]
            coords=bar.coords(bar.find_all()[0])
            assert .45<=coords[2]/bar.winfo_width()<=.55
            assert '0.6 / 1.2' in (ui.hold.get() if view=='camera' else ui.palm_indicator.get())
            if view=='music':
                assert ui.palm_groups[0].winfo_viewable()
                assert ui.expand_camera_button.winfo_height()>=42
            assert all(not group.winfo_manager() for group in ui.volume_groups)
        app.last_frame=time.monotonic()
        for i in range(1,15):app.process_dynamic(palm,1.2+i*.05)
        assert app.armed and app.palm_feedback['state']=='confirmed'
        app.process_dynamic(palm,1.95)
        assert app.armed and app.palm_feedback['state']=='confirmed'
        ui.sync_controls();ui.render_gesture(0,1.95)
        assert 'Gestures enabled' in ui.hold.get() if language=='en' else 'เริ่มควบคุมแล้ว' in ui.hold.get()
        for i in range(9):app.process_dynamic(None,2+i*.05)
        for i in range(27):app.process_dynamic(palm,2.5+i*.05)
        assert not app.armed and app.palm_feedback['state']=='confirmed'
        ui.render_gesture(0,3.8)
        assert 'Gestures paused' in ui.hold.get() if language=='en' else 'พักการควบคุมแล้ว' in ui.hold.get()
        app.reset_dynamic();ui.sync_controls()
        assert not app.palm_feedback['reserved']
        assert all(not group.winfo_manager() for group in ui.palm_groups)
app.palm_feedback={'reserved':True,'progress':1.,'state':'confirmed'}
ui.sync_controls();app.last_frame=time.monotonic()-.5
app.poll()
assert not app.palm_feedback['reserved']
assert all(not group.winfo_manager() for group in ui.palm_groups)
app.close()
print('PASS: release is not completion; palm loading and persistent confirmation in both views/languages/modes; pause and reset')
