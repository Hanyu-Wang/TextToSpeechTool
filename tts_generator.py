import os
import hashlib
import asyncio
import shutil
import subprocess
import tempfile
from uuid import uuid4
from edge_tts import Communicate
from pydub import AudioSegment, effects  # 这行必须在设置FFMPEG_PATH之后
from utils import is_dialogue, parse_dialogue_lines, split_dialogue_paragraph_to_lines, get_ffmpeg_path, get_ffmpeg_cmd

ffmpeg_path, ffprobe_path = get_ffmpeg_path()
ffmpeg_dir = os.path.dirname(ffmpeg_path)

# 设置 pydub 路径
AudioSegment.converter = ffmpeg_path
AudioSegment.ffmpeg = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path

# 添加到 PATH，让 pydub 真正找到
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

print("✅ 设置 pydub 路径:", ffmpeg_path)

# 输出目录，默认保存在 static/audio 下
tts_output_dir = os.path.join(os.path.dirname(__file__), "static/audio")
os.makedirs(tts_output_dir, exist_ok=True)

# ========== 重试配置 ==========
MAX_RETRIES = 3
RETRY_DELAY = 1.5  # 秒，每次重试递增

# ========== 音色配置 ==========
# 格式: (voice_id, 显示标签)
VOICE_CONFIG = {
    "中文": [
        ("zh-CN-XiaoxiaoNeural", "晓晓（女·温暖亲切·普通话）"),
        ("zh-CN-XiaoyiNeural", "晓伊（女·活泼可爱·普通话）"),
        ("zh-CN-YunjianNeural", "云健（男·运动解说）"),
        ("zh-CN-YunxiNeural", "云希（男·少年音）"),
        ("zh-CN-YunxiaNeural", "云夏（男·少年音）"),
        ("zh-CN-YunyangNeural", "云扬（男·新闻播报）"),
    ],
    "英文": [
        ("en-US-AvaMultilingualNeural", "Ava（女·多语言）"),
        ("en-US-EmmaNeural", "Emma（女·友好温暖）"),
        ("en-US-JennyNeural", "Jenny（女·亲切自然）"),
        ("en-US-MichelleNeural", "Michelle（女·专业沉稳）"),
        ("en-US-GuyNeural", "Guy（男·沉稳大气）"),
        ("en-US-ChristopherNeural", "Christopher（男·温暖亲切）"),
        ("en-US-EricNeural", "Eric（男·年轻活力）"),
        ("en-US-RogerNeural", "Roger（男·专业沉稳）"),
    ],
}

# 女声音色ID集合（用于对话模式判断性别）
FEMALE_VOICE_IDS = {
    "zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural",
    "zh-CN-liaoning-XiaobeiNeural", "zh-CN-shaanxi-XiaoniNeural",
    "en-US-AvaMultilingualNeural", "en-US-EmmaNeural",
    "en-US-JennyNeural", "en-US-MichelleNeural",
}

# 对话模式默认男/女音色
DIALOGUE_DEFAULT_VOICES = {
    "中文": {"M": "zh-CN-YunyangNeural", "W": "zh-CN-XiaoxiaoNeural"},
    "英文": {"M": "en-US-GuyNeural", "W": "en-US-EmmaNeural"},
}


def get_voice_list(language):
    """获取指定语言的音色列表，返回 [(voice_id, label), ...]"""
    return VOICE_CONFIG.get(language, VOICE_CONFIG["中文"])


def get_male_voice_list(language):
    """获取指定语言的男声音色列表，返回 [(voice_id, label), ...]"""
    all_voices = get_voice_list(language)
    return [(vid, label) for vid, label in all_voices if not is_female_voice(vid)]


def get_female_voice_list(language):
    """获取指定语言的女声音色列表，返回 [(voice_id, label), ...]"""
    all_voices = get_voice_list(language)
    return [(vid, label) for vid, label in all_voices if is_female_voice(vid)]


def is_female_voice(voice_id):
    """判断音色是否为女声"""
    return voice_id in FEMALE_VOICE_IDS


def insert_silence(duration_ms=300):
    return AudioSegment.silent(duration=duration_ms)


def trim_leading_silence(audio_segment, threshold_dbfs=-45.0, chunk_ms=10, pad_ms=30, fade_in_ms=20):
    """
    裁剪音频开头的静音部分，并用短淡入平滑过渡。

    用于解决 edge-tts 神经语音在合成开头存在渐强爬升（前100~250ms极低响度）的问题。
    典型场景：句号前缀 ". " 产生的静音段被裁掉后，实际语音从一个更干净的起始点开始。

    参数:
        audio_segment: pydub AudioSegment 对象
        threshold_dbfs: 判定语音起始的 dBFS 阈值（默认 -45）
        chunk_ms: 分析粒度（默认 10ms）
        pad_ms: 在检测到的起始点之前保留的毫秒数（默认 30ms）
        fade_in_ms: 淡入时长（默认 20ms），避免裁剪后产生点击声

    返回:
        裁剪后的 AudioSegment
    """
    onset_ms = 0
    found = False
    for ms in range(0, len(audio_segment) - chunk_ms, chunk_ms):
        chunk = audio_segment[ms:ms + chunk_ms]
        if chunk.dBFS > threshold_dbfs:
            onset_ms = ms
            found = True
            break

    if not found:
        return audio_segment  # 未找到语音起始，返回原音频

    # 在起始点之前保留 pad_ms 以不切断辅音起始
    start_ms = max(0, onset_ms - pad_ms)
    trimmed = audio_segment[start_ms:]

    # 如果裁掉了内容，加短淡入避免点击声
    if start_ms > 0 and fade_in_ms > 0:
        trimmed = trimmed.fade_in(fade_in_ms)

    return trimmed


