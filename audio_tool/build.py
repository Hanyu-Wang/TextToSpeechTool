import subprocess
import sys


def build_executable():
    # 构建 PyInstaller 打包命令
    pyinstaller_command = [
        "pyinstaller",  # 使用 PyInstaller
        "--onefile",
        "--add-binary", "ffmpeg/ffmpeg.exe;ffmpeg",  # FFmpeg 可执行文件路径
        "--windowed",  # 适用于 GUI 程序
        "--icon", "app_icon.ico",  # 应用图标
        "gui.py"  # 你的主脚本文件
    ]

    # 调用 PyInstaller 命令
    try:
        subprocess.run(pyinstaller_command, check=True)
        print("打包成功！")
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_executable()
