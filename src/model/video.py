import logging
import os
from enum import Enum

from pydantic import BaseModel

from src import meta
from src.utils import scan_directory


class VideoFile:
    """
    视频文件类，用于封装视频文件的基本信息和操作

    该类提供了视频文件的路径、名称、扩展名等属性的访问方法，
    并实现了视频文件格式的检查功能。
    """

    def __init__(self, file_path: str) -> None:
        """
        初始化视频文件对象

        Args:
            file_path: 视频文件的完整路径

        Raises:
            ValueError: 当文件不是支持的视频格式时抛出
        """
        self.file_path = file_path

        if not self.is_supported():
            raise ValueError(f"文件 {self.file_path} 不是支持的视频文件")

    def __repr__(self) -> str:
        return f"VideoFile({self.file_path})"

    @property
    def fullname(self) -> str:
        """
        获取视频文件的文件名（包含扩展名）

        Returns:
            str: 视频文件的文件名
        """
        return os.path.basename(self.file_path)

    @property
    def filename(self) -> str:
        """
        获取视频文件的文件名（不包含扩展名）

        Returns:
            str: 视频文件的文件名（不包含扩展名）
        """
        return os.path.splitext(self.fullname)[0]

    @property
    def ext(self) -> str:
        """
        获取视频文件的扩展名（小写）

        Returns:
            str: 视频文件的扩展名（小写）
        """
        return os.path.splitext(self.file_path)[1].lower()

    @property
    def output_fullname(self) -> str:
        """
        获取压缩后的视频文件名（包含扩展名）

        Returns:
            str: 压缩后的视频文件名（包含扩展名）
        """
        return f"{self.filename}_x264{self.ext}"

    @property
    def output_path(self) -> str:
        """
        获取压缩后的视频文件的输出路径（包含文件名）

        Returns:
            str: 压缩后的视频文件的输出路径（包含文件名）
        """
        return os.path.join(os.path.dirname(self.file_path), self.output_fullname)

    def is_supported(self) -> bool:
        """
        检查文件是否为支持的视频文件

        Returns:
            bool: 如果文件为支持的视频文件，则返回True
        """
        _, ext = os.path.splitext(self.file_path)
        return (
            os.path.isfile(self.file_path)
            and ext.lower() in meta.SUPPORTED_VIDEO_EXTENSIONS
        )


class TaskStatus(Enum):
    """
    视频处理状态枚举类，定义了视频任务的各种处理状态
    """

    PENDING = "pending"  # 任务待处理
    PROCESSING = "processing"  # 任务正在处理中
    SUCCESS = "success"  # 任务处理成功
    FAILED = "failed"  # 任务处理失败


class TaskInfo(BaseModel):
    """
    视频处理任务配置信息类，用于存储视频压缩任务的配置参数

    Attributes:
        targets: 待处理的文件或文件夹路径列表
        process_config_name: 压缩配置文件名
        delete_audio: 是否删除视频中的音频轨道，默认值为False
        delete_source: 是否在压缩完成后删除源文件，默认值为False
        recursive: 是否递归处理文件夹中的视频文件，默认值为False
    """

    targets: list[str]
    process_config_name: str
    delete_audio: bool = False
    delete_source: bool = False
    recursive: bool = False


class Task:
    """
    视频处理任务类，用于管理视频压缩任务的执行状态和文件列表

    该类负责：
    1. 解析任务配置信息
    2. 扫描并验证待处理的视频文件
    3. 管理任务的处理状态
    4. 提供任务文件列表和数量的访问方法
    """

    def __init__(self, info: TaskInfo):
        """
        初始化视频处理任务

        Args:
            info: 任务配置信息对象，包含待处理文件列表和处理参数

        该方法会：
        1. 初始化任务状态为待处理
        2. 遍历处理目标路径列表
        3. 如果是文件夹且开启递归，则扫描文件夹中的所有视频文件
        4. 验证每个文件是否为支持的视频格式
        5. 将验证通过的视频文件添加到处理队列
        6. 忽略不支持的视频文件并记录警告日志
        """
        self.current_index: int = 0
        self.info = info

        self.status: TaskStatus = TaskStatus.PENDING

        # 遍历展开文件夹
        self.video_sequence: list[VideoFile] = []
        for path in self.info.targets:
            if not os.path.exists(path):
                logging.warning(f"文件 {path} 不存在, 已被略过")
                continue

            if os.path.isdir(path) and self.info.recursive:
                _, video_files = scan_directory(path, meta.SUPPORTED_VIDEO_EXTENSIONS)
                for file_path in video_files:
                    try:
                        video_file = VideoFile(file_path)
                        self.video_sequence.append(video_file)
                    except ValueError:
                        logging.warning(
                            f"文件 {file_path} 不是支持的视频文件, 已被略过"
                        )
                        continue
                continue

            try:
                video_file = VideoFile(path)
                self.video_sequence.append(video_file)
            except ValueError:
                logging.warning(f"文件 {path} 不是支持的视频文件, 已被略过")
                continue

    @property
    def files_num(self) -> int:
        """
        获取任务中的总文件数

        Returns:
            int: 任务中的总文件数
        """
        return len(self.video_sequence)


def resolve_time_str(time_str: str) -> float:
    """
    解析时间字符串为秒数

    Args:
        time_str: 时间字符串，格式为 "HH:MM:SS.xxx"

    Returns:
        float: 时间字符串对应的秒数
    """
    if time_str == "N/A":
        return 0.0

    h, m, s = map(float, time_str.split(":"))
    return h * 3600 + m * 60 + s


def is_progress_line(line: str) -> bool:
    """
    判断是否为进度行

    Args:
        line: 输入行字符串

    Returns:
        bool: 如果是进度行，则返回True
    """
    return "elapsed" in line
