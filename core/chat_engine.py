import json                                    
import uuid                                    
import time                                    
import config 
import websocket                               
import threading                               
from threading import Event                    
from core.logger import log

class ChatClient:
    def __init__(self):
        self.ws = None                           # WebSocket 连接对象
        self.connected = Event()                 # 认证成功标志，用于线程同步
        self.reply = []                          # 收集 agent 回复的文本片段（流式拼接）
        self.done = Event()                      # 回复完成标志，用于等待回复结束
        self.lock = threading.Lock()             # 线程锁，防止并发发送冲突
        self.running = False                     # 客户端运行状态
        self._thread = None                      # 运行 WebSocket 的后台线程
        
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, daemon=True) # 守护线程
            self._thread.start()

    def on_open(self, ws):
        log("[OpenClaw] 连接成功，等待认证...")

    def on_msg(self, ws, msg):
        data = json.loads(msg)                   # 解析 JSON 消息
        evt = data.get("event")                  # 获取事件类型
        typ = data.get("type")                   # 获取消息类型

        # ---- 处理认证：服务端发来 nonce，客户端必须回应 ----
        if evt == "connect.challenge":
            ws.send(json.dumps({                 # 构造并发送 connect 请求
                "type": "req",                   # 消息类型：请求
                "id": str(uuid.uuid4()),         # 请求唯一 ID，用于匹配响应
                "method": "connect",             # 方法名：连接认证
                "params": {                      # 请求参数
                    "minProtocol": 3,            # 最低协议版本（服务端要求）
                    "maxProtocol": 3,            # 最高协议版本（服务端要求）
                    "client": {                  # 客户端信息
                        "id": "cli",             # 客户端标识，必须是预定义值之一
                        "mode": "cli",           # 客户端模式
                        "platform": "linux",     # 运行平台
                        "version": "1.0.0"       # 客户端版本
                    },
                    "auth": {"token": config.OPENCLAW_TOKEN},   # 认证凭据
                    "role": "operator",                         # 角色：操作员
                    "scopes": ["operator.admin"]                # 权限范围：管理员权限
                }
            }))
        
        # ---- 处理请求响应：connect 或 chat.send 的返回结果 ----
        elif typ == "res":
            if data.get("ok") and not self.connected.is_set():  # 认证成功且未设置过标志
                self.connected.set()                            # 设置认证成功标志，唤醒等待线程
                log("[OpenClaw] 认证成功！")
        
        # ---- 处理聊天事件：agent 的流式回复 ----
        elif typ == "event" and evt == "chat":
            payload = data.get("payload", {})                   # 获取事件载荷
            state = payload.get("state")                        # 获取状态：delta=增量更新，final=最终完成
            
            if state == "delta":                                # 增量更新：agent 正在逐字输出
                msg_obj = payload.get("message", {})            # 获取消息对象
                for c in msg_obj.get("content", []):            # 遍历内容块（支持多模态）
                    if c.get("type") == "text":                 # 只处理文本类型
                        self.reply.append(c.get("text", ""))    # 收集文本（非增量全量）
            elif state == "final":                              # 最终完成：agent 回复结束
                self.done.set()                                 # 设置完成标志，唤醒等待线程

    def on_close(self, ws, close_status_code, close_msg):
        log("[OpenClaw] 连接已断开")
        self.connected.clear()                   # 清除认证成功标志

    def on_error(self, ws, error):
        log(f"[OpenClaw] WebSocket错误: {error}")
        self.connected.clear()                   # 异常断开，清除认证标志

    def _run(self):
        self.running = True
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(        # 创建 WebSocket 客户端实例
                    config.OPENCLAW_URL,                 # 连接地址
                    on_open=self.on_open,                # 连接建立回调
                    on_message=self.on_msg,              # 收到消息回调
                    on_error=self.on_error,              # 错误回调
                    on_close=self.on_close               # 关闭回调
                )
                self.ws.run_forever()                    # 启动事件循环，阻塞直到断开
            except Exception as e:
                log(f"[OpenClaw] 运行异常: {e}")
            
            # 若仍处于 running 状态则说明是意外断开，尝试重连
            if self.running:
                log("[OpenClaw] 5秒后尝试重连...")
                time.sleep(5)
            
    def wait_for_ready(self, timeout=10):
        return self.connected.wait(timeout=timeout)
        
    def send(self, message):
        if not self.connected.is_set():
            log("[OpenClaw] 当前未连接，尝试重连中，请稍后再试...")
            return "[网络未连接，请稍后再试]"
            
        with self.lock:                                         # 加锁，防止多线程并发发送
            self.reply = []                                     # 清空上次回复
            self.done.clear()                                   # 重置完成标志
            try:
                self.ws.send(json.dumps({                       # 构造并发送 chat.send 请求
                    "type": "req",                              # 消息类型：请求
                    "id": str(uuid.uuid4()),                    # 请求唯一 ID
                    "method": "chat.send",                      # 方法名：发送聊天消息
                    "params": {
                        "sessionKey": config.OPENCLAW_SESSION,         # 会话标识，相同 key 保持上下文
                        "message": message,                     # 用户消息内容
                        "idempotencyKey": str(uuid.uuid4())     # 幂等键，防止重复发送
                    }
                }))
            except Exception as e:
                log(f"[OpenClaw] 发送失败: {e}")
                self.connected.clear()                          # 发送失败则认为连接已断开
                return "[发送失败]"
                
        
        if self.done.wait(timeout=120):                         # 等待回复完成，最多 120 秒
            return self.reply[-1] if self.reply else ""         # 返回最后一版完整文本
        return "[请求超时]"                                      # 超时返回提示

    def stop(self):
        self.running = False                                    # 取消运行标志，阻止重连
        if self.ws:
            self.ws.close()                                     # 主动关闭底层 WebSocket 连接
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)                        # 等待线程结束退出
