
# TextToSpeechTool

🎤 一个基于 [edge-tts](https://github.com/rany2/edge-tts) 和 PyDub 的桌面音频合成工具，支持中英文文本转语音，支持对话角色音色区分和合成后自动标准化音量。

---

## 📦 功能特点

- 支持中文/英文语音合成（通过 Edge-TTS）
- 对话自动识别角色（M/W）并使用不同音色
- 合成时自动插入静音、统一音量（normalize）
- 图形界面支持文本输入、语言选择、音频保存路径选择
- 可打包为单个 `.exe` 文件发给其他人使用

---

## 🧰 安装依赖

使用国内镜像加速：

```bash
pip install pyinstaller edge-tts pydub -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 🚀 运行程序

确保你已安装 Python 3.11，然后运行：

```bash
python gui.py
```

---

## 🛠️ 打包为 EXE

确保已安装 pyinstaller，并执行打包：

```bash
pyinstaller TextToSpeechTool.spec
```

或使用 `build.py`：

```bash
python build.py
```

打包时会：

- 包含 icon.ico 图标
- 添加 `static/audio` 文件夹用于存放音频
- 可选将 `ffmpeg.exe` 一并打包（需手动添加至 `.spec` 文件）

---

## 📁 项目结构

```
TextToSpeechTool/
├── audio_tool/              # 主模块目录
│   ├── gui.py               # 图形界面主程序
│   ├── tts_generator.py     # TTS合成逻辑
│   ├── utils.py             # 工具函数：对话识别等
│   ├── icon.ico             # 应用图标
│   └── static/audio/        # 生成音频保存位置
├── ffmpeg/                  # 可选：放置 ffmpeg.exe
├── build.py                 # 打包脚本（可选）
├── TextToSpeechTool.spec    # PyInstaller 打包配置
└── README.md
```

---

## 📝 示例截图

（可自行添加界面截图或示例音频）

---

## 🙋 常见问题

- **声音忽大忽小？**
  - 已内置 normalize 处理，如果仍有问题请反馈音频。

- **打包失败或报错？**
  - 推荐使用 Python 3.11，避免使用 `typing` 旧包，确保 `edge-tts` 与 `aiohttp` 兼容。

---

## 📬 联系作者

如有建议或问题欢迎反馈。

