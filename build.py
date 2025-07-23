import PyInstaller.__main__

PyInstaller.__main__.run(
    [
        "./gui.py",
        "--onefile",
        "--noconsole",
        "--icon=./icon.ico",  # 可选
        "--name=TextToSpeechTool",
        "--add-data=./static/audio;./static/audio",  # 保留音频目录
    ]
)
