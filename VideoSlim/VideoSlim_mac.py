#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VideoSlim - A cross-platform video compression application using ffmpeg
Author: hotMonk (inite.cn)
macOS optimized version: v2.0
Modified: All output videos will be in .mp4 format
"""

import os
import json
import logging
import threading
import subprocess
import shutil
from pathlib import Path
from queue import Queue
from typing import List, Dict, Any, Optional

import tkinter as tk
from tkinter import messagebox, StringVar, BooleanVar, END, TOP, W, NE, filedialog
import tkinter.ttk as ttk

# Constants
VERSION = 'v1.0-macOS'
VIDEO_EXTENSIONS = [".mp4", ".mkv", ".mov", ".avi", ".m4v", ".webm", ".flv"]
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "comment": "Configuration file for VideoSlim macOS. CRF: lower=better quality, Preset: slower=better compression",
    "profiles": {
        "default": {
            "crf": 23,
            "preset": "medium",
            "description": "平衡"
        },
        "high_quality": {
            "crf": 18,
            "preset": "slow",
            "description": "高质量，大体积"
        },
        "small_size": {
            "crf": 28,
            "preset": "fast",
            "description": "低质量，小体积"
        }
    }
}


class VideoSlimApp:
    """Main application class for VideoSlim"""

    def __init__(self, root: tk.Tk):
        """Initialize VideoSlim application"""
        self.root = root
        self.version = VERSION
        self.queue = Queue()
        self.profiles = {}
        self.ffmpeg_path = self._find_ffmpeg()

        if not self.ffmpeg_path:
            messagebox.showerror("错误",
                                 "未找到 ffmpeg！请使用 Homebrew 安装:\nbrew install ffmpeg")
            self.root.destroy()
            return

        self._setup_ui()
        self._load_config()

        # Setup message queue checking
        self.root.after(100, self._check_message_queue)

    def _find_ffmpeg(self) -> Optional[str]:
        """Find ffmpeg executable"""
        return shutil.which('ffmpeg')

    def _setup_ui(self):
        """Setup the application's user interface"""
        # Configure root window
        self.root.title(f"VideoSlim 视频压缩 {self.version}")
        self.root.resizable(width=False, height=False)

        # Center window on screen
        window_width, window_height = 600, 450
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

        # Title label
        self.title_var = StringVar()
        self.title_var.set('拖拽视频文件到此处，或点击"选择文件"按钮')
        title_label = tk.Label(self.root, textvariable=self.title_var,
                               font=('Arial', 12), wraplength=550)
        title_label.pack(pady=10)

        # File selection frame
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=5)

        select_btn = tk.Button(file_frame, text='选择文件',
                               command=self._select_files, width=12)
        select_btn.pack(side=tk.LEFT, padx=5)

        select_folder_btn = tk.Button(file_frame, text='选择文件夹',
                                      command=self._select_folder, width=12)
        select_folder_btn.pack(side=tk.LEFT, padx=5)

        clear_btn = tk.Button(file_frame, text='清空列表',
                              command=self._clear_file_list, width=12)
        clear_btn.pack(side=tk.LEFT, padx=5)

        # File list
        list_frame = tk.Frame(self.root)
        list_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

        tk.Label(list_frame, text="待处理文件列表:", anchor=W).pack(fill=tk.X)

        # Listbox with scrollbar
        listbox_frame = tk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)

        # Configuration frame
        config_frame = tk.Frame(self.root)
        config_frame.pack(pady=10, padx=20, fill=tk.X)

        tk.Label(config_frame, text="压缩配置:").pack(side=tk.LEFT)

        self.profile_var = StringVar(value="default")
        self.profile_combo = ttk.Combobox(config_frame, textvariable=self.profile_var,
                                          state='readonly', width=20)
        self.profile_combo.pack(side=tk.LEFT, padx=10)
        self.profile_combo.bind('<<ComboboxSelected>>', self._on_profile_change)

        self.profile_desc_var = StringVar()
        tk.Label(config_frame, textvariable=self.profile_desc_var,
                 fg='gray').pack(side=tk.LEFT, padx=10)

        # Options frame
        options_frame = tk.Frame(self.root)
        options_frame.pack(pady=5, padx=20, fill=tk.X)

        self.recurse_var = BooleanVar()
        tk.Checkbutton(options_frame, text="递归处理子文件夹",
                       variable=self.recurse_var).pack(side=tk.LEFT)

        self.delete_source_var = BooleanVar()
        tk.Checkbutton(options_frame, text="完成后删除原文件",
                       variable=self.delete_source_var).pack(side=tk.LEFT, padx=20)


        # Control buttons
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=20)

        self.compress_btn = tk.Button(control_frame, text='开始压缩',
                                      command=self._start_compression,
                                      bg='#4CAF50', fg='black',
                                      font=('Arial', 12, 'bold'),
                                      width=15)
        self.compress_btn.pack()

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var,
                                            maximum=100)
        self.progress_bar.pack(pady=10, padx=20, fill=tk.X)

        # Setup drag and drop for macOS
        self._setup_drag_drop()

    def _setup_drag_drop(self):
        """Setup drag and drop functionality for macOS"""

        def drop_handler(event):
            # This is a simplified drag-drop handler
            # On macOS, you might need additional libraries like tkinterdnd2
            pass

        # Bind drag events
        self.root.bind('<Button-1>', drop_handler)

    def _select_files(self):
        """Open file dialog to select video files"""
        filetypes = [
            ('视频文件', ' '.join(f'*{ext}' for ext in VIDEO_EXTENSIONS)),
            ('所有文件', '*.*')
        ]

        files = filedialog.askopenfilenames(
            title="选择视频文件",
            filetypes=filetypes
        )

        for file_path in files:
            if file_path not in self.file_listbox.get(0, tk.END):
                self.file_listbox.insert(tk.END, file_path)

    def _select_folder(self):
        """Open folder dialog to select folder containing videos"""
        folder = filedialog.askdirectory(title="选择包含视频的文件夹")
        if folder:
            self._add_videos_from_folder(folder)

    def _add_videos_from_folder(self, folder_path: str):
        """Add all video files from folder to list"""
        folder = Path(folder_path)

        if self.recurse_var.get():
            # Recursive search
            for ext in VIDEO_EXTENSIONS:
                for file_path in folder.rglob(f'*{ext}'):
                    if str(file_path) not in self.file_listbox.get(0, tk.END):
                        self.file_listbox.insert(tk.END, str(file_path))
        else:
            # Only current folder
            for ext in VIDEO_EXTENSIONS:
                for file_path in folder.glob(f'*{ext}'):
                    if str(file_path) not in self.file_listbox.get(0, tk.END):
                        self.file_listbox.insert(tk.END, str(file_path))

    def _clear_file_list(self):
        """Clear the file list"""
        self.file_listbox.delete(0, tk.END)
        self.progress_var.set(0)

    def _load_config(self):
        """Load configuration from file or create default"""
        try:
            if not os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
                self.profiles = DEFAULT_CONFIG['profiles']
            else:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.profiles = config.get('profiles', DEFAULT_CONFIG['profiles'])

            # Update UI
            profile_names = list(self.profiles.keys())
            self.profile_combo['values'] = profile_names
            if profile_names:
                self.profile_var.set(profile_names[0])
                self._on_profile_change()

        except Exception as e:
            logging.error(f"加载配置失败: {e}")
            messagebox.showerror("错误", f"加载配置失败: {e}")

    def _on_profile_change(self, event=None):
        """Handle profile selection change"""
        profile_name = self.profile_var.get()
        if profile_name in self.profiles:
            desc = self.profiles[profile_name].get('description', '')
            self.profile_desc_var.set(desc)

    def _check_message_queue(self):
        """Process messages from compression worker thread"""
        while not self.queue.empty():
            message = self.queue.get()
            action = message.get("action", "")

            if action == "progress":
                self.progress_var.set(message['progress'])
                self.title_var.set(f"处理中: {message.get('filename', '')}")

            elif action == "error":
                messagebox.showerror("错误", f"处理失败！\n{message['error']}")
                self._reset_ui()

            elif action == "complete":
                self.progress_var.set(100)
                self.title_var.set(f"完成！处理了 {message['total']} 个文件")
                messagebox.showinfo("完成", f"成功处理了 {message['total']} 个文件")
                self._reset_ui()

        self.root.after(100, self._check_message_queue)

    def _reset_ui(self):
        """Reset UI to initial state"""
        self.compress_btn.config(state=tk.NORMAL, text='开始压缩')

    def _start_compression(self):
        """Start video compression process"""
        files = list(self.file_listbox.get(0, tk.END))
        if not files:
            messagebox.showwarning("提示", "请先选择要压缩的视频文件")
            return

        profile_name = self.profile_var.get()
        if profile_name not in self.profiles:
            messagebox.showwarning("提示", "请选择有效的压缩配置")
            return

        profile = self.profiles[profile_name]
        delete_source = self.delete_source_var.get()

        # Disable button and start compression
        self.compress_btn.config(state=tk.DISABLED, text='压缩中...')
        self.progress_var.set(0)

        threading.Thread(
            target=self._compression_worker,
            args=(files, profile, delete_source),
            daemon=True
        ).start()

    def _compression_worker(self, file_paths: List[str], profile: Dict[str, Any],
                            delete_source: bool):
        """Worker thread for compressing videos"""
        try:
            total_files = len(file_paths)
            processed = 0

            for i, file_path in enumerate(file_paths):
                if not os.path.exists(file_path):
                    continue

                # Update progress
                progress = (i / total_files) * 100
                self.queue.put({
                    "action": "progress",
                    "progress": progress,
                    "filename": os.path.basename(file_path)
                })

                # Process file
                success = self._compress_single_file(file_path, profile, delete_source)
                if success:
                    processed += 1

            # Signal completion
            self.queue.put({
                "action": "complete",
                "total": processed
            })

        except Exception as e:
            logging.error(f"压缩处理失败: {e}")
            self.queue.put({
                "action": "error",
                "error": str(e)
            })

    def _compress_single_file(self, input_path: str, profile: Dict[str, Any],
                              delete_source: bool) -> bool:
        """Compress a single video file using ffmpeg and output as .mp4"""
        try:
            # Generate output filename - always use .mp4 extension
            input_file = Path(input_path)
            output_file = input_file.parent / f"{input_file.stem}_compressed.mp4"

            # If the output file already exists, add a number suffix
            counter = 1
            while output_file.exists():
                output_file = input_file.parent / f"{input_file.stem}_compressed_{counter}.mp4"
                counter += 1

            # Build ffmpeg command
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-c:v', 'libx264',
                '-crf', str(profile['crf']),
                '-preset', profile['preset'],
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                '-f', 'mp4',  # Explicitly specify MP4 format
                '-y',  # Overwrite output file
                str(output_file)
            ]

            # Execute compression
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                # Success - delete source if requested
                if delete_source and output_file.exists():
                    input_file.unlink()
                logging.info(f"成功压缩: {input_path} -> {output_file}")
                return True
            else:
                logging.error(f"ffmpeg error for {input_path}: {result.stderr}")
                return False

        except Exception as e:
            logging.error(f"压缩文件 {input_path} 失败: {e}")
            return False


def setup_logging():
    """Configure application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('videoslim.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def main():
    """Application entry point"""
    setup_logging()

    root = tk.Tk()

    # macOS specific styling
    if hasattr(tk, 'Style'):
        style = ttk.Style()
        if 'aqua' in style.theme_names():
            style.theme_use('aqua')

    app = VideoSlimApp(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        logging.info("用户中断程序")


if __name__ == '__main__':
    main()