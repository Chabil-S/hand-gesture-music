import sys,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from label_review import load_reviews,exclusion_for
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'review.json'
    assert load_reviews(path)=={}
    entry={'input':'session/clip.csv','sha256':'a'*64,'reason':'user reported wrong pose'}
    path.write_text(json.dumps({'excluded_clips':[entry]}),encoding='utf-8')
    review=load_reviews(path);clip={'csv':'clip.csv','label':'next','split':'validation','samples':79}
    assert exclusion_for(review,'other',clip,'a'*64) is None
    assert exclusion_for(review,'session',clip,'a'*64)['original_label']=='next'
    for altered,checksum in [(dict(clip,split='test'),'a'*64),(clip,'b'*64)]:
        try:exclusion_for(review,'session',altered,checksum)
        except ValueError:pass
        else:raise AssertionError('Unsafe quarantine accepted')
    path.write_text(json.dumps({'excluded_clips':[dict(entry,input='../clip.csv')]}),encoding='utf-8')
    try:load_reviews(path)
    except ValueError:pass
    else:raise AssertionError('Invalid path accepted')
print('PASS: reviewed clips require exact source hash, unrelated clips retained, test filtering refused, raw untouched')
