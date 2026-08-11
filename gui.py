import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading

from tts_generator import (
    generate_audio_with_edge_tts,
    get_male_voice_list,
    get_female_voice_list,
)


# ========== 线程安全的 UI 更新函数 ==========

def update_progress_bar(progress, total):
    """
    线程安全地更新进度条。
    通过 root.after 将更新调度到主线程执行，避免跨线程操作 tkinter。

    参数:
        progress (int/float): 当前进度值。
        total (int/float): 总进度值。
    """
    percentage = (progress / total) * 100 if total > 0 else 0
    root.after(0, lambda p=percentage: _do_update_progress(p))


def _do_update_progress(percentage):
    """在主线程中执行进度条更新"""
    progress_bar['value'] = percentage
    progress_label.config(text=f"{int(percentage)}%")


def update_status(text):
    """
    线程安全地更新状态文字。

    参数:
        text (str): 状态描述文字。
    """
    root.after(0, lambda t=text: status_label.config(text=t))


# ========== 音色联动 ==========

def on_language_change(event=None):
    """
    当语言选择变化时，更新男声和女声下拉列表为对应语言的可用音色。
    """
    language = language_var.get()

    # 更新男声列表
    male_voices = get_male_voice_list(language)
    male_labels = [label for _, label in male_voices]
    if male_labels:
        male_voice_label_var.set(male_labels[0])
    male_voice_select['values'] = male_labels

    # 更新女声列表
    female_voices = get_female_voice_list(language)
    female_labels = [label for _, label in female_voices]
    if female_labels:
        female_voice_label_var.set(female_labels[0])
    female_voice_select['values'] = female_labels


# ========== 生成音频 ==========

def generate_audio():
    """
    获取用户输入的文本、语言、语速和音色设置，选择保存路径，并启动线程生成音频文件。
    """
    text = text_box.get("1.0", tk.END).strip()
    language = language_var.get()
    rate = speed_var.get()
    gender = gender_var.get()
    male_voice_label = male_voice_label_var.get()
    female_voice_label = female_voice_label_var.get()

    if not text:
        messagebox.showerror("错误", "请输入文本以生成音频")
        return

    # 根据显示标签查找对应的音色ID
    male_voices = get_male_voice_list(language)
    female_voices = get_female_voice_list(language)

    selected_male_voice = None
    for voice_id, label in male_voices:
        if label == male_voice_label:
            selected_male_voice = voice_id
            break

    selected_female_voice = None
    for voice_id, label in female_voices:
        if label == female_voice_label:
            selected_female_voice = voice_id
            break

    save_path = filedialog.asksaveasfilename(
        defaultextension=".mp3",
        filetypes=[("MP3 files", "*.mp3")],
        title="选择保存音频的位置和文件名"
    )
    if not save_path:
        return

    # 重置进度条和状态
    progress_bar['value'] = 0
    progress_label.config(text="0%")
    status_label.config(text="正在准备...")

    # 禁用按钮 + 修改文字
    generate_button.config(state=tk.DISABLED, text="正在生成...")

    threading.Thread(
        target=generate_audio_in_thread,
        args=(text, save_path, language, rate, gender,
              selected_male_voice, selected_female_voice),
        daemon=True
    ).start()


def generate_audio_in_thread(text, save_path, language, rate, gender,
                              male_voice, female_voice):
    """
    在子线程中调用 TTS 引擎生成音频文件，并在完成后显示结果提示。

    参数:
        text: 需要转换为语音的文本内容
        save_path: 音频文件的保存路径
        language: 语言（"中文" 或 "英文"）
        rate: 语速设置
        gender: 单文本模式下的性别选择（"男声" 或 "女声"）
        male_voice: 男声音色ID（对话模式使用，单文本模式 gender="男声" 时使用）
        female_voice: 女声音色ID（对话模式使用，单文本模式 gender="女声" 时使用）
    """
    try:
        def progress_callback(progress, total):
            update_progress_bar(progress, total)

        def status_callback(status_text):
            update_status(status_text)

        audio_path = generate_audio_with_edge_tts(
            text=text,
            full_output_path=save_path,
            progress_callback=progress_callback,
            language=language,
            rate=rate,
            male_voice=male_voice,
            female_voice=female_voice,
            gender=gender,
            status_callback=status_callback
        )

        if audio_path:
            update_status("生成完成")
            messagebox.showinfo("成功", f"音频生成成功！\n保存路径: {audio_path}")
        else:
            update_status("生成失败")
            messagebox.showerror("错误", "音频生成失败，请重试")
    except Exception as e:
        update_status("生成失败")
        messagebox.showerror("错误", f"合成失败: {e}")
    finally:
        # 无论成功失败，恢复按钮状态
        generate_button.config(state=tk.NORMAL, text="生成音频")


# ========== 界面布局 ==========

# 创建主窗口
root = tk.Tk()
root.title("文本转语音工具")

# 文本输入
tk.Label(root, text="请输入文本：").pack(padx=10, pady=5)
text_box = tk.Text(root, height=10, width=50)
text_box.pack(padx=10, pady=5)

# 语言选择
tk.Label(root, text="选择语言：").pack(padx=10, pady=5)
language_var = tk.StringVar(value="英文")
language_select = ttk.Combobox(
    root,
    textvariable=language_var,
    values=["英文", "中文"],
    state="readonly"
)
language_select.pack(padx=10, pady=5)
language_select.bind("<<ComboboxSelected>>", on_language_change)

# 语速选择
tk.Label(root, text="选择语速：").pack(padx=10, pady=5)
speed_var = tk.StringVar(value="default")
speed_options = ["default"] + [f"{i}%" for i in range(-30, 35, 5) if i != 0]
speed_select = ttk.Combobox(
    root,
    textvariable=speed_var,
    values=speed_options,
    state="readonly"
)
speed_select.pack(padx=10, pady=5)

# 性别选择（单文本模式使用，对话模式忽略此项）
tk.Label(root, text="单文本性别：").pack(padx=10, pady=5)
gender_var = tk.StringVar(value="女声")
gender_frame = tk.Frame(root)
gender_frame.pack(padx=10, pady=2)
tk.Radiobutton(gender_frame, text="男声", variable=gender_var, value="男声").pack(side=tk.LEFT, padx=10)
tk.Radiobutton(gender_frame, text="女声", variable=gender_var, value="女声").pack(side=tk.LEFT, padx=10)

# 男声音色选择
tk.Label(root, text="男声音色：").pack(padx=10, pady=5)
male_voice_label_var = tk.StringVar()
male_voice_select = ttk.Combobox(
    root,
    textvariable=male_voice_label_var,
    state="readonly"
)
male_voice_select.pack(padx=10, pady=5)

# 女声音色选择
tk.Label(root, text="女声音色：").pack(padx=10, pady=5)
female_voice_label_var = tk.StringVar()
female_voice_select = ttk.Combobox(
    root,
    textvariable=female_voice_label_var,
    state="readonly"
)
female_voice_select.pack(padx=10, pady=5)
# 初始化音色列表（根据当前语言填充男声和女声）
on_language_change()

# 生成按钮
generate_button = tk.Button(root, text="生成音频", command=generate_audio)
generate_button.pack(pady=10)

# 状态标签（显示当前处理阶段）
status_label = tk.Label(root, text="就绪", fg="gray")
status_label.pack(padx=10, pady=2)

# 进度条
progress_bar = ttk.Progressbar(root, length=400, mode='determinate')
progress_bar.pack(padx=10, pady=5)

# 进度百分比标签
progress_label = tk.Label(root, text="0%")
progress_label.pack(padx=10, pady=2)

root.mainloop()
