@echo off
setlocal
title Proofing with AI

rem Double-click this to start the app.
rem
rem The app runs with NO window: this one closes as soon as the app has
rem started, so there is no window to close by mistake (closing it used to
rem stop the app, and every save from the page with it). The app stops on
rem its own 15 minutes after its browser tab is closed. Anything it would
rem have printed goes to logs\app.log, and a problem at startup shows in a
rem message box.
rem
rem pythonw is the Python that runs without a window; "pyw -3" is the
rem fallback for a machine where Python was installed without adding it to
rem PATH. With neither, the app runs inside this window as before.

rem Start in this folder whatever folder the shortcut was launched from,
rem so the whole thing still works after the folder is copied elsewhere.
cd /d "%~dp0"

rem "python" first - that is the one a pip install lands in. "py -3" is the
rem fallback for a machine where Python was installed without adding it to
rem PATH.
set "PY="
where python >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto :run
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto :run

echo.
echo   Python was not found on this computer.
echo.
echo   Install Python 3 from  https://www.python.org/downloads/
echo   and tick "Add python.exe to PATH" during setup.
echo.
pause
exit /b 1

:run
rem Arguments are passed straight through, so a Gemini mode can be forced:
rem     "Proofing with AI.bat" JSON
where pythonw >nul 2>&1
if not errorlevel 1 (
  start "" pythonw "Proofing with AI.py" %*
  exit /b 0
)
where pyw >nul 2>&1
if not errorlevel 1 (
  start "" pyw -3 "Proofing with AI.py" %*
  exit /b 0
)
%PY% "Proofing with AI.py" %*
set "RC=%ERRORLEVEL%"

rem Ctrl-C leaves RC 0, so a clean stop just closes. Only a real failure
rem holds the window open long enough to read the message above.
if not "%RC%"=="0" (
  echo.
  echo   The app stopped with an error ^(code %RC%^). The reason is above.
  echo.
  pause
)
exit /b %RC%
