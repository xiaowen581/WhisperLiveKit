#!/usr/bin/env python3
"""
实时麦克风音频转录脚本
从麦克风持续捕获音频，实时传给 WhisperLiveKit 的 /asr 端点进行语音识别处理。

使用方法:
    python mic_to_asr.py

可选参数:
    --host: 服务器地址 (默认: localhost)
    --port: 服务器端口 (默认: 8000)
    --chunk-duration: 音频块持续时间，毫秒 (默认: 1000)
    --sample-rate: 采样率 (默认: 16000)
    --channels: 声道数 (默认: 1)
"""

import asyncio
import argparse
import json
import logging
import signal
import sys
import threading
import time
from typing import Optional

import pyaudio
import websockets
import numpy as np


# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MicrophoneAudioStreamer:
    """麦克风音频流处理器"""
    
    def __init__(self, host: str = "localhost", port: int = 8000, 
                 chunk_duration: int = 1000, sample_rate: int = 16000, channels: int = 1):
        self.host = host
        self.port = port
        self.chunk_duration = chunk_duration  # 毫秒
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = int(sample_rate * chunk_duration / 1000)  # 每块的采样数
        
        # WebSocket 连接
        self.websocket_url = f"ws://{host}:{port}/asr"
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        
        # PyAudio 设置
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        
        # 控制变量
        self.is_recording = False
        self.should_stop = False
        
        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """处理终止信号"""
        logger.info("接收到终止信号，正在停止...")
        self.should_stop = True

    def list_audio_devices(self):
        """列出所有可用的音频设备"""
        logger.info("可用的音频输入设备:")
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                logger.info(f"  设备 {i}: {device_info['name']} "
                          f"(最大输入声道: {device_info['maxInputChannels']}, "
                          f"默认采样率: {device_info['defaultSampleRate']})")

    async def connect_websocket(self):
        """连接到 WhisperLiveKit WebSocket 服务"""
        try:
            logger.info(f"正在连接到 {self.websocket_url}")
            self.websocket = await websockets.connect(self.websocket_url)
            logger.info("WebSocket 连接成功")
            return True
        except Exception as e:
            logger.error(f"WebSocket 连接失败: {e}")
            return False

    def start_audio_stream(self):
        """启动音频流"""
        try:
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            logger.info(f"音频流已启动 (采样率: {self.sample_rate}Hz, 声道: {self.channels}, "
                       f"块大小: {self.chunk_size} 采样)")
            return True
        except Exception as e:
            logger.error(f"启动音频流失败: {e}")
            return False

    def audio_to_webm_like_bytes(self, audio_data: np.ndarray) -> bytes:
        """
        将音频数据转换为可以发送的字节格式
        这里我们简化处理，直接发送 PCM 数据
        在实际应用中，WhisperLiveKit 期望 WebM 格式，但也可以处理原始音频数据
        """
        # 确保数据在 [-1, 1] 范围内
        audio_data = np.clip(audio_data, -1.0, 1.0)
        
        # 转换为 16-bit PCM
        audio_16bit = (audio_data * 32767).astype(np.int16)
        
        return audio_16bit.tobytes()

    async def send_audio_chunk(self, audio_data: bytes):
        """发送音频块到 WebSocket"""
        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.send(audio_data)
            except Exception as e:
                logger.warning(f"发送音频数据失败: {e}")

    async def receive_transcriptions(self):
        """接收并显示转录结果"""
        try:
            while not self.should_stop and self.websocket and not self.websocket.closed:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if data.get("type") == "ready_to_stop":
                        logger.info("服务器准备停止")
                        break
                    
                    # 处理转录结果
                    self.display_transcription(data)
                    
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    logger.warning(f"收到无效的 JSON 数据: {message}")
                except Exception as e:
                    logger.warning(f"接收消息时出错: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"接收转录结果时出错: {e}")

    def display_transcription(self, data: dict):
        """显示转录结果"""
        lines = data.get("lines", [])
        buffer_transcription = data.get("buffer_transcription", "")
        status = data.get("status", "")
        
        # 清屏并显示当前转录内容
        print("\033[2J\033[H", end="")  # 清屏并移动光标到顶部
        print("=" * 80)
        print("实时语音转录 (按 Ctrl+C 停止)")
        print("=" * 80)
        
        if status == "no_audio_detected":
            print("\n[信息] 未检测到音频...")
        else:
            # 显示已确认的转录行
            for i, line in enumerate(lines):
                speaker_info = ""
                if line.get("speaker") == -2:
                    speaker_info = "[静音]"
                elif line.get("speaker") == -1:
                    speaker_info = "[说话者 1]"
                elif line.get("speaker", 0) > 0:
                    speaker_info = f"[说话者 {line['speaker']}]"
                
                time_info = ""
                if line.get("beg") is not None and line.get("end") is not None:
                    time_info = f" ({line['beg']:.1f}s - {line['end']:.1f}s)"
                
                text = line.get("text", "")
                if text.strip():
                    print(f"{speaker_info}{time_info}: {text}")
                
            # 显示缓冲区中的转录（预览）
            if buffer_transcription.strip():
                print(f"\n[预览] {buffer_transcription}")
        
        print("\n" + "=" * 80)
        
        # 显示状态信息
        remaining_transcription = data.get("remaining_time_transcription", 0)
        remaining_diarization = data.get("remaining_time_diarization", 0)
        
        if remaining_transcription > 0:
            print(f"转录延迟: {remaining_transcription:.1f}秒")
        if remaining_diarization > 0:
            print(f"说话者识别延迟: {remaining_diarization:.1f}秒")

    async def stream_audio(self):
        """音频流处理主循环"""
        logger.info("开始音频流传输...")
        self.is_recording = True
        
        try:
            while not self.should_stop and self.stream and self.websocket:
                if self.websocket.closed:
                    break
                    
                # 读取音频数据
                try:
                    audio_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # 转换为 numpy 数组
                    audio_array = np.frombuffer(audio_data, dtype=np.float32)
                    
                    # 检查音频数据是否有效
                    if len(audio_array) == 0:
                        continue
                    
                    # 转换为字节格式并发送
                    audio_bytes = self.audio_to_webm_like_bytes(audio_array)
                    await self.send_audio_chunk(audio_bytes)
                    
                except Exception as e:
                    logger.warning(f"读取音频数据时出错: {e}")
                    
                # 小延迟以避免过于频繁的发送
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error(f"音频流处理出错: {e}")
        finally:
            self.is_recording = False
            logger.info("音频流传输已停止")

    async def run(self):
        """主运行方法"""
        # 列出可用设备
        self.list_audio_devices()
        
        # 连接 WebSocket
        if not await self.connect_websocket():
            return False
            
        # 启动音频流
        if not self.start_audio_stream():
            return False
            
        logger.info("开始实时语音转录...")
        print("\n开始录音... 按 Ctrl+C 停止\n")
        
        try:
            # 创建并启动任务
            receive_task = asyncio.create_task(self.receive_transcriptions())
            stream_task = asyncio.create_task(self.stream_audio())
            
            # 等待任务完成或中断
            await asyncio.gather(receive_task, stream_task, return_exceptions=True)
            
        except KeyboardInterrupt:
            logger.info("用户中断")
        except Exception as e:
            logger.error(f"运行时出错: {e}")
        finally:
            await self.cleanup()
            
        return True

    async def cleanup(self):
        """清理资源"""
        logger.info("正在清理资源...")
        
        self.should_stop = True
        self.is_recording = False
        
        # 发送停止信号到服务器
        if self.websocket and not self.websocket.closed:
            try:
                # 发送空的音频数据作为停止信号
                await self.websocket.send(b'')
                await asyncio.sleep(0.1)  # 给服务器一点时间处理
            except Exception as e:
                logger.warning(f"发送停止信号失败: {e}")
        
        # 关闭音频流
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            except Exception as e:
                logger.warning(f"关闭音频流失败: {e}")
        
        # 关闭 PyAudio
        if self.audio:
            try:
                self.audio.terminate()
                self.audio = None
            except Exception as e:
                logger.warning(f"终止 PyAudio 失败: {e}")
        
        # 关闭 WebSocket
        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.close()
                self.websocket = None
            except Exception as e:
                logger.warning(f"关闭 WebSocket 失败: {e}")
        
        logger.info("资源清理完成")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="实时麦克风音频转录脚本")
    parser.add_argument("--host", default="localhost", help="WhisperLiveKit 服务器地址")
    parser.add_argument("--port", type=int, default=8000, help="WhisperLiveKit 服务器端口")
    parser.add_argument("--chunk-duration", type=int, default=1000, 
                       help="音频块持续时间（毫秒）")
    parser.add_argument("--sample-rate", type=int, default=16000, 
                       help="音频采样率（Hz）")
    parser.add_argument("--channels", type=int, default=1, 
                       help="音频声道数")
    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_arguments()
    
    streamer = MicrophoneAudioStreamer(
        host=args.host,
        port=args.port,
        chunk_duration=args.chunk_duration,
        sample_rate=args.sample_rate,
        channels=args.channels
    )
    
    success = await streamer.run()
    if success:
        logger.info("程序正常结束")
    else:
        logger.error("程序异常结束")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序出现未处理的异常: {e}")
        sys.exit(1)