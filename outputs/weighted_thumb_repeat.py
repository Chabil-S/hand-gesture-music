"""Two thumb trials only, same frozen weighted model, no media control."""
import live_comparison
from weighted_angle_comparison import create_app as frozen_app

def create_app():
    live_comparison.TRIALS=[('right','previous'),('left','previous')]
    app=frozen_app()
    app.root.title('Hand Gesture Music — Thumb Timing Repeat')
    app.feedback.set('ก่อนกดเริ่มให้แบมือ • ช่วงเตรียมก็แบมือ • ชูโป้งเมื่อหน้าจอบอกทำท่าเท่านั้น')
    return app

if __name__=='__main__':create_app().root.mainloop()
