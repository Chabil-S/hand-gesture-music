"""Apple Music session volume only; no media keys or system-volume fallback.

Core Audio references are opened and released on the calling worker thread.
The package identity is verified before any session can be written.
"""
import ctypes as C
import math
import os
import queue
import threading
import uuid
from contextlib import ExitStack, contextmanager

PACKAGE = 'AppleInc.AppleMusicWin_nzyj5cx40ttqa'
APPLE_EXECUTABLES = frozenset({'applemusic.exe', 'amplibraryagent.exe'})
GUID = C.c_ubyte * 16


def guid(value):
    return GUID.from_buffer_copy(uuid.UUID(value).bytes_le)


def call(pointer, index, arguments=(), types=()):
    table = C.cast(pointer, C.POINTER(C.POINTER(C.c_void_p))).contents
    method = C.WINFUNCTYPE(C.c_long, C.c_void_p, *types)(table[index])
    result = method(pointer, *arguments)
    if result < 0:
        raise OSError(f'Core Audio HRESULT 0x{result & 0xffffffff:08X}')
    return result


@contextmanager
def owned(pointer):
    try:
        yield pointer
    finally:
        if pointer:
            call(pointer, 2)


def query(pointer, iid):
    result = C.c_void_p()
    call(pointer, 0, (C.byref(guid(iid)), C.byref(result)), (C.c_void_p, C.c_void_p))
    return result


def is_apple_music(pid):
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [C.c_uint32, C.c_int, C.c_uint32]
    kernel.OpenProcess.restype = C.c_void_p
    kernel.CloseHandle.argtypes = [C.c_void_p]
    kernel.QueryFullProcessImageNameW.argtypes = [C.c_void_p, C.c_uint32, C.c_wchar_p, C.POINTER(C.c_uint32)]
    kernel.GetPackageFamilyName.argtypes = [C.c_void_p, C.POINTER(C.c_uint32), C.c_wchar_p]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        name = C.create_unicode_buffer(32768)
        length = C.c_uint32(len(name))
        if not kernel.QueryFullProcessImageNameW(handle, 0, name, C.byref(length)):
            return False
        length = C.c_uint32(256)
        family = C.create_unicode_buffer(length.value)
        return (os.path.basename(name.value).lower() in APPLE_EXECUTABLES
                and kernel.GetPackageFamilyName(handle, C.byref(length), family) == 0
                and family.value == PACKAGE)
    finally:
        kernel.CloseHandle(handle)


def select_sessions(records):
    """Prefer streams currently rendering audio over retained idle UI sessions.

    Apple Music plays through its packaged AMPLibraryAgent helper. Its idle UI
    process can retain a separate session whose volume does not affect music.
    Multiple active matches remain ambiguous rather than choosing arbitrarily.
    """
    active = [volume for state, volume in records if state == 1]
    return active or [volume for state, volume in records if state == 0]


@contextmanager
def music_sessions():
    if os.name != 'nt':
        raise OSError('Apple Music volume requires Windows')
    ole = C.OleDLL('ole32')
    ole.CoInitializeEx.argtypes = [C.c_void_p, C.c_uint32]
    ole.CoInitializeEx.restype = C.c_long
    result = ole.CoInitializeEx(None, 0)  # MTA, dedicated worker thread
    if result < 0:
        raise OSError('Cannot initialize Core Audio worker')
    try:
        with ExitStack() as stack:
            enumerator = C.c_void_p()
            ole.CoCreateInstance.argtypes = [C.c_void_p, C.c_void_p, C.c_uint32, C.c_void_p, C.c_void_p]
            ole.CoCreateInstance(C.byref(guid('BCDE0395-E52F-467C-8E3D-C4579291692E')), None, 1,
                                 C.byref(guid('A95664D2-9614-4F35-A746-DE8DB63617E6')), C.byref(enumerator))
            stack.enter_context(owned(enumerator))
            devices = C.c_void_p()
            call(enumerator, 3, (0, 1, C.byref(devices)), (C.c_int, C.c_uint32, C.c_void_p))
            stack.enter_context(owned(devices))
            count = C.c_uint32()
            call(devices, 3, (C.byref(count),), (C.c_void_p,))
            found = []
            for i in range(count.value):
                device = C.c_void_p()
                call(devices, 4, (i, C.byref(device)), (C.c_uint32, C.c_void_p))
                stack.enter_context(owned(device))
                manager = C.c_void_p()
                call(device, 3, (C.byref(guid('77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F')), 1, None, C.byref(manager)),
                     (C.c_void_p, C.c_uint32, C.c_void_p, C.c_void_p))
                stack.enter_context(owned(manager))
                sessions = C.c_void_p()
                call(manager, 5, (C.byref(sessions),), (C.c_void_p,))
                stack.enter_context(owned(sessions))
                number = C.c_int()
                call(sessions, 3, (C.byref(number),), (C.c_void_p,))
                for j in range(number.value):
                    control = C.c_void_p()
                    call(sessions, 4, (j, C.byref(control)), (C.c_int, C.c_void_p))
                    stack.enter_context(owned(control))
                    control2 = stack.enter_context(owned(query(control, 'BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D')))
                    pid, state = C.c_uint32(), C.c_int()
                    call(control2, 14, (C.byref(pid),), (C.c_void_p,))
                    call(control2, 3, (C.byref(state),), (C.c_void_p,))
                    if state.value != 2 and is_apple_music(pid.value):
                        volume = stack.enter_context(owned(query(control, '87CE5498-68D6-44E5-9215-6DA47EF883D8')))
                        found.append((state.value, volume))
            yield select_sessions(found)
    finally:
        ole.CoUninitialize()


