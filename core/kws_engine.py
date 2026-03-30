import time
import sherpa_onnx
import sounddevice as sd
import config
from core.logger import log

class KWSEngine:
    def __init__(self):
        try:
            self.kws = sherpa_onnx.KeywordSpotter(
                tokens=f"{config.KWS_MODEL_PATH}/tokens.txt",                                   # 模型字典文件路径
                encoder=f"{config.KWS_MODEL_PATH}/encoder-epoch-12-avg-2-chunk-16-left-64.onnx",# 编码器模型路径
                decoder=f"{config.KWS_MODEL_PATH}/decoder-epoch-12-avg-2-chunk-16-left-64.onnx",# 解码器模型路径
                joiner=f"{config.KWS_MODEL_PATH}/joiner-epoch-12-avg-2-chunk-16-left-64.onnx",  # 连接器模型路径
                num_threads=1,                                                                  # 使用的线程数量
                feature_dim=80,                                                                 # 语音特征维度
                sample_rate=config.SAMPLE_RATE,                                                 # 音频采样率
                keywords_file=f"{config.KWS_MODEL_PATH}/keywords.txt"                           # 唤醒词文件路径
            )
            log("✅ 唤醒引擎已就绪")
        except Exception as e:
            log(f"❌ 唤醒引擎启动失败: {e}")
            self.kws = None

    # 等待唤醒
    def wait_wake(self, stop_event=None):
        if not self.kws:
            log("唤醒引擎未正确初始化。")
            while not (stop_event and stop_event.is_set()):
                time.sleep(1)
            return False
            
        log("⏸️ 等待唤醒：龙虾老师")
        stream = self.kws.create_stream()           # 创建语音数据流对象
        chunk = int(0.1 * config.SAMPLE_RATE)       # 设置每次读取的音频数据大小（0.1秒）
        
        try:
            with sd.InputStream(samplerate=config.SAMPLE_RATE, channels=1, dtype="float32") as s:
                while True:
                    if stop_event and stop_event.is_set():
                        return False
                        
                    samples, _ = s.read(chunk)                                      # 读取一块音频数据
                    stream.accept_waveform(config.SAMPLE_RATE, samples.reshape(-1)) # 将音频数据送入识别流
                    
                    while self.kws.is_ready(stream):                                # 当识别器准备好时进行解码
                        try:
                            self.kws.decode_stream(stream)
                        except:
                            self.kws.decode(stream)
                    if self.kws.get_result(stream):                                 # 判断是否检测到唤醒词
                        log("✅ 已唤醒！")
                        return True
        except Exception as e:
            log(f"麦克风读取错误: {e}")
            time.sleep(2)
            return False
