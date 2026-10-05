"""Frozen weighted candidate comparison; opens with camera off, never controls music."""
import hashlib,json
from live_comparison import ComparisonApp,BASE

STAMP='20261005_194641'
SHA='f9df930a1654287d5c8e47df66e152129161782464e15a3b6017ff6b81a48a7d'

def create_app():
    d=BASE/'models'/STAMP
    assert hashlib.sha256((d/'gesture_model.joblib').read_bytes()).hexdigest()==SHA
    config=json.loads((d/'selection_frozen.json').read_text(encoding='utf-8'))
    assert config['eligible_for_activation'] is False and config['test_evaluated'] is False
    assert config['revision_validation']['temporal_passed']
    app=ComparisonApp(STAMP)
    app.root.title('Hand Gesture Music — Weighted Angle Comparison')
    return app

if __name__=='__main__':create_app().root.mainloop()
