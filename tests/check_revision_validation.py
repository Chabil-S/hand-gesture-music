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
    for kind,label in [('three_finger_negative','neutral')]+[('base_four_classes',x) for x in ('next','previous','toggle','neutral')]:
        for i in range(7):
            actual.append(label);accepted.append('next' if kind=='three_finger_negative' and i in (1,2) else label)
            hands.append(hand);kinds.append(kind);groups.append(hand+':'+kind+':'+label);times.append(i*.15)
check=revision_checks(actual,accepted,hands,kinds,groups,times)
assert check['passed']
assert all(r['three_finger_false_commands']==2 and r['three_finger_command_events']==0 for r in check['per_hand'].values())
assert not revision_checks(actual,['next']*len(actual),hands,kinds,groups,times)['passed']
assert not revision_checks(actual,['neutral']*len(actual),hands,kinds,groups,times)['passed']
print('PASS: brief frame mistakes do not count as commands; held three-finger errors and missed V clips fail')

# Correct-looking aggregate counts must not hide duplicates during a held thumb.
duplicate_actual=[];duplicate_runtime=[];duplicate_hands=[];duplicate_kinds=[];duplicate_groups=[];duplicate_times=[]
for a,b,h,k,g,t in zip(actual,accepted,hands,kinds,groups,times):
    duplicate_actual.append(a);duplicate_runtime.append(b);duplicate_hands.append(h);duplicate_kinds.append(k);duplicate_groups.append(g);duplicate_times.append(t)
    if g=='right:base_four_classes:previous' and t>.89:
        for j in range(1,30):
            duplicate_actual.append(a);duplicate_runtime.append('neutral' if j in (1,2,3,4) else a)
            duplicate_hands.append(h);duplicate_kinds.append(k);duplicate_groups.append(g);duplicate_times.append(t+j*.15)
assert not revision_checks(duplicate_actual,duplicate_runtime,duplicate_hands,duplicate_kinds,duplicate_groups,duplicate_times)['passed']
# Missing thumb/toggle data cannot pass the new temporal acceptance rule.
indices=[i for i,a in enumerate(actual) if a not in ('previous','toggle')]
assert not revision_checks(*[[x[i] for i in indices] for x in (actual,accepted,hands,kinds,groups,times)])['passed']
print('PASS: all commands and neutral release required, held-thumb repeats rejected')

# A score-rejected neutral is uncertain at runtime and cannot release a latch.
runtime=[('uncertain' if a=='neutral' and k=='base_four_classes' else b) for a,b,k in zip(actual,accepted,kinds)]
assert not revision_checks(actual,accepted,hands,kinds,groups,times,runtime)['passed']
print('PASS: mapping uncertain to neutral for classification metrics cannot fake a release')

aa=[];ee=[];hh=[];kk=[];gg=[];tt=[];rr=[]
for h in ('left','right'):
    for kind,label in [('three_finger_negative','neutral')]+[('base_four_classes',x) for x in ('next','previous','toggle','neutral')]:
        for i in range(21):
            degraded=h=='right' and label=='previous' and i in (1,2)
            aa.append(label);ee.append('neutral' if degraded else label);rr.append('uncertain' if degraded else label)
            hh.append(h);kk.append(kind);gg.append(h+kind+label);tt.append(i*.15)
result=revision_checks(aa,ee,hh,kk,gg,tt,rr)
assert result['temporal_passed'] and not result['passed']
print('PASS: temporal-safe diagnosis remains distinct from full acceptance; low frame recall still fails')

rr_late=[('uncertain' if h=='right' and a=='previous' and t<1.5 else r) for a,h,t,r in zip(aa,hh,tt,rr)]
ee_late=[('neutral' if r=='uncertain' else r) for r in rr_late]
late=revision_checks(aa,ee_late,hh,kk,gg,tt,rr_late)
assert late['event_integrity_passed'] and not late['temporal_passed'] and not late['passed']
print('PASS: exact event counts with slow confirmation do not pass the latency target')
