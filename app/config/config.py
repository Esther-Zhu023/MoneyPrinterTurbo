# app/config/config.py

import os
import shutil
import time
import socket
import logging

# 依赖第三方 toml 库。如果用 Python 3.11+ 且想用标准库，可改为 tomllib 并调整 API。
try:
    import toml  # pip install toml
except ImportError:
    raise ImportError("Missing dependency 'toml'. Please install via: pip install toml")

logger = logging.getLogger("MoneyPrinterTurbo.config")
logger.setLevel(logging.INFO)


def safe_remove_path(path: str, retries: int = 3, delay_sec: float = 0.5) -> None:
    """
    安全删除路径：
    - 软链接：os.unlink
    - 普通文件：os.remove
    - 目录：shutil.rmtree
    对常见的“设备或资源忙”(EBUSY)做有限重试。
    """
    if not os.path.exists(path) and not os.path.islink(path):
        return

    for attempt in range(1, retries + 1):
        try:
            if os.path.islink(path):
                os.unlink(path)
                return
            if os.path.isfile(path):
                os.remove(path)
                return
            if os.path.isdir(path):
                shutil.rmtree(path)
                return
            # 兜底：尝试 unlink
            os.unlink(path)
            return
        except OSError as e:
            # 16: EBUSY, 26: ETXTBSY, 30: EROFS
            if attempt < retries and e.errno in (16, 26, 30):
                time.sleep(delay_sec)
                continue
            raise


def _default_config_text() -> str:
    return """# MoneyPrinterTurbo config
log_level = "DEBUG"
listen_host = "0.0.0.0"
listen_port = 8080
project_name = "MoneyPrinterTurbo"
project_description = "<a href='https://github.com/harry0703/MoneyPrinterTurbo'>https://github.com/harry0703/MoneyPrinterTurbo</a>"
project_version = "1.2.6"

[app]
imagemagick_path = ""
ffmpeg_path = ""

[ui]
hide_log = false
"""


def _config_paths() -> tuple[str, str]:
    """
    统一定义配置路径。root_dir 默认取应用根目录或环境变量。
    """
    # 优先环境变量，可在 Coolify/容器里通过 env 覆盖
    root_dir = os.environ.get("MPT_ROOT", "/MoneyPrinterTurbo")
    config_file = os.path.join(root_dir, "config.toml")
    example_file = os.path.join(root_dir, "config.example.toml")
    return config_file, example_file


def load_config() -> dict:
    """
    加载/初始化配置：
    - 确保目录存在
    - 若配置缺失：从示例复制或写入默认内容
    - 解析并返回配置字典
    """
    config_file, example_file = _config_paths()

    # 确保父目录存在
    os.makedirs(os.path.dirname(config_file), exist_ok=True)

    # 不建议每次都删除配置；仅当你确实需要重置时才调用：
    # safe_remove_path(config_file)

    if not os.path.isfile(config_file):
        if os.path.isfile(example_file):
            shutil.copyfile(example_file, config_file)
            logger.info("copy config.example.toml to config.toml")
        else:
            with open(config_file, "w", encoding="utf-8") as f:
                f.write(_default_config_text())
            logger.info("created default config.toml")

    logger.info(f"load config from file: {config_file}")

    try:
        _config_ = toml.load(config_file)
    except Exception as e:
        logger.warning(f"load config failed: {str(e)}, try to load as utf-8-sig")
        with open(config_file, mode="r", encoding="utf-8-sig") as fp:
            _cfg_content = fp.read()
        _config_ = toml.loads(_cfg_content)

    return _config_


def save_config(_cfg: dict) -> None:
    """
    将当前配置写回 config.toml。
    """
    config_file, _ = _config_paths()
    with open(config_file, "w", encoding="utf-8") as f:
        f.write(toml.dumps(_cfg))
    logger.info(f"saved config to: {config_file}")


# 载入配置并展开常用字段
_cfg = load_config()

app = _cfg.get("app", {})
whisper = _cfg.get("whisper", {})
proxy = _cfg.get("proxy", {})
azure = _cfg.get("azure", {})
siliconflow = _cfg.get("siliconflow", {})
ui = _cfg.get("ui", {"hide_log": False})

hostname = socket.gethostname()

log_level = _cfg.get("log_level", "DEBUG")
listen_host = _cfg.get("listen_host", "0.0.0.0")
listen_port = _cfg.get("listen_port", 8080)
project_name = _cfg.get("project_name", "MoneyPrinterTurbo")
project_description = _cfg.get(
    "project_description",
    "<a href='https://github.com/harry0703/MoneyPrinterTurbo'>https://github.com/harry0703/MoneyPrinterTurbo</a>",
)
project_version = _cfg.get("project_version", "1.2.6")
reload_debug = False

# 环境变量注入（如果配置了路径）
imagemagick_path = app.get("imagemagick_path", "")
if imagemagick_path and os.path.isfile(imagemagick_path):
    os.environ["IMAGEMAGICK_BINARY"] = imagemagick_path

ffmpeg_path = app.get("ffmpeg_path", "")
if ffmpeg_path and os.path.isfile(ffmpeg_path):
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path

logger.info(f"{project_name} v{project_version}")
