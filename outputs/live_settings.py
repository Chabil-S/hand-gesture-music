"""Editable runtime controls, separate from frozen model evaluation."""
import json,math

KEYS=('threshold','hold_seconds','release_seconds','max_frame_gap_seconds')

def validate_settings(values):
    result={k:float(values[k]) for k in KEYS}
    if any(not math.isfinite(v) for v in result.values()):raise ValueError('ทุกค่าต้องเป็นตัวเลขปกติ')
    if not 0<result['threshold']<=1:raise ValueError('คะแนนรับท่าต้องมากกว่า 0 และไม่เกิน 100%')
    if any(result[k]<=0 for k in KEYS[1:]):raise ValueError('เวลาทั้งหมดต้องมากกว่า 0 วินาที')
    return result

def load_settings(path,frozen):
    values={k:frozen[k] for k in KEYS}
    if path.exists():values.update(json.loads(path.read_text(encoding='utf-8')))
    return validate_settings(values)

def save_settings(path,values):
    result=validate_settings(values)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)
    return result
