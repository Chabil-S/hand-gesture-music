"""Experimental landmark geometry and temporal policies; no trained-model changes.

Distances use palm scale and aspect-corrected XYZ. These defaults still require
the user's live validation; they are not measured recognition accuracy.
"""
import math
import numpy as np


def angle(a, b, c):
    u, v = a-b, c-b
    denominator = np.linalg.norm(u)*np.linalg.norm(v)
    if denominator < 1e-8:
        return 0.
    return math.degrees(math.acos(float(np.clip(np.dot(u,v)/denominator,-1,1))))


def geometry(coords, width, height):
    if width <= 0 or height <= 0:
        return None
    try:
        points = np.asarray(coords, dtype=float).reshape(21,3).copy()
    except (ValueError, TypeError):
        return None
    if not np.isfinite(points).all():
        return None
    points[:,1] *= height/width
    scale = (np.linalg.norm(points[0]-points[9])+np.linalg.norm(points[5]-points[17]))/2
    # Tiny or edge-on palms give an unreliable aperture, even when detected.
    if scale*width < 25 or np.linalg.norm(points[5,:2]-points[17,:2])*width < 18:
        return None
    extended, folded = [], []
    for mcp,pip,dip,tip in [(5,6,7,8),(9,10,11,12),(13,14,15,16),(17,18,19,20)]:
        pip_angle = angle(points[mcp],points[pip],points[dip])
        dip_angle = angle(points[pip],points[dip],points[tip])
        reach = np.linalg.norm(points[tip]-points[0])/max(1e-8,np.linalg.norm(points[pip]-points[0]))
        extended.append(pip_angle>150 and dip_angle>145 and reach>1.12)
        folded.append(pip_angle<125 or reach<1.05)
    aperture = float(np.linalg.norm(points[4]-points[8])/scale)
    index_angle = angle(points[5],points[6],points[7])
    index_tip_angle = angle(points[6],points[7],points[8])
    index_ready = index_angle>135 and index_tip_angle>130
    # Permit a gently curved index when the tips touch, but exclude a tight fist.
    index_ready = index_ready or (aperture<.26 and index_angle>105 and index_tip_angle>110)
    return {
        'aperture':aperture,
        'pinch_pose':bool(index_ready and all(folded[1:]) and aperture<1.6),
        'open_palm':bool(all(extended) and np.linalg.norm(points[4]-points[5])/scale>.45),
    }


class PinchVolume:
    def __init__(self, hold=.45, max_gap=.3, gain=.25, deadband=.035, interval=.12, max_step=.03):
        self.hold, self.max_gap, self.gain = hold, max_gap, gain
        self.deadband, self.interval, self.max_step = deadband, interval, max_step
        self.reset()

    def reset(self):
        self.active=False
        self.since=self.anchor=self.filtered=self.last_time=self.last_sent=None

    def update(self, sample, timestamp):
        if self.last_time is not None and (timestamp<=self.last_time or timestamp-self.last_time>self.max_gap):
            self.reset()
        elapsed=timestamp-self.last_time if self.last_time is not None else 0
        self.last_time=timestamp
        if sample is None or not sample.get('pinch_pose'):
            self.reset()
            return {'state':'waiting','delta':None}
        aperture=sample['aperture']
        if not math.isfinite(aperture) or not 0<=aperture<=1.6:
            self.reset()
            return {'state':'waiting','delta':None}
        if self.filtered is None:
            self.filtered=aperture
        else:
            alpha=1-math.exp(-elapsed/.08)
            self.filtered+=alpha*(aperture-self.filtered)
        if not self.active:
            # Start closed for an increase or open for a decrease. No jump on entry.
            endpoint=aperture<=.26 or aperture>=.8
            if not endpoint:
                self.since=self.anchor=None
                return {'state':'start_pose','delta':None}
            if self.since is None or abs(aperture-self.anchor)>.08:
                self.since=timestamp;self.anchor=aperture
            if timestamp-self.since < self.hold:
                return {'state':'hold','progress':(timestamp-self.since)/self.hold,'delta':None}
            self.active=True;self.anchor=self.filtered;self.last_sent=timestamp
            return {'state':'active','delta':None}
        change=self.filtered-self.anchor
        if abs(change)<self.deadband or timestamp-self.last_sent<self.interval:
            return {'state':'active','delta':None}
        delta=max(-self.max_step,min(self.max_step,change*self.gain))
        self.anchor=self.filtered;self.last_sent=timestamp
        return {'state':'active','delta':delta}


class PalmControl:
    """Deliberate open palm hold; one toggle until release, including while paused."""
    def __init__(self, hold=1.2, release=.35, max_gap=.3):
        self.hold,self.release,self.max_gap=hold,release,max_gap
        self.reset()

    def reset(self, require_release=True):
        self.latched=require_release
        self.since=self.release_since=self.last_time=None

    def update(self, sample, timestamp):
        if self.last_time is not None and (timestamp<=self.last_time or timestamp-self.last_time>self.max_gap):
            self.since=self.release_since=None
            self.latched=True  # never toggle immediately after a tracking outage
        self.last_time=timestamp
        palm=sample is not None and sample.get('open_palm',False)
        if not palm:
            self.since=None
            if self.release_since is None:self.release_since=timestamp
            if timestamp-self.release_since>=self.release:self.latched=False
            return {'reserved':False,'toggle':False,'progress':0.}
        self.release_since=None
        if self.latched:
            return {'reserved':True,'toggle':False,'progress':1.}
        if self.since is None:self.since=timestamp
        progress=min(1,(timestamp-self.since)/self.hold)
        if progress>=1:
            self.latched=True;self.since=None
            return {'reserved':True,'toggle':True,'progress':1.}
        return {'reserved':True,'toggle':False,'progress':progress}
