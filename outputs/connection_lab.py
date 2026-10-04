"""Small local UI to test the music connection before adding the camera."""
import asyncio
import queue
import threading
import tkinter as tk
from media_connection_probe import run

root = tk.Tk()
root.title('Hand Gesture Music — Connection Test')
root.geometry('820x510')
root.configure(bg='#101827')
root.minsize(740, 480)
messages = queue.Queue()
font = 'Leelawadee UI'
tk.Label(root, text='ระบบควบคุมเพลงด้วยท่าทางมือ', font=(font, 24, 'bold'),
         bg='#101827', fg='#f1f5f9').pack(anchor='w', padx=34, pady=(30, 6))
tk.Label(root, text='ขั้นที่ 1 • ทดสอบการเชื่อมต่อ Apple Music', font=(font, 14),
         bg='#101827', fg='#93c5fd').pack(anchor='w', padx=34)
tk.Label(root, text='หน้าต่างนี้ยังไม่ใช้กล้องหรือโมเดล AI', font=(font, 12),
         bg='#101827', fg='#cbd5e1').pack(anchor='w', padx=34, pady=(6, 24))
song = tk.StringVar(value='กด “อ่านสถานะ” เพื่อตรวจเพลงปัจจุบัน')
status = tk.StringVar(value='เปิด Apple Music และเริ่มเพลงไว้ก่อน')
card = tk.Frame(root, bg='#1e293b', padx=22, pady=18)
card.pack(fill='x', padx=34)
tk.Label(card, textvariable=song, font=(font, 17, 'bold'), bg='#1e293b', fg='white',
         wraplength=710, justify='left').pack(anchor='w')
tk.Label(card, textvariable=status, font=(font, 12), bg='#1e293b', fg='#cbd5e1',
         wraplength=710, justify='left').pack(anchor='w', pady=(8, 0))
buttons = []
def execute(action):
    for button in buttons:
        button.configure(state='disabled')
    status.set('กำลังตรวจผล…')
    def worker():
        try:
            messages.put((True, asyncio.run(run(action))))
        except Exception as error:
            messages.put((False, str(error)))
    threading.Thread(target=worker, daemon=True).start()

row = tk.Frame(root, bg='#101827')
row.pack(fill='x', padx=34, pady=24)
for label, action in [('ก่อนหน้า', 'previous_track'), ('เล่น / พัก', 'toggle'), ('ถัดไป', 'next'), ('อ่านสถานะ', 'status')]:
    button = tk.Button(row, text=label, command=lambda a=action: execute(a),
                       font=(font, 13), bg='#2563eb', fg='white', activebackground='#1d4ed8',
                       activeforeground='white', relief='flat', padx=18, pady=12)
    button.pack(side='left', padx=(0, 10))
    buttons.append(button)
tk.Label(root, text='ส่งคำสั่งเฉพาะ Apple Music ผ่าน Windows\nบันทึกสถานะก่อนและหลังใน connection_events.jsonl',
         font=(font, 11), bg='#101827', fg='#94a3b8', justify='left').pack(anchor='w', padx=34)

def poll():
    try:
        ok, value = messages.get_nowait()
        if ok:
            info = value.get('after', value['before'])
            song.set(info['title'] or 'ไม่มีชื่อเพลง')
            state = {'PLAYING': 'กำลังเล่น', 'PAUSED': 'พักเพลง'}.get(info['status'], info['status'])
            result = (' • ตรวจพบผลคำสั่งแล้ว' if value.get('observed_success')
                      else ' • ยังไม่ยืนยันผล โปรดดูเครื่องเล่น' if value['action'] != 'status' else '')
            status.set(f'{state} • {info["artist"]}' + result)
        else:
            status.set('เชื่อมต่อไม่สำเร็จ: ' + value)
        for button in buttons:
            button.configure(state='normal')
    except queue.Empty:
        pass
    root.after(100, poll)
root.after(100, poll)
root.mainloop()
