@echo off
rem Launches the Norwegian for DiffSinger GUI. Double-click to run.
rem This file sits in gui\, but the package has to be imported from the
rem project root, so step one level up first.
cd /d "%~dp0.."

python -m gui
if errorlevel 1 (
    echo.
    echo The GUI exited with an error. Make sure Python is installed and on PATH,
    echo and run: python -m pip install -r gui/requirements.txt
    pause
)
