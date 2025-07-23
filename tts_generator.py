import os
import hashlib
import asyncio
from uuid import uuid4
from edge_tts import Communicate
from pydub import AudioSegment, effects
from utils import is_dialogue, parse_dialogue_lines, split_dialogue_paragraph_to_lines

# 输出目录，默认保存在 static/audio 下
tts_output_dir = os.path.join(os.path.dirname(__file__), "static/audio")
os.makedirs(tts_output_dir, exist_ok=True)


# 插入一段静音，默认 300 毫秒
def insert_silence(duration_ms=300):
    return AudioSegment.silent(duration=duration_ms)


# 合并多个音频段，加静音并统一音量
def combine_audio_segments(temp_paths, output_path, pause_duration_ms=300, progress_callback=None):
    combined = AudioSegment.empty()
    silence = insert_silence(pause_duration_ms)
    total = len(temp_paths)

    for i, path in enumerate(temp_paths):
        segment = AudioSegment.from_file(path, format="mp3")
        segment = effects.normalize(segment)  # ✅ 每段音频做音量归一化
        combined += segment + silence
        if progress_callback:
            progress_callback(i + 1, total)

    combined = effects.normalize(combined)  # ✅ 合并后整体再做一次 normalize
    combined.export(output_path, format="mp3")


# 单句合成，支持语速
async def synthesize_sentence_edge_tts(text, voice, output_path, rate="default"):
    if rate == "default":
        communicate = Communicate(text, voice=voice)
    else:
        communicate = Communicate(text, voice=voice, rate=rate)
    await communicate.save(output_path)


# 主接口：根据输入文本合成音频
def generate_audio_with_edge_tts(text, filename=None, progress_callback=None, language="中文",
                                 output_dir=None, full_output_path=None, rate="default"):
    # 基于文本生成默认文件名（哈希）
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    filename = filename or f"tts_{text_hash}.mp3"

    # 最终保存路径（优先使用 full_output_path）
    if full_output_path:
        output_path = full_output_path
    else:
        output_dir = output_dir or tts_output_dir
        output_path = os.path.join(output_dir, filename)

    # 设置默认音色
    default_voice = "en-US-GuyNeural" if language == "英文" else "zh-CN-XiaoxiaoNeural"

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
                    progress_callback(idx + 1, total)

        asyncio.run(synthesize_all())
        combine_audio_segments(temp_paths, output_path, progress_callback=progress_callback)

        # 删除临时文件
        for path in temp_paths:
            os.remove(path)

        return output_path

    # === 普通整段文本处理 ===
    else:
        async def synthesize():
            # 设置语速参数
            if rate == "default":
                communicate = Communicate(text, voice=default_voice)
            else:
                communicate = Communicate(text, voice=default_voice, rate=rate)

            await communicate.save(output_path)
            if progress_callback:
                progress_callback(1, 1)

        try:
            asyncio.run(synthesize())

            # ✅ 合成后做 normalize，提升整体音量一致性
            audio = AudioSegment.from_file(output_path, format="mp3")
            audio = effects.normalize(audio)
            audio.export(output_path, format="mp3")

            return output_path
        except Exception as e:
            print(f"[ERROR] 合成失败: {e}")
            return None
