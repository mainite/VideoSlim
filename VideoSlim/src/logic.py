import logging
import os
import subprocess
from queue import Queue
from typing import List, Tuple, Any

import requests
from pymediainfo import MediaInfo

from .config import Config
from .message import *


def is_video_file(file_path: str, video_extensions: list[str]) -> bool:
    """
    Check if file is a supported video file

    Args:
        file_path: File path to check

    Returns:
        True if file is a supported video file
    """
    _, ext = os.path.splitext(file_path)
    return os.path.isfile(file_path) and ext.lower() in video_extensions


def clean_temp_files(temp_file_names: list[str]):
    """Clean up temporary files"""
    for temp_file in temp_file_names:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                logging.warning(f"删除临时文件 {temp_file} 失败: {e}")


def get_output_filename(input_path: str) -> str:
    """
    Generate output filename for compressed video

    Args:
        input_path: Input video file path

    Returns:
        Output file path
    """
    file_name, _ = os.path.splitext(input_path)
    return f"{file_name}_x264.mp4"


def scan_directory(directory: str, extensions: List[str]) -> Tuple[List[str], List[str]]:
    """
    Recursively scan directory for files with specific extensions

    Args:
        directory: Directory to scan
        extensions: List of file extensions to include

    Returns:
        Tuple of (subfolders, files)
    """
    subfolders, files = [], []

    for entry in os.scandir(directory):
        if entry.is_dir():
            subfolders.append(entry.path)
        elif entry.is_file() and os.path.splitext(entry.name)[1].lower() in extensions:
            files.append(entry.path)

    # Recursively scan subfolders
    for folder in list(subfolders):
        sf, f = scan_directory(folder, extensions)
        subfolders.extend(sf)
        files.extend(f)

    return subfolders, files


def send_message(queue: Queue, message: Message):
    queue.put(message)


