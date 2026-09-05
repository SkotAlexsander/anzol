@echo off
rem Anzol — abre a janela do app sem deixar console aberto atras.
rem Usa pythonw (sem console); se nao existir, cai pro python normal.

cd /d "%~dp0"

where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw desktop.py
) else (
    python desktop.py
)