class AppleMusicVolume:
    def read(self):
        with music_sessions() as sessions:
            if len(sessions) != 1:
                return {'available': False, 'reason': 'missing' if not sessions else 'ambiguous'}
            return self.snapshot(sessions[0])

    @staticmethod
    def snapshot(pointer):
        level, muted = C.c_float(), C.c_int()
        call(pointer, 4, (C.byref(level),), (C.c_void_p,))
        call(pointer, 6, (C.byref(muted),), (C.c_void_p,))
        return {'available': True, 'level': level.value, 'muted': bool(muted.value)}

    def adjust(self, delta, still_current=lambda: True):
        if not math.isfinite(delta):
            raise ValueError('Invalid volume change')
        delta = max(-.03, min(.03, delta))
        with music_sessions() as sessions:
            if len(sessions) != 1:
                return {'available': False, 'reason': 'missing' if not sessions else 'ambiguous'}
            volume = sessions[0]
            before = self.snapshot(volume)
            if not still_current():
                return dict(before, cancelled=True)
            level = max(0., min(1., before['level'] + delta))
            call(volume, 3, (level, None), (C.c_float, C.c_void_p))
            after=self.snapshot(volume)  # Preserve mute state; verify actual session value.
            return dict(after,before_level=before['level'],requested_delta=delta,
                        verified=abs(after['level']-level)<1e-5)


class VolumeWorker:
    """Bounded, replaceable pending work; pause and tracking loss invalidate writes."""
    def __init__(self, stop, backend=None):
        self.stop = stop
        self.backend = backend or AppleMusicVolume()
        self.pending = queue.Queue(maxsize=1)
        self.results = queue.Queue(maxsize=1)
        self.epoch = 0

    def start(self):
        threading.Thread(target=self.worker, daemon=True).start()

    def cancel(self):
        self.epoch += 1

    def submit(self, delta=None):
        if delta is not None and (not math.isfinite(delta) or abs(delta) > .03):
            raise ValueError('Volume step must be finite and at most 3%')
        item = (self.epoch, delta)
        try:
            self.pending.put_nowait(item)
        except queue.Full:
            try:self.pending.get_nowait()
            except queue.Empty:pass
            self.pending.put_nowait(item)

    def worker(self):
        while not self.stop.is_set():
            try:epoch, delta = self.pending.get(timeout=.1)
            except queue.Empty:continue
            if epoch != self.epoch:
                continue
            try:
                valid = lambda: epoch == self.epoch and not self.stop.is_set()
                result = self.backend.read() if delta is None else self.backend.adjust(delta, valid)
            except Exception as error:
                result = {'available': False, 'reason': 'error', 'error': str(error)}
            if delta is not None:result=dict(result,requested_delta=delta)
            if epoch != self.epoch or self.stop.is_set():
                continue
            try:self.results.get_nowait()
            except queue.Empty:pass
            self.results.put_nowait(result)
