import os
import tkinter as tk
import tkinter.ttk as ttk
import webbrowser
from queue import Queue
from tkinter import END, NE, TOP, BooleanVar, StringVar, W, messagebox

import windnd

from src import meta, utils
from src.controller import Controller
from src.model import message
from src.service.message import MessageService
from src.service.video import VideoService


class View:
    """
    VideoSlim应用程序的主视图类

    负责创建和管理用户界面，处理用户交互，并显示应用程序的状态和结果。
    实现了视频文件的拖拽功能、压缩控制和进度显示等核心功能。
    """

    def __init__(self, root: tk.Tk, controller: Controller):
        """
        初始化VideoSlim应用程序视图

        Args:
            root: Tkinter根窗口对象
            controller: 控制器对象，用于处理业务逻辑
        """
        self.root = root
        self.controller = controller
        self.queue = Queue()
        self.configs_name_list = []
        self.configs_dict = {}

        self._setup_ui()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Setup message queue checking
        self.root.after(50, self._check_message_queue)

    def _setup_ui(self):
        """
        设置应用程序的用户界面

        创建并配置所有UI组件，包括窗口、按钮、文本框、复选框等，
        设置窗口位置、大小、图标和拖拽功能。
        """
        # Configure root window
        self.root.title(f"VideoSlim 视频压缩 {meta.VERSION}")
        self.root.resizable(width=False, height=False)

        # Set icon if available
        icon_path = utils.get_path("./tools/icon.ico")
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
        github_link.bind(
            "<Button-1>",
            lambda event: webbrowser.open_new_tab(
                "https://github.com/DongGuoZheng/VideoSlim"
            ),
        )

        # Title label
        self.title_var = StringVar()
        self.title_var.set("将视频拖拽到此窗口:")
        self.title_label = tk.Label(self.root, textvariable=self.title_var, anchor=W)
        self.title_label.place(x=26, y=8, width=380, height=24)

        # File list text box
        self.text_box = tk.Text(self.root, width=100, height=20)
        self.text_box.place(x=24, y=40, width=480, height=190)

        # Progress bar
        self.cur_bar = ttk.Progressbar(self.root, orient="horizontal", maximum=100)
        self.cur_bar.place(x=24, y=230, width=480, height=20)

        self.total_bar = ttk.Progressbar(self.root, orient="horizontal", maximum=100)
        self.total_bar.place(x=24, y=250, width=480, height=10)

        # Clear button
        clear_btn_text = StringVar()
        clear_btn_text.set("清空")
        clear_btn = tk.Button(
            self.root, textvariable=clear_btn_text, command=self._clear_file_list
        )
        clear_btn.place(x=168, y=291, width=88, height=40)

        # Compress button
        compress_btn_text = StringVar()
        compress_btn_text.set("压缩")
        self.compress_btn = tk.Button(
            self.root, textvariable=compress_btn_text, command=self._start_compression
        )
        self.compress_btn.place(x=280, y=291, width=88, height=40)

        # Options checkboxes
        self.recurse_var = BooleanVar()
        recurse_check = tk.Checkbutton(
            self.root,
            text="递归(至最深深度)子文件夹里面的视频",
            variable=self.recurse_var,
            onvalue=True,
            offvalue=False,
        )
        recurse_check.place(x=20, y=261)

        self.delete_source_var = BooleanVar()
        delete_source_check = tk.Checkbutton(
            self.root,
            text="完成后删除旧文件",
            variable=self.delete_source_var,
            onvalue=True,
            offvalue=False,
        )
        delete_source_check.place(x=20, y=287)

        self.delete_audio_var = BooleanVar()
        delete_audio_check = tk.Checkbutton(
            self.root,
            text="删除音频轨道",
            variable=self.delete_audio_var,
            onvalue=True,
            offvalue=False,
        )
        delete_audio_check.place(x=20, y=313)

        # Setup drag and drop
        # force_unicode=True 让 windnd 使用 Unicode (W) 版 Win32 API(DragQueryFileW)，
        # 避免系统 ANSI 代码页无法表示的字符（如 emoji）被替换成 '?' 导致路径失效
        windnd.hook_dropfiles(self.root, func=self._on_drop_files, force_unicode=True)

        # Configuration selection
        config_label = tk.Label(self.root, text="选择参数配置")
        config_label.place(x=388, y=265)

        self.select_config_name = StringVar(self.root, value="default")
        self.config_combobox = ttk.Combobox(
            self.root,
            height=10,
            width=10,
            state="readonly",
            values=[],
            textvariable=self.select_config_name,
        )
        self.config_combobox.place(x=388, y=291)

    def _on_drop_files(self, file_paths):
        """
        处理拖拽到应用程序中的文件

        Args:
            file_paths: 拖拽的文件路径列表（force_unicode=True 时为 str 列表）
        """
        files = "\n".join(file_paths)
        self.text_box.insert(END, files + "\n")

    def _on_close(self):
        """
        处理应用程序关闭事件

        当用户点击关闭按钮时，会调用此方法。
        该方法会发送一个退出消息到消息队列，通知其他组件应用程序正在关闭。
        """
        # 如果有正在处理的任务，提示用户确认是否继续
        if VideoService.get_instance().is_processing():
            response = messagebox.askyesno(
                "确认", "当前有正在处理的任务，是否关闭程序？"
            )
            if not response:
                return

        self.controller.close()

    def _clear_file_list(self):
        """
        清空文件列表文本框
        """
        self.text_box.delete("1.0", END)

    def _check_message_queue(self):
        """
        检查消息队列并处理接收到的消息

        定期检查应用程序的消息队列，根据消息类型执行相应的处理逻辑，
        包括显示警告、错误、更新提示，处理压缩进度和完成消息等。
        """

        while True:
            msg = MessageService.get_instance().try_receive_message()

            match msg:
                case None:
                    break
                case message.WarningMessage(title=t, message=m):
                    # Display warning message
                    messagebox.showwarning(t, m)
                case message.UpdateMessage():
                    # Update message box
                    messagebox.showinfo("更新提示", "有新版本可用，请前往官网更新")
                case message.ErrorMessage(title=t, message=m):
                    # Display error message
                    messagebox.showerror(t, m)
                case message.ExitMessage():
                    # Exit application
                    self.root.destroy()
                case message.ConfigLoadMessage(config_names=config_names):
                    # 将加载的配置显示在选项框，并自动选中第一个
                    self.config_combobox.config(values=config_names)
                    self.select_config_name.set(config_names[0])
                case message.CompressionStartMessage():
                    # Disable button
                    self.compress_btn.config(state=tk.DISABLED)
                    self.cur_bar["value"] = 0
                    self.cur_bar.update()
                    self.total_bar["value"] = 0
                    self.total_bar.update()
                case message.CompressionCurrentProgressMessage(
                    file_name=_, current=current, total=total
                ):
                    self.cur_bar["value"] = current / total * 100
                    self.cur_bar.update()
                case message.CompressionTotalProgressMessage(
                    current=current, total=total, file_name=file_name
                ):
                    # Update progress display
                    self.title_var.set(
                        f"[{current}/{total}] "
                        f"当前处理文件：{file_name}，进度：{current / total * 100: .2f}%"
                    )
                    self.title_label.update()
                    self.total_bar["value"] = (current / total) * 100
                    self.total_bar.update()
                case message.CompressionErrorMessage(title=t, message=m):
                    # Display error message
                    messagebox.showerror(t, m)
                    self.compress_btn.config(state=tk.NORMAL)
                case message.CompressionFinishedMessage(total=total):
                    # All files processed
                    messagebox.showinfo("提示", "转换结束")
                    self.title_var.set(f"处理完成！已经处理 {total} 个文件")
                    self.title_label.update()
                    self.compress_btn.config(state=tk.NORMAL)

                    self.cur_bar["value"] = 0
                    self.cur_bar.update()
                    self.total_bar["value"] = 100
                    self.total_bar.update()
                case _:
                    continue

        # Schedule next check
        self.root.after(1000, self._check_message_queue)

    def _start_compression(self):
        """
        启动视频压缩过程

        从UI获取用户选择的配置和选项，验证文件列表，然后调用控制器
        开始视频压缩任务，并禁用压缩按钮以防止重复点击。
        """
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

        self.controller.compression(
            config_name, delete_audio, delete_source, lines, recurse
        )
