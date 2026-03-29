import numpy as np
import wave
import sounddevice as sd
import config 
from core.logger import log

class AudioIO:
    @staticmethod
    def record(stop_event=None):
        log("🎤 说话中...")
        chunk_size = int(config.SAMPLE_RATE * 0.1)  # 每次读取0.1秒的音频块
        audio_chunks = []                           # 存储所有音频片段
        silent_count = 0                            # 静音计数
        wait_count = 0                              # 等待说话的计数器
        speaking = False                            # 是否正在说话的标记

        try:
            # 打开麦克风输入流，开始录音
            with sd.InputStream(samplerate=config.SAMPLE_RATE, channels=1, dtype="float32") as stream:
                while True:
                    if stop_event and stop_event.is_set():
                        log("🛑 录音被中断")
                        return None
                        
                    chunk, _ = stream.read(chunk_size)   # 读取一块音频数据
                    volume = np.abs(chunk).mean()        # 计算音量
                    chunk = chunk.reshape(-1)            # 展平数组
                    audio_chunks.append(chunk)           # 保存音频片段

                    if config.DEBUG:
                        status = "🎤 说话中" if speaking else "💤 监听中"
                        log(f"\r{status} | 当前音量: {volume:.4f} | 当前阈值: {config.SILENCE_THRESHOLD}", end="")

                    # 计算当前音频块的音量
                    if volume > config.SILENCE_THRESHOLD:
                        speaking = True                  # 检测到说话
                        silent_count = 0                 # 清空静音计数
                    else:                               
                        if speaking:                    
                            silent_count += 1            # 说话后检测到静音，计数+1
                        else:                           
                            wait_count += 1              # 还没开口，等待计数+1

                    # 说话结束且静音超时，退出录音
                    if speaking and silent_count >= config.SILENCE_LIMIT:
                        break

                    # 唤醒后一直不说话超时兜底
                    if not speaking and wait_count >= config.MAX_WAIT_CHUNKS:
                        log("⏳ 等待说话超时，退出本次录音")
                        return None
        except Exception as e:
            log(f"❌ 录音错误: {e}")
            return None

        audio = np.concatenate(audio_chunks)            # 拼接所有音频片段
        audio = np.clip(audio, -1, 1)                   # 限制音频范围防止溢出

        with wave.open(config.WAV_TEMP, "wb") as wf:
            wf.setnchannels(1)                          # 单声道
            wf.setsampwidth(2)                          # 16位采样
            wf.setframerate(config.SAMPLE_RATE)         # 设置采样率
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())

        return config.WAV_TEMP
