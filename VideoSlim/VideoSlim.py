#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VideoSlim - A video compression application using x264
Author: hotMonk (inite.cn)
Refactored version: v1.8
"""

import os
import json
import time
import logging
import threading
import subprocess
import webbrowser
from queue import Queue
from typing import List, Dict, Tuple, Any, Optional

import tkinter as tk
from tkinter import messagebox, StringVar, BooleanVar, END, TOP, W, NE
import tkinter.ttk as ttk
import windnd
import requests
from pymediainfo import MediaInfo

# Constants
VERSION = 'v1.8'
VIDEO_EXTENSIONS = [".mp4", ".mkv", ".mov", ".avi"]
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "comment": "Configuration file for VideoSlim. See README.md for parameter descriptions.",
    "configs": {
        "default": {
            "x264": {
                "crf": 23.5,
                "preset": 8,
                "I": 600,
                "r": 4,
                "b": 3,
                "opencl_acceleration": False
            }
        },
        "custom_template": {
            "x264": {
                "crf": 30,
                "preset": 8,
                "I": 600,
                "r": 4,
                "b": 3,
                "opencl_acceleration": False
            }
        },
        "default_gpu": {
            "x264": {
                "opencl_acceleration": True,
                "crf": 23.5,
                "preset": 8,
                "I": 600,
                "r": 4,
                "b": 3
            }
        }
    }
}
TEMP_FILES = ["./pre_temp.mp4", "./old_atemp.wav", "./old_atemp.mp4", "./old_vtemp.mp4"]


class Config:
    """Configuration class for VideoSlim"""
    
    class X264:
        """X264 encoder configuration"""
        
        def __init__(self, config_dict: Dict[str, Any] = None):
            """
            Initialize X264 configuration
            
            Args:
                config_dict: Dictionary containing X264 parameters
            """
            if config_dict is None:
                config_dict = {}
                
            self._crf = config_dict.get("crf", 23.5)
            self._preset = config_dict.get("preset", 8)
            self.opencl_acceleration = config_dict.get("opencl_acceleration", False)
            self.I = config_dict.get("I", 600)
            self.r = config_dict.get("r", 4)
            self.b = config_dict.get("b", 3)
            
            # Validate values
            self.crf = self._crf
            self.preset = self._preset
            
        @property
        def crf(self) -> float:
            """Get CRF value"""
            return self._crf
            
        @crf.setter
        def crf(self, value: float):
            """
            Set CRF value within valid range [0, 51]
            
            Args:
                value: CRF value
            """
            self._crf = max(0, min(51, value))
            
        @property
        def preset(self) -> int:
            """Get preset value"""
            return self._preset
            
        @preset.setter
        def preset(self, value: int):
            """
            Set preset value within valid range [0, 9]
            
            Args:
                value: Preset value
            """
            self._preset = max(0, min(9, value))
            
    def __init__(self, config_dict: Dict[str, Any] = None):
        """
        Initialize configuration
        
        Args:
            config_dict: Dictionary containing configuration parameters
        """
        if config_dict is None:
            config_dict = {"name": "Default", "x264": {}}
            
        self.name = config_dict.get("name", "Default")
        self.X264 = self.X264(config_dict.get("x264", {}))
    
    @staticmethod
    def fix_dict(config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fill missing parameters in configuration dictionary
        
        Args:
            config_dict: Configuration dictionary to fix
            
        Returns:
            Complete configuration dictionary
        """
        # Ensure x264 section exists
        if "x264" not in config_dict:
            config_dict["x264"] = {}
            
        # Set default values for missing parameters
        x264_defaults = {
            "crf": 23.5,
            "preset": 8,
            "I": 600,
            "r": 4,
            "b": 3,
            "opencl_acceleration": False
        }
        
        for key, default_value in x264_defaults.items():
            if key not in config_dict["x264"]:
                config_dict["x264"][key] = default_value
                
        return config_dict


