#!/usr/bin/env python3
"""
测试脚本 - 验证与 WhisperLiveKit 服务器的连接
这个脚本不使用麦克风，只测试 WebSocket 连接功能
"""

import asyncio
import json
import logging
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_connection(host="localhost", port=8000):
    """测试 WebSocket 连接"""
    websocket_url = f"ws://{host}:{port}/asr"
    
    try:
        logger.info(f"尝试连接到 {websocket_url}")
        
        async with websockets.connect(websocket_url) as websocket:
            logger.info("✅ WebSocket 连接成功!")
            
            # 发送测试数据（空音频数据）
            logger.info("发送测试数据...")
            await websocket.send(b'')
            
            # 尝试接收响应
            logger.info("等待服务器响应...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"✅ 收到服务器响应: {response}")
                
                # 尝试解析 JSON
                try:
                    data = json.loads(response)
                    logger.info(f"✅ JSON 解析成功: {data}")
                except json.JSONDecodeError:
                    logger.info(f"⚠️  响应不是 JSON 格式: {response}")
                    
            except asyncio.TimeoutError:
                logger.info("⚠️  5秒内未收到响应，这可能是正常的")
            
            logger.info("测试完成")
            
    except ConnectionRefusedError:
        logger.error("❌ 连接被拒绝 - 请确保 WhisperLiveKit 服务器正在运行")
        logger.error("   启动命令: whisperlivekit-server --model tiny.en")
        return False
    except Exception as e:
        logger.error(f"❌ 连接测试失败: {e}")
        return False
    
    return True

async def main():
    """主函数"""
    print("🧪 WhisperLiveKit WebSocket 连接测试")
    print("=" * 50)
    
    success = await test_websocket_connection()
    
    if success:
        print("\n✅ 连接测试成功!")
        print("现在你可以运行实际的麦克风转录脚本:")
        print("  python simple_mic_to_asr.py")
    else:
        print("\n❌ 连接测试失败!")
        print("请检查:")
        print("1. WhisperLiveKit 服务器是否已启动")
        print("2. 服务器地址和端口是否正确")
        print("3. 防火墙设置")

if __name__ == "__main__":
    asyncio.run(main())