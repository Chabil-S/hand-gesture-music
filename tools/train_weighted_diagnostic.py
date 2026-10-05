"""Train-only weighting experiment; never load test coordinates or activate music."""
import csv, hashlib, json, sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
import joblib
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import f1_score
from gesture_features import features
from joint_features import FingerReachFeatures
from revision_validation import revision_checks
from label_review import load_reviews, exclusion_for

BASE=Path(__file__).resolve().parents[1]/'outputs'
EXCLUDED={'20261004_213132_79f24dc6','20261004_214424_3624e47e'}

def main():
    protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [BASE/'latest_model.json',BASE/'evaluation_history.json'] if p.exists()}
    audit=json.loads((BASE/'data_audit.json').read_text(encoding='utf-8'))
    reviews=load_reviews(BASE/'data/label_review.json')
    X=[]; rows=[]; inputs=[]
    for s in audit:
        if s['session_id'] in EXCLUDED: continue
        assert s['complete'] and not s['errors'] and s['verified_actual_hand']
        d=BASE/'data/raw'/s['session_id']
        meta=json.loads((d/'session.json').read_text(encoding='utf-8'))
        kind=meta.get('collection_kind','base_four_classes')
        for line in (d/'clips.jsonl').read_text(encoding='utf-8').splitlines():
            c=json.loads(line)
            if not c['accepted'] or c['split']=='test': continue
            p=d/c['csv']; sha=hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha==c['sha256']
            if exclusion_for(reviews,s['session_id'],c,sha): continue
            inputs.append({'file':str(p.relative_to(BASE)), 'sha256':sha})
            with p.open(encoding='utf-8',newline='') as f:
                for r in csv.DictReader(f):
                    assert r['split'] in ('train','validation')
                    X.append(features([float(r[f'{a}{i}']) for i in range(21) for a in 'xyz'],int(r['width']),int(r['height'])))
                    rows.append((r['label'],r['split'],s['verified_actual_hand'],kind,s['session_id']+':'+r['clip_id'],float(r['elapsed_seconds'])))
    X=np.asarray(X); y=np.array([r[0] for r in rows]); tr=np.array([r[1]=='train' for r in rows]); va=~tr
    hand=np.array([r[2] for r in rows]); kind=np.array([r[3] for r in rows]); group=np.array([r[4] for r in rows]); times=np.array([r[5] for r in rows])
    assert not set(group[tr])&set(group[va])
    trials=[]; best=None; best_rank=None; best_model=None
    for C in (1,10):
        for negative_weight in (2,4,8):
            for neutral_weight in (1,2):
                weights=np.ones(tr.sum())
                weights[(y[tr]=='neutral') & (kind[tr]=='base_four_classes')]=neutral_weight
                weights[kind[tr]=='three_finger_negative']=negative_weight
                weights/=weights.mean()
                model=make_pipeline(FingerReachFeatures(),StandardScaler(),SVC(C=C,probability=True,random_state=42))
                model.fit(X[tr],y[tr],svc__sample_weight=weights)
                prob=model.predict_proba(X[va]); pred=model.classes_[prob.argmax(axis=1)]
                for threshold in (.6,.7,.8,.85,.9):
                    runtime=np.where(prob.max(axis=1)>=threshold,pred,'uncertain')
                    effective=np.where(runtime=='uncertain','neutral',runtime)
                    checks=revision_checks(y[va],effective,hand[va],kind[va],group[va],times[va],runtime)
                    score=float(np.mean([f1_score(y[va][hand[va]==h],effective[hand[va]==h],average='macro') for h in ('left','right')]))
                    t={'C':C,'three_finger_weight':negative_weight,'base_neutral_weight':neutral_weight,'threshold':threshold,'selection_score':score,'checks':checks}
                    trials.append(t)
                    rank=(checks['passed'],checks['temporal_passed'],score)
                    if checks['event_integrity_passed'] and (best_rank is None or rank>best_rank):best=t;best_rank=rank;best_model=model
                print(C,negative_weight,neutral_weight,'done',flush=True)
    report={'protocol':'train-only sample weights normalized to mean one; unchanged validation and gate; test coordinates never loaded','counts':{'train':int(tr.sum()),'validation':int(va.sum())},'inputs':inputs,'excluded_sessions':sorted(EXCLUDED),'trials':trials,'selected':best,'test_evaluated':False,'activated':False}
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    dest=BASE/'weighted_experiments'/stamp;dest.mkdir(parents=True)
    if best:
        modeldir=BASE/'models'/stamp;modeldir.mkdir()
        config={'selected_model':'Weighted FingerReach SVC RBF C='+str(best['C']),'threshold':best['threshold'],'hold_seconds':.6,'release_seconds':.35,'max_frame_gap_seconds':.3,'eligible_for_activation':False,'full_validation_passed':best['checks']['passed'],'revision_validation':best['checks'],'purpose':'weighted validation-only diagnostic; no music activation','test_evaluated':False,'trained_on':'train only','counts':report['counts'],'inputs':inputs,'weighting':{k:best[k] for k in ('three_finger_weight','base_neutral_weight')},'excluded_sessions':sorted(EXCLUDED)}
        (modeldir/'selection_frozen.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
        joblib.dump(best_model,modeldir/'gesture_model.joblib')
        (BASE/'data/latest_diagnostic.json').write_text(json.dumps({'directory':str(modeldir.relative_to(BASE))}),encoding='utf-8')
        report['model_directory']=str(modeldir.relative_to(BASE))
    for p,sha in protected.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha
    report['production_and_test_history_unchanged']=True
    (dest/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'report_directory':str(dest),'selected':best,'counts':report['counts']},indent=2),flush=True)

if __name__=='__main__':main()
