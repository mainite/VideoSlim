# Copyright (c) <2023> <hotMonk> <inite.cn>
import time
import tkinter
import tkinter.ttk
import logging
from queue import Queue
from tkinter import *
import webbrowser
import windnd
from tkinter import messagebox
from moviepy.editor import *
import requests
import os
import threading
import subprocess
from subprocess import CREATE_NO_WINDOW
import json

extention_lists = [".mp4", ".mkv", ".mov", ".avi"]


def fast_scandir(dir, ext):  # dir: str, ext: list
    # Thanks to @not2qbit in https://stackoverflow.com/questions/18394147/how-to-do-a-recursive-sub-folder-search-and-return-files-in-a-list?answertab=modifieddesc#tab-top 
    subfolders, files = [], []
    for f in os.scandir(dir):
        if f.is_dir():
            subfolders.append(f.path)
        if f.is_file():
            if os.path.splitext(f.name)[1].lower() in ext:
                files.append(f.path)

    for dir in list(subfolders):
        sf, f = fast_scandir(dir, ext)
        subfolders.extend(sf)
        files.extend(f)
    return subfolders, files


class Config:
    """
    配置类
    """

    class X264:
        """
        X264配置类
        """

        _crf = 23.5
        _preset = 8
        I = 600
        r = 4
        b = 3
        opencl_accerleration = False

        def __init__(self):
            # 默认配置
            self._crf = 23.5
            self._preset = 8
            self.opencl_acceleration = False
            self.I = 600
            self.r = 4
            self.b = 3

        def __init__(self, val: dict):
            self._crf = val["crf"]
            self._preset = val["preset"]
            self.opencl_acceleration = val["opencl_acceleration"]
            self.I = val["I"]
            self.r = val["r"]
            self.b = val["b"]

        @property
        def crf(self):
            return self._crf

        @crf.setter
        def crf(self, val):
            """
            设置crf值 [0,51]
            :param val:
            :return:
            """
            val = max(0, val)
            val = min(51, val)
            self._crf = val

        @property
        def preset(self):
            return self._preset

        @preset.setter
        def preset(self, val):
            """
            设置preset值 [0,9]
            :param val:
            :return:
            """
            val = max(0, val)
            val = min(9, val)
            self._preset = val

    def __init__(self):
        self.name = "Default"
        self.X264 = self.X264()

    def __init__(self, val: dict):
        """
        使用完整的配置字典进行初始化
        :param val: 配置字典，需要完整
        """
        self.name = val["name"]
        self.X264 = self.X264(val["x264"])

    @staticmethod
    def fixDict(config_dict: dict) -> dict:
        """
        修复残缺参数的配置字典为完整的配置字典
        :param config_dict: 配置字典
        :return:
        """
        # 检查参数是否完整
        # x264
        if "x264" not in config_dict:
            config_dict["x264"] = {
                "crf": 23.5,
                "preset": 8,
                "I": 600,
                "r": 4,
                "b": 3,
                "opencl_acceleration": False
            }
        if "crf" not in config_dict["x264"]:
            config_dict["x264"]["crf"] = 23.5
        if "preset" not in config_dict["x264"]:
            config_dict["x264"]["preset"] = 8
        if "I" not in config_dict["x264"]:
            config_dict["x264"]["I"] = 600
        if "r" not in config_dict["x264"]:
            config_dict["x264"]["r"] = 4
        if "b" not in config_dict["x264"]:
            config_dict["x264"]["b"] = 3
        if "opencl_acceleration" not in config_dict["x264"]:
            config_dict["x264"]["opencl_acceleration"] = True

        return config_dict


