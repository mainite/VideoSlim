#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VideoSlim - A video compression application using x264
Refactored version: v1.8
"""

import datetime
import logging
import os
import tkinter as tk

from src import meta
from src.controller import Controller
from src.service import init_services
from src.view import View


def setup_logging():
    """
    配置日志记录功能

    每次启动都会在 log 文件夹下生成一个以当前时间戳命名的日志文件，
    便于区分不同次运行产生的日志。
    """
    os.makedirs(meta.LOG_DIR, exist_ok=True)
    log_file_path = os.path.join(
        meta.LOG_DIR,
        datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log",
    )

    logging.basicConfig(
        level=logging.DEBUG,
        filename=log_file_path,
        filemode="w",
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8",
    )


def main():
    """
    应用程序的主入口函数

    该函数会：
    1. 配置日志记录系统
    2. 初始化所有服务（配置、消息、存储、更新）
    3. 创建Tkinter根窗口
    4. 初始化视图和控制器
    5. 启动Tkinter主事件循环
    """
    setup_logging()

    init_services()

    root = tk.Tk()
    app = View(root, Controller())
    root.mainloop()


if __name__ == "__main__":
    main()
