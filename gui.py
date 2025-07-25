import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading

from tts_generator import generate_audio_with_edge_tts


def update_progress_bar(progress, total, progress_bar):
    """
        更新进度条的显示值。

        参数:
            progress (int): 当前已完成的进度。
            total (int): 总共需要完成的进度。
            progress_bar (ttk.Progressbar): 要更新的进度条控件。
        """
    progress_bar['value'] = (progress / total) * 100
    root.update_idletasks()


def generate_audio():
    """
        获取用户输入的文本、语言和语速设置，选择保存路径，并启动线程生成音频文件。
        若输入为空则弹出提示；若未选择保存路径则取消操作。
        """
    text = text_box.get("1.0", tk.END).strip()
    language = language_var.get()
    rate = speed_var.get()
    gender = voice_gender_var.get()

    if not text:
        messagebox.showerror("错误", "请输入文本以生成音频")
        return

    save_path = filedialog.asksaveasfilename(
        defaultextension=".mp3",
        filetypes=[("MP3 files", "*.mp3")],
        title="选择保存音频的位置和文件名"
    )
    if not save_path:
        return
    # 禁用按钮 + 修改文字
    generate_button.config(state=tk.DISABLED, text="正在生成...")

    threading.Thread(
        target=generate_audio_in_thread,
        args=(text, save_path, language, rate, gender)
    ).start()


def generate_audio_in_thread(text, save_path, language, rate, gender):
    """
       在子线程中调用 TTS 引擎生成音频文件，并在完成后显示结果提示。

       参数:
           text (str): 需要转换为语音的文本内容。
           save_path (str): 音频文件的保存路径。
           language (str): 选择的语言（如“中文”或“英文”）。
           rate (str): 语速设置（如"default"或百分比字符串如"-20%"）。

       异常处理:
           捕获所有异常并在图形界面中弹出错误信息。
       """
    try:
        def progress_callback(progress, total):
            update_progress_bar(progress, total, progress_bar)

        audio_path = generate_audio_with_edge_tts(
            text=text,
            full_output_path=save_path,
            progress_callback=progress_callback,
            language=language,
            rate=rate,
            gender=gender
        )

        if audio_path:
            messagebox.showinfo("成功", f"音频生成成功！\n保存路径: {audio_path}")
        else:
            messagebox.showerror("错误", "音频生成失败")
    except Exception as e:
        messagebox.showerror("错误", f"合成失败: {e}")
    finally:
        # 无论成功失败，恢复按钮状态
        generate_button.config(state=tk.NORMAL, text="生成音频")


# 创建主窗口
root = tk.Tk()
root.title("文本转语音工具")

tk.Label(root, text="请输入文本：").pack(padx=10, pady=5)
text_box = tk.Text(root, height=10, width=50)
text_box.pack(padx=10, pady=5)

tk.Label(root, text="选择语言：").pack(padx=10, pady=5)
language_var = tk.StringVar(value="英文")
language_select = ttk.Combobox(
    root,
    textvariable=language_var,
    values=["英文", "中文"],
    state="readonly"
)
language_select.pack(padx=10, pady=5)

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

# 音色选择（新增）
tk.Label(root, text="选择音色：").pack(padx=10, pady=5)
voice_gender_var = tk.StringVar(value="女声")
voice_select = ttk.Combobox(
    root,
    textvariable=voice_gender_var,
    values=["女声", "男声"],
    state="readonly"
)
voice_select.pack(padx=10, pady=5)

generate_button = tk.Button(root, text="生成音频", command=generate_audio)
generate_button.pack(pady=10)

progress_bar = ttk.Progressbar(root, length=400, mode='determinate')
progress_bar.pack(padx=10, pady=10)

root.mainloop()
