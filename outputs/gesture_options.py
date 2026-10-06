"""Normal-use gesture options; separate from trained-model/runtime thresholds."""
import json

DEFAULTS={'volume_enabled':True,'palm_enabled':True}


def validate_options(values):
    if not isinstance(values,dict) or any(type(values.get(key)) is not bool for key in DEFAULTS):
        raise ValueError('ตัวเลือกท่าควบคุมต้องเป็นเปิดหรือปิด')
    return {key:values[key] for key in DEFAULTS}


def load_options(path):
    return validate_options(json.loads(path.read_text(encoding='utf-8'))) if path.exists() else dict(DEFAULTS)


def save_options(path,values):
    result=validate_options(values)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)
    return result
