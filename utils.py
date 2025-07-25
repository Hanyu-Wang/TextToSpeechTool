import re
import sys
import os


def is_dialogue(text: str) -> bool:
    return bool(re.search(r"(M|W)[:：]", text))


def split_dialogue_paragraph_to_lines(text: str):
    return text.strip().splitlines()


def parse_dialogue_lines(lines):
    parsed = []
    for line in lines:
        match = re.match(r"(M|W)[:：]\s*(.*)", line)
        if match:
            parsed.append((match.group(1), match.group(2).strip()))
    return parsed


def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        # ✅ 打包环境（PyInstaller）
        base_path = os.path.join(sys._MEIPASS, "ffmpeg")
    else:
        # ✅ 开发环境：以当前文件夹为根目录（不再跳一级）
        base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg")

    ffmpeg_path = os.path.abspath(os.path.join(base_path, "ffmpeg.exe"))
    ffprobe_path = os.path.abspath(os.path.join(base_path, "ffprobe.exe"))

    return ffmpeg_path, ffprobe_path


# 获取用于 subprocess 的命令列表（带完整路径）
def get_ffmpeg_cmd():
    ffmpeg_path, _ = get_ffmpeg_path()
    return [ffmpeg_path]
