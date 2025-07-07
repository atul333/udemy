@echo off
:start
echo Starting Udemy Course Coupons Bot...
start /min pythonw bot.py
echo Bot is running in background. You can close this window.
echo The bot will automatically restart if it stops.
timeout /t 60 /nobreak >nul
tasklist /FI "IMAGENAME eq pythonw.exe" 2>NUL | find /I /N "pythonw.exe">NUL
if "%ERRORLEVEL%"=="1" goto start