# Copyright (c) <2023> <hotMonk> <inite.cn>
import time
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

extention_lists = [".mp4",".mkv",".mov",".avi"]

def fast_scandir(dir, ext):    # dir: str, ext: list
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

class DragDropApp():
    def __init__(self, root):

        #定义当前版本号
        self.Version_number = 'v1.5'

        self.root = root
        self.root.title("VideoSlim 视频压缩  "+self.Version_number)
        self.root.resizable(width=False, height=False)
        self.root.iconbitmap(os.path.join(os.getcwd(), "./tools/icon.ico"))
        screenwidth = self.root.winfo_screenwidth()
        screenheight = self.root.winfo_screenheight()
        size = '%dx%d+%d+%d' % (527, 351, (screenwidth - 527) / 2, (screenheight - 351) / 2)
        self.root.geometry(size)

        # 创建超链接标签
        hyperlink_label = Label(self.root, text="github", fg="#cdcdcd", cursor="hand2")
        hyperlink_label.pack(side=TOP, anchor=NE, padx=25, pady=8)
        hyperlink_label.bind("<Button-1>", lambda event: webbrowser.open_new_tab("https://github.com/mainite/VideoSlim"))

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
        button1 = Button(self.root, textvariable=button1_title, command=self.DoCompress)  # ,command=按钮点击触发的函数
        button1.place(x=280, y=291, width=88, height=40)

        # 选择框
        self.recurse_var = BooleanVar()
        recurse_check = Checkbutton(self.root, text="递归(至最深深度)子文件夹里面的视频", variable=self.recurse_var,
                                          onvalue=True, offvalue=False)
        recurse_check.place(x=20,y=261)
        
        self.delete_source_var = BooleanVar()
        delete_source_check = Checkbutton(self.root, text="完成后删除旧文件", variable=self.delete_source_var,
                                          onvalue=True, offvalue=False)
        delete_source_check.place(x=20, y=287)

        self.delete_audio_var = BooleanVar()
        delete_audio_check = Checkbutton(self.root, text="删除音频轨道", variable=self.delete_audio_var, onvalue=True,offvalue=False)
        delete_audio_check.place(x=20, y=313)

        # 拖拽控件
        windnd.hook_dropfiles(self.root, func=self.drop_file)

    def drop_file(self, event):
        files = '\n'.join((item.decode('gbk') for item in event))
        self.text_box.insert(END, files + "\n")

    def ClearContent(self):
        self.text_box.delete("1.0", END)

    def GetSaveOutFileName(self, filename):
        file_name, file_ext = os.path.splitext(filename)
        save_out_name = file_name + "_x264.mp4"
        return save_out_name

    def DoCompress(self):
        text_content = self.text_box.get("1.0", END)
        if text_content != "":
            lines = text_content.splitlines()
            if len(lines) <= 1:
                messagebox.showwarning("提示", "请先拖拽文件到此处")
                return False
            lines.remove("")
            index = 0
            for file_name in lines:
                index += 1
                if os.path.isdir(file_name):
                    _,files = fast_scandir(file_name,extention_lists)
                    lines.extend(files)
                    self.Label1_title.set(f"[{index}/{len(lines)}]从该文件夹递归添加文件：{os.path.basename(file_name)}")
                    self.label1.update()
                    time.sleep(3)
                    continue
                if file_name != "":
                    self.Label1_title.set(f"[{index}/{len(lines)}]当前处理文件：{os.path.basename(file_name)}")
                    self.label1.update()
                    save_out_name = self.GetSaveOutFileName(file_name)
                    # 判断视频是否拥有音频轨道
                    video = VideoFileClip(file_name)
                    if video.audio is None or self.delete_audio_var.get():
                        print("视频没有音频轨道")

                        command1 = r'.\tools\x264_32-8bit.exe --crf 23.5 --preset 8 -I 600 -r 4 -b 3 --me umh -i 1 --scenecut 60 -f 1:1 --qcomp 0.5 --psy-rd 0.3:0 --aq-mode 2 --aq-strength 0.8 -o "{}"  "{}"'
                        subprocess.check_call(command1.format(save_out_name,file_name),creationflags=CREATE_NO_WINDOW)

                        # # 莫名其妙的占用进程，导致文件无法删除
                        # current_pid = os.getpid()
                        # for proc in psutil.process_iter():
                        #     if proc.ppid() == current_pid:
                        #         if proc.name() == 'ffmpeg-win64-v4.2.2.exe':
                        #             proc.kill()
                        #             break

                        time.sleep(1)
                        if self.delete_source_var.get():
                            os.remove(file_name)


                    else:
                        print("视频有音频轨道")
                        command1 = [r'.\tools\ffmpeg.exe', '-i', file_name, '-vn', '-sn', '-v', '0', '-c:a', 'pcm_s16le', '-f', 'wav', ".\old_atemp.wav"]
                        command2 = r'.\tools\neroAacEnc.exe -ignorelength -lc -br 128000 -if ".\old_atemp.wav" -of ".\old_atemp.mp4"'
                        command3 = r'.\tools\x264_64-8bit.exe --crf 23.5 --preset 8 -I 600 -r 4 -b 3 --me umh -i 1 --scenecut 60 -f 1:1 --qcomp 0.5 --psy-rd 0.3:0 --aq-mode 2 --aq-strength 0.8 -o ".\old_vtemp.mp4"  "{}"'
                        command4 = r'.\tools\mp4box.exe -add ".\old_vtemp.mp4#trackID=1:name=" -add ".\old_atemp.mp4#trackID=1:name=" -new "{}"'
                        command5 = "del .\\old_atemp.mp4 .\\old_vtemp.mp4"
                        command6 = r'del "{}"'

                        try:
                            process1 = subprocess.Popen(command1,shell=True,
                                                  creationflags=CREATE_NO_WINDOW)
                            process1.wait()
                            process1.kill()
                            subprocess.check_call(command2,shell=True,
                                                  creationflags=CREATE_NO_WINDOW
                                                  )
                            subprocess.check_call(command3.format(file_name),creationflags=CREATE_NO_WINDOW)
                            subprocess.check_call(command4.format(save_out_name),creationflags=CREATE_NO_WINDOW)
                            # subprocess.check_call(command4,cwd=os.getcwd())
                            # 莫名其妙的占用进程，导致文件无法删除
                            # current_pid = os.getpid()
                            # for proc in psutil.process_iter():
                            #     if proc.ppid() == current_pid:
                            #         if proc.name() == 'ffmpeg-win64-v4.2.2.exe':
                            #             proc.kill()
                            #             break

                            time.sleep(1)
                            video.close()
                            if self.delete_source_var.get():
                                os.remove(file_name)
                                
                        except Exception as err:
                            messagebox.showerror("错误","发生错误!\n"+err.__str__())
                        finally:
                            os.remove("./old_atemp.wav")
                            os.remove("./old_atemp.mp4")
                            os.remove("./old_vtemp.mp4")


            # 弹出信息框
            messagebox.showinfo("提示", "转换完成")

    def version_number_detection(self):
        url = f"https://api.github.com/repos/mainite/VideoSlim/releases"
        response = requests.get(url)
        data = response.json()
        if data and len(data):
            latest_release = data[0]
            if latest_release['tag_name'] != self.Version_number:
                messagebox.showinfo("更新提示", "有新版本可用，请前往官网更新")


if __name__ == '__main__':
    root = Tk()
    app = DragDropApp(root)
    t1 = threading.Thread(target=app.version_number_detection)
    t1.start()
    root.mainloop()