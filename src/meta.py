from src import utils

"""
VideoSlim 应用程序常量定义
"""

# 应用程序版本号
VERSION = "v2.1.0"

# 检查更新的 GitHub API URL
CHECK_UPDATE_URL = "https://api.github.com/repos/DongGuoZheng/VideoSlim/releases"

# 支持的视频文件扩展名列表
SUPPORTED_VIDEO_EXTENSIONS = [".mp4", ".mkv", ".mov", ".avi"]

# 配置文件路径
CONFIG_FILE_PATH = "config.json"

# 存储文件路径
STORE_PATH = "store"

# 日志文件夹路径
LOG_DIR = "log"

# 临时文件路径列表
TEMP_FILES = ["./pre_temp.mp4"]


def get_ffmpeg_path() -> str:
    """
    获取FFmpeg可执行文件的路径

    Returns:
        str: FFmpeg可执行文件的路径
    """
    return utils.get_path("./tools/ffmpeg.exe")


FFMPEG_PATH = get_ffmpeg_path()
