import tkinter as tk
import os
import windnd
from tkinter import filedialog



class DragDropApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VidesSlim 视频压缩")
        self.geometry("400x100")

        self.text_var = tk.StringVar()
        self.text_var.set("将视频拖拽到此窗口")
        self.text_box = tk.Entry(self, textvariable=self.text_var, width=50)
        self.text_box.pack(pady=10)

        self.button = tk.Button(self, text="压缩", command=self.DoCompress)
        #self.button.pack(side="bottom")
        self.button.place(relx=0.75,y=50, width=60, height=30)

        windnd.hook_dropfiles(self, func=self.drop_file)

        # self.text_box.bind("<Button-3>", self.clear_text)
        #self.bind("<B1-Motion>", self.drag_motion)


    def dragged_files(files, self):
        msg = '\n'.join((item.decode('gbk') for item in files))
        self.text_var.set(msg)

   # def clear_text(self, event):
   #      self.text_var.set("")

    def drag_motion(self, event):
        self.text_var.set("正在拖拽文件...")

    def drop_file(self, event):
        files = '\n'.join((item.decode('gbk') for item in event))
        self.text_var.set(files)
        #showinfo("拖拽文件路径", files)

    def DoCompress(self):
        text_content = self.text_box.get()

        file_name, file_ext = os.path.splitext(text_content)
        new_file_name = file_name + "_x264.mp4"

        batCmd = "compress.bat " + text_content + " " + new_file_name

        os.system("start " + batCmd)




app = DragDropApp()
app.mainloop()
