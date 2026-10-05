"""Exercise real Tk views with deterministic camera/music inputs; no music commands."""
import asyncio
import json
import queue
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from datetime import timedelta
from unittest.mock import patch

import numpy as np
from PIL import Image

BASE=Path(__file__).resolve().parents[1]/'outputs'
sys.path.insert(0,str(BASE))
import gesture_music_app as live
from music_display import read_display
from music_ui import SoftButton


async def check_reader():
    manager=SimpleNamespace(get_sessions=lambda:[])
    data,key,cover=await read_display(manager)
    assert not data['connected'] and key is None and cover is None
    properties=SimpleNamespace(title='Test track',artist='Test artist',album_title='Album',track_number=1,thumbnail=None)
    async def media():return properties
    timeline=SimpleNamespace(position=timedelta(seconds=34),start_time=timedelta(),end_time=timedelta(seconds=240))
    controls=SimpleNamespace(is_play_pause_toggle_enabled=True,is_next_enabled=True,is_previous_enabled=False)
    session=SimpleNamespace(source_app_user_model_id='AppleInc.AppleMusicWin_nzyj5cx40ttqa!App',
        try_get_media_properties_async=media,get_playback_info=lambda:SimpleNamespace(controls=controls,playback_status=SimpleNamespace(name='PLAYING')),
        get_timeline_properties=lambda:timeline)
    manager.get_sessions=lambda:[session]
    data,key,cover=await read_display(manager)
    assert data['title']=='Test track' and data['duration_seconds']==240 and cover is None
    assert not data['can_previous'] and data['position_seconds']==34
    manager.get_sessions=lambda:[session,session]
    assert not (await read_display(manager))[0]['connected']


asyncio.run(check_reader())
with patch.object(live.MusicDisplay,'start',lambda self:None):
    app=live.LiveApp()
app.root.update()
ui=app.ui
assert ui.view=='camera' and not app.camera_running and not app.armed
app.gate.latched=True;app.gate.candidate='previous';app.gate.since=123
epoch=app.music.epoch
for view in ('music','settings','camera'):
    ui.show(view);app.root.update()
    assert app.gate.latched and app.gate.candidate=='previous' and app.gate.since==123
    assert app.music.epoch==epoch
    assert ui.pages[view].winfo_ismapped()
app.gate.reset()
ui.set_music({'connected':True,'title':'A very long song title '*6,'artist':'Artist',
    'status':'PLAYING','position_seconds':34,'duration_seconds':240,'cover':Image.new('RGB',(400,400),'#84B3CE'),
    'can_toggle':True,'can_next':True,'can_previous':False})
assert ui.times.get()=='0:34  /  4:00'
assert ui.transport[0][0].state=='disabled' and ui.transport[1][0].state=='normal'
ui.set_music({'connected':False,'message':'Disconnected'})
assert ui.cover_image is None and all(button.state=='disabled' for button,key in ui.transport)
app.camera_running=True;app.last_frame=time.monotonic()
ui.sync_controls();app.toggle_control()
assert app.armed and all(b.text=='พักการควบคุม' for b in ui.controls)
app.toggle_camera()
assert not app.armed and not app.camera_running and app.camera_stop.is_set()
assert all(b.state=='disabled' for b in ui.controls)
app.camera_stop.clear()
class Scores:
    classes_=np.array(['neutral','previous'])
    def predict_proba(self,X):return np.array([[.03,.97]])
app.model=Scores()
coords=[v for i in range(21) for v in (.2+i*.015,.2+i*.01,0)]
app.frames.put({'t':time.monotonic(),'w':640,'h':480,'count':1,'hands':[{'coords':coords}],
                'rgb':np.zeros((480,640,3),dtype=np.uint8)})
app.poll()
assert app.gate.candidate=='previous' and ui.confidence.get()=='97%'
with tempfile.TemporaryDirectory() as temp:
    original=live.BASE;live.BASE=Path(temp)
    try:
        ui.show('settings');ui.settings_values['threshold'].set('85')
        ui.settings_values['hold_seconds'].set('0.8');ui.save_settings()
        assert ui.view=='camera' and app.config['threshold']==.85 and not app.armed
        assert json.loads((Path(temp)/'live_settings.json').read_text())['hold_seconds']==.8
    finally:live.BASE=original
for dimensions in ('1080x820','1220x900'):
    app.root.geometry(dimensions)
    for view in ('camera','music','settings'):
        ui.show(view);app.root.update()
        if view=='settings':
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from descendants(child)
            advanced=next(w for w in descendants(ui.pages['settings']) if isinstance(w,SoftButton) and w.text=='การตั้งค่าเพิ่มเติม')
            advanced.invoke();app.root.update()
            for w in descendants(ui.pages['settings']):
                if isinstance(w,SoftButton) and w.winfo_ismapped():
                    assert w.winfo_height()>=42,(dimensions,w.text,w.winfo_height())
                    assert w.winfo_y()+w.winfo_height()<=w.master.winfo_height(),(dimensions,w.text)
            advanced.invoke();app.root.update()
        for b in [*ui.nav_buttons.values(),ui.read_button]:
            assert b.winfo_rootx()+b.winfo_width()<=app.root.winfo_rootx()+app.root.winfo_width()
            assert b.winfo_rooty()+b.winfo_height()<=app.root.winfo_rooty()+app.root.winfo_height()
app.close()
print('PASS: mode switches preserve gate; camera stop pauses commands; media loss clears art/controls; 95% gate unchanged; settings persist and pause; UI fits minimum and default sizes')
