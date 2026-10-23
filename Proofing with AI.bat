@echo off
setlocal
title Proofing with AI

rem Double-click this to start the app.
rem
rem Python runs INSIDE this window - no second command window opens. The
rem window is deliberately kept: it is where a missing key file or a failed
rem call reports itself, and closing it is how the local server is stopped.
rem Minimise it and work in the browser.

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
