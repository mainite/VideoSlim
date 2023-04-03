from tkinter import *
import os
import windnd
import subprocess
from tkinter import filedialog

# 创建 STARTUPINFO 对象
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

class DragDropApp(Tk):
    def __init__(self):
        super().__init__()
        self.title("VideoSlim 视频压缩")


        self.resizable(width=False, height=False)
        screenwidth = self.winfo_screenwidth()
        screenheight = self.winfo_screenheight()
        size = '%dx%d+%d+%d' % (527, 351, (screenwidth - 527) / 2, (screenheight - 351) / 2)
        self.geometry(size)

        # self.iconbitmap(设置软件图标，ICO图标完整路径)
        # self.bind('1',给窗口绑定事件函数)

        Label1_title = StringVar()
        Label1_title.set('将视频拖拽到此窗口:')
        Label1 = Label(self, textvariable=Label1_title, anchor=W)
        Label1.place(x=26, y=8, width=160, height=24)

        self.text_var = StringVar()
        self.text_var.set("将视频拖拽到此窗口")
        self.text_box = Text(self, width=100, height=20)
        self.text_box.place(x=24, y=40, width=480, height=232)


        button2_title = StringVar()
        button2_title.set('清空')
        button2 = Button(self, textvariable=button2_title,command=self.ClearContent)  # ,command=按钮点击触发的函数
        button2.place(x=168, y=291, width=88, height=40)
        # 按钮2.bind('1',给按钮绑定事件函数)

        button1_title = StringVar()
        button1_title.set('压缩')
        button1 = Button(self, textvariable=button1_title ,command=self.DoCompress)  # ,command=按钮点击触发的函数
        button1.place(x=280, y=291, width=88, height=40)



        windnd.hook_dropfiles(self, func=self.drop_file)

    def ClearContent(self):
        self.text_box.delete("1.0", END)



    def drop_file(self, event):
        files = '\n'.join((item.decode('gbk') for item in event))
        self.text_box.insert(END, files+"\n")


    def MakeBatCmd(self,filename):
        file_name, file_ext = os.path.splitext(filename)
        new_file_name = file_name + "_x264.mp4"
        batCmd = "compress.bat " + filename + " " + new_file_name
        return new_file_name


    def DoCompress(self):
        text_content = self.text_box.get("1.0",END)

        if text_content != "":
            lines = text_content.splitlines()
            for lin in lines:
                new_file_name = self.MakeBatCmd(lin)
                args = ["Hello","World"]
                subprocess.call(['compress.bat', lin, new_file_name], startupinfo=startupinfo)
                print("has finished executing.")

        else:
            print("No video file")

app = DragDropApp()
app.mainloop()