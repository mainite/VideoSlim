import os
import threading
import webbrowser
from queue import Queue

import tkinter as tk
from tkinter import messagebox, StringVar, BooleanVar, END, TOP, W, NE
import tkinter.ttk as ttk
import windnd

from .message import *
from .controller import Controller


class View:
    """Main application class for VideoSlim"""

    def __init__(self, root: tk.Tk, controller: Controller):
        """
        Initialize VideoSlim application

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.controller = controller
        self.queue = Queue()
        self.configs_name_list = []
        self.configs_dict = {}

        self._setup_ui()

        # Setup message queue checking
        self.root.after(1000, self._check_message_queue)

    def _setup_ui(self):
        """Set up the application's user interface"""
        # Configure root window
        self.root.title(f"VideoSlim 视频压缩 {self.controller.meta_info['VERSION']}")
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
        queue = self.controller.queue
        while not queue.empty():
            message = queue.get()

            if not isinstance(message, Message):
                continue

            if isinstance(message, WarningMessage):
                # Display warning message
                messagebox.showwarning(message.title, message.message)
                continue

            if isinstance(message, UpdateMessage):
                # Update message box
                messagebox.showinfo("更新提示", "有新版本可用，请前往官网更新")
                continue

            if isinstance(message, ErrorMessage):
                # Display error message
                messagebox.showerror(message.title, message.message)
                continue

            if isinstance(message, ExitMessage):
                # Exit application
                self.root.destroy()
                continue

            if isinstance(message, ConfigLoadMessage):
                # 将加载的配置显示在选项框，并自动选中第一个
                self.config_combobox.config(values=message.config_names)
                self.select_config_name.set(message.config_names[0])
                continue

            if isinstance(message, CompressionStartMessage):
                # Disable button
                self.compress_btn.config(state=tk.DISABLED)
                continue

            if isinstance(message, CompressionProgressMessage):
                # Update progress display
                self.title_var.set(f"[{message.current}/{message.total}] "
                                   f"当前处理文件：{message.file_name}，进度：{message.current / message.total: .2f}%")
                self.title_label.update()
                continue

            if isinstance(message, CompressionErrorMessage):
                # Display error message
                messagebox.showerror(message.title, message.message)
                self.compress_btn.config(state=tk.NORMAL)

            if isinstance(message, CompressionFinishedMessage):
                # All files processed
                self.title_var.set(f"处理完成！已经处理 {message.total} 个文件")
                self.title_label.update()
                messagebox.showinfo("提示", "转换完成")
                self.compress_btn.config(state=tk.NORMAL)

        # Schedule next check
        self.root.after(1000, self._check_message_queue)

    def _start_compression(self):
        """Start video compression process"""
        # Get selected configuration

        config_name = self.select_config_name.get()
        delete_source = self.delete_source_var.get()
        delete_audio = self.delete_audio_var.get()
        recurse = self.recurse_var.get()

        # Get file list
        text_content = self.text_box.get("1.0", END)
        lines = [line for line in text_content.splitlines() if line.strip()]

        if not lines:
            messagebox.showwarning("提示", "请先拖拽文件到此处")
            return

        # 禁用按钮
        self.compress_btn.config(state=tk.DISABLED)

        self.controller.compression(config_name, delete_audio, delete_source, lines, recurse)
