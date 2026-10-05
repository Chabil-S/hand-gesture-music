@echo off
start "" "%~dp0..\.venv\Scripts\pythonw.exe" "%~dp0live_comparison.py" --candidate latest-diagnostic
