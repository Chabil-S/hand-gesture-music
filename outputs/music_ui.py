"""Light and monochrome dark desktop views for the live controller."""
import tkinter as tk
import json
from tkinter import messagebox
from tkinter import font as tkfont
from PIL import Image, ImageTk, ImageOps, ImageDraw
from ui_language import LocalizedVar

FONT = 'Leelawadee UI'
CREAM = '#F5EEDD'
SKY = '#84B3CE'
BLUE = '#16587B'
INK = '#174760'
MUTED = '#426477'
LINE = '#D4DCCC'
SOFT = '#E8E6D9'
CAMERA = '#D4E1E3'
FIELD = '#FCF8EF'

LIGHT_PALETTE = {name: globals()[name] for name in
                 ('CREAM','SKY','BLUE','INK','MUTED','LINE','SOFT','CAMERA','FIELD')}
DARK_PALETTE = dict(CREAM='#101010', SKY='#2E2E2E', BLUE='#FFFFFF',
                    INK='#F4F4F4', MUTED='#B8B8B8', LINE='#3D3D3D',
                    SOFT='#242424', CAMERA='#1C1C1C', FIELD='#181818')
PALETTES = {'light': LIGHT_PALETTE, 'dark': DARK_PALETTE}

def set_palette(theme):
    globals().update(PALETTES[theme])


class SoftButton(tk.Canvas):
    """Rounded, keyboard-operable action with the configure API used by LiveApp."""
    def __init__(self, parent, text, command, primary=False, width=210):
        super().__init__(parent, width=width, height=44, bg=parent.cget('bg'),
                         highlightthickness=0, takefocus=1)
        self.text, self.command, self.primary = text, command, primary
        self.state = 'normal'
        self.text_font=tkfont.Font(family=FONT,size=12)
        self.bind('<Configure>', lambda e: self.draw())
        self.bind('<Button-1>', lambda e: self.invoke())
        self.bind('<Return>', lambda e: self.invoke())
        self.bind('<space>', lambda e: self.invoke())
        self.bind('<FocusIn>', lambda e: self.draw())
        self.bind('<FocusOut>', lambda e: self.draw())
        self.winfo_toplevel().locale.callbacks.append(self.draw)
        self.draw()

    def configure(self, cnf=None, **kwargs):
        if hasattr(self, 'text'):
            changed=False
            for key in ('text', 'state'):
                if key in kwargs:
                    value=kwargs.pop(key)
                    changed=changed or getattr(self,key)!=value
                    setattr(self,key,value)
            result = super().configure(cnf, **kwargs) if cnf is not None or kwargs else None
            if changed or cnf is not None or kwargs:self.draw()
            return result
        return super().configure(cnf, **kwargs)

    config = configure

    def invoke(self):
        if self.state != 'disabled':
            self.focus_set()
            self.command()

    def draw(self):
        self.delete('all')
        w = max(10, self.winfo_width() if self.winfo_width()>1 else int(self.cget('width')))
        r, h = 10, 42
        fill = SOFT if self.state=='disabled' else BLUE if self.primary else SOFT
        text = MUTED if self.state=='disabled' else CREAM if self.primary else INK
        self.create_polygon(2+r,2,w-r-2,2,w-2,2,w-2,2+r,w-2,h-r,w-2,h,
                            w-r-2,h,r+2,h,2,h,2,h-r,2,r+2,2,2,
                            smooth=True, fill=fill, outline=BLUE if self.focus_get()==self else fill)
        self.display_text=self.winfo_toplevel().locale.text(self.text)
        font=self.text_font; font.configure(size=12)
        if font.measure(self.display_text)>w-20:font.configure(size=11)
        self.create_text(w/2,22,text=self.display_text,fill=text,font=font)



class NumberField(tk.Canvas):
    """Rounded surface with a native, selectable text entry inside."""
    def __init__(self,parent,variable,width=150,unit='',large=False):
        super().__init__(parent,width=width,height=52,bg=parent.cget('bg'),highlightthickness=0)
        self.unit=unit
        self.entry=tk.Entry(self,textvariable=variable,font=(FONT,20 if large else 15,'bold' if large else 'normal'),
                            bg=FIELD,fg=BLUE,insertbackground=BLUE,selectbackground=BLUE,
                            selectforeground=CREAM,bd=0,highlightthickness=0,relief='flat')
        self.bind('<Configure>',lambda e:self.draw())
        self.entry.bind('<FocusIn>',lambda e:self.draw())
        self.entry.bind('<FocusOut>',lambda e:self.draw())
        self.draw()

    def draw(self):
        self.delete('all')
        w=max(40,self.winfo_width() if self.winfo_width()>1 else int(self.cget('width')))
        self.create_polygon(14,2,w-14,2,w-2,2,w-2,14,w-2,38,w-2,50,w-14,50,
                            14,50,2,50,2,38,2,14,2,2,smooth=True,fill=FIELD,
                            outline=BLUE if self.entry.focus_get()==self.entry else SKY,width=1)
        self.entry.place(x=15,y=8,width=max(20,w-30-(28 if self.unit else 0)),height=36)
        if self.unit:self.create_text(w-22,27,text=self.unit,fill=MUTED,font=(FONT,12))


