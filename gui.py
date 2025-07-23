import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
from tts_generator import generate_audio_with_edge_tts


def update_progress_bar(progress, total, progress_bar):
    progress_bar['value'] = (progress / total) * 100
    root.update_idletasks()


def generate_audio():
    text = text_box.get("1.0", tk.END).strip()
    language = language_var.get()

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

    threading.Thread(
        target=generate_audio_in_thread,
        args=(text, save_path, language)
    ).start()


def generate_audio_in_thread(text, save_path, language):
    try:
        def progress_callback(progress, total):
            update_progress_bar(progress, total, progress_bar)

        audio_path = generate_audio_with_edge_tts(
            text=text,
            full_output_path=save_path,
            progress_callback=progress_callback,
            language=language
        )

        if audio_path:
            messagebox.showinfo("成功", f"音频生成成功！\n保存路径: {audio_path}")
        else:
            messagebox.showerror("错误", "音频生成失败")
    except Exception as e:
        messagebox.showerror("错误", f"合成失败: {e}")


# 创建主窗口
root = tk.Tk()
root.title("文本转语音工具")

tk.Label(root, text="请输入文本：").pack(padx=10, pady=5)
text_box = tk.Text(root, height=10, width=50)
text_box.pack(padx=10, pady=5)

tk.Label(root, text="选择语言：").pack(padx=10, pady=5)
language_var = tk.StringVar(value="中文")
language_select = ttk.Combobox(
    root,
    textvariable=language_var,
    values=["中文", "英文"],
    state="readonly"
)
language_select.pack(padx=10, pady=5)

tk.Button(root, text="生成音频", command=generate_audio).pack(pady=10)

progress_bar = ttk.Progressbar(root, length=400, mode='determinate')
progress_bar.pack(padx=10, pady=10)

root.mainloop()
