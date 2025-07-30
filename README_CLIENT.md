# 实时麦克风音频转录脚本使用说明

本项目提供了一套完整的Python脚本，用于从麦克风持续捕获音频并实时传给 WhisperLiveKit 的 ASR 服务进行语音识别处理。

## 📋 文件列表

- **`simple_mic_to_asr.py`** - 简化版实时转录客户端（推荐）
- **`mic_to_asr.py`** - 完整功能版本，支持更多自定义选项
- **`check_connection.py`** - WebSocket 连接测试工具
- **`README_CLIENT.md`** - 本使用说明文档

## 🚀 快速开始

### 1. 启动 WhisperLiveKit 服务器

首先，在一个终端中启动 WhisperLiveKit 服务器：

```bash
# 使用tiny模型（快速，适合测试）
whisperlivekit-server --model tiny.en

# 或使用更精确的模型
whisperlivekit-server --model base --language zh  # 中文
whisperlivekit-server --model medium --language auto  # 自动检测语言

# 启用说话者识别
whisperlivekit-server --model base --diarization
```

服务器启动成功后，你会看到类似的输出：
```
INFO:     Started server process [1234]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8000
```

### 2. 测试连接

在另一个终端中，运行连接测试：

```bash
python check_connection.py
```

如果连接成功，你会看到：
```
🧪 WhisperLiveKit WebSocket 连接测试
==================================================
INFO:__main__:尝试连接到 ws://localhost:8000/asr
INFO:__main__:✅ WebSocket 连接成功!
INFO:__main__:发送测试数据...
INFO:__main__:等待服务器响应...
INFO:__main__:测试完成

✅ 连接测试成功!
现在你可以运行实际的麦克风转录脚本:
  python simple_mic_to_asr.py
```

### 3. 运行客户端脚本

#### 简化版本（推荐）

```bash
python simple_mic_to_asr.py
```

#### 完整版本

```bash
python mic_to_asr.py
```

## 📁 脚本说明

### `simple_mic_to_asr.py` （推荐）

**特点：**
- 🎯 简单易用，开箱即用
- 🔧 无额外依赖（除了 pyaudio 和 websockets）
- 🎨 美观的实时界面显示
- ⚡ 与 WhisperLiveKit 的 web 接口兼容

**使用方法：**
```bash
python simple_mic_to_asr.py [选项]

选项:
  --host HOST    服务器地址 (默认: localhost)  
  --port PORT    服务器端口 (默认: 8000)
```

**示例：**
```bash
# 连接到本地服务器
python simple_mic_to_asr.py

# 连接到远程服务器
python simple_mic_to_asr.py --host 192.168.1.100 --port 8000
```

### `mic_to_asr.py` （功能完整版）

**特点：**
- 🔧 更多自定义选项
- 📊 详细的音频设备信息
- ⚙️ 可调节的音频参数
- 🎛️ 高级音频处理

**使用方法：**
```bash
python mic_to_asr.py [选项]

选项:
  --host HOST              服务器地址 (默认: localhost)
  --port PORT              服务器端口 (默认: 8000)
  --chunk-duration DURATION  音频块持续时间，毫秒 (默认: 1000)
  --sample-rate RATE       采样率 (默认: 16000)
  --channels CHANNELS      声道数 (默认: 1)
```

## 🛠️ 依赖安装

### 基础依赖

```bash
# 安装 WhisperLiveKit
pip install whisperlivekit

# 安装音频处理库
pip install pyaudio websockets
```

### 系统依赖（如果 pyaudio 安装失败）

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio
```

**macOS:**
```bash
brew install portaudio
pip install pyaudio
```

**Windows:**
- 下载预编译的 PyAudio 包或使用 conda

## 🎛️ 功能特性

### 实时转录显示

脚本会实时显示：
- ✅ **已确认转录**: 经过完整处理的文本
- 🔄 **实时预览**: 正在处理的音频预览
- 👤 **说话者识别**: 区分不同说话者（如果启用）
- ⏰ **时间戳**: 显示每段话的时间范围
- 📊 **状态信息**: 处理延迟和系统状态

### 界面示例

```
================================================================================
🎤 实时语音转录 - WhisperLiveKit
按 Ctrl+C 停止录音
================================================================================

