@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python -m PyInstaller --windowed --onedir --name=RAG_H ^
  --icon=assets\logo.ico ^
  --add-data "config.json;." ^
  --add-data "config.default.json;." ^
  --add-data "assets;assets" ^
  --collect-all chromadb ^
  --collect-all PySide6 ^
  --hidden-import app.core ^
  --hidden-import app.providers ^
  --hidden-import app.ui ^
  --hidden-import app.ui.workers ^
  --hidden-import app.ui.widgets ^
  --hidden-import app.utils ^
  main.py
pause
