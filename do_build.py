#!/usr/bin/env python3
"""PyInstaller build script for RAG_H."""
import PyInstaller.__main__
import os

root = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    '--windowed',
    '--onedir',
    '--name=RAG_H',
    f'--icon={os.path.join(root, "assets", "logo.ico")}',
    f'--add-data={os.path.join(root, "config.json")};.',
    f'--add-data={os.path.join(root, "config.default.json")};.',
    f'--add-data={os.path.join(root, "assets")};assets',
    '--collect-all=chromadb',
    '--collect-all=PySide6',
    '--hidden-import=app.core',
    '--hidden-import=app.providers',
    '--hidden-import=app.ui',
    '--hidden-import=app.ui.workers',
    '--hidden-import=app.ui.widgets',
    '--hidden-import=app.utils',
    os.path.join(root, "main.py"),
])
