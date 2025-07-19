import os
import hashlib
import asyncio
from uuid import uuid4
from edge_tts import Communicate
from pydub import AudioSegment
from utils import is_dialogue, parse_dialogue_lines, split_dialogue_paragraph_to_lines

tts_output_dir = os.path.join(os.path.dirname(__file__), "static/audio")
os.makedirs(tts_output_dir, exist_ok=True)


def insert_silence(duration_ms=300):
    return AudioSegment.silent(duration=duration_ms)


def combine_audio_segments(temp_paths, output_path, pause_duration_ms=300, progress_callback=None):
    combined = AudioSegment.empty()
    silence = insert_silence(pause_duration_ms)
    total_files = len(temp_paths)

    for i, path in enumerate(temp_paths):
        combined += AudioSegment.from_file(path, format="mp3") + silence
        if progress_callback:
            progress_callback(i + 1, total_files)  # 更新进度

    combined.export(output_path, format="mp3")


async def synthesize_sentence_edge_tts(text, voice, output_path, progress_callback=None):
    communicate = Communicate(text, voice=voice)
    await communicate.save(output_path)
    if progress_callback:
        progress_callback(1, 1)  # 单句完成，更新进度


def generate_audio_with_edge_tts(text, filename=None, progress_callback=None):
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    filename = filename or f"tts_{text_hash}.mp3"
    output_path = os.path.join(tts_output_dir, filename)

    if os.path.exists(output_path):
        print(f"[CACHE] 使用缓存音频: {filename}")
        return output_path

    if is_dialogue(text):
        print("[INFO] 识别为对话题，按角色合成...")
        lines = parse_dialogue_lines(split_dialogue_paragraph_to_lines(text))
        temp_paths = []

        async def synthesize_all():
            total_lines = len(lines)
            for idx, (role, sentence) in enumerate(lines):
                voice = "en-US-GuyNeural" if role == "M" else "en-US-AvaMultilingualNeural"
                temp_file = os.path.join(tts_output_dir, f"temp_{uuid4().hex}.mp3")
                await synthesize_sentence_edge_tts(sentence, voice, temp_file, progress_callback)
                temp_paths.append(temp_file)
                if progress_callback:
                    progress_callback(idx + 1, total_lines)  # 更新进度条

        asyncio.run(synthesize_all())
        combine_audio_segments(temp_paths, output_path, progress_callback=progress_callback)

        for path in temp_paths:
            os.remove(path)

        print(f"[SUCCESS] 多音色对话音频生成成功: {filename}")
        return output_path

    else:
        print("[INFO] 识别为非对话题，整段合成...")

        async def synthesize():
            communicate = Communicate(text, voice="en-US-GuyNeural")
            await communicate.save(output_path)
            if progress_callback:
                progress_callback(1, 1)  # 更新进度条

        try:
            asyncio.run(synthesize())
            print(f"[SUCCESS] 音频生成成功: {filename}")
            return output_path
        except Exception as e:
            print(f"[ERROR] 合成失败: {e}")
            return None
