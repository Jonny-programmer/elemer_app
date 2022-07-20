# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('templates\\MainWindowTemplate.ui', 'templates'), ('templates\\MultiOperatorTemplate.ui', 'templates'), ('templates\\PasteSerialNumbersTemplate.ui', 'templates'), ('templates\\SelectEnterTypeTemplate.ui', 'templates'), ('img\\splash.png', 'img'), ('backgrounds\\vector_1.jpeg', 'backgrounds'), ('backgrounds\\vector_2.jpeg', 'backgrounds'), ('backgrounds\\vector_3.jpeg', 'backgrounds'), ('backgrounds\\vector_4.jpeg', 'backgrounds'), ('backgrounds\\vector_5.jpeg', 'backgrounds'), ('backgrounds\\vector_6.jpeg', 'backgrounds'), ('backgrounds\\vector_7.jpeg', 'backgrounds'), ('backgrounds\\img.png', 'backgrounds'), ('data_files\\a.txt', 'data_files')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='img\\icon.png',
)
