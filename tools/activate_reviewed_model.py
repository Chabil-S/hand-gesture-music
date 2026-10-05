"""Recheck a frozen candidate against explicit local policy, then switch the live pointer."""
import csv,hashlib,json,shutil,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/'outputs'
sys.path.insert(0,str(BASE))
import numpy as np,joblib
from gesture_features import features,FEATURE_VERSION
from revision_validation import revision_checks

SOURCE='20261005_194641'
SHA='f9df930a1654287d5c8e47df66e152129161782464e15a3b6017ff6b81a48a7d'

def main():
    policy=json.loads((BASE/'acceptance_policy.json').read_text(encoding='utf-8'))
    target=float(policy['minimum_command_recall'])
    if not 0<target<=1:raise ValueError('Recall target must be in (0,1]')
    source=BASE/'models'/SOURCE;artifact=source/'gesture_model.joblib'
    assert hashlib.sha256(artifact.read_bytes()).hexdigest()==SHA
    cfg=json.loads((source/'selection_frozen.json').read_text(encoding='utf-8'))
    assert cfg['threshold']==.8 and cfg['hold_seconds']==.6 and cfg['release_seconds']==.35
    audit={s['session_id']:s for s in json.loads((BASE/'data_audit.json').read_text(encoding='utf-8'))}
    X=[];ys=[];hands=[];kinds=[];groups=[];times=[]
    for item in cfg['inputs']:
        path=BASE/item['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        sid=path.parent.name
        meta=json.loads((path.parent/'session.json').read_text(encoding='utf-8'))
        with path.open(encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f):
                if r['split']!='validation':continue
                X.append(features([float(r[f'{a}{i}']) for i in range(21) for a in 'xyz'],int(r['width']),int(r['height'])))
                ys.append(r['label']);hands.append(audit[sid]['verified_actual_hand']);kinds.append(meta.get('collection_kind','base_four_classes'))
                groups.append(sid+':'+r['clip_id']);times.append(float(r['elapsed_seconds']))
    assert len(X)==cfg['counts']['validation']
    m=joblib.load(artifact);p=m.predict_proba(np.asarray(X));pred=m.classes_[p.argmax(axis=1)]
    runtime=np.where(p.max(axis=1)>=cfg['threshold'],pred,'uncertain')
    checks=revision_checks(ys,np.where(runtime=='uncertain','neutral',runtime),hands,kinds,groups,times,runtime,minimum_command_recall=target)
    if not checks['passed']:raise RuntimeError('Candidate fails requested acceptance policy; live pointer unchanged')
    previous=json.loads((BASE/'latest_model.json').read_text(encoding='utf-8'))
    history=BASE/'evaluation_history.json';history_sha=hashlib.sha256(history.read_bytes()).hexdigest()
    stamp=datetime.now(timezone(timedelta(hours=7))).strftime('%Y%m%d_%H%M%S')
    dest=BASE/'models'/('reviewed_'+stamp);dest.mkdir()
    shutil.copy2(artifact,dest/'gesture_model.joblib')
    release=dict(cfg)
    release.update(feature_version=FEATURE_VERSION,eligible_for_activation=True,full_validation_passed=True,
        purpose='user-authorized live trial with revised command-recall acceptance policy',
        revision_validation=checks,original_revision_validation=cfg['revision_validation'],
        acceptance_policy=policy,source_directory=SOURCE,model_sha256=SHA,
        previous_live_directory=previous['directory'],test_evaluated=False,
        activation_scope='local Apple Music trial; not independently tested generalization',
        user_authorization='User requested minimum acceptance 85% and trying this model; no further capture')
    (dest/'selection_frozen.json').write_text(json.dumps(release,ensure_ascii=False,indent=2),encoding='utf-8')
    assert hashlib.sha256(history.read_bytes()).hexdigest()==history_sha
    (BASE/'latest_model.json').write_text(json.dumps({'directory':str(dest.relative_to(BASE))}),encoding='utf-8')
    print(json.dumps({'directory':str(dest),'minimum_command_recall':target,'threshold':cfg['threshold'],'previous_live':previous,'checks':checks},indent=2))

if __name__=='__main__':main()