class ModernSlider(tk.Canvas):
    """Thin filled track with a round thumb; pointer and keyboard input."""
    def __init__(self,parent,command):
        super().__init__(parent,height=42,bg=parent.cget('bg'),highlightthickness=0,takefocus=1)
        self.command=command;self.value=95.0
        self.bind('<Configure>',lambda e:self.draw())
        self.bind('<Button-1>',self.drag);self.bind('<B1-Motion>',self.drag)
        self.bind('<Left>',lambda e:self.change(self.value-1))
        self.bind('<Right>',lambda e:self.change(self.value+1))
        self.bind('<Home>',lambda e:self.change(1));self.bind('<End>',lambda e:self.change(100))
        self.bind('<FocusIn>',lambda e:self.draw());self.bind('<FocusOut>',lambda e:self.draw())

    def get(self):return self.value

    def set(self,value):
        self.value=min(100,max(1,float(value)));self.draw()

    def change(self,value):
        self.set(value);self.command(self.value)

    def drag(self,event):
        self.focus_set()
        ratio=(event.x-14)/max(1,self.winfo_width()-28)
        self.change(round(1+99*ratio))

    def draw(self):
        self.delete('all');width=max(30,self.winfo_width())
        x=14+(width-28)*(self.value-1)/99
        self.create_line(14,21,width-14,21,fill=SOFT,width=7,capstyle='round')
        self.create_line(14,21,x,21,fill=BLUE,width=7,capstyle='round')
        if self.focus_get()==self:self.create_oval(x-13,8,x+13,34,outline=SKY,width=2)
        self.create_oval(x-9,12,x+9,30,fill=BLUE,outline=CREAM,width=3)


