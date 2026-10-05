"""Select models on validation, freeze settings, then evaluate test once."""
import argparse
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
from sklearn.svm import SVC
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from gesture_features import features, FEATURE_VERSION
from revision_validation import revision_checks
from joint_features import JointFeatures
from combined_features import CombinedFeatures

BASE=Path(__file__).resolve().parent
LABELS=['neutral','next','previous','toggle']
THAI={'neutral':'ไม่สั่งงาน','next':'ถัดไป','previous':'ก่อนหน้า','toggle':'เล่น/พัก'}

def dump(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--require-three-finger-validation",action="store_true")
    parser.add_argument("--exclude-session",action="append",default=[],help="Explicitly exclude abandoned sessions; recorded in model provenance")
    parser.add_argument("--activate",action="store_true",help="Explicitly make a revision the live model after reviewing its report")
    options=parser.parse_args()
    history_path=BASE/'evaluation_history.json'
    history=json.loads(history_path.read_text(encoding='utf-8')) if history_path.exists() else {'test_sessions':[]}
    previously_evaluated=set(history['test_sessions'])
    audit=json.loads((BASE/'data_audit.json').read_text(encoding='utf-8'))
    excluded=[session for session in audit if session['session_id'] in options.exclude_session]
    if set(options.exclude_session)-{session['session_id'] for session in audit}:
        raise RuntimeError('Unknown excluded session')
    audit=[session for session in audit if session['session_id'] not in options.exclude_session]
    if not audit or any(s['errors'] or not s['complete'] or not s['verified_actual_hand'] for s in audit):
        raise RuntimeError('Data audit incomplete or actual hand unverified')
    X=[]; y=[]; hand=[]; split=[]; groups=[]; clip_ids=[]; inputs=[]; kinds=[]; elapsed=[]; clip_groups=[]
    for session in audit:
        directory=BASE/'data'/'raw'/session['session_id']
        metadata=json.loads((directory/'session.json').read_text(encoding='utf-8'))
        kind=metadata.get('collection_kind','base_four_classes')
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
                    kinds.append(kind)
                    elapsed.append(float(row['elapsed_seconds']));clip_groups.append(session['session_id']+':'+row['clip_id'])
                    y.append(row['label']); hand.append(session['verified_actual_hand']); split.append(row['split'])
                    groups.append(session['session_id']+':'+row['round_id']); clip_ids.append(row['clip_id'])
    X=np.asarray(X); y=np.asarray(y); hand=np.asarray(hand); split=np.asarray(split); groups=np.asarray(groups); kinds=np.asarray(kinds);elapsed=np.asarray(elapsed);clip_groups=np.asarray(clip_groups)
    require_revision=options.require_three_finger_validation or 'three_finger_negative' in kinds
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
        ('Logistic neutral weight=3',make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=3000,class_weight={'neutral':3,'next':1,'previous':1,'toggle':1}))),
        ('SVC RBF C=1',make_pipeline(StandardScaler(),SVC(C=1,gamma='scale',probability=True,random_state=42))),
        ('SVC RBF C=10',make_pipeline(StandardScaler(),SVC(C=10,gamma='scale',probability=True,random_state=42))),
        ('SVC RBF neutral weight=3',make_pipeline(StandardScaler(),SVC(C=1,gamma='scale',probability=True,random_state=42,class_weight={'neutral':3,'next':1,'previous':1,'toggle':1}))),
        ('Joint Logistic C=1',make_pipeline(JointFeatures(),StandardScaler(),LogisticRegression(C=1,max_iter=3000))),
        ('Joint Logistic C=10',make_pipeline(JointFeatures(),StandardScaler(),LogisticRegression(C=10,max_iter=3000))),
        ('Joint KNN k=5',make_pipeline(JointFeatures(),StandardScaler(),KNeighborsClassifier(n_neighbors=5,weights='distance'))),
        ('Joint SVC RBF C=1',make_pipeline(JointFeatures(),StandardScaler(),SVC(C=1,gamma='scale',probability=True,random_state=42))),
        ('Joint SVC RBF C=10',make_pipeline(JointFeatures(),StandardScaler(),SVC(C=10,gamma='scale',probability=True,random_state=42))),
        ('Combined Logistic C=0.1',make_pipeline(CombinedFeatures(),StandardScaler(),LogisticRegression(C=.1,max_iter=3000))),
        ('Combined Logistic C=1',make_pipeline(CombinedFeatures(),StandardScaler(),LogisticRegression(C=1,max_iter=3000))),
        ('Combined Logistic C=10',make_pipeline(CombinedFeatures(),StandardScaler(),LogisticRegression(C=10,max_iter=3000))),
    ]
    baseline_validation=None
    if require_revision and (BASE/'latest_model.json').exists():
        old_directory=BASE/json.loads((BASE/'latest_model.json').read_text(encoding='utf-8'))['directory']
        old_config=json.loads((old_directory/'selection_frozen.json').read_text(encoding='utf-8'))
        old_model=joblib.load(old_directory/'gesture_model.joblib')
        old_prob=old_model.predict_proba(X[va])
        old_accepted=np.where(old_prob.max(axis=1)>=old_config['threshold'],
                              old_model.classes_[old_prob.argmax(axis=1)],'neutral')
        baseline_validation={'directory':str(old_directory.relative_to(BASE)),
                             'checks':revision_checks(y[va],old_accepted,hand[va],kinds[va])}
    candidates=[]; revision_trials=[]
    for name,model in models:
        model.fit(X[tr],y[tr])
        pred=model.predict(X[va])
        per_hand={h:f1_score(y[va & (hand==h)],model.predict(X[va & (hand==h)]),
                            labels=LABELS,average='macro',zero_division=0) for h in ['left','right']}
        entry={'name':name,'validation_macro_f1':float(f1_score(y[va],pred,labels=LABELS,average='macro')),
               'validation_accuracy':float(accuracy_score(y[va],pred)),
               'validation_hand_macro_f1':per_hand,'selection_score':float(np.mean(list(per_hand.values())))}
        candidates.append(entry)
        if require_revision:
            probabilities=model.predict_proba(X[va])
            for threshold in [0.6,0.7,0.8,0.85,0.9]:
                effective=np.where(probabilities.max(axis=1)>=threshold,
                                   model.classes_[probabilities.argmax(axis=1)],'neutral')
                checks=revision_checks(y[va],effective,hand[va],kinds[va],clip_groups[va],elapsed[va],
                                       np.where(probabilities.max(axis=1)>=threshold,model.classes_[probabilities.argmax(axis=1)],'uncertain'))
                per_hand=[f1_score(y[va][hand[va]==h],effective[hand[va]==h],labels=LABELS,
                                  average='macro',zero_division=0) for h in ['left','right']]
                revision_trials.append({'model_index':len(candidates)-1,'model':name,
                                        'threshold':threshold,'selection_score':float(np.mean(per_hand)),
                                        'checks':checks})
        print(name,entry['selection_score'],flush=True)
    best_index=max(range(len(candidates)),key=lambda i:candidates[i]['selection_score'])
    selected_revision=None
    if require_revision:
        eligible=[trial for trial in revision_trials if trial['checks']['passed']]
        if not eligible:
            dump(BASE/'three_finger_validation_attempt.json',{'trials':revision_trials,'published':False})
            raise RuntimeError('No candidate passed all-command/three-finger validation; current model unchanged, test not evaluated')
        selected_revision=max(eligible,key=lambda t:t['selection_score'])
        best_index=selected_revision['model_index']
    name,model=models[best_index]
    probabilities=model.predict_proba(X[va]); classes=model.classes_
    raw_pred=classes[np.argmax(probabilities,axis=1)]; scores=probabilities.max(axis=1)
    threshold_trials=[]
    for threshold in [0.6,0.7,0.8,0.85,0.9]:
        effective=np.where(scores>=threshold,raw_pred,'neutral')
        per_hand=[f1_score(y[va][hand[va]==h],effective[hand[va]==h],labels=LABELS,average='macro',zero_division=0) for h in ['left','right']]
        threshold_trials.append({'threshold':threshold,'mean_hand_macro_f1':float(np.mean(per_hand)),
                                 'neutral_false_commands':int(np.sum((y[va]=='neutral') & (effective!='neutral'))),
                                 'command_coverage':float(np.mean(effective[y[va]!='neutral']!='neutral'))})
    chosen=max(threshold_trials,key=lambda t:(t['mean_hand_macro_f1'],-t['neutral_false_commands'],t['command_coverage']))
    if selected_revision:
        chosen=next(t for t in threshold_trials if t['threshold']==selected_revision['threshold'])
    stamp=datetime.now(timezone(timedelta(hours=7))).strftime('%Y%m%d_%H%M%S')
    destination=BASE/'models'/stamp
    destination.mkdir(parents=True,exist_ok=False)
    config={'selected_model':name,'feature_version':FEATURE_VERSION,'threshold':chosen['threshold'],
            'hold_seconds':0.6,'release_seconds':0.35,'max_frame_gap_seconds':0.3,
            'sklearn_version':sklearn.__version__,'trained_on':'train only',
            'selection':'mean per-hand validation macro-F1; candidate order breaks exact ties',
            'threshold_selection':'validation only','temporal_settings':'engineering defaults; not tuned on test',
            'counts':{s:int(np.sum(split==s)) for s in ['train','validation','test']},'inputs':inputs}
    config['excluded_sessions']=[{'session_id':session['session_id'],'complete':session['complete'],'reason':'explicit operator exclusion'} for session in excluded]
    config['baseline_validation']=baseline_validation
    config['collection_kinds']=sorted(set(kinds.tolist()))
    config['revision_validation']=selected_revision['checks'] if selected_revision else None
    if selected_revision:
        config['selection']='validation-only: pass all-command, neutral, three-finger and measured-neutral release checks per hand, then maximize gated per-hand macro-F1; stable candidate/threshold order breaks ties'
        config['test_scope']='fresh and previously evaluated test sessions are reported separately; previously evaluated sessions are regression checks'
        config['test_session_scope']={session['session_id']:('regression' if session['session_id'] in previously_evaluated else 'fresh') for session in audit}
    # Persist selection before calculating any test performance.
    dump(destination/'selection_frozen.json',config)
    joblib.dump(model,destination/'gesture_model.joblib')
    dump(destination/'validation_candidates.json',{'models':candidates,'thresholds':threshold_trials,'revision_trials':revision_trials})
    np.savez_compressed(destination/'derived_features.npz',X=X,y=y,hand=hand,split=split,group=groups,kind=kinds)
    metrics={}
    revision_metrics={}
    for partition in ['validation','test']:
        mask=split==partition
        prob=model.predict_proba(X[mask]); pred=model.classes_[prob.argmax(axis=1)]
        gated=np.where(prob.max(axis=1)>=chosen['threshold'],pred,'neutral')
        revision_metrics[partition]=revision_checks(y[mask],gated,hand[mask],kinds[mask],clip_groups[mask],elapsed[mask],
            np.where(prob.max(axis=1)>=chosen['threshold'],pred,'uncertain'))
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
    dump(destination/'three_finger_metrics.json',revision_metrics)
    session_test={}
    for session in audit:
        mask=te & np.char.startswith(groups,session['session_id']+':')
        if not mask.any():continue
        probabilities=model.predict_proba(X[mask])
        accepted=np.where(probabilities.max(axis=1)>=chosen['threshold'],
                          model.classes_[probabilities.argmax(axis=1)],'neutral')
        session_test[session['session_id']]={'kind':str(kinds[mask][0]),'hand':session['verified_actual_hand'],
            'samples':int(mask.sum()),'false_commands':int(np.sum((y[mask]=='neutral') & (accepted!='neutral'))),
            'accepted_accuracy':float(accuracy_score(y[mask],accepted))}
    dump(destination/'test_by_session.json',session_test)
    dump(history_path,{'test_sessions':sorted(previously_evaluated|set(session_test))})
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
              'มีผู้ใช้คนเดียวและเก็บในสภาพใกล้กัน จึงยังสรุปผลข้ามคนหรือแสงอื่นไม่ได้ ไม่มีป้ายหน้ามือ/หลังมือให้รายงานคะแนนแยก',
              'กลุ่ม neutral ยังมีเพียงท่าอื่นที่เก็บ ไม่ครอบคลุมท่าที่ไม่รู้จักทุกแบบ คะแนนสูงก็อาจสั่งผิดเมื่อเจอท่าใหม่',
              'หน้าทดลองเริ่มในโหมดดูผล ไม่ส่งเพลง ต้องกดเริ่มควบคุมก่อน ยืนยันท่า 0.6 วินาทีและปล่อยเป็น neutral หรือเอามือออก 0.35 วินาทีก่อนคำสั่งถัดไป',
              'ต้องทดสอบสั่งเพลงจริงแยก: แต่ละคำสั่ง มือซ้าย/ขวา ค้างท่า ปล่อยท่า ไม่เห็นมือ และท่าอื่น พร้อมบันทึกคำสั่งผิด/ซ้ำและผลเครื่องเล่น',
              '', 'อ้างอิงวิธีประเมิน: https://scikit-learn.org/stable/modules/cross_validation.html']
    (destination/'MODEL_REPORT_TH.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if selected_revision:
        with (destination/'MODEL_REPORT_TH.md').open('a',encoding='utf-8') as report:
            report.write('\n## การตรวจทุกคำสั่งและท่าสามนิ้ว\n\nเลือกโมเดลและเกณฑ์คะแนนจาก validation เท่านั้น ก่อนเปิด test ต้องผ่าน: '+selected_revision['checks']['rule']+'\n')
            report.write('ชุด test ท่าเดิมเคยประเมินแล้ว จึงเป็นการตรวจการถดถอย ส่วน test สามนิ้วเป็นชุดใหม่ ไม่ใช่ชุดทดสอบใหม่ของทุกท่า\n')
            for partition,checks in revision_metrics.items():
                for h,r in checks['per_hand'].items():
                    report.write(f"{partition} {h}: สามนิ้วสั่งผิด {r['three_finger_false_commands']}/{r['three_finger_samples']} เฟรม; รับ V {r['v_accepted']}/{r['v_samples']} เฟรม\n")
    if not selected_revision or options.activate:
        dump(BASE/'latest_model.json',{'directory':str(destination.relative_to(BASE))})
    else:
        print('Revision saved for review; live model unchanged.',flush=True)
    print(json.dumps({'selected':name,'threshold':chosen['threshold'],'counts':config['counts'],
                      'test':{h:{k:v for k,v in r.items() if k in ['accuracy','macro_f1','samples','gated_accuracy','neutral_false_commands','missed_command_frames']} for h,r in metrics['test'].items()},
                      'directory':str(destination)},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
