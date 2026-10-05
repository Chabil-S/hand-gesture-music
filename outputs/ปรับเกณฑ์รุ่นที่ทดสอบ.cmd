@echo off
chcp 65001 >nul
"%~dp0..\.venv\Scripts\python.exe" "%~dp0..\tools\activate_reviewed_model.py" > "%~dp0acceptance_update.log" 2>&1
if errorlevel 1 (
  echo รุ่นนี้ไม่ผ่านเกณฑ์ที่ตั้งไว้ หรือมีข้อผิดพลาด ยังไม่เปลี่ยนรุ่นใช้งาน ดู acceptance_update.log
  pause
  exit /b 1
)
echo ตรวจผ่านและตั้งรุ่นใช้งานแล้ว ปิดหน้าควบคุมเพลงเดิม แล้วเปิดระบบควบคุมเพลง.cmd ใหม่
pause