def time_text(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds//60}:{seconds%60:02d}'


class MusicUI:
    def __init__(self, app):
        self.app, self.root = app, app.root
        self.locale=self.root.locale
        self.theme='light'
        if self.locale.path:
            try:
                preferences=json.loads(self.locale.path.read_text(encoding='utf-8'))
                if isinstance(preferences,dict) and preferences.get('theme') in PALETTES:
                    self.theme=preferences['theme']
            except (OSError,ValueError):pass
        set_palette(self.theme)
        self.view = 'camera'
        self.rgb = None
        self.cover_image = None
        self.photos = {}
        self.music = {'connected': False}
        self.root.configure(bg=CREAM)
        self.root.geometry('1220x900')
        self.root.minsize(1080, 820)
        self.root.title('Gesture Music')
        self.status = LocalizedVar(value='เปิด Apple Music และเริ่มเพลงเพื่อเชื่อมต่อ')
        self.title = tk.StringVar(value='ยังไม่มีเพลงที่กำลังฟัง')
        self.artist = tk.StringVar(value='เปิด Apple Music แล้วเริ่มเพลง')
        self.mini_title = tk.StringVar(value='ยังไม่มีเพลงที่กำลังฟัง')
        self.mini_details = tk.StringVar(value='เปิด Apple Music แล้วเริ่มเพลง')
        self.mini_status = tk.StringVar(value='ยังไม่ได้เชื่อมต่อ')
        self.playback = LocalizedVar(value='ยังไม่ได้เชื่อมต่อ')
        self.cover_hint = LocalizedVar(value='ยังไม่มีภาพปกจาก Apple Music')
        self.confidence = tk.StringVar(value='—')
        self.hold = LocalizedVar(value='พร้อมรับท่า')
        self.threshold = LocalizedVar()
        self.release = LocalizedVar()
        self.timing = LocalizedVar()
        self.control_state = LocalizedVar(value='โหมดดูผล')
        self.control_hint = LocalizedVar(value='ค้างท่า = 1 คำสั่ง')
        self.palm_indicator = LocalizedVar()
        self.camera_caption = tk.StringVar(value='เปิดกล้องเพื่อลองท่า')
        self.settings_values = {}
        self.header()
        body = tk.Frame(self.root, bg=CREAM)
        body.pack(fill='both', expand=True)
        nav = tk.Frame(body, bg=SOFT, width=165)
        nav.pack(side='left', fill='y');nav.pack_propagate(False)
        self.label(nav, 'มุมมอง', 10, MUTED).pack(anchor='w', padx=22, pady=(26,14))
        self.nav_buttons = {}
        for key, text in [('camera','จับท่าทาง'),('music','กำลังฟัง'),('settings','ตั้งค่า')]:
            button = SoftButton(nav, text, lambda k=key:self.show(k), width=137)
            button.pack(fill='x',padx=14,pady=4)
            self.nav_buttons[key]=button
        self.label(nav, self.status, 10, MUTED, wrap=130).pack(side='bottom',anchor='w',padx=18,pady=12)
        tk.Frame(body,bg=LINE,width=1).pack(side='left',fill='y')
        self.content = tk.Frame(body,bg=CREAM)
        self.content.pack(side='left',fill='both',expand=True)
        self.pages = {name:tk.Frame(self.content,bg=CREAM,padx=26,pady=20)
                      for name in ('camera','music','settings')}
        self.controls=[];self.videos=[];self.covers=[];self.transport=[];self.volume_groups=[]
        self.palm_groups=[];self.palm_bars=[]
        self.build_camera(self.pages['camera'])
        self.build_music(self.pages['music'])
        self.build_settings(self.pages['settings'])
        self.refresh_settings()
        self.show('camera')
        self.locale.callbacks.append(self.refresh_language)
        self.refresh_language()

    def label(self, parent, value, size=11, color=None, wrap=0, bold=False):
        if color is None:color=INK
        args={'textvariable':value} if isinstance(value,tk.Variable) else {'text':value}
        widget=tk.Label(parent, **args, font=(FONT,max(11,size),'bold' if bold else 'normal'),
                        bg=parent.cget('bg'),fg=color,anchor='w',justify='left',wraplength=wrap)
        if isinstance(value,str):self.locale.bind(widget,value)
        return widget

    def header(self):
        row=tk.Frame(self.root,bg=CREAM,padx=28,pady=18);row.pack(fill='x')
        tk.Label(row,text='gm.',bg=BLUE,fg=CREAM,font=(FONT,20,'bold'),padx=8,pady=4).pack(side='left',padx=(0,14))
        title=tk.Frame(row,bg=CREAM);title.pack(side='left')
        self.label(title,'Gesture Music',20,bold=True).pack(anchor='w')
        self.label(title,'เพลงของคุณ ในจังหวะของมือ',10,MUTED).pack(anchor='w')
        self.read_button=SoftButton(row,'อ่านสถานะ Apple Music',lambda:self.app.request('status'),width=225)
        self.read_button.pack(side='right')
        tk.Frame(self.root,bg=LINE,height=1).pack(fill='x')

    def page_heading(self, page, eyebrow, title):
        row=tk.Frame(page,bg=CREAM);row.pack(fill='x',pady=(0,18))
        left=tk.Frame(row,bg=CREAM);left.pack(side='left')
        self.label(left,eyebrow,11 if title else 22,MUTED if title else INK,bold=not title).pack(anchor='w')
        if title:self.label(left,title,22,bold=True).pack(anchor='w')

    def camera_box(self, parent, small=False):
        box=tk.Frame(parent,bg=CAMERA)
        top=tk.Frame(box,bg=CAMERA,padx=12,pady=6);top.pack(fill='x')
        self.label(top,'ภาพจากกล้อง' if not small else 'กล้อง',10).pack(side='left')
        if not small:
            self.open_button=SoftButton(top,'เปิดกล้อง',self.app.toggle_camera,width=150)
            self.open_button.pack(side='right')
        caption=LocalizedVar(value='เปิดกล้องเพื่อลองท่า')
        video=tk.Label(box,textvariable=caption,bg=CAMERA,fg=MUTED,font=(FONT,12),width=1,height=1)
        video.caption=caption
        video.pack(fill='both',expand=True,padx=10,pady=8)
        self.videos.append(video)
        bottom=tk.Frame(box,bg=SKY,padx=10,pady=8);bottom.pack(fill='x')
        self.label(bottom,self.app.detection,9,BLUE,wrap=230 if small else 520).pack(anchor='w')
        return box

    def control(self, parent, palm_progress=False):
        group=tk.Frame(parent,bg=SOFT,padx=10,pady=10)
        group.pack(fill='x',pady=(12,8))
        self.label(group,self.control_state,12,BLUE,bold=True,wrap=210).pack(anchor='w')
        button=SoftButton(group,'เริ่มควบคุมเพลง',self.app.toggle_control,primary=True)
        button.pack(fill='x',pady=(8,8));button.configure(state='disabled')
        self.label(group,self.timing,11,INK,wrap=210).pack(anchor='w')
        self.label(group,self.control_hint,11,MUTED,wrap=210).pack(anchor='w',pady=(5,0))
        volume=tk.Frame(group,bg=SOFT)
        self.label(volume,self.app.volume_status,12,BLUE,bold=True,wrap=210).pack(anchor='w',pady=(8,2))
        self.label(volume,self.app.volume_feedback,11,INK,wrap=210).pack(anchor='w')
        self.volume_groups.append(volume)
        if palm_progress:
            palm=tk.Frame(group,bg=SOFT)
            self.label(palm,self.palm_indicator,11,BLUE,bold=True,wrap=210).pack(anchor='w',pady=(8,6))
            bar=tk.Canvas(palm,height=6,bg=CREAM,highlightthickness=0)
            bar.pack(fill='x',pady=(0,4))
            self.palm_groups.append(palm);self.palm_bars.append(bar)
        self.controls.append(button)
        return button

    def guide(self, parent, horizontal=False):
        row=tk.Frame(parent,bg=CREAM);row.pack(fill='x',pady=16)
        items=[('กำมือ','เล่น / พัก'),('V ชี้–กลาง พับโป้ง','ถัดไป'),('ชูโป้ง','ก่อนหน้า'),
               ('จีบชี้–โป้ง','เพิ่ม / ลดเสียง'),('แบมือค้าง 1.2 วินาที','พัก / เริ่มควบคุม')]
        for index,(pose, command) in enumerate(items):
            item=tk.Frame(row,bg=CREAM)
            if horizontal:
                row.columnconfigure(index%3,weight=1,uniform='guide')
                item.grid(row=index//3,column=index%3,sticky='ew',pady=3)
            else:item.pack(fill='x',pady=3)
            self.label(item,pose,10,MUTED,wrap=160 if horizontal else 230).pack(anchor='w')
            self.label(item,command,11,bold=True).pack(anchor='w')

    def build_camera(self,page):
        body=tk.Frame(page,bg=CREAM);body.pack(fill='both',expand=True)
        aside=tk.Frame(body,bg=CREAM,width=235);aside.pack(side='right',fill='y',padx=(22,0));aside.pack_propagate(False)
        left=tk.Frame(body,bg=CREAM);left.pack(side='left',fill='both',expand=True)
        self.camera_box(left).pack(fill='both',expand=True)
        self.video=self.videos[-1]
        self.label(left,'กำมือ: เล่น/พัก · V: ถัดไป · โป้ง: ก่อนหน้า\nจีบ: เสียง · แบมือ: พัก/เริ่มควบคุม',11,MUTED,wrap=700).pack(anchor='w',pady=(8,6))
        self.label(aside,'ท่าที่ตรวจพบ',10,MUTED).pack(anchor='w',pady=(12,0))
        self.label(aside,self.app.pose,22,bold=True,wrap=230).pack(anchor='w',pady=(4,16))
        self.confidence_group=tk.Frame(aside,bg=CREAM)
        self.confidence_group.pack(fill='x')
        self.label(self.confidence_group,self.confidence,38,BLUE).pack(anchor='w')
        self.label(self.confidence_group,'คะแนนโมเดล',9,MUTED).pack(anchor='w')
        self.label(self.confidence_group,self.threshold,11,MUTED).pack(anchor='w',pady=(3,0))
        self.hold_label=self.label(aside,self.hold,10,MUTED,wrap=230)
        self.hold_label.pack(anchor='w',pady=(22,8))
        self.hold_bar=tk.Canvas(aside,height=6,bg=SOFT,highlightthickness=0)
        self.hold_bar.pack(fill='x')
        self.control_button=self.control(aside)
        self.label(aside,self.app.feedback,11,INK,wrap=230).pack(anchor='w',pady=(4,10))
        mini=tk.Frame(page,bg=SOFT,padx=16,pady=12);mini.pack(fill='x',pady=(4,0))
        self.mini_cover=tk.Label(mini,bg=SOFT,width=64,height=64,bd=0,highlightthickness=0)
        self.mini_cover.pack(side='left',padx=(0,14));self.covers.append((self.mini_cover,64))
        SoftButton(mini,'ดูหน้ากำลังฟัง',lambda:self.show('music'),width=160).pack(side='right',padx=(14,0))
        self.label(mini,self.mini_status,11,BLUE,wrap=165).pack(side='right',padx=(12,0))
        details=tk.Frame(mini,bg=SOFT);details.pack(side='left',fill='x',expand=True)
        self.label(details,self.mini_title,13,bold=True).pack(anchor='w')
        self.label(details,self.mini_details,11,MUTED).pack(anchor='w')
        self.mini_details_frame=details

    def build_music(self,page):
        self.page_heading(page,'Now playing',None)
        body=tk.Frame(page,bg=CREAM);body.pack(fill='both',expand=True)
        aside=tk.Frame(body,bg=CREAM,width=245);aside.pack(side='right',fill='y',padx=(30,0));aside.pack_propagate(False)
        focus=tk.Frame(body,bg=CREAM);focus.pack(side='left',fill='both',expand=True)
        self.cover=tk.Label(focus,bg=CREAM,bd=0,highlightthickness=0)
        self.cover.pack(pady=(2,16));self.covers.append((self.cover,285))
        self.label(focus,self.cover_hint,9,MUTED).pack()
        self.label(focus,self.title,22,bold=True,wrap=430).pack(pady=(0,3))
        self.label(focus,self.artist,12,MUTED,wrap=430).pack()
        self.label(focus,self.playback,10,MUTED).pack(pady=(6,16))
        self.timeline=tk.Canvas(focus,height=5,bg=SOFT,highlightthickness=0)
        self.timeline.pack(fill='x',padx=12)
        self.times=LocalizedVar(value='—  /  —')
        self.label(focus,self.times,10,MUTED).pack(anchor='w',padx=12,pady=(6,12))
        actions=tk.Frame(focus,bg=CREAM);actions.pack()
        for text,action,key in [('ก่อนหน้า','previous_track','can_previous'),('เล่น / พัก','toggle','can_toggle'),('ถัดไป','next','can_next')]:
            b=SoftButton(actions,text,lambda a=action:self.app.manual_request(a),primary=action=='toggle',width=125)
            b.pack(side='left',padx=4);b.configure(state='disabled');self.transport.append((b,key))
        self.label(focus,'ปุ่มเพลงสั่งงานทันที · โหมดดูผลใช้กับท่ามือ',9,MUTED).pack(pady=(10,0))
        camera=self.camera_box(aside,True);camera.pack(fill='x');camera.configure(height=200);camera.pack_propagate(False)
        self.music_camera_box=camera
        self.label(aside,self.app.pose,16,bold=True,wrap=230).pack(anchor='w',pady=(15,0))
        self.control(aside,palm_progress=True)
        self.music_camera_help=self.label(aside,'สลับมุมมองได้โดยไม่หยุดรับท่า',11,MUTED,wrap=230)
        self.music_camera_help.pack(anchor='w',pady=(0,10))
        self.expand_camera_button=SoftButton(aside,'ขยายกล้องและดูผล',lambda:self.show('camera'))
        self.expand_camera_button.pack(fill='x')
        self.label(page,self.app.feedback,10,MUTED,wrap=850).pack(anchor='w',pady=(8,0))

    def build_settings(self,page):
        self.page_heading(page,'PREFERENCES','ปรับให้เข้ากับมือคุณ')
        form=tk.Frame(page,bg=CREAM);form.pack(pady=6,fill='x',padx=60)
        def entry(parent,key,width=12):
            value=tk.StringVar();self.settings_values[key]=value
            widget=NumberField(parent,value,width=width*12+30,unit='%' if key=='threshold' else '',large=key=='threshold')
            return widget
        row=tk.Frame(form,bg=CREAM);row.pack(fill='x')
        self.label(row,'คะแนนขั้นต่ำรับท่า (%)',14,bold=True).pack(side='left')
        entry(row,'threshold',7).pack(side='right')
        self.label(form,'สูงขึ้น: รับเฉพาะท่าที่มั่นใจมากขึ้น · ต่ำลง: รับท่าได้ง่ายขึ้น',10,MUTED).pack(anchor='w',pady=10)
        slider=ModernSlider(form,command=lambda v:self.settings_values['threshold'].set(f'{float(v):g}'))
        slider.pack(fill='x',pady=(2,0))
        self.threshold_slider=slider
        ends=tk.Frame(form,bg=CREAM);ends.pack(fill='x')
        self.label(ends,'รับง่ายขึ้น',11,MUTED).pack(side='left')
        self.label(ends,'เข้มงวดขึ้น',11,MUTED).pack(side='right')
        def sync_entry(*args):
            try:self.sync_slider(float(self.settings_values['threshold'].get()))
            except ValueError:pass
        self.settings_values['threshold'].trace_add('write',sync_entry)
        tk.Frame(form,bg=LINE,height=1).pack(fill='x',pady=14)
        self.label(form,'จังหวะการออกคำสั่ง',14,bold=True).pack(anchor='w',pady=(0,12))
        timing=tk.Frame(form,bg=CREAM);timing.pack(fill='x')
        for key,title,help_text in [('hold_seconds','เวลาค้างท่า','วินาที · ค้างก่อนส่งคำสั่ง'),
                                   ('release_seconds','เวลาปล่อยมือ','วินาที · เว้นก่อนรับท่าใหม่')]:
            column=tk.Frame(timing,bg=CREAM);column.pack(side='left',fill='x',expand=True,padx=(0,16))
            self.label(column,title,12).pack(anchor='w')
            entry(column,key,18).pack(fill='x',pady=8)
            self.label(column,help_text,10,MUTED).pack(anchor='w')
        advanced=tk.Frame(form,bg=CREAM)
        row=tk.Frame(advanced,bg=CREAM);row.pack(fill='x',pady=8)
        self.label(row,'ช่วงภาพขาดที่ยอมรับ (วินาที)',11).pack(side='left')
        entry(row,'max_frame_gap_seconds',9).pack(side='right')
        self.label(advanced,'เว้นเกินนี้จะเริ่มนับเวลาค้างท่าใหม่',10,MUTED).pack(anchor='w')
        def toggle_advanced():
            if advanced.winfo_manager():advanced.pack_forget()
            else:advanced.pack(fill='x',after=extras,pady=4)
        extras=tk.Frame(form,bg=CREAM);extras.pack(fill='x',pady=(8,0))
        advanced_button=SoftButton(extras,'การตั้งค่าเพิ่มเติม',toggle_advanced,width=180)
        advanced_button.pack(side='left')
        SoftButton(extras,'ท่าควบคุม',self.open_gesture_options,width=180).pack(side='left',padx=(12,0))
        self.label(form,'บันทึกแล้วกลับโหมดดูผล เพื่อให้ลองท่าก่อนเปิดควบคุมเพลง',10,MUTED).pack(anchor='w',pady=(10,6))
        buttons=tk.Frame(form,bg=CREAM);buttons.pack(fill='x',pady=8)
        SoftButton(buttons,'บันทึกและใช้ค่า',self.save_settings,primary=True,width=170).pack(side='right')
        SoftButton(buttons,'คืนค่าที่รุ่นเคยทดสอบ',self.restore_settings,width=225).pack(side='right',padx=12)
        # Deliberately absent from the normal settings surface and tab order.
        self.private_preferences=tk.Frame(form,bg=CREAM)
        self.language_button=SoftButton(self.private_preferences,'EN',self.toggle_language,width=100)
        self.language_button.pack(side='right')
        self.theme_button=SoftButton(self.private_preferences,'ธีมมืด',self.toggle_theme,width=150)
        self.theme_button.pack(side='right',padx=(0,8))
        self.root.bind('<Control-Shift-L>',self.reveal_language)
        self.root.bind('<Control-Shift-l>',self.reveal_language)

    def open_gesture_options(self):
        if not hasattr(self,'gesture_options_window'):
            window=tk.Toplevel(self.root,bg=CREAM)
            window.locale=self.locale
            window.geometry('490x440');window.resizable(False,False)
            window.transient(self.root)
            window.protocol('WM_DELETE_WINDOW',window.withdraw)
            self.gesture_options_window=window
            body=tk.Frame(window,bg=CREAM,padx=24,pady=20);body.pack(fill='both',expand=True)
            self.label(body,'ท่าควบคุม',18,bold=True).pack(anchor='w')
            self.label(body,'ใช้ร่วมกับท่าเพลง · จำตัวเลือกเมื่อเปิดใหม่',11,MUTED,wrap=440).pack(anchor='w',pady=(4,14))
            self.volume_option=tk.BooleanVar()
            self.palm_option=tk.BooleanVar()
            for source,variable,description in [
                ('จีบปรับเสียง Apple Music',self.volume_option,
                 'พับกลาง–นาง–ก้อย · ค้างจีบหรือกาง 0.45 วินาที\nกางเพิ่ม · หุบลด · ปล่อยมือก่อนท่าเพลง'),
                ('แบมือค้างเพื่อพัก / เริ่มควบคุม',self.palm_option,
                 'แบทั้งห้านิ้ว 1.2 วินาที แล้วปล่อย\nตรวจท่านี้ได้ระหว่างพัก ถ้ากล้องยังเปิดอยู่')]:
                check=tk.Checkbutton(body,variable=variable,bg=CREAM,fg=INK,activebackground=CREAM,activeforeground=INK,
                                     selectcolor=CREAM,font=(FONT,12,'bold'),anchor='w',bd=0)
                self.locale.bind(check,source);check.pack(anchor='w',pady=(4,0))
                self.label(body,description,11,MUTED,wrap=435).pack(anchor='w',padx=(25,0),pady=(3,10))
            self.label(body,'ใช้ค่าแล้วกลับโหมดดูผล · กดเริ่มควบคุมเพื่อส่งคำสั่งจริง',11,MUTED,wrap=435).pack(anchor='w',pady=(4,10))
            def apply():
                try:self.app.set_gesture_options(self.volume_option.get(),self.palm_option.get())
                except (ValueError,OSError) as error:
                    messagebox.showerror(self.locale.text('ยังไม่ได้เปลี่ยนค่า'),str(error),parent=window)
                    return
                window.withdraw();self.show('camera')
            SoftButton(body,'บันทึกท่าควบคุม',apply,primary=True,width=180).pack(anchor='e')
        self.volume_option.set(self.app.volume_enabled)
        self.palm_option.set(self.app.palm_enabled)
        self.gesture_options_window.title(self.locale.text('ท่าควบคุม'))
        self.gesture_options_window.deiconify();self.gesture_options_window.lift()

    def reveal_language(self,event=None):
        if self.view!='settings':return
        if self.private_preferences.winfo_manager():self.private_preferences.pack_forget()
        else:self.private_preferences.pack(anchor='e',pady=(6,0))
        return 'break'

    def show(self,name):
        if hasattr(self,'private_preferences'):self.private_preferences.pack_forget()
        self.view=name
        for key,page in self.pages.items():
            page.pack_forget()
            self.nav_buttons[key].primary=key==name;self.nav_buttons[key].draw()
        self.pages[name].pack(fill='both',expand=True)
        if name=='settings':self.refresh_settings()
        self.root.update_idletasks()
        if self.rgb is not None:self.render_frame(self.rgb)
        self.render_cover()
        self.set_music(self.music)

    def refresh_settings(self):
        for key,value in self.settings_values.items():
            value.set(f'{self.app.config[key]*100:g}' if key=='threshold' else f'{self.app.config[key]:g}')
        self.threshold.set(f'คะแนนขั้นต่ำรับท่า {self.app.config["threshold"]:.0%}')
        self.release.set(f'เวลาปล่อยมือ {self.app.config["release_seconds"]:g} วินาที')
        self.timing.set(f'ค้าง {self.app.config["hold_seconds"]:g} วินาที · ปล่อย {self.app.config["release_seconds"]:g} วินาที')
        self.sync_slider(self.app.config['threshold']*100)

    def sync_slider(self,value):
        self.threshold_slider.set(value)

    def restore_settings(self):
        for key,value in self.settings_values.items():
            value.set(f'{self.app.frozen_config[key]*100:g}' if key=='threshold' else f'{self.app.frozen_config[key]:g}')
        self.sync_slider(self.app.frozen_config['threshold']*100)

    def save_settings(self):
        try:
            values={k:float(v.get()) for k,v in self.settings_values.items()}
            values['threshold']/=100
            self.app.apply_runtime_settings(values)
        except (ValueError,OSError) as error:
            messagebox.showerror(self.locale.text('ยังไม่ได้เปลี่ยนค่า'),self.locale.text(str(error)),parent=self.root)
            return
        self.refresh_settings();self.show('camera')

    def sync_controls(self):
        volume_active=self.app.volume_enabled and self.app.pinch_feedback.get('state')!='waiting'
        palm_active=self.app.palm_enabled and self.app.palm_feedback.get('reserved',False)
        self.control_state.set('กำลังควบคุมด้วยมือ' if self.app.armed else 'โหมดดูผล · ยังไม่ส่งคำสั่งมือ')
        for b in self.controls:
            b.configure(text='พักการควบคุม' if self.app.armed else 'เริ่มควบคุมเพลง',
                        state='normal' if self.app.camera_running and self.app.last_frame is not None else 'disabled')
        self.open_button.configure(text='ปิดกล้อง' if self.app.camera_running else 'เปิดกล้อง')
        for group in self.volume_groups:
            if volume_active and not palm_active:
                if not group.winfo_manager():group.pack(fill='x')
            else:group.pack_forget()
        for group in self.palm_groups:
            if palm_active:
                if not group.winfo_manager():group.pack(fill='x')
            else:group.pack_forget()
        snapshot=self.app.last_volume
        if snapshot:
            self.app.volume_status.set(f'เสียง Apple Music {snapshot["level"]:.0%}'+(' · ปิดเสียง' if snapshot.get('muted') else ''))
        else:self.app.volume_status.set('เสียง Apple Music · ยังอ่านไม่ได้')
        if palm_active:
            self.timing.set(f'แบมือ {self.app.palm.hold:g} วินาที · ปล่อย {self.app.palm.release:g} วินาที')
            self.control_hint.set('ปล่อยมือก่อนแบมืออีกครั้ง')
        elif volume_active:
            self.control_state.set('กำลังปรับเสียง' if self.app.armed else 'ดูผลจีบ')
            self.timing.set(f'ค้างจีบ {self.app.pinch.hold:g} วินาที · พับอีกสามนิ้ว')
            self.control_hint.set('เอามือออกเพื่อจบ')
        else:
            self.timing.set(f'ค้าง {self.app.config["hold_seconds"]:g} วินาที · ปล่อย {self.app.config["release_seconds"]:g} วินาที')
            self.control_hint.set('ค้างท่า = 1 คำสั่ง')
        if volume_active or palm_active:
            self.confidence_group.pack_forget()
            self.music_camera_box.configure(height=140)
            self.music_camera_help.pack_forget()
        else:
            if not self.confidence_group.winfo_manager():
                self.confidence_group.pack(fill='x',before=self.hold_label)
            self.music_camera_box.configure(height=200)
            if not self.music_camera_help.winfo_manager():
                self.music_camera_help.pack(anchor='w',pady=(0,10),before=self.expand_camera_button)

    def toggle_language(self):
        try:self.locale.set_language('en' if self.locale.language=='th' else 'th')
        except OSError as error:
            messagebox.showerror(self.locale.text('ยังไม่ได้เปลี่ยนค่า'),str(error),parent=self.root)

    def refresh_language(self):
        self.language_button.configure(text='EN' if self.locale.language=='th' else 'ไทย')
        self.theme_button.configure(text='ธีมมืด' if self.theme=='light' else 'ธีมสว่าง')
        self.set_music(self.music)

    def toggle_theme(self):
        theme='dark' if self.theme=='light' else 'light'
        try:self.locale.save_preference('theme',theme)
        except OSError as error:
            messagebox.showerror(self.locale.text('ยังไม่ได้เปลี่ยนค่า'),str(error),parent=self.root)
            return
        self.apply_theme(theme)

    def apply_theme(self,theme):
        old=PALETTES[self.theme];new=PALETTES[theme]
        replacements={color.lower():new[name] for name,color in old.items()}
        self.theme=theme;set_palette(theme)
        def recolor(widget):
            options=widget.keys();changes={}
            for key in ('background','foreground','activebackground','activeforeground',
                        'disabledforeground','insertbackground','selectbackground',
                        'selectforeground','selectcolor','highlightbackground','highlightcolor'):
                if key in options:
                    value=str(widget.cget(key)).lower()
                    if value in replacements:changes[key]=replacements[value]
            if changes:widget.configure(**changes)
            if isinstance(widget,tk.Canvas):
                for item in widget.find_all():
                    for key in ('fill','outline'):
                        try:value=widget.itemcget(item,key).lower()
                        except tk.TclError:continue
                        if value in replacements:widget.itemconfigure(item,**{key:replacements[value]})
            for child in widget.winfo_children():recolor(child)
            if isinstance(widget,(SoftButton,NumberField,ModernSlider)):widget.draw()
        recolor(self.root)
        self.theme_button.configure(text='ธีมมืด' if theme=='light' else 'ธีมสว่าง')
        self.render_cover()
        self.set_music(self.music)

    def render_frame(self,rgb):
        self.rgb=rgb
        for i,video in enumerate(self.videos):
            if not video.winfo_viewable():continue
            picture=ImageOps.contain(Image.fromarray(rgb),
                                    (max(1,video.winfo_width()-8),max(1,video.winfo_height()-8)),
                                    Image.Resampling.LANCZOS)
            self.photos['video'+str(i)]=ImageTk.PhotoImage(picture)
            video.configure(image=self.photos['video'+str(i)],text='')

    def camera_off(self):
        self.rgb=None
        for video in self.videos:video.configure(image='',text='เปิดกล้องเพื่อลองท่า')
        self.sync_controls()

    def render_gesture(self,score,timestamp):
        volume_active=self.app.volume_enabled and self.app.pinch_feedback.get('state')!='waiting'
        self.confidence.set(f'{score:.0%}' if score else '—')
        gate=self.app.gate
        ratio=1 if gate.latched else min(1,max(0,(timestamp-gate.since)/gate.hold)) if gate.since is not None else 0
        self.hold.set('ปล่อยมือก่อนออกคำสั่งใหม่' if gate.latched else f'ค้างท่า {ratio*gate.hold:.1f} / {gate.hold:g} วินาที' if gate.since is not None else 'พร้อมรับท่า')
        if volume_active:
            pinch=self.app.pinch
            ratio=1 if pinch.active else min(1,max(0,(timestamp-pinch.since)/pinch.hold)) if pinch.since is not None else 0
            self.hold.set('ขยับนิ้วเพื่อปรับเสียง' if pinch.active else 'ค้างจีบเพื่อเริ่ม')
            state=self.app.pinch_feedback['state']
            if state=='release':ratio=0.;self.hold.set('ปล่อยมือก่อนเริ่มจีบ')
            elif state=='hold':self.hold.set(f'จีบค้าง {ratio*pinch.hold:.1f} / {pinch.hold:g} วินาที')
        palm=self.app.palm_feedback
        if self.app.palm_enabled and palm.get('reserved'):
            ratio=palm.get('progress',0.)
            state=palm.get('state')
            text=('เริ่มควบคุมแล้ว · ปล่อยมือ' if self.app.armed else 'พักการควบคุมแล้ว · ปล่อยมือ') if state=='confirmed' else (
                'ปล่อยมือก่อนแบมืออีกครั้ง' if state=='release' else
                f'แบมือค้าง {ratio*self.app.palm.hold:.1f} / {self.app.palm.hold:g} วินาที')
            self.hold.set(text);self.palm_indicator.set(text)
        for bar in self.palm_bars:
            bar.delete('all')
            bar.create_rectangle(0,0,bar.winfo_width()*ratio,6,fill=BLUE,outline='')
        self.hold_bar.delete('all')
        self.hold_bar.create_rectangle(0,0,self.hold_bar.winfo_width()*ratio,6,fill=BLUE,outline='')

    def set_music(self,data):
        self.music=data
        connected=data.get('connected',False)
        self.status.set('Apple Music · เชื่อมต่อแล้ว' if connected else data.get('message','ยังไม่ได้เชื่อมต่อ'))
        self.title.set(data.get('title') or self.locale.text('ยังไม่มีชื่อเพลง' if connected else 'ยังไม่มีเพลงที่กำลังฟัง'))
        self.artist.set(data.get('artist') or self.locale.text('ไม่ระบุศิลปิน' if connected else 'เปิด Apple Music แล้วเริ่มเพลง'))
        self.playback.set({'PLAYING':'กำลังเล่น','PAUSED':'พักเพลง','STOPPED':'หยุดเล่น'}.get(data.get('status'),'ยังไม่ได้เล่นเพลง'))
        width=max(220,self.mini_details_frame.winfo_width())
        def fit(text,size):
            font=tkfont.Font(family=FONT,size=size)
            if font.measure(text)<=width:return text
            while text and font.measure(text+'…')>width:text=text[:-1]
            return text+'…'
        self.mini_title.set(fit(self.title.get(),13))
        details=' · '.join(part for part in (data.get('artist'),data.get('album')) if part)
        self.mini_details.set(fit(details or self.artist.get(),11))
        cover=data.get('cover')
        self.cover_hint.set('' if cover is not None else 'ยังไม่มีภาพปกจาก Apple Music')
        if cover is not self.cover_image:
            self.cover_image=cover;self.render_cover()
        for button,key in self.transport:button.configure(state='normal' if connected and data.get(key) and not self.app.busy else 'disabled')
        position=data.get('position_seconds',0);duration=data.get('duration_seconds',0)
        self.mini_status.set(self.playback.get()+(f'  ·  {time_text(position)} / {time_text(duration)}' if duration>0 else ''))
        self.times.set(f'{time_text(position)}  /  {time_text(duration)}' if duration>0 else 'ไม่มีข้อมูลระยะเวลาเพลง')
        self.timeline.delete('all')
        self.timeline.create_rectangle(0,0,self.timeline.winfo_width()*min(1,position/duration) if duration else 0,5,fill=BLUE,outline='')

    def render_cover(self):
        for i,(label,size) in enumerate(self.covers):
            if self.cover_image is None:
                picture=Image.new('RGB',(size,size),SKY)
            else:picture=ImageOps.fit(self.cover_image,(size,size),method=Image.Resampling.LANCZOS)
            mask=Image.new('L',(size,size),0)
            ImageDraw.Draw(mask).rounded_rectangle((0,0,size,size),radius=min(16,size//5),fill=255)
            background=Image.new('RGB',(size,size),label.master.cget('bg'));background.paste(picture,(0,0),mask)
            self.photos['cover'+str(i)]=ImageTk.PhotoImage(background)
            label.configure(image=self.photos['cover'+str(i)],width=size,height=size)
