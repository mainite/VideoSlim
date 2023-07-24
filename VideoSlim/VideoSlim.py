# Copyright (c) <2023> <hotMonk> <inite.cn>

from tkinter import *
import os
import webbrowser
import windnd

class DragDropApp(Tk):
    def __init__(self):
        super().__init__()
        self.title("VideoSlim 视频压缩")
        self.resizable(width=False, height=False)
        screenwidth = self.winfo_screenwidth()
        screenheight = self.winfo_screenheight()
        size = '%dx%d+%d+%d' % (527, 351, (screenwidth - 527) / 2, (screenheight - 351) / 2)
        self.geometry(size)

        # self.iconbitmap(SetICO，ICO_Path)
        # self.bind('1',BindEvent)

        # Create a label widget with a hyperlink
        hyperlink_label = Label(self, text="github", fg="#cdcdcd", cursor="hand2")
        hyperlink_label.pack(side=TOP, anchor=NE, padx=25, pady=8)
        hyperlink_label.bind("<Button-1>", lambda event: webbrowser.open_new_tab("https://github.com/mainite/VideoSlim"))



        Label1_title = StringVar()
        Label1_title.set('将视频拖拽到此窗口:')
        Label1 = Label(self, textvariable=Label1_title, anchor=W)
        Label1.place(x=26, y=8, width=160, height=24)


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

        self.delete_source_var = BooleanVar()
        delete_source_check = Checkbutton(self, text="完成后删除旧文件", variable=self.delete_source_var, onvalue=True, offvalue=False)
        delete_source_check.place(x=20, y=295)

        windnd.hook_dropfiles(self, func=self.drop_file)

    def ClearContent(self):
        self.text_box.delete("1.0", END)



    def drop_file(self, event):
        files = '\n'.join((item.decode('gbk') for item in event))
        self.text_box.insert(END, files+"\n")


    def GetSaveOutFileName(self,filename):
        file_name, file_ext = os.path.splitext(filename)
        save_out_name = file_name + "_x264.mp4"
        batCmd = "compress.bat " + filename + " " + save_out_name
        return save_out_name


    def DoCompress(self):
        text_content = self.text_box.get("1.0",END)




        if text_content != "":
            lines = text_content.splitlines()
            for file_name in lines:
                if file_name != "":
                    save_out_name = self.GetSaveOutFileName(file_name)
                    command1 = r'.\tools\ffmpeg.exe -i "{}" -vn -sn -v 0 -c:a pcm_s16le -f wav pipe: | .\tools\neroAacEnc.exe -ignorelength -lc -br 128000 -if - -of ".\old_atemp.mp4"'.format(file_name)
                    command2 = r'.\tools\x264_64-10bit.exe --crf 23.5 --preset 8 -I 600 -r 4 -b 3 --me umh -i 1 --scenecut 60 -f 1:1 --qcomp 0.5 --psy-rd 0.3:0 --aq-mode 2 --aq-strength 0.8 -o ".\old_vtemp.mp4"  "{}"'.format(file_name)
                    command3 = r'.\tools\mp4box.exe -add ".\old_vtemp.mp4#trackID=1:name=" -add ".\old_atemp.mp4#trackID=1:name=" -new "{}"'.format(save_out_name)
                    command4 = "del .\\old_atemp.mp4 .\\old_vtemp.mp4"

                    command5 = r'del "{}"'.format(file_name)

                    os.system(command1)
                    os.system(command2)
                    os.system(command3)
                    os.system(command4)

                    if self.delete_source_var.get():
                        os.system(command5)


            print("Has Finished ！！！")
        else:
            print("No video file")

app = DragDropApp()
app.mainloop()
