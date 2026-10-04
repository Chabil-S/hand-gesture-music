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

actual=[];accepted=[];hands=[];kinds=[];groups=[];times=[]
for hand in ('left','right'):
    for kind,label in [('three_finger_negative','neutral'),('base_four_classes','next')]:
        for i in range(7):
            actual.append(label);accepted.append('next' if label=='next' or i in (1,2) else 'neutral')
            hands.append(hand);kinds.append(kind);groups.append(hand+':'+kind);times.append(i*.15)
check=revision_checks(actual,accepted,hands,kinds,groups,times)
assert check['passed']
assert all(r['three_finger_false_commands']==2 and r['three_finger_command_events']==0 for r in check['per_hand'].values())
assert not revision_checks(actual,['next']*len(actual),hands,kinds,groups,times)['passed']
assert not revision_checks(actual,['neutral']*len(actual),hands,kinds,groups,times)['passed']
print('PASS: brief frame mistakes do not count as commands; held three-finger errors and missed V clips fail')
