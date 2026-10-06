"""Dynamic gesture safety and geometry invariance using synthetic landmarks."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'outputs'))
from dynamic_gestures import geometry,PinchVolume,PalmControl

def pinch(distance):return {'pinch_pose':True,'open_palm':False,'aperture':distance}
def arm(engine,distance,start=0):
    for i in range(11):result=engine.update(pinch(distance),start+i*.05)
    assert engine.active and result['delta'] is None

volume=PinchVolume();arm(volume,.15)
up=[volume.update(pinch(.15+i*.025),.55+i*.05)['delta'] for i in range(20)]
assert any(d is not None for d in up) and all(0<d<=.03 for d in up if d is not None)
for i in range(25):volume.update(pinch(.625),1.55+i*.05)
assert all(volume.update(pinch(.625),2.85+i*.05)['delta'] is None for i in range(10))
volume.reset();arm(volume,1.05)
down=[volume.update(pinch(1.05-i*.025),.55+i*.05)['delta'] for i in range(20)]
assert any(d is not None for d in down) and all(-.03<=d<0 for d in down if d is not None)
volume.update(None,2);assert not volume.active
assert volume.update(pinch(1),2.05)['delta'] is None
volume.reset();arm(volume,.15)
volume.update(pinch(1.2),5);assert not volume.active
assert volume.update(pinch(float('nan')),5.1)['delta'] is None
volume.reset();assert volume.update(pinch(.5),0)['state']=='start_pose'
volume.reset();arm(volume,.15)
assert all(volume.update(pinch(.15+(.008 if i%2 else -.008)),.55+i*.05)['delta'] is None for i in range(40))

palm=PalmControl()
assert not any(palm.update({'open_palm':True},i*.05)['toggle'] for i in range(40))
for i in range(9):palm.update(None,2+i*.05)
events=[palm.update({'open_palm':True},2.5+i*.05) for i in range(50)]
assert sum(e['toggle'] for e in events)==1 and all(e['reserved'] for e in events)
assert not palm.update({'open_palm':True},8)['toggle']

# Palm geometry mirrors, translates and scales consistently; no image-label data needed.
points=np.zeros((21,3));points[0]=(.5,.8,0)
for mcp in (5,9,13,17):
    x=.3+(mcp-5)*.03
    points[mcp]=x,.6,0
    points[mcp+1]=x,.45,0
    points[mcp+2]=x,.32,0
    points[mcp+3]=x,.2,0
points[1]=.33,.72,0;points[2]=.23,.65,0;points[3]=.18,.57,0;points[4]=.10,.5,0
sample=geometry(points.reshape(-1),640,480)
assert sample['open_palm'] and not sample['pinch_pose']
pinched=points.copy()
for mcp in (9,13,17):
    x=pinched[mcp,0]
    pinched[mcp+1]=x,.45,0
    pinched[mcp+2]=x,.55,0
    pinched[mcp+3]=x,.65,0
pinched[4]=pinched[8]+(.02,0,0)
assert geometry(pinched.reshape(-1),640,480)['pinch_pose']
index_only=pinched.copy();index_only[4]=index_only[2]+(.01,.01,0)
assert not geometry(index_only.reshape(-1),640,480)['pinch_pose']
fully_open=pinched.copy();fully_open[4]=(-.15,.6,0)
wide=geometry(fully_open.reshape(-1),640,480)
assert wide['aperture']>1.6 and wide['pinch_pose']
for transform in (lambda p:p*np.array([-1,1,1]),lambda p:p*.7+.1):
    assert geometry(transform(fully_open).reshape(-1),640,480)['pinch_pose']
full_volume=PinchVolume();arm(full_volume,.15)
wide_steps=[full_volume.update(pinch(.15+i*.05),.55+i*.05) for i in range(51)]
assert full_volume.active
assert any(step['delta'] is not None and step['delta']>0 for step in wide_steps[32:])
full_volume.reset();arm(full_volume,2.5)
closing=[full_volume.update(pinch(2.5-i*.045),.55+i*.05) for i in range(51)]
assert full_volume.active and any(step['delta'] is not None and step['delta']<0 for step in closing)
assert all(abs(step['delta'])<=.03 for step in wide_steps+closing if step['delta'] is not None)
# A V sign or three fingers must not enter the volume pose.
for fingers in ((9,), (9,13)):
    other=pinched.copy()
    for mcp in fingers:other[mcp:mcp+4]=points[mcp:mcp+4]
    assert not geometry(other.reshape(-1),640,480)['pinch_pose']
fist=pinched.copy();fist[6]=.3,.45,0;fist[7]=.3,.55,0;fist[8]=.3,.65,0
assert not geometry(fist.reshape(-1),640,480)['pinch_pose']
for transform in (lambda p:p*np.array([-1,1,1]),lambda p:p*.7+.1):
    changed=geometry(transform(points).reshape(-1),640,480)
    assert changed['open_palm'] and abs(sample['aperture']-changed['aperture'])<1e-6
assert geometry(np.zeros(63),640,480) is None
assert geometry([float('nan')]*63,640,480) is None
assert geometry(points.reshape(-1),0,480) is None
print('PASS: opening/closing, no entry jump, jitter filter, frame loss, one toggle per palm, mirror/scale invariance')
