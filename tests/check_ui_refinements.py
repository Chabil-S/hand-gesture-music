"""Language, numeric controls and metadata checks without touching live preferences."""
import sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
import gesture_music_app as live
from ui_language import Localizer
from music_ui import SoftButton,NumberField,ModernSlider

with tempfile.TemporaryDirectory() as temp:
    prefs=Path(temp)/'preferences.json'
    locale=Localizer(prefs,'th')
    with patch.object(live,'Localizer',lambda path:locale),patch.object(live.MusicDisplay,'start',lambda self:None):
        app=live.LiveApp()
    ui=app.ui
    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)
    app.root.update()
    assert int(ui.mini_cover.cget('borderwidth'))==0
    assert int(ui.mini_cover.cget('highlightthickness'))==0
    data={'connected':True,'title':'กำลังเล่น','artist':'ศิลปินไทย','album':'อัลบั้มทดสอบ',
          'status':'PLAYING','position_seconds':84,'duration_seconds':222,
          'cover':Image.new('RGB',(40,40),'#84B3CE'),'can_toggle':True,'can_next':True,'can_previous':True}
    ui.set_music(data)
    assert 'ศิลปินไทย' in ui.mini_details.get() and '1:24' in ui.mini_status.get()
    app.gate.latched=True;app.gate.since=321;epoch=app.music.epoch
    ui.show('settings');ui.settings_values['threshold'].set('85.5')
    ui.toggle_language()
    assert locale.language=='en' and Localizer(prefs).language=='en'
    assert ui.settings_values['threshold'].get()=='85.5'
    assert app.gate.latched and app.gate.since==321 and app.music.epoch==epoch
    assert ui.title.get()=='กำลังเล่น' and ui.artist.get()=='ศิลปินไทย'
    assert ui.playback.get()=='Playing' and ui.nav_buttons['settings'].display_text=='Settings'
    app.pose.set('ยังไม่แน่ใจ');assert app.pose.get()=='Uncertain'
    app.detection.set('พบ 2 มือ • รับจากมือกรอบสีเขียว');assert '2 hand(s)' in app.detection.get()
    app.feedback.set('ยืนยันท่า: ก่อนหน้า');assert app.feedback.get()=='Confirmed: Previous'
    ui.threshold_slider.change(92);assert ui.settings_values['threshold'].get()=='92'
    ui.settings_values['threshold'].set('98.5');assert ui.threshold_slider.get()==98.5
    ui.threshold_slider.change(110);assert ui.settings_values['threshold'].get()=='100'
    for language in ('th','en'):
        locale.set_language(language)
        for size in ('1080x820','1220x900'):
            app.root.geometry(size)
            for view in ('camera','music','settings'):
                ui.show(view);app.root.update()
                if view=='settings':
                    advanced=next(w for w in descendants(ui.pages[view]) if isinstance(w,SoftButton) and w.text=='การตั้งค่าเพิ่มเติม')
                    advanced.invoke();app.root.update()
                for widget in descendants(ui.pages[view]):
                    if isinstance(widget,(SoftButton,NumberField)) and widget.winfo_ismapped():
                        assert widget.winfo_height()>=42,(language,size,view,getattr(widget,'text','number'),widget.winfo_height())
                        assert widget.winfo_y()+widget.winfo_height()<=widget.master.winfo_height(),(language,size,view,getattr(widget,'text','number'))
                if view=='settings':advanced.invoke();app.root.update()
    locale.set_language('th')
    assert app.pose.get()=='ยังไม่แน่ใจ'
    app.close()
print('PASS: bilingual menus and runtime feedback, persistent language, unchanged metadata/gate/edits, slider-entry sync, borderless mini artwork, both languages at both sizes')
