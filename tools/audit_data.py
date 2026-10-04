import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

base=Path(__file__).resolve().parents[1]/'outputs'
sessions=[]
verification=json.loads((base/'hand_verification.json').read_text(encoding='utf-8')) if (base/'hand_verification.json').exists() else {}
for directory in sorted((base/'data'/'raw').iterdir()):
    if not directory.is_dir(): continue
    meta=json.loads((directory/'session.json').read_text(encoding='utf-8'))
    clips=[json.loads(line) for line in (directory/'clips.jsonl').read_text(encoding='utf-8').splitlines()]
    errors=[]
    count=Counter()
    handedness=Counter()
    round_splits=defaultdict(set)
    accepted=[]
    for clip in clips:
        path=directory/clip['csv']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=clip['sha256']:
            errors.append('hash mismatch: '+path.name)
        with path.open(encoding='utf-8',newline='') as file: rows=list(csv.DictReader(file))
        if len(rows)!=clip['samples']: errors.append('row count: '+path.name)
        elapsed=[]
        for row in rows:
            if any(row[key]!=str(value) for key,value in [('session_id',meta['session_id']),
                       ('round_id',clip['round_id']),('split',clip['split']),
                       ('label',clip['label']),('clip_id',clip['clip_id'])]):
                errors.append('row metadata mismatch: '+path.name)
            if not all(math.isfinite(float(row[f'{axis}{i}'])) for i in range(21) for axis in 'xyz'):
                errors.append('nonfinite coordinates: '+path.name)
            elapsed.append(float(row['elapsed_seconds']))
        if any(b<=a for a,b in zip(elapsed,elapsed[1:])): errors.append('nonincreasing time: '+path.name)
        round_splits[clip['round_id']].add(clip['split'])
        if clip['accepted']:
            accepted.append(clip)
            count[(clip['split'],clip['label'])]+=len(rows)
            handedness.update(row['handedness'] for row in rows)
    if any(len(s)>1 for s in round_splits.values()): errors.append('round crosses splits')
    expected={(round_id,label) for round_id in range(1,len(meta['round_splits'])+1) for label in meta['classes']}
    complete=expected=={(clip['round_id'],clip['label']) for clip in accepted}
    sessions.append({'session_id':meta['session_id'],'declared_hand':meta['declared_hand'],
                     'round_count':len(meta['round_splits']),'class_count':len(meta['classes']),
                     'verified_actual_hand':verification.get(meta['session_id'],{}).get('verified_actual_hand'),
                     'accepted_clips':len(accepted),'total_samples':sum(count.values()),
                     'complete':complete,'errors':sorted(set(errors)),
                     'counts':[{'split':split,'label':label,'samples':n} for (split,label),n in sorted(count.items())],
                     'detected_handedness':dict(handedness)})
(base/'data_audit.json').write_text(json.dumps(sessions,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# ตรวจข้อมูลท่ามือ','', 'รายงานนี้ตรวจเฉพาะความครบและความสอดคล้องของข้อมูล ไม่ใช่ผลประเมินโมเดล','']
for item in sessions:
    lines += [f'## {item["session_id"]}', '', f'มือที่ผู้ใช้ระบุ: {item["declared_hand"]}',
              f'ข้างจริงที่ผู้ใช้ยืนยันในแชท: {item["verified_actual_hand"] or "รอยืนยัน"} (บันทึกแยกใน hand_verification.json ไม่แก้ข้อมูลเดิม)',
              f'เก็บผ่านเกณฑ์จำนวน {item["accepted_clips"]} ช่วง รวม {item["total_samples"]} ตัวอย่าง',
              f'ครบ {item["round_count"]} รอบ × {item["class_count"]} กลุ่ม: {item["complete"]}',
              f'ข้อผิดพลาดรูปแบบ/จำนวน/แฮช/เวลา/การแบ่งรอบ: {item["errors"] or "ไม่พบ"}', '',
              '| กลุ่ม | train | validation | test |','|---|---:|---:|---:|']
    counts={(r['split'],r['label']):r['samples'] for r in item['counts']}
    for label in ['toggle','next','previous','neutral']:
        lines.append('| '+label+' | '+' | '.join(str(counts.get((split,label),0)) for split in ['train','validation','test'])+' |')
    lines += ['',f'ป้ายข้างมือจากตัวตรวจ (ไม่ใช่การยืนยันข้างจริง): {item["detected_handedness"]}', '']
lines += ['ข้อมูลจากคนเดียวและถ่ายในช่วงเวลาใกล้กัน ยังไม่ยืนยันว่าป้ายท่าที่ผู้ใช้ทำถูกต้องทุกตัวอย่าง หรือใช้ได้กับทุกคนและทุกสภาพแสง',
          'เก็บทั้งรอบไว้ในชุดเดียวกันเสมอ ไม่สุ่มเฟรมข้ามชุด และต้องเลือกโมเดลจาก validation ก่อนใช้ test ประเมินท้ายงาน',
          'ข้อมูลมือซ้ายที่เพิ่มจะเป็น session ใหม่ มีรอบ train/validation/test ของตนเอง และรายงานผลแยกตามข้างมือ',
          'การสะท้อนพิกัดช่วยให้รูปมือสองข้างคล้ายกันได้ แต่ไม่ทดแทนการเก็บและทดสอบมือซ้ายจริง']
(base/'DATA_AUDIT_TH.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(sessions,ensure_ascii=False,indent=2))