def process_single_file(queue: Queue, file_path: str, config: Config, delete_audio: bool,
                        delete_source: bool, index: int, total: int, temp_file_names: list[str]):
    """
    Process a single video file

    Args:
        file_path: Path to video file
        config: Compression configuration
        delete_audio: Whether to delete audio tracks
        delete_source: Whether to delete source files
        index: Index of current file
        total: Total number of files
        :param queue:
    """
    try:
        # Clean up any existing temporary files
        clean_temp_files(temp_file_names)

        # Notify start of processing
        send_message(queue, CompressionProgressMessage(index, total, file_path))

        # Generate output filename
        output_path = get_output_filename(file_path)

        # Get media info
        media_info = MediaInfo.parse(file_path)
        current_file = file_path
        commands = []

        # Handle video rotation if needed
        if (hasattr(media_info.video_tracks[0], "other_rotation") and
                media_info.video_tracks[0].other_rotation):
            logging.info("视频元信息含有旋转，进行预处理")
            pre_temp = "./pre_temp.mp4"
            commands.append(
                f'./tools/ffmpeg.exe -i "{current_file}" "{pre_temp}"'
            )
            current_file = pre_temp

        # Generate compression commands based on audio presence
        has_audio = len(media_info.audio_tracks) > 0 and not delete_audio

        if has_audio:
            # Process with audio
            commands.extend([
                # Extract audio to WAV
                f'./tools/ffmpeg.exe -i "{current_file}" -vn -sn -v 0 -c:a pcm_s16le -f wav "./old_atemp.wav"',
                # Encode audio with AAC
                './tools/neroAacEnc.exe -ignorelength -lc -br 128000 -if "./old_atemp.wav" -of "./old_atemp.mp4"',
                # Encode video with x264
                f'./tools/x264_64-8bit.exe --crf {config.X264.crf} --preset {config.X264.preset} '
                f'-I {config.X264.I} -r {config.X264.r} -b {config.X264.b} '
                f'--me umh -i 1 --scenecut 60 -f 1:1 --qcomp 0.5 --psy-rd 0.3:0 '
                f'--aq-mode 2 --aq-strength 0.8 -o "./old_vtemp.mp4" "{current_file}"'
                + (' --opencl' if config.X264.opencl_acceleration else ''),
                # Mux video and audio
                f'./tools/mp4box.exe -add "./old_vtemp.mp4#trackID=1:name=" '
                f'-add "./old_atemp.mp4#trackID=1:name=" -new "{output_path}"'
            ])
        else:
            # Process without audio
            commands.append(
                f'./tools/x264_64-8bit.exe --crf {config.X264.crf} --preset {config.X264.preset} '
                f'-I {config.X264.I} -r {config.X264.r} -b {config.X264.b} '
                f'--me umh -i 1 --scenecut 60 -f 1:1 --qcomp 0.5 --psy-rd 0.3:0 '
                f'--aq-mode 2 --aq-strength 0.8 -o "{output_path}" "{current_file}"'
                + (' --opencl' if config.X264.opencl_acceleration else '')
            )

        # Execute commands
        for command in commands:
            logging.info(f"执行命令: {command}")
            subprocess.check_call(
                command,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        # Delete source if requested
        if delete_source and os.path.exists(output_path):
            os.remove(file_path)

    except Exception as e:
        logging.error(f"处理文件 {file_path} 失败: {e}")
        send_message(queue, CompressionErrorMessage("错误", f"处理文件 {file_path} 失败: {e}"))

    finally:
        # Always clean up temp files
        clean_temp_files(temp_file_names)


def get_file_paths_from_list(file_paths: list[str], files_to_process: list[Any], recurse: bool,
                             video_extensions: list[str]):
    for file_path in file_paths:
        if not file_path or not os.path.exists(file_path):
            continue

        if os.path.isdir(file_path) and recurse:
            # Recursively scan directory for video files
            _, video_files = scan_directory(file_path, video_extensions)
            files_to_process.extend(video_files)
        elif is_video_file(file_path, video_extensions):
            files_to_process.append(file_path)


def check_for_updates(queue, version):
    """Check for newer versions on GitHub"""
    try:
        url = "https://api.github.com/repos/mainite/VideoSlim/releases"
        response = requests.get(url, timeout=10)
        data = response.json()

        if data and len(data) > 0:
            latest_release = data[0]
            if latest_release['tag_name'] != version:
                send_message(queue, UpdateMessage())
    except Exception as e:
        logging.warning(f"检查更新失败: {e}")


def compression_files(queue: Queue, config: Config, delete_audio: bool, delete_source: bool,
                      file_paths: list[str], recurse: bool, video_extensions: list[str], temp_file_names: list[str]):
    """
    压缩处理视频文件的主函数
    参数:
        queue: 消息队列，用于发送处理状态和错误信息
        config: 压缩配置对象，包含压缩参数
        delete_audio: 是否删除原始音频文件的布尔值
        delete_source: 是否删除源文件的布尔值
        file_paths: 要处理的文件路径列表
        recurse: 是否递归处理子目录的布尔值
    返回:
        None
    """

    try:
        # Preprocess file list (expand directories if needed)
        files_to_process = []

        for file_path in file_paths:
            if not file_path or not os.path.exists(file_path):
                continue

            if os.path.isdir(file_path) and recurse:
                # Recursively scan directory for video files
                _, video_files = scan_directory(file_path, video_extensions)
                files_to_process.extend(video_files)
            elif is_video_file(file_path, video_extensions):
                files_to_process.append(file_path)

        if not files_to_process:
            send_message(queue, CompressionErrorMessage("错误", "没有找到可处理的视频文件"))
            return

        send_message(queue, CompressionStartMessage(len(files_to_process)))

        # Process each file
        for index, file_path in enumerate(files_to_process, 1):
            process_single_file(
                queue=queue,
                file_path=file_path,
                config=config,
                delete_audio=delete_audio,
                delete_source=delete_source,
                index=index,
                total=len(files_to_process),
                temp_file_names=temp_file_names
            )

        # Signal completion
        send_message(queue, CompressionFinishedMessage(len(files_to_process)))

    except Exception as e:
        logging.error(f"压缩处理失败: {e}")
        send_message(queue, CompressionErrorMessage("错误", f"发生错误！\n{e}"))
