"""Focused paired live diagnostic; preserves the fixed model and runtime gate."""
import live_comparison

FROZEN_CANDIDATE='20261005_163211'
FOCUS_TRIALS=[(hand,pose) for hand in ('right','left') for pose in ('previous','neutral','three_finger')]

def create_app():
    live_comparison.TRIALS=list(FOCUS_TRIALS)
    app=live_comparison.ComparisonApp(FROZEN_CANDIDATE)
    app.root.title('Hand Gesture Music — Thumb Focus Comparison')
    app.feedback.set('เฉพาะชูโป้ง/แบมือ/สามนิ้ว 6 ช่วง • ปิดหน้ากล้องเดิมก่อนเปิดกล้อง')
    return app

if __name__=='__main__':create_app().root.mainloop()
