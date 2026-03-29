# openclaw_bot/config.py
import os

MODELS_DIR = "/home/pi/PiClow/models"
DEBUG = True                      

# ==================== OpenClaw 配置 ====================
OPENCLAW_URL = "wss://openclaw.tailf3cca.ts.net"
OPENCLAW_TOKEN = "c6205bad8df577a6849e8"
OPENCLAW_SESSION = "agent:tutor:pi-chat"

# ======================= 唤醒配置 =======================
IDLE_EXIT_SECONDS = 2 * 60        # 2分钟无对话自动退出对话
EXIT_KEYWORDS = ["退出", "结束", "再见", "拜拜", "关闭"]
KWS_MODEL_PATH = os.path.join(MODELS_DIR, "sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01")                  # 唤醒词模型

# ======================= 智能录音 =======================
WAV_TEMP = "/tmp/record_temp.wav"
SAMPLE_RATE = 16000               # 录音采样率，标准16000Hz
SILENCE_THRESHOLD = 0.04          # 判断静音的音量阈值
SILENCE_LIMIT = 15                # 说完话后连续静音的次数，超时退出。*0.1 是对应时间
MAX_WAIT_CHUNKS = 200             # 唤醒后未说话的次数，超时退出。*0.1 是对应时间

# ======================= 语音识别 =======================
ACTIVE_ASR = "sherpa_small"       # 可选: whisper / sherpa_small / sherpa_big
SHERPA_SMALL_MODEL = os.path.join(MODELS_DIR, "sherpa-onnx-streaming-zipformer-small-bilingual-zh-en-2023-02-16")   # 离线语音识别基础模型
SHERPA_BIG_MODEL = os.path.join(MODELS_DIR, "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20")           # 离线语音识别完整模型