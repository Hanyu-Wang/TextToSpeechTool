import os
import hashlib
import asyncio
from uuid import uuid4
from edge_tts import Communicate
from pydub import AudioSegment, effects
from utils import is_dialogue, parse_dialogue_lines, split_dialogue_paragraph_to_lines

tts_output_dir = os.path.join(os.path.dirname(__file__), "static/audio")
os.makedirs(tts_output_dir, exist_ok=True)


def insert_silence(duration_ms=300):
    return AudioSegment.silent(duration=duration_ms)


def combine_audio_segments(temp_paths, output_path, pause_duration_ms=300, progress_callback=None):
    combined = AudioSegment.empty()
    silence = insert_silence(pause_duration_ms)
    total = len(temp_paths)

    for i, path in enumerate(temp_paths):
        segment = AudioSegment.from_file(path, format="mp3")
        segment = effects.normalize(segment)  # ✅ normalize 每段
        combined += segment + silence
        if progress_callback:
            progress_callback(i + 1, total)

    combined = effects.normalize(combined)  # ✅ 合并后整体 normalize
    combined.export(output_path, format="mp3")


async def synthesize_sentence_edge_tts(text, voice, output_path):
    communicate = Communicate(text, voice=voice)
    await communicate.save(output_path)


def generate_audio_with_edge_tts(text, filename=None, progress_callback=None, language="中文", output_dir=None,
                                 full_output_path=None):
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    filename = filename or f"tts_{text_hash}.mp3"

    # 最终保存路径优先使用 full_output_path
    if full_output_path:
        output_path = full_output_path
    else:
        output_dir = output_dir or tts_output_dir
        output_path = os.path.join(output_dir, filename)

    # 设置音色
    if language == "英文":
        default_voice = "en-US-GuyNeural"
    else:
        default_voice = "zh-CN-XiaoxiaoNeural"

    # 对话处理
    if is_dialogue(text) and language == "英文":
        lines = parse_dialogue_lines(split_dialogue_paragraph_to_lines(text))
        temp_paths = []

        async def synthesize_all():
            total = len(lines)
            for idx, (role, sentence) in enumerate(lines):
                role_voice = "en-US-GuyNeural" if role == "M" else "en-US-AvaMultilingualNeural"
                temp_file = os.path.join(tts_output_dir, f"temp_{uuid4().hex}.mp3")
                await synthesize_sentence_edge_tts(sentence, role_voice, temp_file)
                temp_paths.append(temp_file)
                if progress_callback:
                    progress_callback(idx + 1, total)

        asyncio.run(synthesize_all())
        combine_audio_segments(temp_paths, output_path, progress_callback=progress_callback)

        for path in temp_paths:
            os.remove(path)

        return output_path
    else:
        async def synthesize():
            communicate = Communicate(text, voice=default_voice)
            await communicate.save(output_path)
            if progress_callback:
                progress_callback(1, 1)

        try:
            asyncio.run(synthesize())

            # ✅ 非对话整段 normalize 一次
            audio = AudioSegment.from_file(output_path, format="mp3")
            audio = effects.normalize(audio)
            audio.export(output_path, format="mp3")

            return output_path
        except Exception as e:
            print(f"[ERROR] 合成失败: {e}")
            return None
