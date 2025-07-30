#!/usr/bin/env python3
"""
WhisperLiveKit 客户端演示脚本
展示如何使用不同的配置选项
"""

import subprocess
import sys
import time

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"命令: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"返回码: {result.returncode}")
        if result.stdout:
            print(f"输出:\n{result.stdout}")
        if result.stderr:
            print(f"错误:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        print("⏰ 命令超时（这对于网络连接测试是正常的）")
    except Exception as e:
        print(f"❌ 执行出错: {e}")

def main():
    """主演示函数"""
    print("🎯 WhisperLiveKit 客户端脚本演示")
    print("本演示展示各种脚本的帮助信息和基本功能")
    
    # 检查Python环境
    run_command([sys.executable, "--version"], "检查Python版本")
    
    # 检查依赖
    run_command([sys.executable, "-c", 
                "import pyaudio, websockets, asyncio; print('✅ 所有必需依赖已安装')"], 
                "检查依赖安装")
    
    # 显示简化版客户端帮助
    run_command([sys.executable, "simple_mic_to_asr.py", "--help"], 
                "简化版客户端帮助信息")
    
    # 显示完整版客户端帮助
    run_command([sys.executable, "mic_to_asr.py", "--help"], 
                "完整版客户端帮助信息")
    
    # 测试连接（会很快失败，因为没有服务器运行）
    run_command([sys.executable, "check_connection.py"], 
                "测试WebSocket连接（预期失败）")
    
    # 语法检查
    run_command([sys.executable, "-m", "py_compile", "simple_mic_to_asr.py"], 
                "简化版客户端语法检查")
    
    run_command([sys.executable, "-m", "py_compile", "mic_to_asr.py"], 
                "完整版客户端语法检查")
    
    run_command([sys.executable, "-m", "py_compile", "check_connection.py"], 
                "连接测试脚本语法检查")
    
    print(f"\n{'='*60}")
    print("✅ 演示完成!")
    print("📖 要查看详细使用说明，请阅读 README_CLIENT.md")
    print("🚀 要开始使用，请先启动 WhisperLiveKit 服务器:")
    print("   whisperlivekit-server --model tiny.en")
    print("然后运行客户端:")
    print("   python simple_mic_to_asr.py")
    print('='*60)

if __name__ == "__main__":
    main()