class DragDropApp():
    def __init__(self, root):

        # 定义当前版本号
        self.Version_number = 'v1.6'

        self.root = root
        self.root.title("VideoSlim 视频压缩  " + self.Version_number)
        self.root.resizable(width=False, height=False)
        self.root.iconbitmap(os.path.join(os.getcwd(), "./tools/icon.ico"))
        screenwidth = self.root.winfo_screenwidth()
        screenheight = self.root.winfo_screenheight()
        size = '%dx%d+%d+%d' % (527, 351, (screenwidth - 527) / 2, (screenheight - 351) / 2)
        self.root.geometry(size)

        # 创建超链接标签
        hyperlink_label = Label(self.root, text="github", fg="#cdcdcd", cursor="hand2")
        hyperlink_label.pack(side=TOP, anchor=NE, padx=25, pady=8)
        hyperlink_label.bind("<Button-1>",
                             lambda event: webbrowser.open_new_tab("https://github.com/mainite/VideoSlim"))

        # 提示文本
        self.Label1_title = StringVar()
        self.Label1_title.set('将视频拖拽到此窗口:')
        self.label1 = Label(self.root, textvariable=self.Label1_title, anchor=W)
        self.label1.place(x=26, y=8, width=300, height=24)

        # 文件框
        self.text_box = Text(self.root, width=100, height=20)
        self.text_box.place(x=24, y=40, width=480, height=220)

        # 清空按钮
        button2_title = StringVar()
        button2_title.set('清空')
        button2 = Button(self.root, textvariable=button2_title, command=self.ClearContent)  # ,command=按钮点击触发的函数
        button2.place(x=168, y=291, width=88, height=40)

        # 压缩按钮
        button1_title = StringVar()
        button1_title.set('压缩')
        self.button1 = Button(self.root, textvariable=button1_title, command=self.DoCompress)  # ,command=按钮点击触发的函数
        self.button1.place(x=280, y=291, width=88, height=40)

        # 选择框
        self.recurse_var = BooleanVar()
        recurse_check = Checkbutton(self.root, text="递归(至最深深度)子文件夹里面的视频", variable=self.recurse_var,
                                    onvalue=True, offvalue=False)
        recurse_check.place(x=20, y=261)

        self.delete_source_var = BooleanVar()
        delete_source_check = Checkbutton(self.root, text="完成后删除旧文件", variable=self.delete_source_var,
                                          onvalue=True, offvalue=False)
        delete_source_check.place(x=20, y=287)

        self.delete_audio_var = BooleanVar()
        delete_audio_check = Checkbutton(self.root, text="删除音频轨道", variable=self.delete_audio_var, onvalue=True,
                                         offvalue=False)
        delete_audio_check.place(x=20, y=313)

        # 拖拽控件
        windnd.hook_dropfiles(self.root, func=self.drop_file)

        # 配置选择功能
        # self.label1 = Label(self.root, textvariable=self.Label1_title, anchor=W)
        # self.label1.place(x=26, y=8, width=300, height=24)
        config_label = Label(self.root, text="选择参数配置")
        config_label.place(x=388, y=265)

        self.configs_name_list = []
        self.configs_dict = {}
        self.read_config()

        # 如果没有检测到配置文件，退出
        if len(self.configs_name_list) <= 0:
            self.root.destroy()
            return

        self.select_config_name = StringVar(self.root, value="default")
        config_combobox = tkinter.ttk.Combobox(self.root, height=10, width=10, state='readonly',
                                               values=self.configs_name_list, textvariable=self.select_config_name)
        config_combobox.place(x=388, y=291)

        # 压缩子进程通讯
        self.queue = Queue()
        self.root.after(1000, self.check_message_queue)

    def drop_file(self, event):
        files = '\n'.join((item.decode('gbk') for item in event))
        self.text_box.insert(END, files + "\n")

    def ClearContent(self):
        self.text_box.delete("1.0", END)

    @staticmethod
    def GetSaveOutFileName(filename):
        file_name, file_ext = os.path.splitext(filename)
        save_out_name = file_name + "_x264.mp4"
        return save_out_name

    def check_message_queue(self):
        """
        定期检查消息队列
        :return:
        """
        while not self.queue.empty():
            item = self.queue.get()
            if item["action"] == "start":
                # 开始处理
                self.Label1_title.set(f"[{item["index"]}/{item["total"]}]当前处理文件：{item["filename"]}")
                self.label1.update()
            elif item["action"] == "error":
                # 返回错误
                messagebox.showerror("错误", f"发生错误！\n{item["err"].__str__()}")
            elif item["action"] == "finish_all":
                messagebox.showinfo("提示", "转换完成")
                self.button1.config(state=tkinter.NORMAL)
            else:
                pass

        self.root.after(1000, self.check_message_queue)

    # 压缩
    def compress(self, config, delete_audio, delete_source, lines):
        index = 0
        for file_name in lines:
            index += 1
            if file_name == "":
                continue

            # 如果已经存在 old_atemp.mp4 等文件的时候，会卡住（因为 ffmpeg 会等待文件覆写确认 (y/n) ）
            # 检查如果上次的临时文件还在，则删除
            if os.path.exists("./old_atemp.wav"):
                os.remove("./old_atemp.wav")
            if os.path.exists("./old_atemp.mp4"):
                os.remove("./old_atemp.mp4")
            if os.path.exists("./old_vtemp.mp4"):
                os.remove("./old_vtemp.mp4")

            save_out_name = self.GetSaveOutFileName(file_name)

            # 判断视频是否拥有音频轨道
            video = VideoFileClip(file_name)
            commands = []
            if video.audio is None or delete_audio:
                logging.info("视频没有音频轨道")

                command1 = rf'.\tools\x264_64-8bit.exe --crf {config.X264.crf} --preset {config.X264.preset} -I {config.X264.I} -r {config.X264.r} -b {config.X264.b} --me umh -i 1 --scenecut 60 -f 1:1 --qcomp 0.5 --psy-rd 0.3:0 --aq-mode 2 --aq-strength 0.8 -o "{save_out_name}"  "{file_name}"'
                commands.append(command1)

                time.sleep(1)
            else:
                logging.info("视频有音频轨道")

                commands.append(
                    rf'.\tools\ffmpeg.exe -i {file_name} -vn -sn -v 0 -c:a pcm_s16le -f wav ".\old_atemp.wav"')

                commands.append(
                    r'.\tools\neroAacEnc.exe -ignorelength -lc -br 128000 -if ".\old_atemp.wav" -of ".\old_atemp.mp4"')

                command3 = rf'.\tools\x264_64-8bit.exe --crf {config.X264.crf} --preset {config.X264.preset} -I {config.X264.I} -r {config.X264.r} -b {config.X264.b} --me umh -i 1 --scenecut 60 -f 1:1 --qcomp 0.5 --psy-rd 0.3:0 --aq-mode 2 --aq-strength 0.8 -o ".\old_vtemp.mp4"  "{file_name}"'
                # opencl 使用 gpu 辅助进行
                if config.X264.opencl_acceleration:
                    command3 += ' --opencl'
                commands.append(command3)

                commands.append(
                    rf'.\tools\mp4box.exe -add ".\old_vtemp.mp4#trackID=1:name=" -add ".\old_atemp.mp4#trackID=1:name=" -new "{self.GetSaveOutFileName(file_name)}"')

                time.sleep(1)

            try:
                self.queue.put({"action": "start", "index": index, "total": len(lines), "filename": file_name})
                for command in commands:
                    logging.info(f"正在执行命令: {command}")
                    subprocess.check_call(command, creationflags=CREATE_NO_WINDOW)
                if delete_source:
                    os.remove(file_name)
            except Exception as e:
                logging.error(f"命令执行失败: {e}")
                self.queue.put({"action": "error", "err": e})
                return
            finally:
                # 删除临时文件
                if os.path.exists("./old_atemp.wav"):
                    os.remove("./old_atemp.wav")
                if os.path.exists("./old_atemp.mp4"):
                    os.remove("./old_atemp.mp4")
                if os.path.exists("./old_vtemp.mp4"):
                    os.remove("./old_vtemp.mp4")
            self.queue.put({"action": "finish", "index": index, "filename": file_name})

            video.close()

        self.queue.put({"action": "finish_all"})

    def DoCompress(self):
        # 缓存选择的配置文件，补充配置缺失的值
        config = self.configs_dict[self.select_config_name.get()]
        delete_source = self.delete_source_var.get()
        delete_audio = self.delete_audio_var.get()

        # 获取文件列表
        text_content = self.text_box.get("1.0", END)
        if text_content == "":
            messagebox.showwarning("提示", "请先拖拽文件到此处")
            return False

        lines = text_content.splitlines()
        if len(lines) <= 1:
            messagebox.showwarning("提示", "请先拖拽文件到此处")
            return False
        lines.remove("")

        # 预处理，将文件夹处理成文件
        for file_name in lines:
            if os.path.isdir(file_name):
                _, files = fast_scandir(file_name, extention_lists)
                lines.extend(files)
                time.sleep(3)
                continue

        # 子线程压缩
        threading.Thread(target=self.compress, args=(config, delete_audio, delete_source, lines)).start()
        self.button1.config(state=tkinter.DISABLED)

    def version_number_detection(self):
        url = f"https://api.github.com/repos/mainite/VideoSlim/releases"
        response = requests.get(url)
        data = response.json()
        if data and len(data):
            latest_release = data[0]
            if latest_release['tag_name'] != self.Version_number:
                messagebox.showinfo("更新提示", "有新版本可用，请前往官网更新")

    def read_config(self):
        """
        读取配置参数文件
        :return: void
        """
        try:
            if not os.path.exists("config.json"):
                messagebox.showwarning("警告", "没有检测到配置文件，将生成一个配置文件")
                f = open("config.json", "w", encoding="utf-8")
                f.write(r'''{
  "comment": "参数配置文件，不写会取用内置默认值。如果读取不到，说明配置文件不合法，请检查配置文件。具体参数的意思可以在README.md中看到",
  "configs": {
    "default": {
      "x264": {
        "crf": 23.5,
        "preset": 8,
        "I": 600,
        "r": 4,
        "b": 3
      }
    },
    "custom_template": {
      "x264": {
        "crf": 30,
        "preset": 8,
        "I": 600,
        "r": 4,
        "b": 3
      }
    },
    "default_gpu": {
      "x264": {
        "opencl_acceleration": true
      }
    }
  }
}''')
                f.close()
                return

            configs_file = open("config.json", encoding="utf-8")
            configs_json = json.load(configs_file)
            configs = configs_json["configs"]
        except:
            # 读取失败，放弃读取
            return

        for name, param in configs.items():
            # # 检查参数是否完整
            # # x264
            # if "x264" not in param:
            #     param["x264"] = {
            #         "crf": 23.5,
            #         "preset": 8,
            #         "I": 600,
            #         "r": 4,
            #         "b": 3
            #     }
            # if "crf" not in param["x264"]:
            #     param["x264"]["crf"] = 23.5
            # if "preset" not in param["x264"]:
            #     param["x264"]["preset"] = 8
            # if "I" not in param["x264"]:
            #     param["x264"]["I"] = 600
            # if "r" not in param["x264"]:
            #     param["x264"]["r"] = 4
            # if "b" not in param["x264"]:
            #     param["x264"]["b"] = 3
            # if "opencl_acceleration" not in param["x264"]:
            #     param["x264"]["opencl_acceleration"] = False

            param = Config.fixDict(param)

            logging.info("读取到配置文件 {}，参数为 {}".format(name, param))

            # 检查参数是否合法
            if name in self.configs_name_list or name in self.configs_dict:
                messagebox.showwarning("警告", "读取到重名的配置文件 {}\n将仅读取最前的配置".format(name))
                continue
            if param["x264"]["crf"] > 51 or param["x264"]["crf"] < 0:
                messagebox.showwarning("警告",
                                       "配置文件 {} 中的 crf 参数不合法\n将放弃读取该配置".format(name))
                continue
            if param["x264"]["preset"] < 0 or param["x264"]["preset"] > 9:
                messagebox.showwarning("警告",
                                       "配置文件 {} 中的 preset 参数不合法\n将放弃读取该配置".format(name))
                continue

            # 合法，登记配置
            config_dict = param
            config_dict["name"] = name
            self.configs_dict[name] = Config(config_dict)
            self.configs_name_list.append(name)

        configs_file.close()
        return


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    root = Tk()
    app = DragDropApp(root)
    t1 = threading.Thread(target=app.version_number_detection)
    t1.start()
    root.mainloop()
