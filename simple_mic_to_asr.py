#!/usr/bin/env python3
"""
简化版实时麦克风音频转录脚本
从麦克风持续捕获音频，实时传给 WhisperLiveKit 的 /asr 端点进行语音识别处理。

使用方法:
    python simple_mic_to_asr.py

要求：
    - WhisperLiveKit 服务器已经在运行 (python -m whisperlivekit.basic_server 或 whisperlivekit-server)
    - 安装了 pyaudio: pip install pyaudio
    
可选参数:
    --host: 服务器地址 (默认: localhost)
    --port: 服务器端口 (默认: 8000)
"""

import asyncio
import argparse
import json
import logging
import signal
import sys
import wave
import io
from typing import Optional

import pyaudio
import websockets


# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SimpleMicrophoneStreamer:
    """简化的麦克风音频流处理器"""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.websocket_url = f"ws://{host}:{port}/asr"
        
        # 音频设置 - 使用与 web 接口相似的设置
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_duration = 1.0  # 1秒
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        
        # 连接和控制
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.should_stop = False
        
        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """处理终止信号"""
        logger.info("接收到终止信号，正在停止...")
        self.should_stop = True

    def create_wav_bytes(self, audio_data: bytes) -> bytes:
        """将PCM音频数据包装成WAV格式"""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)
        
        wav_buffer.seek(0)
        return wav_buffer.read()

    async def connect_websocket(self):
        """连接到 WhisperLiveKit WebSocket 服务"""
        try:
            logger.info(f"正在连接到 {self.websocket_url}")
            self.websocket = await websockets.connect(self.websocket_url)
            logger.info("WebSocket 连接成功")
            return True
        except Exception as e:
            logger.error(f"WebSocket 连接失败: {e}")
            logger.error("请确保 WhisperLiveKit 服务器正在运行:")
            logger.error("  whisperlivekit-server --model tiny.en")
            return False

    def start_audio_stream(self):
        """启动音频流"""
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,  # 16-bit
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            logger.info(f"音频流已启动 (采样率: {self.sample_rate}Hz, 声道: {self.channels})")
            return True
        except Exception as e:
            logger.error(f"启动音频流失败: {e}")
            logger.error("请检查麦克风是否正确连接并授予权限")
            return False

    async def display_transcription(self, data: dict):
        """显示转录结果"""
        lines = data.get("lines", [])
        buffer_transcription = data.get("buffer_transcription", "")
        status = data.get("status", "")
        
        # 清屏并显示内容
        print("\033[2J\033[H", end="")  # 清屏
        print("=" * 80)
        print("🎤 实时语音转录 - WhisperLiveKit")
        print("按 Ctrl+C 停止录音")
        print("=" * 80)
        
        if status == "no_audio_detected":
            print("\n💤 未检测到音频，请开始说话...")
        else:
            # 显示已确认的转录结果
            if lines:
                print("\n📝 转录结果:")
                for i, line in enumerate(lines):
                    speaker_label = ""
                    if line.get("speaker") == -2:
                        speaker_label = "🔇 [静音]"
                    elif line.get("speaker") == -1:
                        speaker_label = "👤 [说话者 1]"
                    elif line.get("speaker", 0) > 0:
                        speaker_label = f"👤 [说话者 {line['speaker']}]"
                    
                    # 时间信息
                    time_info = ""
                    if line.get("beg") is not None and line.get("end") is not None:
                        time_info = f" ({line['beg']:.1f}s-{line['end']:.1f}s)"
                    
                    text = line.get("text", "").strip()
                    if text:
                        print(f"  {speaker_label}{time_info}: {text}")
            
            # 显示预览转录（实时）
            if buffer_transcription.strip():
                print(f"\n🔄 实时预览: {buffer_transcription}")
        
        # 显示状态信息
        remaining_transcription = data.get("remaining_time_transcription", 0)
        remaining_diarization = data.get("remaining_time_diarization", 0)
        
        status_lines = []
        if remaining_transcription > 0:
            status_lines.append(f"⏳ 转录延迟: {remaining_transcription:.1f}s")
        if remaining_diarization > 0:
            status_lines.append(f"⏳ 说话者识别延迟: {remaining_diarization:.1f}s")
        
        if status_lines:
            print("\n" + " | ".join(status_lines))
        
        print("=" * 80)

    async def receive_messages(self):
        """接收并处理 WebSocket 消息"""
        try:
            while not self.should_stop and self.websocket and not self.websocket.closed:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    
                    # 尝试解析 JSON
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        logger.warning(f"收到非JSON消息: {message}")
                        continue
                    
                    # 处理特殊消息类型
                    if data.get("type") == "ready_to_stop":
                        logger.info("🛑 服务器准备停止")
                        break
                    
                    # 显示转录结果
                    await self.display_transcription(data)
                    
                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebSocket 连接已关闭")
                    break
                except Exception as e:
                    logger.warning(f"接收消息时出错: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"接收消息处理器出错: {e}")

    async def send_audio_loop(self):
        """音频发送循环"""
        logger.info("🎙️ 开始录音...")
        
        try:
            while not self.should_stop and self.websocket and not self.websocket.closed:
                try:
                    # 读取音频数据
                    audio_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    if len(audio_data) == 0:
                        continue
                    
                    # 直接发送原始音频数据 (类似于 MediaRecorder 的输出)
                    await self.websocket.send(audio_data)
                    
                except Exception as e:
                    logger.warning(f"发送音频数据时出错: {e}")
                    break
                
                # 短暂延迟
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"音频发送循环出错: {e}")

    async def run(self):
        """主运行方法"""
        logger.info("🚀 启动 WhisperLiveKit 客户端")
        
        # 连接 WebSocket
        if not await self.connect_websocket():
            return False
            
        # 启动音频流
        if not self.start_audio_stream():
            await self.cleanup()
            return False
        
        # 显示初始界面
        print("\n" + "=" * 80)
        print("🎤 实时语音转录已启动")
        print("请开始说话，转录结果将实时显示")
        print("按 Ctrl+C 停止")
        print("=" * 80 + "\n")
        
        try:
            # 创建并发任务
            receive_task = asyncio.create_task(self.receive_messages())
            send_task = asyncio.create_task(self.send_audio_loop())
            
            # 等待任务完成
            done, pending = await asyncio.wait(
                [receive_task, send_task], 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 取消未完成的任务
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except KeyboardInterrupt:
            logger.info("👋 用户中断程序")
        except Exception as e:
            logger.error(f"❌ 运行时出错: {e}")
        finally:
            await self.cleanup()
            
        return True

    async def cleanup(self):
        """清理资源"""
        logger.info("🧹 正在清理资源...")
        
        self.should_stop = True
        
        # 发送停止信号
        if self.websocket and not self.websocket.closed:
            try:
                # 发送空数据作为停止信号
                empty_data = b''
                await self.websocket.send(empty_data)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.debug(f"发送停止信号失败: {e}")
        
        # 关闭音频流
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.debug(f"关闭音频流失败: {e}")
        
        # 关闭 PyAudio
        if self.audio:
            try:
                self.audio.terminate()
            except Exception as e:
                logger.debug(f"终止 PyAudio 失败: {e}")
        
        # 关闭 WebSocket
        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.debug(f"关闭 WebSocket 失败: {e}")
        
        logger.info("✅ 资源清理完成")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="WhisperLiveKit 实时语音转录客户端",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python simple_mic_to_asr.py                    # 连接到本地服务器
  python simple_mic_to_asr.py --host 192.168.1.100  # 连接到远程服务器
  
注意:
  - 请确保 WhisperLiveKit 服务器正在运行
  - 启动服务器: whisperlivekit-server --model tiny.en
        """
    )
    
    parser.add_argument("--host", default="localhost", 
                       help="WhisperLiveKit 服务器地址 (默认: localhost)")
    parser.add_argument("--port", type=int, default=8000, 
                       help="WhisperLiveKit 服务器端口 (默认: 8000)")
    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_arguments()
    
    print("🎯 WhisperLiveKit 实时语音转录客户端")
    print(f"🌐 连接目标: {args.host}:{args.port}")
    
    streamer = SimpleMicrophoneStreamer(host=args.host, port=args.port)
    
    success = await streamer.run()
    if success:
        print("\n✅ 程序正常结束")
    else:
        print("\n❌ 程序异常结束")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        logger.error(f"❌ 程序出现未处理异常: {e}")
        sys.exit(1)