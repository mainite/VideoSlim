import logging
import os
import subprocess
import time
from typing import Optional

from src import meta
from src.model.config import ConfigModel
from src.model.message import (
    CompressionCurrentProgressMessage,
    CompressionErrorMessage,
    CompressionFinishedMessage,
    CompressionStartMessage,
    CompressionStoppedMessage,
    CompressionTotalProgressMessage,
)
from src.model.video import Task, VideoFile, is_progress_line, resolve_time_str
from src.service.config import ConfigService
from src.service.message import MessageService
from src.utils import timer


class VideoService:
    """
    视频处理服务类，提供视频压缩和处理的核心功能

    该类作为应用程序的核心服务之一，负责视频文件的压缩处理，支持单个文件处理和批量任务处理。
    它使用FFmpeg、x264、NeroAACEnc等工具实现视频压缩，并通过消息服务发送处理状态和进度信息，
    使UI能够实时更新处理进度。
    """

    _instance: Optional["VideoService"] = None

    running_process: list[subprocess.Popen] = []

    # 缓存的编码器能力探测结果：None 表示尚未探测
    _opencl_supported: Optional[bool] = None
    _encoder_supported: dict[str, bool] = {}

    # encoder="auto" 时的探测优先级（均为厂商硬件编码器）
    _ENCODER_PRIORITY: list[str] = ["h264_nvenc", "h264_qsv", "h264_amf"]

    # 是否正在停止处理：停止时不再重试，避免停机过程中重新启动 ffmpeg
    _stopping: bool = False

    def __init__(self) -> None:
        if self._instance is not None:
            raise ValueError("VideoService 是单例类，不能重复实例化")

        self.message_service = MessageService.get_instance()

    @staticmethod
    def get_instance() -> "VideoService":
        """
        获取 VideoService 的单例实例

        Returns:
            VideoService: VideoService 的单例实例
        """
        if VideoService._instance is None:
            VideoService._instance = VideoService()

        return VideoService._instance

    @staticmethod
    def _is_opencl_supported() -> bool:
        """
        探测当前 ffmpeg 是否支持 libx264 的 OpenCL lookahead 加速

        该探测只会在首次调用时执行一次，结果会被缓存。若当前 ffmpeg 构建不包含
        OpenCL 支持，则返回 False，调用方应跳过 -opencl 参数以保证压缩正常进行。

        Returns:
            bool: 支持 OpenCL 时返回 True，否则返回 False
        """
        if VideoService._opencl_supported is not None:
            return VideoService._opencl_supported

        supported = False
        try:
            result = subprocess.run(
                [meta.FFMPEG_PATH, "-hide_banner", "-h", "encoder=libx264"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=10,
                check=False,
            )
            supported = "opencl" in result.stdout.lower()
        except Exception as e:
            logging.warning(f"探测 OpenCL 支持失败: {e}")

        if not supported:
            logging.warning(
                "当前 ffmpeg 未编译 OpenCL 支持，opencl_acceleration 已自动忽略，"
                "将使用软件编码。如需 OpenCL 加速请更换带 OpenCL 的 ffmpeg 构建。"
            )

        VideoService._opencl_supported = supported
        return supported

    @staticmethod
    def _is_encoder_supported(encoder: str) -> bool:
        """
        探测指定的硬件编码器在当前机器上是否真正可用

        仅检查 ffmpeg 是否编译了该编码器是不够的，还需确认驱动/硬件是否就绪，因此
        这里实际编码一帧黑帧进行验证。结果会被缓存，避免重复探测。

        Args:
            encoder: 编码器名称，如 h264_nvenc

        Returns:
            bool: 可用时返回 True，否则返回 False
        """
        if encoder in VideoService._encoder_supported:
            return VideoService._encoder_supported[encoder]

        supported = False
        try:
            result = subprocess.run(
                [
                    meta.FFMPEG_PATH,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "nullsrc=s=256x144:d=0.2",
                    "-c:v",
                    encoder,
                    "-f",
                    "null",
                    "-",
                ],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
                check=False,
            )
            supported = result.returncode == 0
            if not supported:
                logging.info(
                    f"硬件编码器 {encoder} 不可用: {(result.stdout or '').strip()[:200]}"
                )
        except Exception as e:
            logging.warning(f"探测硬件编码器 {encoder} 失败: {e}")

        VideoService._encoder_supported[encoder] = supported
        return supported

    @staticmethod
    def _select_auto_encoder() -> str:
        """
        自动选择可用的硬件编码器

        按 _ENCODER_PRIORITY 顺序探测，返回首个真正可用的硬件编码器；
        若均不可用则回退到 libx264 软件编码。

        Returns:
            str: 选中的编码器名称
        """
        for candidate in VideoService._ENCODER_PRIORITY:
            if VideoService._is_encoder_supported(candidate):
                logging.info(f"自动选择硬件编码器: {candidate}")
                return candidate

        logging.warning("未检测到可用的硬件编码器，已回退到 libx264 软件编码")
        return "libx264"

    @staticmethod
    def _resolve_encoder(config: ConfigModel) -> str:
        """
        解析最终使用的视频编码器

        - encoder 为 "auto" 时自动选择可用的硬件编码器（见 _select_auto_encoder）
        - 若配置选择了硬件编码器但其不可用，则根据 fallback_to_cpu 决定是否回退到
          libx264 软件编码，避免因硬件/驱动缺失导致压缩任务失败

        Args:
            config: 视频压缩配置对象

        Returns:
            str: 实际使用的编码器名称
        """
        encoder = config.x264.encoder

        if encoder == "auto":
            return VideoService._select_auto_encoder()

        if encoder == "libx264":
            return "libx264"

        if VideoService._is_encoder_supported(encoder):
            return encoder

        if config.x264.fallback_to_cpu:
            logging.warning(f"硬件编码器 {encoder} 不可用，已回退到 libx264 软件编码")
            return "libx264"

        logging.error(f"硬件编码器 {encoder} 不可用，且未启用回退")
        return encoder

    @staticmethod
    def _build_video_args(config: ConfigModel, encoder: str) -> list[str]:
        """
        根据编码器构建视频编码参数

        libx264 使用 crf/preset 等原有参数；硬件编码器使用各自对应的恒定质量参数，
        并保留关键帧间隔、B 帧等通用设置。

        Args:
            config: 视频压缩配置对象
            encoder: 实际使用的编码器名称

        Returns:
            list[str]: 视频编码参数列表
        """
        x264 = config.x264
        if encoder == "libx264":
            return [
                "-c:v",
                "libx264",
                "-crf",
                str(x264.crf),
                "-preset",
                x264.preset,
                "-keyint_min",
                str(x264.I),
                "-g",
                str(x264.I),
                "-refs",
                str(x264.r),
                "-bf",
                str(x264.b),
                "-me_method",
                "umh",
                "-sc_threshold",
                "60",
                "-b_strategy",
                "1",
                "-qcomp",
                "0.5",
                "-psy-rd",
                "0.3:0",
                "-aq-mode",
                "2",
                "-aq-strength",
                "0.8",
                *VideoService._build_opencl_args(config),
            ]

        args = ["-c:v", encoder]
        # 关键帧间隔 / B 帧为多数硬件编码器通用的参数
        args += ["-g", str(x264.I), "-bf", str(x264.b)]

        match encoder:
            case "h264_nvenc":
                # NVIDIA，-b:v 0 表示纯恒定质量模式
                args += [
                    "-preset",
                    "p4",
                    "-tune",
                    "hq",
                    "-rc",
                    "vbr",
                    "-cq",
                    str(int(round(x264.crf))),
                    "-b:v",
                    "0",
                    "-rc-lookahead",
                    "32",
                ]
            case "h264_qsv":
                args += [
                    "-global_quality",
                    str(int(round(x264.crf))),
                    "-look_ahead",
                    "1",
                ]
            case "h264_amf":
                args += [
                    "-rc",
                    "cqp",
                    "-qp_i",
                    str(int(round(x264.crf))),
                    "-qp_p",
                    str(int(round(x264.crf))),
                    "-qp_b",
                    str(int(round(x264.crf))),
                    "-quality",
                    "quality",
                ]
            case "h264_mf":
                args += ["-rate_control", "quality", "-quality", "90"]

        return args

    @staticmethod
    def _build_hwaccel_args(config: ConfigModel) -> list[str]:
        """
        构建硬件解码参数

        -hwaccel 是输入选项，必须位于 -i 之前。使用 ffmpeg 的软回退机制：当指定
        的硬件解码器不可用或解码失败时，会自动回退到软件解码，而不会导致整体失败。

        Args:
            config: 视频压缩配置对象

        Returns:
            list[str]: 需要追加到 -i 之前的参数列表，未启用时返回空列表
        """
        if config.x264.hwaccel == "none":
            return []
        return ["-hwaccel", config.x264.hwaccel]

    @staticmethod
    def _build_opencl_args(config: ConfigModel) -> list[str]:
        """
        构建 OpenCL 加速参数

        -opencl 是 libx264 的编码器选项，位于 -i 之后、输出文件之前。仅当配置开启
        且当前 ffmpeg 确实支持时才追加，避免因不支持的构建导致整个压缩任务失败。

        Args:
            config: 视频压缩配置对象

        Returns:
            list[str]: 需要追加到编码参数中的参数列表，未启用或不可用时返回空列表
        """
        if not config.x264.opencl_acceleration:
            return []
        if not VideoService._is_opencl_supported():
            return []
        return ["-opencl"]

    @staticmethod
    def _build_command(
        input_args: list[str],
        video_args: list[str],
        delete_audio: bool,
        preserve_extra_streams: bool,
        output_path: str,
    ) -> list[str]:
        """
        构建 ffmpeg 压缩命令

        Args:
            input_args: 输入相关参数（ffmpeg 路径、输入选项、-i 输入文件）
            video_args: 视频编码参数
            delete_audio: 是否删除音频
            preserve_extra_streams: 是否原样复制字幕等额外流
            output_path: 输出文件路径

        Returns:
            list[str]: 完整的命令参数列表
        """
        # 只映射首个视频流，避免把数据流（如 tmcd 时间码轨道）写入不支持的容器
        command = [*input_args, *video_args, "-map", "0:v:0"]

        if preserve_extra_streams:
            # 字幕原样复制，不重新编码（如 mov_text、srt、ass 等）
            command += ["-map", "0:s?", "-c:s", "copy"]

        if delete_audio:
            command += ["-an"]
        else:
            command += ["-map", "0:a?", "-c:a", "aac", "-b:a", "128k"]

        command += ["-movflags", "faststart", output_path]
        return command

    @staticmethod
    def _run_command(command: list[str], file: VideoFile) -> None:
        """
        执行 ffmpeg 命令，并实时解析进度

        Args:
            command: 命令参数列表
            file: 当前处理的视频文件，用于发送进度消息

        Raises:
            subprocess.CalledProcessError: 当命令执行失败时抛出
        """
        logging.info(f"执行命令: {subprocess.list2cmdline(command)}")

        # 使用Popen创建子进程并添加到running_process列表
        process = subprocess.Popen(
            command,
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 合并stdout和stderr到stdout
            text=True,
            # ffmpeg 输出为 UTF-8；显式指定编码，避免按系统本地编码(如 GBK)解码
            # 含特殊字符(如 emoji)的文件名时抛 UnicodeDecodeError
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            universal_newlines=True,
        )
        VideoService.running_process.append(process)

        # 等待进程完成，同时解析进度
        cur_time: float = -0.01  # 当前视频播放时间
        total_time: float = -1  # 视频总时长
        update_time = time.time()  # 上次更新进度的时间
        while process.poll() is None:
            line = ""
            try:
                stdout = process.stdout
                if not stdout:
                    continue

                line = stdout.readline()

                if not is_progress_line(line):
                    if total_time == -1 and "Duration" in line:
                        # 解析视频总时长
                        total_time = resolve_time_str(
                            line.split("Duration: ")[1].split(",")[0]
                        )
                        logging.debug(f"视频总时长: {total_time}")

                    if line.strip() == "":
                        continue

                    logging.debug(f"{line.strip()}")
                    continue

                # 解析当前播放时间
                cur_time = resolve_time_str(line.split("time=")[1].split(" ")[0])

                # 发送进度
                if update_time < time.time() - 1:
                    update_time = time.time()
                    MessageService.get_instance().send_message(
                        CompressionCurrentProgressMessage(
                            file_name=file.file_path,
                            current=cur_time,
                            total=total_time,
                        )
                    )

            except Exception as e:
                logging.error(f"读取 stdout 时出错:  {e} 输出: {line.strip()}")

        stdout, stderr = process.communicate()

        # 从running_process列表中移除已完成的进程
        if process in VideoService.running_process:
            VideoService.running_process.remove(process)

        # Log command output
        if stdout:
            logging.debug(f"command stdout: {stdout.strip()}")
        if stderr:
            logging.warning(f"command stderr: {stderr.strip()}")

        # Check return code
        if process.returncode != 0:
            if VideoService._stopping:
                logging.info(f"命令已被终止，退出码: {process.returncode}")
            else:
                logging.error(f"命令执行失败，退出码: {process.returncode}")
            raise subprocess.CalledProcessError(process.returncode, command)

    @timer
    @staticmethod
    def process_single_file(
        file: VideoFile,
        config_name: str,
        delete_audio: bool,
        delete_source: bool,
    ):
        """
        处理单个视频文件的压缩任务

        Args:
            file: 视频文件对象，包含源文件路径和输出路径信息
            config_name: 压缩配置文件名，用于获取压缩参数
            delete_audio: 是否删除视频中的音频轨道
            delete_source: 是否在压缩完成后删除源文件

        Raises:
            ValueError: 当配置文件不存在或媒体信息读取错误时抛出
            subprocess.CalledProcessError: 当压缩命令执行失败时抛出
        """
        config_service = ConfigService.get_instance()

        # 读取配置
        config = config_service.get_config(config_name)
        if config is None:
            logging.error(f"配置文件 {config_name} 不存在")
            raise ValueError(f"配置文件 {config_name} 不存在")

        # Generate output filename
        output_path = file.output_path

        ffmpeg_path = meta.FFMPEG_PATH

        input_file = file.file_path

        # 硬件解码参数（输入选项，必须位于 -i 之前）
        hwaccel_args = VideoService._build_hwaccel_args(config)

        # 解析实际使用的编码器（硬件不可用时按配置回退到 libx264）
        encoder = VideoService._resolve_encoder(config)
        logging.info(f"使用视频编码器: {encoder}")

        # 统一的输入前缀与编码参数，供有/无音频两个分支复用
        input_args = [ffmpeg_path, "-y", *hwaccel_args, "-i", input_file]
        video_args = VideoService._build_video_args(config, encoder)

        # 优先保留原视频中的字幕等额外流：这些流直接复制，不重新编码；
        # 视频与音频正常压缩。
        # 若额外流与输出容器不兼容（会在写入文件头时立即失败），则回退为
        # 仅输出视频与音频流，避免由此导致整个压缩任务失败。
        command = VideoService._build_command(
            input_args, video_args, delete_audio, True, output_path
        )
        try:
            VideoService._run_command(command, file)
        except subprocess.CalledProcessError as e:
            if VideoService._stopping:
                # 用户主动停止，直接向上抛出，不再回退重试
                raise
            logging.warning(f"保留字幕等额外流失败（{e}），回退为仅输出视频与音频流")
            VideoService._run_command(
                VideoService._build_command(
                    input_args, video_args, delete_audio, False, output_path
                ),
                file,
            )

        # Delete source if requested
        if delete_source and os.path.exists(output_path):
            logging.debug(f"存在输出文件：{output_path}，删除源文件: {file.file_path}")
            os.remove(file.file_path)

    @timer
    @staticmethod
    def process_task(task: Task):
        """
        处理视频压缩任务，支持批量处理多个视频文件

        Args:
            task: 视频处理任务对象，包含待处理文件列表和处理配置

        该方法会：
        1. 发送任务开始消息
        2. 遍历处理任务中的每个视频文件
        3. 发送当前文件处理进度消息
        4. 调用process_single_file处理单个文件
        5. 处理可能出现的异常并发送错误消息
        6. 发送任务完成消息
        """
        message_service = MessageService.get_instance()

        logging.info(f"process task: {task.info}")

        # 新任务开始，重置停止标记
        VideoService._stopping = False

        logging.debug(f"process task sequence: {task.video_sequence}")

        if task.files_num == 0:
            message_service.send_message(
                CompressionErrorMessage("错误", "没有找到可处理的视频文件")
            )
            return

        message_service.send_message(CompressionStartMessage(task.files_num))

        # Process each file
        for index, video_file in enumerate(task.video_sequence, 1):
            if VideoService._stopping:
                # 已被请求终止：不再处理后续文件，避免关闭程序后仍有 ffmpeg 在压缩
                logging.info("检测到终止请求，不再处理后续文件")
                break

            logging.debug(
                f"process file: {video_file.file_path}, index: {index}, total: {task.files_num}"
            )

            # Notify start of processing
            message_service.send_message(
                CompressionTotalProgressMessage(
                    index - 1,
                    task.files_num,
                    video_file.file_path,
                )
            )

            try:
                VideoService.clean_temp_files()
                VideoService.process_single_file(
                    file=video_file,
                    config_name=task.info.process_config_name,
                    delete_audio=task.info.delete_audio,
                    delete_source=task.info.delete_source,
                )
            except Exception as e:
                if VideoService._stopping:
                    # 因终止而中断：属于预期行为，不作为错误上报
                    logging.info(f"文件 {video_file.file_path} 的处理已终止")
                    break
                logging.error(f"处理文件 {video_file.file_path} 失败: {e}")
                message_service.send_message(
                    CompressionErrorMessage(
                        "错误", f"处理文件 {video_file.file_path} 失败: {e}"
                    )
                )
            finally:
                VideoService.clean_temp_files()

        if VideoService._stopping:
            # 任务被终止：通知界面恢复可用状态，而不是提示"转换结束"
            logging.info("压缩任务已被终止")
            message_service.send_message(CompressionStoppedMessage())
            return

        # Signal completion
        message_service.send_message(
            CompressionFinishedMessage(len(task.video_sequence))
        )

    @staticmethod
    def clean_temp_files():
        """
        清理视频处理过程中生成的临时文件

        该方法会遍历meta.TEMP_FILES中定义的所有临时文件路径，
        并删除存在的临时文件。如果删除失败，会记录警告日志但不会抛出异常。

        Returns:
            None
        """
        for temp_file in meta.TEMP_FILES:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logging.warning(f"删除临时文件 {temp_file} 失败: {e}")

    @staticmethod
    def stop_process():
        """
        停止当前正在运行的视频处理进程

        该方法会终止running_process中存储的子进程，
        并等待其退出。如果进程未运行或已退出，
        则不执行任何操作。

        Returns:
            None
        """
        logging.info(
            f"正在停止所有视频处理进程，共 {len(VideoService.running_process)} 个进程"
        )

        # 标记为正在停止，避免被终止的进程触发回退重试
        VideoService._stopping = True

        # 创建进程列表的副本，避免在遍历过程中修改原列表
        processes_to_stop = list(VideoService.running_process)

        for process in processes_to_stop:
            try:
                logging.debug(f"正在终止进程: {process.pid}")
                process.terminate()

                # 等待进程退出，最多等待5秒
                logging.debug(f"等待进程 {process.pid} 退出")
                process.wait(timeout=5)

                if process.returncode is None:
                    # 如果进程仍未退出，强制终止
                    logging.warning(f"进程 {process.pid} 未在5秒内退出，正在强制终止")
                    process.kill()
                    # 再次等待确认进程退出
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        logging.error(f"进程 {process.pid} 无法强制终止")
                else:
                    logging.debug(
                        f"进程 {process.pid} 已退出，退出码: {process.returncode}"
                    )
            except Exception as e:
                logging.error(f"处理进程 {process.pid} 时发生错误: {e}")

        # 清空进程列表
        VideoService.running_process.clear()
        logging.info("所有视频处理进程已停止")

    @staticmethod
    def is_processing() -> bool:
        """
        检查是否有正在运行的视频处理进程

        Returns:
            bool: 如果有正在运行的进程则返回True，否则返回False
        """
        return len(VideoService.running_process) > 0
