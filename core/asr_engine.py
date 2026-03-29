import wave
import config 
import numpy as np
import sherpa_onnx
from faster_whisper import WhisperModel
from core.logger import log

class ASREngine:
    def __init__(self):
        self.model = None
        try:
            if config.ACTIVE_ASR == "whisper":
                self.model = WhisperModel("small", device="cpu", compute_type="int8") # 加载模型
                log("✅ Whisper ASR 引擎已就绪")
                
            elif config.ACTIVE_ASR in ["sherpa_small", "sherpa_big"]:
                model_dir = config.SHERPA_SMALL_MODEL if config.ACTIVE_ASR == "sherpa_small" else config.SHERPA_BIG_MODEL
                self.model = sherpa_onnx.OnlineRecognizer.from_transducer(
                    encoder=f"{model_dir}/encoder-epoch-99-avg-1.onnx",   # 编码器模型路径
                    decoder=f"{model_dir}/decoder-epoch-99-avg-1.onnx",   # 解码器模型路径
                    joiner=f"{model_dir}/joiner-epoch-99-avg-1.onnx",     # 连接器模型路径
                    tokens=f"{model_dir}/tokens.txt",                     # 字典文件路径
                    num_threads=4,                                        # 线程数
                    feature_dim=80,                                       # 语音特征维度
                    sample_rate=config.SAMPLE_RATE,                       # 采样率
                    decoding_method="greedy_search",                      # 解码方式
                    max_active_paths=1                                    # 最小搜索路径，进一步降低耗时
                )
                log(f"✅ Sherpa ASR ({config.ACTIVE_ASR}) 引擎已就绪")
        except Exception as e:
            log(f"❌ ASR 启动失败: {e}")

    def recognize(self, audio_file):
        if not self.model or not audio_file:
            return ""
            
        if config.ACTIVE_ASR == "whisper":
            segs, _ = self.model.transcribe(audio_file, language="zh")  # 执行音频转文字
            return "".join(s.text for s in segs).strip()                # 拼接识别结果并返回
            
        elif config.ACTIVE_ASR in ["sherpa_small", "sherpa_big"]:
            try:
                with wave.open(audio_file, "rb") as wf:
                    samples = np.frombuffer(wf.readframes(-1), dtype=np.int16).astype(np.float32) / 32768.0
                
                stream = self.model.create_stream()                     # 创建识别流
                stream.accept_waveform(config.SAMPLE_RATE, samples)    
                
                while self.model.is_ready(stream):                      # 循环解码音频流
                    self.model.decode_stream(stream)
                return self.model.get_result(stream).strip()            # 返回识别结果
            except Exception as e:
                log(f"❌ 识别报错：{e}")
                return ""
        return ""
