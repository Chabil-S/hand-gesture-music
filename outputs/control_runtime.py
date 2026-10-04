"""Live control policies independent of UI and of the trained classifier."""
import queue
import threading
import time
import numpy as np

class ActiveHand:
    def __init__(self):self.wrist=None;self.missing_since=None
    def reset(self):self.wrist=None;self.missing_since=None
    def select(self,hands,t,can_switch):
        commands=[i for i,h in enumerate(hands) if h['label'] in ('toggle','next','previous')]
        if len({hands[i]['label'] for i in commands})>1:
            return None,False,'conflict'
        if not hands:
            if self.missing_since is None:self.missing_since=t
            return None,False,'no_hand'
        def largest(indices):
            return max(indices,key=lambda i:np.linalg.norm(np.asarray(hands[i]['coords']).reshape(21,3)[0]-np.asarray(hands[i]['coords']).reshape(21,3)[9]))
        changed=False
        if self.wrist is None:
            index=commands[0] if len(commands)==1 else largest(range(len(hands)))
            changed=True
        else:
            distances=[np.linalg.norm(np.asarray(h['coords'][:2])-self.wrist) for h in hands]
            index=int(np.argmin(distances))
            if distances[index]>0.25:
                if self.missing_since is None:self.missing_since=t
                if not can_switch or t-self.missing_since<0.35:
                    return None,False,'active_missing'
                index=commands[0] if len(commands)==1 else largest(range(len(hands)))
                changed=True
            elif can_switch and hands[index]['label']=='neutral' and len(commands)==1 and commands[0]!=index:
                index=commands[0];changed=True
        self.wrist=np.asarray(hands[index]['coords'][:2]).copy()
        self.missing_since=None
        return index,changed,'selected'

class MusicQueue:
    """One worker preserves order; pausing invalidates unsent commands."""
    def __init__(self,runner,results):
        self.runner=runner;self.results=results;self.pending=queue.Queue(maxsize=3)
        self.epoch=0
        threading.Thread(target=self.worker,daemon=True).start()
    def cancel_pending(self):self.epoch+=1
    def submit(self,action):
        self.pending.put_nowait((self.epoch,action,time.monotonic()))
    def worker(self):
        while True:
            epoch,action,submitted=self.pending.get()
            if epoch!=self.epoch:
                self.results.put((action,None,'cancelled',epoch));continue
            started=time.monotonic()
            try:
                result=self.runner(action)
                result['queue_wait_seconds']=started-submitted
                result['request_seconds']=time.monotonic()-started
                self.results.put((action,result,None,epoch))
            except Exception as error:self.results.put((action,None,str(error),epoch))