class VideoSlimApp:
    """Main application class for VideoSlim"""
    
    def __init__(self, root: tk.Tk):
        """
        Initialize VideoSlim application
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.version = VERSION
        self.queue = Queue()
        self.configs_name_list = []
        self.configs_dict = {}
        
        self._setup_ui()
        self._read_config()
        
        # Setup message queue checking
        self.root.after(1000, self._check_message_queue)
        
        # Start version check in background
        threading.Thread(target=self._check_for_updates, daemon=True).start()
        
    def _setup_ui(self):
        """Setup the application's user interface"""
        # Configure root window
        self.root.title(f"VideoSlim 视频压缩 {self.version}")
        self.root.resizable(width=False, height=False)
        
        # Set icon if available
        icon_path = os.path.join(os.getcwd(), "./tools/icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
            
        # Center window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width, window_height = 527, 351
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        
        # Create GitHub link
        github_link = tk.Label(self.root, text="github", fg="#cdcdcd", cursor="hand2")
        github_link.pack(side=TOP, anchor=NE, padx=25, pady=8)
        github_link.bind("<Button-1>", 
                        lambda event: webbrowser.open_new_tab("https://github.com/mainite/VideoSlim"))
        
        # Title label
        self.title_var = StringVar()
        self.title_var.set('将视频拖拽到此窗口:')
        self.title_label = tk.Label(self.root, textvariable=self.title_var, anchor=W)
        self.title_label.place(x=26, y=8, width=380, height=24)
        
        # File list text box
        self.text_box = tk.Text(self.root, width=100, height=20)
        self.text_box.place(x=24, y=40, width=480, height=220)
        
        # Clear button
        clear_btn_text = StringVar()
        clear_btn_text.set('清空')
        clear_btn = tk.Button(self.root, textvariable=clear_btn_text, command=self._clear_file_list)
        clear_btn.place(x=168, y=291, width=88, height=40)
        
        # Compress button
        compress_btn_text = StringVar()
        compress_btn_text.set('压缩')
        self.compress_btn = tk.Button(self.root, textvariable=compress_btn_text, command=self._start_compression)
        self.compress_btn.place(x=280, y=291, width=88, height=40)
        
        # Options checkboxes
        self.recurse_var = BooleanVar()
        recurse_check = tk.Checkbutton(self.root, text="递归(至最深深度)子文件夹里面的视频", 
                                     variable=self.recurse_var, onvalue=True, offvalue=False)
        recurse_check.place(x=20, y=261)
        
        self.delete_source_var = BooleanVar()
        delete_source_check = tk.Checkbutton(self.root, text="完成后删除旧文件", 
                                           variable=self.delete_source_var, onvalue=True, offvalue=False)
        delete_source_check.place(x=20, y=287)
        
        self.delete_audio_var = BooleanVar()
        delete_audio_check = tk.Checkbutton(self.root, text="删除音频轨道", 
                                          variable=self.delete_audio_var, onvalue=True, offvalue=False)
        delete_audio_check.place(x=20, y=313)
        
        # Setup drag and drop
        windnd.hook_dropfiles(self.root, func=self._on_drop_files)
        
        # Configuration selection
        config_label = tk.Label(self.root, text="选择参数配置")
        config_label.place(x=388, y=265)
        
        self.select_config_name = StringVar(self.root, value="default")
        self.config_combobox = ttk.Combobox(self.root, height=10, width=10, state='readonly',
                                          values=[], textvariable=self.select_config_name)
        self.config_combobox.place(x=388, y=291)
    
    def _on_drop_files(self, file_paths):
        """
        Handle files dropped into application
        
        Args:
            file_paths: List of file paths dropped
        """
        files = '\n'.join(item.decode('gbk') for item in file_paths)
        self.text_box.insert(END, files + "\n")
    
    def _clear_file_list(self):
        """Clear the file list text box"""
        self.text_box.delete("1.0", END)
    
    def _check_message_queue(self):
        """Process messages from compression worker thread"""
        while not self.queue.empty():
            message = self.queue.get()
            action = message.get("action", "")
            
            if action == "start":
                # Update progress display
                self.title_var.set(f"[{message['index']}/{message['total']}] "
                                 f"当前处理文件：{message['filename']}")
                self.title_label.update()
                
            elif action == "error":
                # Display error message
                messagebox.showerror("错误", f"发生错误！\n{message['err']}")
                self.compress_btn.config(state=tk.NORMAL)
                
            elif action == "finish_all":
                # All files processed
                self.title_var.set(f"处理完成！已经处理 {message['total']} 个文件")
                self.title_label.update()
                messagebox.showinfo("提示", "转换完成")
                self.compress_btn.config(state=tk.NORMAL)
        
        # Schedule next check
        self.root.after(1000, self._check_message_queue)
    
    def _read_config(self):
        """Read configuration from file or create default configuration"""
        try:
            # Create default config if file doesn't exist
            if not os.path.exists(CONFIG_FILE):
                messagebox.showwarning("警告", "没有检测到配置文件，将生成一个配置文件")
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
                
                # Load configs from default config
                configs = DEFAULT_CONFIG["configs"]
            else:
                # Load configs from file
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    configs = json.load(f)["configs"]
                    
            # Process each config
            for name, params in configs.items():
                # Fix incomplete config
                params = Config.fix_dict(params)
                
                # Validate config values
                if name in self.configs_name_list or name in self.configs_dict:
                    messagebox.showwarning("警告", f"读取到重名的配置文件 {name}\n将仅读取最前的配置")
                    continue
                    
                if params["x264"]["crf"] > 51 or params["x264"]["crf"] < 0:
                    messagebox.showwarning("警告", f"配置文件 {name} 中的 crf 参数不合法\n将放弃读取该配置")
                    continue
                    
                if params["x264"]["preset"] < 0 or params["x264"]["preset"] > 9:
                    messagebox.showwarning("警告", f"配置文件 {name} 中的 preset 参数不合法\n将放弃读取该配置")
                    continue
                
                # Register valid config
                params["name"] = name
                self.configs_dict[name] = Config(params)
                self.configs_name_list.append(name)
                
            # Update combobox values
            if self.configs_name_list:
                self.config_combobox.config(values=self.configs_name_list)
                self.select_config_name.set(self.configs_name_list[0])
            else:
                messagebox.showerror("错误", "没有有效的配置，应用将退出")
                self.root.destroy()
                
        except Exception as e:
            logging.error(f"读取配置文件失败: {e}")
            messagebox.showerror("错误", f"读取配置文件失败: {e}")
            self.root.destroy()
    
    def _check_for_updates(self):
        """Check for newer versions on GitHub"""
        try:
            url = "https://api.github.com/repos/mainite/VideoSlim/releases"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data and len(data) > 0:
                latest_release = data[0]
                if latest_release['tag_name'] != self.version:
                    messagebox.showinfo("更新提示", "有新版本可用，请前往官网更新")
        except Exception as e:
            logging.warning(f"检查更新失败: {e}")
    
    def _start_compression(self):
        """Start video compression process"""
        # Get selected configuration
        config_name = self.select_config_name.get()
        if not config_name or config_name not in self.configs_dict:
            messagebox.showwarning("提示", "请选择有效的配置")
            return
        
        config = self.configs_dict[config_name]
        delete_source = self.delete_source_var.get()
        delete_audio = self.delete_audio_var.get()
        
        # Get file list
        text_content = self.text_box.get("1.0", END)
        lines = [line for line in text_content.splitlines() if line.strip()]
        
        if not lines:
            messagebox.showwarning("提示", "请先拖拽文件到此处")
            return
        
        # Start compression in background thread
        self.compress_btn.config(state=tk.DISABLED)
        threading.Thread(
            target=self._compression_worker,
            args=(config, delete_audio, delete_source, lines, self.recurse_var.get()),
            daemon=True
        ).start()
    
    def _compression_worker(self, config: Config, delete_audio: bool, delete_source: bool, 
                           file_paths: List[str], recurse: bool):
        """
        Worker thread for compressing videos
        
        Args:
            config: Compression configuration
            delete_audio: Whether to delete audio tracks
            delete_source: Whether to delete source files
            file_paths: List of file paths to process
            recurse: Whether to recursively process folders
        """
        try:
            # Preprocess file list (expand directories if needed)
            files_to_process = []
            
            for file_path in file_paths:
                if not file_path or not os.path.exists(file_path):
                    continue
                    
                if os.path.isdir(file_path) and recurse:
                    # Recursively scan directory for video files
                    _, video_files = self._scan_directory(file_path, VIDEO_EXTENSIONS)
                    files_to_process.extend(video_files)
                elif os.path.isfile(file_path) and self._is_video_file(file_path):
                    files_to_process.append(file_path)
            
            if not files_to_process:
                self.queue.put({
                    "action": "error", 
                    "err": "没有找到可处理的视频文件"
                })
                return
            
            # Process each file
            for index, file_path in enumerate(files_to_process, 1):
                self._process_single_file(
                    file_path=file_path,
                    config=config,
                    delete_audio=delete_audio,
                    delete_source=delete_source,
                    index=index,
                    total=len(files_to_process)
                )
            
            # Signal completion
            self.queue.put({"action": "finish_all", "total": len(files_to_process)})
            
        except Exception as e:
            logging.error(f"压缩处理失败: {e}")
            self.queue.put({"action": "error", "err": e})
    
    def _process_single_file(self, file_path: str, config: Config, delete_audio: bool, 
                            delete_source: bool, index: int, total: int):
        """
        Process a single video file
        
        Args:
            file_path: Path to video file
            config: Compression configuration
            delete_audio: Whether to delete audio tracks
            delete_source: Whether to delete source files
            index: Index of current file
            total: Total number of files
        """
        try:
            # Clean up any existing temporary files
            self._clean_temp_files()
            
            # Notify start of processing
            self.queue.put({
                "action": "start", 
                "index": index, 
                "total": total, 
                "filename": file_path
            })
            
            # Generate output filename
            output_path = self._get_output_filename(file_path)
            
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
            self.queue.put({"action": "error", "err": f"处理文件 {file_path} 失败: {e}"})
            
        finally:
            # Always clean up temp files
            self._clean_temp_files()
    
    @staticmethod
    def _scan_directory(directory: str, extensions: List[str]) -> Tuple[List[str], List[str]]:
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
            sf, f = VideoSlimApp._scan_directory(folder, extensions)
            subfolders.extend(sf)
            files.extend(f)
            
        return subfolders, files
    
    @staticmethod
    def _get_output_filename(input_path: str) -> str:
        """
        Generate output filename for compressed video
        
        Args:
            input_path: Input video file path
            
        Returns:
            Output file path
        """
        file_name, _ = os.path.splitext(input_path)
        return f"{file_name}_x264.mp4"
    
    @staticmethod
    def _clean_temp_files():
        """Clean up temporary files"""
        for temp_file in TEMP_FILES:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logging.warning(f"删除临时文件 {temp_file} 失败: {e}")
    
    @staticmethod
    def _is_video_file(file_path: str) -> bool:
        """
        Check if file is a supported video file
        
        Args:
            file_path: File path to check
            
        Returns:
            True if file is a supported video
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in VIDEO_EXTENSIONS


def setup_logging():
    """Configure application logging"""
    logging.basicConfig(
        level=logging.INFO,
        filename='log.txt',
        filemode='w',
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def main():
    """Application entry point"""
    setup_logging()
    
    root = tk.Tk()
    app = VideoSlimApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