# 使用FFmpeg进行响度标准化
def combine_audio_with_ffmpeg(temp_paths, output_path, pause_duration_ms=300, progress_callback=None):
    # 验证路径
    ffmpeg_path, _ = get_ffmpeg_path()
    if not os.path.exists(ffmpeg_path):
        raise FileNotFoundError(f"FFmpeg 不存在: {ffmpeg_path}")

    temp_combined = os.path.join(tempfile.gettempdir(), f"temp_combined_{uuid4().hex}.mp3")

    # 合并音频片段（使用 pydub，已通过环境变量配置 FFmpeg）
    combined = AudioSegment.empty()
    silence = insert_silence(pause_duration_ms)

    total = len(temp_paths)
    for i, path in enumerate(temp_paths):
        segment = AudioSegment.from_file(path, format="mp3")
        combined += segment + silence
        if progress_callback:
            progress_callback(i + 1, total)

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
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg 命令失败: {e.stderr}")
        raise
    finally:
        # 清理临时文件（容错处理，清理失败不影响主流程）
        for path in [temp_combined] + temp_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as cleanup_err:
                print(f"  [警告] 清理临时文件失败: {path} - {cleanup_err}")


# 单句合成，支持语速和失败重试（最多 MAX_RETRIES 次）
async def synthesize_sentence_edge_tts(text, voice, output_path, rate="default",
                                       max_retries=MAX_RETRIES, status_callback=None):
    """
    使用 edge-tts 合成单句语音，失败时自动重试。

    参数:
        text: 待合成文本
        voice: edge-tts 音色ID
        output_path: 输出文件路径
        rate: 语速，"default" 或如 "+20%"/"-10%"
        max_retries: 最大重试次数
        status_callback: 可选的状态回调函数，接收字符串参数

    异常:
        超过最大重试次数后抛出最后一次异常
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            if rate == "default":
                communicate = Communicate(text, voice=voice)
            else:
                communicate = Communicate(text, voice=voice, rate=rate)
            await communicate.save(output_path)
            return  # 成功则直接返回
        except Exception as e:
            last_error = e
            print(f"  [重试 {attempt}/{max_retries}] 合成失败: {e}")
            # 清理可能产生的不完整文件
            if os.path.exists(output_path):
                os.remove(output_path)
            if attempt < max_retries:
                delay = RETRY_DELAY * attempt  # 递增延迟
                if status_callback:
                    status_callback(f"正在重试 ({attempt}/{max_retries})...")
                await asyncio.sleep(delay)
    # 所有重试均失败，抛出最后的异常
    raise last_error


# 主接口：根据输入文本合成音频
def generate_audio_with_edge_tts(text, filename=None, progress_callback=None, language="中文",
                                 output_dir=None, full_output_path=None, rate="default",
                                 voice=None, male_voice=None, female_voice=None,
                                 gender="女声", status_callback=None):
    """
    根据输入文本合成音频文件。

    参数:
        text: 需要转换为语音的文本内容
        filename: 输出文件名（可选，默认基于文本哈希）
        progress_callback: 进度回调 callback(progress, total)，progress/total 范围 0~100
        language: 语言（"中文" 或 "英文"）
        output_dir: 输出目录（可选）
        full_output_path: 完整输出路径（优先级高于 output_dir）
        rate: 语速设置
        voice: 指定音色ID（仅单文本模式有效，优先于 male_voice/female_voice）
        male_voice: 对话模式男声音色ID（或单文本模式下 gender="男声" 时使用）
        female_voice: 对话模式女声音色ID（或单文本模式下 gender="女声" 时使用）
        gender: 单文本模式下的性别选择（"男声" 或 "女声"）
        status_callback: 状态文字回调 callback(str)

    返回:
        成功时返回输出文件路径，失败返回 None
    """
    # 基于文本生成默认文件名（哈希）
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    filename = filename or f"tts_{text_hash}.mp3"

    # 最终保存路径（优先使用 full_output_path）
    if full_output_path:
        output_path = full_output_path
    else:
        output_dir = output_dir or tts_output_dir
        output_path = os.path.join(output_dir, filename)

    # 确定音色：
    # 单文本模式 — voice 优先，其次按 gender 从 male_voice/female_voice 中取，最后用默认
    # 对话模式 — male_voice/female_voice 分别用于 M/W 角色
    if voice:
        selected_voice = voice
    elif gender == "男声" and male_voice:
        selected_voice = male_voice
    elif gender == "女声" and female_voice:
        selected_voice = female_voice
    else:
        if language == "英文":
            selected_voice = "en-US-GuyNeural" if gender == "男声" else "en-US-EmmaNeural"
        else:
            selected_voice = "zh-CN-YunyangNeural" if gender == "男声" else "zh-CN-XiaoxiaoNeural"

    # === 中英双语对话文本处理 ===
    if is_dialogue(text) and language in ("中文", "英文"):
        lines = parse_dialogue_lines(split_dialogue_paragraph_to_lines(text))
        temp_paths = []
        total = len(lines)

        # 对话模式：男声/女声分别使用用户选择的音色，未选则用默认
        dialogue_voices = {
            "M": male_voice or DIALOGUE_DEFAULT_VOICES[language]["M"],
            "W": female_voice or DIALOGUE_DEFAULT_VOICES[language]["W"],
        }

        # 进度分两阶段：合成阶段 0% → 60%，合并阶段 60% → 100%
        if status_callback:
            status_callback("正在逐句合成语音...")

        # 句首哨兵前缀：英文用 ". "，中文用 "。"，给 TTS 模型热身避免开头渐强爬升
        lead_in = "." if language == "英文" else "。"

        async def synthesize_all():
            for idx, (role, sentence) in enumerate(lines):
                role_voice = dialogue_voices[role]
                temp_file = os.path.join(tempfile.gettempdir(), f"temp_{uuid4().hex}.mp3")

                # 第一句加句号前缀，让 TTS 模型先"热身"再发音，
                # 避免开头第一个词出现渐强爬升导致发虚/失真
                synth_text = sentence
                if idx == 0:
                    synth_text = lead_in + sentence

                await synthesize_sentence_edge_tts(
                    synth_text, role_voice, temp_file, rate=rate,
                    status_callback=status_callback
                )

                # 第一句合成后裁掉句号前缀产生的开头静音
                if idx == 0:
                    seg = AudioSegment.from_file(temp_file, format="mp3")
                    seg = trim_leading_silence(seg)
                    seg.export(temp_file, format="mp3")

                temp_paths.append(temp_file)
                # 合成阶段进度：映射到 0~60
                if progress_callback:
                    pct = int(60 * (idx + 1) / total) if total > 0 else 60
                    progress_callback(pct, 100)

        asyncio.run(synthesize_all())

        # 合并阶段
        if status_callback:
            status_callback("正在合并音频并标准化音量...")

        def combine_progress(current, total_combine):
            if progress_callback:
                pct = 60 + int(40 * current / total_combine) if total_combine > 0 else 100
                progress_callback(pct, 100)

        combine_audio_with_ffmpeg(temp_paths, output_path, progress_callback=combine_progress)

        if progress_callback:
            progress_callback(100, 100)
        if status_callback:
            status_callback("生成完成")

        return output_path

    # === 普通整段文本处理 ===
    else:
        if status_callback:
            status_callback("正在合成语音...")

        # 带重试的合成（加句号前缀让 TTS 模型先"热身"，避免开头第一个词渐强爬升）
        synth_text = ". " + text

        async def synthesize():
            last_error = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    if rate == "default":
                        communicate = Communicate(synth_text, voice=selected_voice)
                    else:
                        communicate = Communicate(synth_text, voice=selected_voice, rate=rate)
                    await communicate.save(output_path)
                    return  # 成功
                except Exception as e:
                    last_error = e
                    print(f"  [重试 {attempt}/{MAX_RETRIES}] 合成失败: {e}")
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    if attempt < MAX_RETRIES:
                        delay = RETRY_DELAY * attempt
                        if status_callback:
                            status_callback(f"正在重试 ({attempt}/{MAX_RETRIES})...")
                        await asyncio.sleep(delay)
            raise last_error

        try:
            # 合成开始
            if progress_callback:
                progress_callback(0, 100)

            asyncio.run(synthesize())

            # 裁掉句号前缀产生的开头静音
            seg = AudioSegment.from_file(output_path, format="mp3")
            seg = trim_leading_silence(seg)
            seg.export(output_path, format="mp3")

            # 合成完成 → 50%
            if progress_callback:
                progress_callback(50, 100)

            # FFmpeg 标准化音量
            if status_callback:
                status_callback("正在标准化音量...")

            temp_single = os.path.join(tempfile.gettempdir(), f"temp_single_{uuid4().hex}.mp3")
            shutil.copy2(output_path, temp_single)

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
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 标准化完成 → 100%
            if progress_callback:
                progress_callback(100, 100)
            if status_callback:
                status_callback("生成完成")

            # 清理临时文件（容错处理）
            try:
                if os.path.exists(temp_single):
                    os.remove(temp_single)
            except Exception as cleanup_err:
                print(f"  [警告] 清理临时文件失败: {cleanup_err}")

            return output_path
        except Exception as e:
            print(f"合成失败: {str(e)}")
            if status_callback:
                status_callback("生成失败")
            # 清理残留文件
            if 'temp_single' in locals() and os.path.exists(temp_single):
                try:
                    os.remove(temp_single)
                except Exception:
                    pass
            return None
