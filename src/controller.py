import logging
import threading
from typing import Optional

from src.model import message
from src.model.video import Task, TaskInfo
from src.service.message import MessageService
from src.service.store import StoreService
from src.service.updater import UpdateService
from src.service.video import VideoService


class Controller:
    """
    VideoSlim应用程序的控制器类

    负责处理应用程序的控制逻辑，包括视频压缩任务的启动和更新检查。
    作为视图和服务层之间的桥梁，协调用户界面和业务逻辑的交互。
    """

    def __init__(self):
        """
        初始化控制器

        启动一个后台线程检查应用程序更新，确保用户始终使用最新版本。
        """
        # 当前压缩任务所在的后台线程，用于判断任务是否仍在运行
        self._task_thread: Optional[threading.Thread] = None

        threading.Thread(
            target=UpdateService.check_for_updates,
            daemon=True,
        ).start()

    def is_task_running(self) -> bool:
        """
        判断当前是否仍有压缩任务在运行

        Returns:
            bool: 压缩任务线程仍在运行时返回 True
        """
        return self._task_thread is not None and self._task_thread.is_alive()

    def terminate(self):
        """
        终止当前正在运行的压缩任务

        终止正在执行的 ffmpeg 子进程，并阻止任务继续处理列表中后续的文件。
        未在压缩时调用不会产生副作用。
        """
        logging.info("收到终止请求")
        VideoService.get_instance().stop_process()

    def close(self):
        """
        关闭应用程序

        1. 停止所有视频处理任务
        2. 清理临时文件
        3. 发送退出消息通知视图关闭
        4.  dump 配置到文件
        """
        VideoService.get_instance().stop_process()
        VideoService.get_instance().clean_temp_files()
        MessageService.get_instance().send_message(message.ExitMessage())
        StoreService.get_instance().dump()

    def compression(
        self,
        config_name: str,
        delete_audio: bool,
        delete_source: bool,
        file_paths: list[str],
        recurse: bool,
    ):
        """
        压缩视频文件

        创建视频压缩任务，并在后台线程中执行。

        Args:
            config_name: 要使用的压缩配置名称
            delete_audio: 是否删除视频中的音频轨道
            delete_source: 压缩完成后是否删除源文件
            file_paths: 要压缩的视频文件路径列表
            recurse: 如果路径是目录，是否递归处理其中的所有视频文件
        """

        task = Task(
            info=TaskInfo(
                targets=file_paths,
                process_config_name=config_name,
                delete_audio=delete_audio,
                delete_source=delete_source,
                recursive=recurse,
            ),
        )

        self._task_thread = threading.Thread(
            target=VideoService.process_task,
            args=(task,),
        )
        self._task_thread.start()
