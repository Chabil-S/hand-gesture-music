import csv,json,sys,time,threading,queue
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from control_runtime import ActiveHand,MusicQueue
from gesture_features import GestureGate

def hand(x,label):
    p=np.zeros((21,3));p[:,0]=x;p[9,1]=.1
    return {'coords':p.reshape(-1).tolist(),'label':label}
selector=ActiveHand()
index,_,_=selector.select([hand(.2,'next'),hand(.8,'neutral')],0,True)
assert index==0
index,changed,_=selector.select([hand(.8,'neutral'),hand(.21,'next')],.1,False)
assert index==1 and not changed
assert selector.select([hand(.2,'next'),hand(.8,'toggle')],.2,False)[2]=='conflict'
assert selector.select([hand(.8,'neutral')],.3,False)[2]=='active_missing'
selector.reset()
assert selector.select([hand(.2,'toggle'),hand(.8,'toggle')],0,True)[0] is not None
selector.reset()
assert selector.select([hand(.2,'pinch'),hand(.8,'neutral')],0,True)[0]==0
assert selector.select([hand(.8,'neutral'),hand(.21,'pinch')],.1,False)[0]==1
assert selector.select([hand(.2,'pinch'),hand(.8,'next')],.2,False)[2]=='conflict'
selector.reset()
assert selector.select([hand(.2,'palm'),hand(.8,'neutral')],0,True)[0]==0

results=queue.Queue();blocked=threading.Event();entered=threading.Event();calls=[]
def runner(action):
    calls.append(action)
    if action=='first':entered.set();blocked.wait(2)
    return {'action':action}
dispatcher=MusicQueue(runner,results)
dispatcher.submit('first');assert entered.wait(1)
dispatcher.submit('second')
gate=GestureGate()
assert sum(gate.update('toggle',i*.05) is not None for i in range(20))==1
for t in np.arange(1,1.5,.05):gate.update('no_hand',float(t))
assert sum(gate.update('toggle',float(t)) is not None for t in np.arange(1.5,2.5,.05))==1
blocked.set()
assert results.get(timeout=2)[0]=='first'
assert results.get(timeout=2)[0]=='second'
assert calls==['first','second']
blocked.clear();entered.clear();dispatcher.submit('first');assert entered.wait(1)
dispatcher.submit('cancel_me');dispatcher.cancel_pending();blocked.set()
results.get(timeout=2)
assert results.get(timeout=2)[2]=='cancelled' and 'cancel_me' not in calls

print('PASS: hand ordering, conflict handling, ordered commands, receive/release during wait, pause cancellation')

# Slow observed absence must release; an uncertain outage must not count.
gate=GestureGate();gate.latched=True
for t in (0.,.4,.8):gate.update('no_hand',t)
assert not gate.latched
gate.reset();gate.latched=True
for t,label in ((0.,'no_hand'),(.31,'uncertain'),(.4,'no_hand')):gate.update(label,t)
assert gate.latched
for t in (.5,.6,.8):gate.update('neutral',t)
assert not gate.latched