📝 转录结果:
  👤 [说话者 1] (0.0s-3.2s): 你好，这是一个测试
  👤 [说话者 1] (3.5s-6.1s): 语音识别效果很好

🔄 实时预览: 现在我在说另一句话

⏳ 转录延迟: 0.5s | ⏳ 说话者识别延迟: 1.2s
================================================================================
```

## 🔧 故障排除

### 常见问题

1. **WebSocket 连接失败**
   ```
   ERROR:__main__:❌ 连接测试失败: Multiple exceptions: [Errno 111] Connect call failed
   ```
   - 确保 WhisperLiveKit 服务器正在运行
   - 检查服务器地址和端口是否正确
   - 运行 `python check_connection.py` 进行诊断

2. **服务器启动失败 - 模型下载问题**
   ```
   LocalEntryNotFoundError: Cannot find an appropriate cached snapshot folder
   ```
   - 确保有稳定的网络连接
   - 首次运行时需要下载模型文件
   - 尝试使用更小的模型：`--model tiny`

3. **麦克风权限问题**
   ```
   启动音频流失败: [Errno -9996] Invalid input device
   ```
   - 检查麦克风是否正确连接
   - 确保程序有麦克风访问权限
   - 在 Linux 上可能需要将用户添加到 audio 组

4. **PyAudio 安装失败**
   ```
   fatal error: portaudio.h: No such file or directory
   ```
   - 参考上面的系统依赖安装说明
   - Ubuntu: `sudo apt-get install portaudio19-dev`
   - macOS: `brew install portaudio`
   - 考虑使用 conda 环境

5. **ALSA 错误（Linux）**
   ```
   ALSA lib pcm.c:2721:(snd_pcm_open_noupdate) Unknown PCM sysdefault
   ```
   - 这些警告通常不影响功能
   - 如果影响使用，可以安装 `pulseaudio-utils`

### 调试模式

启用详细日志输出来诊断问题：

```bash
# 设置环境变量启用调试日志
export PYTHONPATH=/path/to/WhisperLiveKit
python -v simple_mic_to_asr.py --host localhost --port 8000

# 或者直接查看服务器日志
whisperlivekit-server --model tiny.en --log-level debug
```

### 测试流程

推荐的测试流程：

1. **检查依赖安装**
   ```bash
   python -c "import pyaudio, websockets, asyncio; print('✅ 所有依赖已安装')"
   ```

2. **启动服务器**
   ```bash
   whisperlivekit-server --model tiny.en
   ```

3. **测试连接**
   ```bash
   python check_connection.py
   ```

4. **运行客户端**
   ```bash
   python simple_mic_to_asr.py
   ```

## 🎯 使用场景

- 📝 **会议记录**: 实时转录会议讨论
- 🎤 **演讲转录**: 转录演讲或讲座内容  
- 💬 **对话记录**: 记录多人对话并识别说话者
- 🔊 **无障碍辅助**: 为听障人士提供实时字幕
- 📻 **媒体处理**: 转录播客或音频内容

## 📈 性能优化建议

1. **模型选择**:
   - `tiny.en`: 最快，适合实时场景
   - `base`: 平衡速度和准确性
   - `medium/large`: 最准确，但需要更多计算资源

2. **硬件要求**:
   - 推荐使用 GPU 加速
   - 至少 4GB 内存
   - 稳定的网络连接（如果使用远程服务器）

3. **网络优化**:
   - 本地部署以减少延迟
   - 使用有线网络连接
   - 避免网络拥堵时段

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这些脚本！

## 📄 许可证

这些脚本遵循与 WhisperLiveKit 相同的许可证。