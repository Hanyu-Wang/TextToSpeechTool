import os
import hashlib
import asyncio
import shutil
import subprocess
import tempfile
from uuid import uuid4
from edge_tts import Communicate
from utils import is_dialogue, parse_dialogue_lines, split_dialogue_paragraph_to_lines, get_ffmpeg_path, get_ffmpeg_cmd

# 配置pydub使用的ffmpeg路径
ffmpeg_path, ffprobe_path = get_ffmpeg_path()
os.environ["FFMPEG_PATH"] = ffmpeg_path  # 关键：设置环境变量让pydub找到ffmpeg

from pydub import AudioSegment, effects  # 这行必须在设置FFMPEG_PATH之后

# 输出目录，默认保存在 static/audio 下
tts_output_dir = os.path.join(os.path.dirname(__file__), "static/audio")
os.makedirs(tts_output_dir, exist_ok=True)


# 插入一段静音，默认 300 毫秒
def insert_silence(duration_ms=300):
    return AudioSegment.silent(duration=duration_ms)


# 使用FFmpeg进行响度标准化
def combine_audio_with_ffmpeg(temp_paths, output_path, pause_duration_ms=300, progress_callback=None):
    # 验证路径
    ffmpeg_path, _ = get_ffmpeg_path()
    if not os.path.exists(ffmpeg_path):
        raise FileNotFoundError(f"FFmpeg 不存在: {ffmpeg_path}")

    # 使用系统临时目录
    import tempfile
    temp_combined = os.path.join(tempfile.gettempdir(), f"temp_combined_{uuid4().hex}.mp3")

    # 合并音频片段（使用 pydub，已通过环境变量配置 FFmpeg）
    combined = AudioSegment.empty()
    silence = insert_silence(pause_duration_ms)

    for i, path in enumerate(temp_paths):
        segment = AudioSegment.from_file(path, format="mp3")
        combined += segment + silence
        if progress_callback:
            progress_callback(i + 1, len(temp_paths))

    combined.export(temp_combined, format="mp3")

    # 使用 subprocess 调用 FFmpeg（使用完整命令列表）
    ffmpeg_cmd = get_ffmpeg_cmd() + [
        "-i", temp_combined,
        "-filter_complex", "loudnorm=I=-16:LRA=11:TP=-1",
        "-y",
        output_path
    ]

    print(f"[DEBUG] 执行命令: {' '.join(ffmpeg_cmd)}")

    try:
        subprocess.run(
            ffmpeg_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding = "utf-8",
            errors = "replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg 命令失败: {e.stderr}")
        raise
    finally:
        # 清理临时文件
        if os.path.exists(temp_combined):
            os.remove(temp_combined)
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)


# 单句合成，支持语速
async def synthesize_sentence_edge_tts(text, voice, output_path, rate="default"):
    if rate == "default":
        communicate = Communicate(text, voice=voice)
    else:
        communicate = Communicate(text, voice=voice, rate=rate)
    await communicate.save(output_path)


# 主接口：根据输入文本合成音频
def generate_audio_with_edge_tts(text, filename=None, progress_callback=None, language="中文",
                                 output_dir=None, full_output_path=None, rate="default", gender="女声"):
    # 基于文本生成默认文件名（哈希）
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    filename = filename or f"tts_{text_hash}.mp3"

    # 最终保存路径（优先使用 full_output_path）
    if full_output_path:
        output_path = full_output_path
    else:
        output_dir = output_dir or tts_output_dir
        output_path = os.path.join(output_dir, filename)

    if language == "英文":
        default_voice = "en-US-GuyNeural" if gender == "男声" else "en-US-AvaMultilingualNeural"
    else:
        default_voice = "zh-CN-YunyangNeural" if gender == "男声" else "zh-CN-XiaoxiaoNeural"

    # === 英文对话文本处理 ===
    if is_dialogue(text) and language == "英文":
        lines = parse_dialogue_lines(split_dialogue_paragraph_to_lines(text))
        temp_paths = []

        # 异步合成所有对话句子
        async def synthesize_all():
            total = len(lines)
            for idx, (role, sentence) in enumerate(lines):
                # 男声 M 用 Guy，女声 W 用 Ava
                role_voice = "en-US-GuyNeural" if role == "M" else "en-US-AvaMultilingualNeural"
                temp_file = os.path.join(tts_output_dir, f"temp_{uuid4().hex}.mp3")
                await synthesize_sentence_edge_tts(sentence, role_voice, temp_file, rate=rate)
                temp_paths.append(temp_file)
                if progress_callback:
                    progress_callback(idx + 1, total)  # 回调单句合成进度

        asyncio.run(synthesize_all())

        # 调用修改后的合并函数（使用FFmpeg处理音量）
        combine_audio_with_ffmpeg(temp_paths, output_path, progress_callback=progress_callback)

        return output_path

    # === 普通整段文本处理 ===
    else:
        async def synthesize():
            if rate == "default":
                communicate = Communicate(text, voice=default_voice)
            else:
                communicate = Communicate(text, voice=default_voice, rate=rate)
            await communicate.save(output_path)
            if progress_callback:
                progress_callback(1, 1)  # 单段合成完成

        try:
            asyncio.run(synthesize())

            # 使用系统临时目录
            temp_single = os.path.join(tempfile.gettempdir(), f"temp_single_{uuid4().hex}.mp3")
            shutil.copy2(output_path, temp_single)

            # 使用完整命令列表
            ffmpeg_cmd = get_ffmpeg_cmd() + [
                "-i", temp_single,
                "-filter_complex", "loudnorm=I=-16:LRA=11:TP=-1",
                "-y",
                output_path
            ]

            print(f"[DEBUG] 执行命令: {' '.join(ffmpeg_cmd)}")

            subprocess.run(
                ffmpeg_cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding = "utf-8",
                errors = "replace",
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 清理临时文件
            if os.path.exists(temp_single):
                os.remove(temp_single)

            return output_path
        except Exception as e:
            print(f"合成失败: {str(e)}")
            # 清理残留文件
            if 'temp_single' in locals() and os.path.exists(temp_single):
                os.remove(temp_single)
            return None
