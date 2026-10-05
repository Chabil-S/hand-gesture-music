"""Read-only Apple Music display feed, independent of the command worker."""
import asyncio
import io
import queue
import threading
import time

from PIL import Image
import winrt.windows.foundation
import winrt.windows.foundation.collections
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
from winrt.windows.storage.streams import DataReader

APPLE_MUSIC_ID = 'AppleInc.AppleMusicWin_nzyj5cx40ttqa!App'


async def read_cover(reference):
    if reference is None:
        return None
    stream = await reference.open_read_async()
    try:
        size = int(stream.size)
        if not 0 < size <= 8 * 1024 * 1024:
            return None
        reader = DataReader(stream.get_input_stream_at(0))
        try:
            loaded = await reader.load_async(size)
            data = bytearray(loaded)
            reader.read_bytes(data)
            with Image.open(io.BytesIO(data)) as image:
                image.thumbnail((600, 600))
                return image.convert('RGB').copy()
        finally:
            reader.close()
    finally:
        stream.close()


async def read_display(manager, cached_key=None, cached_cover=None):
    matches = [s for s in manager.get_sessions()
               if s.source_app_user_model_id == APPLE_MUSIC_ID]
    if len(matches) != 1:
        return {'connected': False, 'message': 'เปิด Apple Music และเริ่มเพลงเพื่อเชื่อมต่อ'}, None, None
    session = matches[0]
    media = await session.try_get_media_properties_async()
    info = session.get_playback_info()
    timeline = session.get_timeline_properties()
    key = (media.title, media.artist, media.album_title, media.track_number)
    cover = cached_cover
    if key != cached_key or cover is None:
        try:
            cover = await asyncio.wait_for(read_cover(media.thumbnail), timeout=2)
        except Exception:
            cover = None
    controls = info.controls
    return {
        'connected': True, 'title': media.title or 'ยังไม่มีชื่อเพลง',
        'artist': media.artist or 'ไม่ระบุศิลปิน', 'album': media.album_title,
        'status': info.playback_status.name, 'cover': cover,
        'position_seconds': max(0, timeline.position.total_seconds()-timeline.start_time.total_seconds()),
        'duration_seconds': max(0, (timeline.end_time-timeline.start_time).total_seconds()),
        'can_toggle': controls.is_play_pause_toggle_enabled,
        'can_next': controls.is_next_enabled, 'can_previous': controls.is_previous_enabled,
    }, key, cover


class MusicDisplay:
    def __init__(self, stop):
        self.stop = stop
        self.results = queue.Queue(maxsize=1)
        self.refresh = threading.Event()

    def start(self):
        threading.Thread(target=lambda: asyncio.run(self.worker()), daemon=True).start()

    async def worker(self):
        key = cover = None
        while not self.stop.is_set():
            try:
                manager = await asyncio.wait_for(
                    GlobalSystemMediaTransportControlsSessionManager.request_async(), timeout=3)
                data, key, cover = await asyncio.wait_for(read_display(manager, key, cover), timeout=5)
            except Exception:
                data = {'connected': False, 'message': 'อ่าน Apple Music ไม่ได้ · ลองเปิดเพลงแล้วอ่านสถานะอีกครั้ง'}
                key = cover = None
            if self.stop.is_set():
                break
            try:
                self.results.get_nowait()
            except queue.Empty:
                pass
            self.results.put_nowait(data)
            deadline = time.monotonic()+1.5
            while time.monotonic()<deadline and not self.stop.is_set():
                if self.refresh.is_set():
                    self.refresh.clear()
                    break
                await asyncio.sleep(.1)
