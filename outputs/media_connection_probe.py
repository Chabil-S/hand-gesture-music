"""Local Apple Music connection probe. No keyboard injection or credentials."""
import argparse
import asyncio
import ctypes
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import winrt.windows.foundation
import winrt.windows.foundation.collections
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

LOG = Path(__file__).with_name('connection_events.jsonl')


def foreground():
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    handle = user32.GetForegroundWindow()
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(ctypes.c_void_p(handle), ctypes.byref(pid))
    return {'window_handle': handle, 'process_id': pid.value}


async def snapshot(session):
    media = await session.try_get_media_properties_async()
    info = session.get_playback_info()
    controls = info.controls
    return {
        'app_id': session.source_app_user_model_id,
        'title': media.title,
        'artist': media.artist,
        'status': info.playback_status.name,
        'position_seconds': session.get_timeline_properties().position.total_seconds(),
        'can_toggle': controls.is_play_pause_toggle_enabled,
        'can_next': controls.is_next_enabled,
        'can_previous': controls.is_previous_enabled,
    }


async def run(action):
    started=time.monotonic()
    manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
    matches = [s for s in manager.get_sessions()
               if s.source_app_user_model_id == 'AppleInc.AppleMusicWin_nzyj5cx40ttqa!App']
    if len(matches) != 1:
        raise RuntimeError(f'Expected one Apple Music media session; found {len(matches)}. '
                           'Open Apple Music and start a song first.')
    session = matches[0]
    before = await snapshot(session)
    record = {'time': datetime.now(timezone(timedelta(hours=7))).isoformat(),
              'action': action, 'foreground_before': foreground(), 'before': before}
    if action != 'status':
        methods = {'toggle': session.try_toggle_play_pause_async,
                   'play': session.try_play_async, 'pause': session.try_pause_async,
                   'next': session.try_skip_next_async,
                   'previous': session.try_skip_previous_async}
        if action == 'previous_track':
            record['api_accepted'] = bool(await asyncio.wait_for(session.try_skip_previous_async(), timeout=5))
            record['previous_requests'] = 1
            # Apple Music may restart the current track first. Only request again
            # after confirming that the same track moved back to its beginning.
            for _ in range(15):
                await asyncio.sleep(0.1)
                interim = await snapshot(session)
                if interim['title'] != before['title']:
                    break
                if before['position_seconds'] > 3 and interim['position_seconds'] <= 2:
                    record['confirmed_restart'] = interim
                    record['previous_requests'] = 2
                    record['api_accepted'] = bool(await asyncio.wait_for(session.try_skip_previous_async(), timeout=5))
                    break
        else:
            record['api_accepted'] = bool(await asyncio.wait_for(methods[action](), timeout=5))
        record['observations'] = []
        for _ in range(4):
            await asyncio.sleep(0.75)
            record['observations'].append(await snapshot(session))
        record['after'] = record['observations'][-1]
        if action in ('next', 'previous_track'):
            record['observed_success'] = record['after']['title'] != before['title']
        elif action == 'toggle':
            record['observed_success'] = record['after']['status'] != before['status']
    record['foreground_after'] = foreground()
    record['elapsed_seconds']=time.monotonic()-started
    with LOG.open('a', encoding='utf-8') as file:
        file.write(json.dumps(record, ensure_ascii=False) + '\n')
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['status', 'toggle', 'play', 'pause', 'next', 'previous', 'previous_track'])
    asyncio.run(run(parser.parse_args().action))
