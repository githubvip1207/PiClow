import os
import sys
import time
import asyncio
import threading
import signal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import IDLE_EXIT_SECONDS, EXIT_KEYWORDS
from core.kws_engine import KWSEngine
from core.asr_engine import ASREngine
from core.audio_io import AudioIO
from core.tts_engine import TTSEngine
from core.chat_engine import ChatClient
from core.logger import log

# 全局退出事件
stop_event = threading.Event()

def signal_handler(sig, frame):
    log("🛑 收到退出信号，正在安全关闭服务...")
    stop_event.set()

async def main():
    log("🚀 启动服务...")
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    except Exception:
        pass

    # 初始化各引擎模块
    kws = KWSEngine()
    asr = ASREngine()
    chat = ChatClient()
    
    # 初始化连接时间缓冲
    log("⏳ 等待云端 WebSocket 连接初始化...")
    chat.wait_for_ready(timeout=10)

    while not stop_event.is_set():
        
        if not kws.wait_wake(stop_event):  # 等待唤醒
            if stop_event.is_set():        # 被中断或者出错
                break
            time.sleep(1)
            continue
            
        await TTSEngine.speak("我在呢！")
        last_active = time.time()
        
        while not stop_event.is_set():                          # 连续多次多轮对话
            log("🗣️ 开始录音")
            audio = AudioIO.record(stop_event)                  # 智能停顿侦测录音
            if not audio:
                if stop_event.is_set():
                    break
                last_active -= 5                                # 空白超时直接退出当前多轮对话
                
            log("🗣️ 录音结束")
            text = asr.recognize(audio) if audio else ""        # 推理获得文字
            log(f"🗣️ 你说: {text}")
            
            if text.strip():
                last_active = time.time()
                if any(k in text for k in EXIT_KEYWORDS):       # 用户主动说退出
                    log("🔊 开始说话")
                    await TTSEngine.speak("好的，退下了！")
                    log("🔊 说话结束")
                    break
                log("⏳ 正在请求云端大模型...")
                reply = chat.send(text)                         # 请求云端大模型并播放返回对话
                log(f"☁️ 云端返回: {reply}")
                log("🔊 开始说话")
                await TTSEngine.speak(reply)
                log("🔊 说话结束")
            #else:
            #    if audio:                                       # 有音频但是没识别出文字
            #        log("🔊 开始说话")
            #        await TTSEngine.speak("我没听清哦")
            #        log("🔊 说话结束")
            if time.time() - last_active >= IDLE_EXIT_SECONDS:  # 超时时间不说话，主动退下
                log("🔊 开始说话")
                await TTSEngine.speak("长时间未说话，我退下啦")
                log("🔊 说话结束")
                break
                
    log("🧹 停止 WebSocket 客户端线程...")                      # 收到结束信号的大扫除
    chat.stop()
    log("✋ 服务已安全退出")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("🛑 被用户强行中断。")
        stop_event.set()
