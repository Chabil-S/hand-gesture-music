@echo off
cd /d "%~dp0"
"..\.venv\Scripts\pythonw.exe" "gesture_collector.py" --negative --wide-angles --hand right
