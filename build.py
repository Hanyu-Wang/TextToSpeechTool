import PyInstaller.__main__

PyInstaller.__main__.run(
    [
        "audio_tool/gui.py",
        "--onefile",
        "--noconsole",
        "--icon=audio_tool/icon.ico",  # 可选
        "--name=TextToSpeechTool",
        "--add-data=audio_tool/static/audio;audio_tool/static/audio",  # 保留音频目录
    ]
)
