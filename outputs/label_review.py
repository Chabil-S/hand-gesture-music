"""Explicit, hash-bound clip quarantine; never modifies or infers raw labels."""
import json
from pathlib import PurePosixPath

def load_reviews(path):
    if not path.exists():return {}
    values=json.loads(path.read_text(encoding='utf-8'))
    result={}
    for entry in values['excluded_clips']:
        key=entry['input'];parts=PurePosixPath(key).parts
        if len(parts)!=2 or any(p in ('.','..') for p in parts) or '\\' in key or ':' in key:
            raise ValueError('Invalid reviewed clip path')
        if not entry.get('reason') or len(entry.get('sha256',''))!=64:raise ValueError('Incomplete label review')
        if key in result:raise ValueError('Duplicate clip review')
        result[key]=entry
    return result

def exclusion_for(reviews,session_id,clip,checksum):
    entry=reviews.get(session_id+'/'+clip['csv'])
    if entry is None:return None
    if checksum!=entry['sha256']:raise ValueError('Reviewed source hash changed')
    if clip['split']=='test':raise ValueError('Test label issue requires a new evaluation plan; cannot silently filter test')
    return dict(entry,original_label=clip['label'],split=clip['split'],samples=clip['samples'])
