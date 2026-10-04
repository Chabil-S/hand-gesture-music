"""Select models on validation, freeze settings, then evaluate test once."""
import csv
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from gesture_features import features, FEATURE_VERSION

BASE=Path(__file__).resolve().parent
LABELS=['neutral','next','previous','toggle']
THAI={'neutral':'ไม่สั่งงาน','next':'ถัดไป','previous':'ก่อนหน้า','toggle':'เล่น/พัก'}

def dump(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    audit=json.loads((BASE/'data_audit.json').read_text(encoding='utf-8'))
    if not audit or any(s['errors'] or not s['complete'] or not s['verified_actual_hand'] for s in audit):
        raise RuntimeError('Data audit incomplete or actual hand unverified')
    X=[]; y=[]; hand=[]; split=[]; groups=[]; clip_ids=[]; inputs=[]
    for session in audit:
        directory=BASE/'data'/'raw'/session['session_id']
        for line in (directory/'clips.jsonl').read_text(encoding='utf-8').splitlines():
            clip=json.loads(line)
            if not clip['accepted']: continue
            path=directory/clip['csv']
            checksum=hashlib.sha256(path.read_bytes()).hexdigest()
            if checksum!=clip['sha256']: raise RuntimeError('Input hash mismatch')
            inputs.append({'file':str(path.relative_to(BASE)),'sha256':checksum})
            with path.open(encoding='utf-8',newline='') as file:
                for row in csv.DictReader(file):
                    X.append(features([float(row[f'{axis}{i}']) for i in range(21) for axis in 'xyz'],
                                      int(row['width']),int(row['height'])))
                    y.append(row['label']); hand.append(session['verified_actual_hand']); split.append(row['split'])
                    groups.append(session['session_id']+':'+row['round_id']); clip_ids.append(row['clip_id'])
    X=np.asarray(X); y=np.asarray(y); hand=np.asarray(hand); split=np.asarray(split); groups=np.asarray(groups)
    for a,b in [('train','validation'),('train','test'),('validation','test')]:
        if set(groups[split==a]) & set(groups[split==b]): raise RuntimeError('Group leakage')
    tr=split=='train'; va=split=='validation'; te=split=='test'
    models=[
        ('Logistic C=1',make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=3000))),
        ('Logistic C=10',make_pipeline(StandardScaler(),LogisticRegression(C=10,max_iter=3000))),
        ('KNN k=5',make_pipeline(StandardScaler(),KNeighborsClassifier(n_neighbors=5,weights='distance'))),
        ('KNN k=11',make_pipeline(StandardScaler(),KNeighborsClassifier(n_neighbors=11,weights='distance'))),
        ('RandomForest depth=12',RandomForestClassifier(n_estimators=160,max_depth=12,random_state=42,n_jobs=-1)),
        ('RandomForest full',RandomForestClassifier(n_estimators=160,random_state=42,n_jobs=-1)),
    ]
    candidates=[]
    for name,model in models:
        model.fit(X[tr],y[tr])
        pred=model.predict(X[va])
        per_hand={h:f1_score(y[va & (hand==h)],model.predict(X[va & (hand==h)]),
                            labels=LABELS,average='macro',zero_division=0) for h in ['left','right']}
        entry={'name':name,'validation_macro_f1':float(f1_score(y[va],pred,labels=LABELS,average='macro')),
               'validation_accuracy':float(accuracy_score(y[va],pred)),
               'validation_hand_macro_f1':per_hand,'selection_score':float(np.mean(list(per_hand.values())))}
        candidates.append(entry)
        print(name,entry['selection_score'],flush=True)
    best_index=max(range(len(candidates)),key=lambda i:candidates[i]['selection_score'])
    name,model=models[best_index]
    probabilities=model.predict_proba(X[va]); classes=model.classes_
    raw_pred=classes[np.argmax(probabilities,axis=1)]; scores=probabilities.max(axis=1)
    threshold_trials=[]
    for threshold in [0.6,0.7,0.8,0.9]:
        effective=np.where(scores>=threshold,raw_pred,'neutral')
        per_hand=[f1_score(y[va][hand[va]==h],effective[hand[va]==h],labels=LABELS,average='macro',zero_division=0) for h in ['left','right']]
        threshold_trials.append({'threshold':threshold,'mean_hand_macro_f1':float(np.mean(per_hand)),
                                 'neutral_false_commands':int(np.sum((y[va]=='neutral') & (effective!='neutral'))),
                                 'command_coverage':float(np.mean(effective[y[va]!='neutral']!='neutral'))})
    chosen=max(threshold_trials,key=lambda t:(t['mean_hand_macro_f1'],-t['neutral_false_commands'],t['command_coverage']))
    stamp=datetime.now(timezone(timedelta(hours=7))).strftime('%Y%m%d_%H%M%S')
    destination=BASE/'models'/stamp
    destination.mkdir(parents=True,exist_ok=False)
    config={'selected_model':name,'feature_version':FEATURE_VERSION,'threshold':chosen['threshold'],
            'hold_seconds':0.6,'release_seconds':0.35,'max_frame_gap_seconds':0.3,
            'sklearn_version':sklearn.__version__,'trained_on':'train only',
            'selection':'mean per-hand validation macro-F1; candidate order breaks exact ties',
            'threshold_selection':'validation only','temporal_settings':'engineering defaults; not tuned on test',
            'counts':{s:int(np.sum(split==s)) for s in ['train','validation','test']},'inputs':inputs}
    # Persist selection before calculating any test performance.
    dump(destination/'selection_frozen.json',config)
    joblib.dump(model,destination/'gesture_model.joblib')
    dump(destination/'validation_candidates.json',{'models':candidates,'thresholds':threshold_trials})
    np.savez_compressed(destination/'derived_features.npz',X=X,y=y,hand=hand,split=split,group=groups)
    metrics={}
    for partition in ['validation','test']:
        mask=split==partition
        prob=model.predict_proba(X[mask]); pred=model.classes_[prob.argmax(axis=1)]
        gated=np.where(prob.max(axis=1)>=chosen['threshold'],pred,'neutral')
        rows={}
        for h in ['all','left','right']:
            sub=np.ones(mask.sum(),dtype=bool) if h=='all' else hand[mask]==h
            rows[h]={'samples':int(sub.sum()),'accuracy':float(accuracy_score(y[mask][sub],pred[sub])),
                     'macro_f1':float(f1_score(y[mask][sub],pred[sub],labels=LABELS,average='macro',zero_division=0)),
                     'report':classification_report(y[mask][sub],pred[sub],labels=LABELS,output_dict=True,zero_division=0),
                     'confusion_matrix':confusion_matrix(y[mask][sub],pred[sub],labels=LABELS).tolist(),
                     'gated_accuracy':float(accuracy_score(y[mask][sub],gated[sub])),
                     'neutral_false_commands':int(np.sum((y[mask][sub]=='neutral') & (gated[sub]!='neutral'))),
                     'missed_command_frames':int(np.sum((y[mask][sub]!='neutral') & (gated[sub]=='neutral')))}
        metrics[partition]=rows
    dump(destination/'classification_metrics.json',metrics)
    with (destination/'test_predictions.csv').open('x',encoding='utf-8',newline='') as file:
        writer=csv.writer(file); writer.writerow(['hand','group','actual','predicted','score','accepted_label'])
        prob=model.predict_proba(X[te]); pred=model.classes_[prob.argmax(axis=1)]
        for h,g,actual,p,score in zip(hand[te],groups[te],y[te],pred,prob.max(axis=1)):
            writer.writerow([h,g,actual,p,float(score),p if score>=chosen['threshold'] else 'uncertain'])
    lines=['# ผลฝึกโมเดลรู้จำท่ามือ','',f'เลือกโมเดล: **{name}** จาก validation ของสองข้าง ไม่ใช้ test เลือกโมเดล',
           f'จำนวนตัวอย่าง: train {tr.sum()}, validation {va.sum()}, test {te.sum()}','',
           '| ชุด | ข้าง | ความถูกต้องรายเฟรม | Macro-F1 | จำนวนเฟรม |','|---|---|---:|---:|---:|']
    for part in ['validation','test']:
        for h in ['all','right','left']:
            r=metrics[part][h]
            lines.append(f'| {part} | {h} | {100*r["accuracy"]:.2f}% | {r["macro_f1"]:.4f} | {r["samples"]} |')
    lines += ['', '| โมเดลที่ลอง | Validation เฉลี่ย Macro-F1 สองข้าง |','|---|---:|']
    for c in candidates: lines.append(f'| {c["name"]} | {c["selection_score"]:.4f} |')
    lines += ['',f'เกณฑ์คะแนนโมเดลสำหรับยืนยันท่า: {chosen["threshold"]:.2f} เลือกจาก validation คะแนนนี้ไม่ใช่โอกาสถูกที่สอบเทียบแล้ว',
              'พิกัดถูกแปลงเป็นระยะระหว่างจุด 210 ค่า ปรับสัดส่วนภาพและหารด้วยขนาดฝ่ามือ ช่วยให้สองข้าง/ตำแหน่ง/มุมคล้ายกันโดยไม่ต้องใช้ป้าย Left/Right จากตัวตรวจเป็นคุณลักษณะ',
              'MediaPipe สกัดตำแหน่งมือด้วยโมเดลสำเร็จรูป ส่วนตัวจำแนก 4 กลุ่มฝึกใหม่จากข้อมูลผู้ใช้ ไม่ใช้ Gesture Recognizer สำเร็จรูป',
              'แบ่งทั้ง session+round เป็นกลุ่มเดียวกันตามแผนเดิม ไม่มีการสุ่มเฟรมข้ามชุด โมเดลสุดท้ายยังฝึกด้วย train เท่านั้น',
              '## Confusion matrix ของ test', '', 'แถวคือท่าจริง คอลัมน์คือท่าที่โมเดลทำนาย', '',
              '| จริง / ทำนาย | ไม่สั่งงาน | ถัดไป | ก่อนหน้า | เล่น/พัก |','|---|---:|---:|---:|---:|']
    for label,row in zip(LABELS,metrics['test']['all']['confusion_matrix']):
        lines.append('| '+THAI[label]+' | '+' | '.join(map(str,row))+' |')
    lines += ['', '## ข้อจำกัดและขั้นต่อไป','',
              'คะแนนรายเฟรมไม่ได้เท่ากับอัตราสั่งเพลงสำเร็จจริง และเฟรมในแต่ละช่วงมีความสัมพันธ์กัน จำนวนเฟรมจึงไม่ใช่จำนวนการทดลองอิสระ',
              'มีผู้ใช้คนเดียว มือขวา 1 session และมือซ้าย 1 session สภาพใกล้กัน จึงยังสรุปผลข้ามคนหรือแสงอื่นไม่ได้ ไม่มีป้ายหน้ามือ/หลังมือให้รายงานคะแนนแยก',
              'กลุ่ม neutral ยังมีเพียงท่าอื่นที่เก็บ ไม่ครอบคลุมท่าที่ไม่รู้จักทุกแบบ คะแนนสูงก็อาจสั่งผิดเมื่อเจอท่าใหม่',
              'หน้าทดลองเริ่มในโหมดดูผล ไม่ส่งเพลง ต้องกดเริ่มควบคุมก่อน ยืนยันท่า 0.6 วินาทีและปล่อยเป็น neutral หรือเอามือออก 0.35 วินาทีก่อนคำสั่งถัดไป',
              'ต้องทดสอบสั่งเพลงจริงแยก: แต่ละคำสั่ง มือซ้าย/ขวา ค้างท่า ปล่อยท่า ไม่เห็นมือ และท่าอื่น พร้อมบันทึกคำสั่งผิด/ซ้ำและผลเครื่องเล่น',
              '', 'อ้างอิงวิธีประเมิน: https://scikit-learn.org/stable/modules/cross_validation.html']
    (destination/'MODEL_REPORT_TH.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    dump(BASE/'latest_model.json',{'directory':str(destination.relative_to(BASE))})
    print(json.dumps({'selected':name,'threshold':chosen['threshold'],'counts':config['counts'],
                      'test':{h:{k:v for k,v in r.items() if k in ['accuracy','macro_f1','samples','gated_accuracy','neutral_false_commands','missed_command_frames']} for h,r in metrics['test'].items()},
                      'directory':str(destination)},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
