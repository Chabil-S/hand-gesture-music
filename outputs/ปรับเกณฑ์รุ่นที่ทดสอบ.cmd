@echo off
"%~dp0..\.venv\Scripts\python.exe" "%~dp0..\tools\activate_reviewed_model.py" > "%~dp0acceptance_update.log" 2>&1
if errorlevel 1 goto failed
echo PASS: model activated under the requested evaluation target.
echo Close the music controller and reopen it to load this model.
goto done
:failed
echo NOT ACTIVATED: validation failed or an error occurred.
echo The current live model is unchanged. See acceptance_update.log.
pause
exit /b 1
:done
pause
