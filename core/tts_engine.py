import os
import asyncio
import edge_tts
from core.logger import log

class TTSEngine:
    @staticmethod
    async def speak(text):
        if not text:
            return
        log(f"🔊 {text}")
        f = "/tmp/tts_output.mp3"
        try:
            communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
            await communicate.save(f)
            # 使用 mpg123 播放，不展示额外终端输出
            os.system(f"mpg123 -q {f}")
        except Exception as e:
            log(f"❌ TTS播报失败: {e}")
            
    @staticmethod
    def speak_sync(text):
        asyncio.run(TTSEngine.speak(text))
