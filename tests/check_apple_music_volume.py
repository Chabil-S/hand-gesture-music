"""Session scoping, bounded writes, cancellation, and worker recovery without real audio writes."""
import queue
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'outputs'))
import apple_music_volume as audio

# The real playback helper is in the Apple Music package; idle UI sessions
# cannot win over its active stream. Never choose among multiple active streams.
assert audio.select_sessions([(0,'ui'),(1,'helper'),(0,'old helper')])==['helper']
assert audio.select_sessions([(1,'a'),(1,'b'),(0,'ui')])==['a','b']
assert audio.select_sessions([(0,'a'),(0,'b')])==['a','b']
assert audio.select_sessions([(2,'expired')])==[]

class Function:
    def __init__(self,fn):self.fn=fn
    def __call__(self,*args):return self.fn(*args)
class Kernel:
    def __init__(self,name,family):
        self.closed=[]
        self.OpenProcess=Function(lambda *args:42)
        self.CloseHandle=Function(lambda handle:self.closed.append(handle))
        def image(handle,flags,buffer,length):buffer.value=name;return 1
        def package(handle,length,buffer):buffer.value=family;return 0
        self.QueryFullProcessImageNameW=Function(image)
        self.GetPackageFamilyName=Function(package)
for executable,family,expected in (
    ('AppleMusic.exe',audio.PACKAGE,True),
    ('AMPLibraryAgent.exe',audio.PACKAGE,True),
    ('AMPLibraryAgent.exe','AnotherPackage',False),
    ('other.exe',audio.PACKAGE,False),
):
    kernel=Kernel(executable,family)
    with patch.object(audio.C,'WinDLL',lambda *args,**kwargs:kernel):
        assert audio.is_apple_music(123)==expected
    assert kernel.closed==[42]


@contextmanager
def sessions(items):
    yield items


backend = audio.AppleMusicVolume()
writes = []
with patch.object(audio, 'call', lambda *args: writes.append(args)), \
     patch.object(backend, 'snapshot', lambda ptr: {'available':True, 'level':.99, 'muted':True}):
    for targets in ([], [1, 2]):
        with patch.object(audio, 'music_sessions', lambda:sessions(targets)):
            assert not backend.adjust(.02)['available']
    assert not writes
    with patch.object(audio, 'music_sessions', lambda:sessions([1])):
        assert backend.adjust(.03, lambda:False)['cancelled']
        assert not writes
        assert backend.adjust(.9)['muted']  # no SetMute call
        assert len(writes)==1 and writes[0][1]==3 and writes[0][2][0]==1.
        backend.adjust(-.9)
        assert abs(writes[-1][2][0]-.96)<1e-6
        try:backend.adjust(float('nan'));raise AssertionError('accepted NaN')
        except ValueError:pass

stop, entered, release = threading.Event(), threading.Event(), threading.Event()
class FakeBackend:
    def __init__(self):self.writes=[];self.fail=False
    def read(self):
        if self.fail:raise OSError('device disconnected')
        return {'available':True,'level':.5}
    def adjust(self, delta, valid):
        entered.set();release.wait(2)
        if valid():self.writes.append(delta)
        return {'available':True,'level':.5}
fake=FakeBackend();worker=audio.VolumeWorker(stop,fake);worker.start()
worker.submit(.02);assert entered.wait(1)
worker.cancel();release.set()
worker.submit();assert worker.results.get(timeout=2)['available']
assert not fake.writes
fake.fail=True;worker.submit();assert worker.results.get(timeout=2)['reason']=='error'
fake.fail=False;worker.submit();assert worker.results.get(timeout=2)['available']
stop.set()
print('PASS: packaged playback-helper identity, active-session selection, ambiguity rejection, bounds, mute preserved, cancellation, error recovery')
