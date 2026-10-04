import numpy as np

PAIRS = np.triu_indices(21, 1)
FEATURE_VERSION = 'pairwise_xyz_palm_scale_v1'

def features(coords, width, height):
    points = np.asarray(coords, dtype=float).reshape(21, 3).copy()
    if not np.isfinite(points).all():
        raise ValueError('Nonfinite landmarks')
    points[:, 1] *= height / width
    scale = (np.linalg.norm(points[0]-points[9]) + np.linalg.norm(points[5]-points[17])) / 2
    if scale < 1e-5:
        raise ValueError('Degenerate palm scale')
    distances = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2) / scale
    return distances[PAIRS]

class GestureGate:
    """One command per held pose; uncertain frames never release the latch."""
    def __init__(self, hold=0.6, release=0.35, max_gap=0.3):
        self.hold=hold
        self.release=release
        self.max_gap=max_gap
        self.reset()

    def reset(self):
        self.latched=False
        self.candidate=None
        self.since=None
        self.release_since=None
        self.last_time=None

    def update(self, label, timestamp):
        if self.last_time is not None and timestamp-self.last_time > self.max_gap:
            self.candidate=None
            self.since=None
            self.release_since=None
        self.last_time=timestamp
        if label in ('neutral', 'no_hand'):
            self.candidate=None
            self.since=None
            if self.release_since is None: self.release_since=timestamp
            if timestamp-self.release_since>=self.release: self.latched=False
            return None
        self.release_since=None
        if label not in ('toggle', 'next', 'previous') or self.latched:
            self.candidate=None
            self.since=None
            return None
        if self.candidate!=label:
            self.candidate=label
            self.since=timestamp
        if timestamp-self.since>=self.hold:
            self.latched=True
            self.candidate=None
            return label
        return None
