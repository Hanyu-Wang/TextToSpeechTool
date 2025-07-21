import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
import threading
import os
from audio_tool.tts_generator import generate_audio_with_edge_tts


# 进度条更新函数
def update_progress_bar(progress, total, progress_bar):
    progress_bar['value'] = (progress / total) * 100
    root.update_idletasks()


def generate_audio():
    text = text_box.get("1.0", tk.END).strip()

    if not text:
        messagebox.showerror("错误", "请输入文本以生成音频")
        return

    # 弹出文件保存对话框，获取用户选择的保存路径
    save_path = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3 files", "*.mp3")])

    # 如果用户取消选择，返回
    if not save_path:
        return

        # 创建一个新的线程来执行音频合成任务，避免阻塞主线程
    threading.Thread(target=generate_audio_in_thread, args=(text, save_path)).start()


def generate_audio_in_thread(text, save_path):
    try:
        # 使用进度条更新函数，并传递保存路径
        def progress_callback(progress, total):
            update_progress_bar(progress, total, progress_bar)

        # 将音频文件保存到用户选择的路径
        audio_path = generate_audio_with_edge_tts(text, filename=os.path.basename(save_path),
                                                  progress_callback=progress_callback)

        if audio_path:
            messagebox.showinfo("成功", f"音频生成成功！\n路径: {audio_path}")
        else:
            messagebox.showerror("错误", "音频生成失败")
    except Exception as e:
        messagebox.showerror("错误", f"合成失败: {e}")


# 创建主窗口
root = tk.Tk()
root.title("音频合成工具")

# 创建文本框
text_label = tk.Label(root, text="请输入文本：")
text_label.pack(padx=10, pady=5)
text_box = tk.Text(root, height=10, width=40)
text_box.pack(padx=10, pady=5)

# 创建生成音频按钮
generate_button = tk.Button(root, text="生成音频", command=generate_audio)
generate_button.pack(padx=10, pady=20)

# 创建进度条
progress_bar = ttk.Progressbar(root, length=300, mode='determinate')
progress_bar.pack(padx=10, pady=10)

# 启动 GUI
root.mainloop()
