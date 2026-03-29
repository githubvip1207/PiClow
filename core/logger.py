import time
import sys

_last_is_inline = False

def log(message, end="\n"):
    """
    统一的日志打印方法，自动附加时间戳。
    对于带有 \r 的原地刷新打印，会将时间戳放在 \r 后面。
    """
    global _last_is_inline
    msg_str = str(message)
    time_str = time.strftime('%Y-%m-%d %H:%M:%S')

    if msg_str.startswith("\r"):
        # \033[K 用于清除光标到行尾的内容，防止较短日志覆盖较长日志时残留字符
        sys.stdout.write(f"\r[{time_str}] {msg_str[1:]}\033[K{end}")
        sys.stdout.flush()
        _last_is_inline = (end == "")
    else:
        # 如果上一次输出了不换行的 inline 日志，则在写入新日志前先换行
        prefix = "\n" if _last_is_inline else ""
        sys.stdout.write(f"{prefix}[{time_str}] {msg_str}{end}")
        sys.stdout.flush()
        _last_is_inline = (end == "")
