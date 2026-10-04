import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from revision_validation import revision_checks

actual=['neutral','next','neutral','next']
hands=['left','left','right','right']
kinds=['three_finger_negative','base_four_classes']*2
assert revision_checks(actual,actual,hands,kinds)['passed']
assert not revision_checks(actual,['next','next','neutral','next'],hands,kinds)['passed']
assert not revision_checks(actual,['neutral','neutral','neutral','next'],hands,kinds)['passed']
assert not revision_checks(actual[:2],actual[:2],hands[:2],kinds[:2])['passed']
assert not revision_checks(['next','next'],['next','next'],['left','right'],['base_four_classes']*2)['passed']
assert not revision_checks(actual,['previous','next','neutral','next'],hands,kinds)['passed']
print('PASS: revision requires both hands, new negatives, no false commands, and retained V recognition')
