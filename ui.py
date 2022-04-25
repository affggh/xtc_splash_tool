#!/usr/bin/env python2
# -*- coding:utf-8 -*-
#
# Python script by affggh
# LICIENCE : Apache 2.0
#
import os, sys
import time
import Tkinter as tk
import ttk
from tkFileDialog import askopenfilename
from PIL import Image, ImageTk
import subprocess
import threading
sys.path.append(os.path.abspath(os.path.dirname(sys.argv[0])) + "\\bin")
import logo_gen as lg
import logo_gen_decoder as ld

VERSION = "1.0"
AUTHOR = "affggh"
WINDOWTITLE = "小天才 MSM8909W 开机第一屏通用修改工具 by affggh"

uiwidth = 520
uiheight = 300

root = tk.Tk()
# Vars
filename = tk.StringVar()
global refreshflag
refreshflag = True
global img1
global img2
if os.path.isfile("pic/splash1.png"):
    img1 = ImageTk.PhotoImage(Image.open("pic/splash1.png").resize((160, 180), Image.ANTIALIAS))
if os.path.isfile("pic/splash2.png"):
    img2 = ImageTk.PhotoImage(Image.open("pic/splash2.png").resize((160, 180), Image.ANTIALIAS))

global DeviceState
global DeviceSerialno

# init
def get_time():  # 返回当前时间
    time1 = ''
    time2 = time.strftime('%H:%M:%S')
    if time2 != time1:
        time1 = time2
    return time1

def selectFile():
    global filepath
    filepath = askopenfilename()                   # 选择打开什么文件，返回文件名
    showinfo(filepath)
    if filepath == "":
        showinfo("未选择文件")
        return False
    else:
        return True

def showinfo(textmsg):
    text.insert(tk.END,"[%s]" %(get_time()) + "%s" %(textmsg) + "\n")
    text.update() # 实时返回信息
    text.yview('end')

class StdoutRedirector():
    def __init__(self):
    	# 将其备份
        self.stdoutbak = sys.stdout		
        self.stderrbak = sys.stderr
        # 重定向
        sys.stdout = self
        sys.stderr = self

    def write(self,string):
        text.insert(tk.END,"[%s]" %(get_time()) + "%s" %(string))
        text.update() # 实时返回信息
        text.yview('end')


def decrypt():
    showinfo("选择splash.img进行解析，图片输出到pic目录")
    if selectFile():
        ld.process_splashimg(filepath, "pic\splash.png")
        #showinfo(filepath)
    showinfo("结束")

def encrypt():
    pngs = ['pic/splash1.png', 'pic/splash2.png']
    global payloadLimit    # This is for logo_gen.py detect
    payloadLimit = 32768 - 512
    for i in pngs:
        if not os.path.isfile(i):
            showinfo("图片 %s 不存在" %(i))
            return False
    if os.path.isfile("image/splash.img"):
        os.remove("image/splash.img")
        showinfo("移除已存在的splash.img")
    showinfo("生成新的splash.img")
    lg.MakeLogoImage(pngs[0], "image/splash.img")
    size = os.path.getsize("image/splash.img")
    if size > 32768:
        showinfo("png图像过于复杂生成过大，无法刷回splash分区，请替换该图片 ：" + pngs[0])
        os.remove("image/splash.img")
        return False

    with open("image/splash.img", "rb+") as f:
        lg.MakeLogoImage(pngs[1], "image/tmp.img")
        f.seek(32768)
        with open("image/tmp.img", "rb") as f2:
            buf = f2.read()
            f.write(buf)
    os.remove("image/tmp.img")

    if os.path.getsize("image/splash.img") > 32768*2:
        showinfo("png图像过于复杂生成过大，无法刷回splash分区，请替换该图片 ：" + pngs[1])
        os.remove("image/splash.img")

def runcmd(cmd):
    try:
        ret = subprocess.Popen(cmd,shell=False,
                 stdin=subprocess.PIPE,
                 stdout=subprocess.PIPE,
                 stderr=subprocess.STDOUT)
        for i in iter(ret.stdout.readline,b""):
            showinfo(i.decode("gb2312","ignore").strip())
    except subprocess.CalledProcessError as e:
        for i in iter(e.stdout.readline,b""):
            showinfo(e.decode("gb2312","ignore").strip())

def cleanup():
    if os.path.isfile("image/splash.img"):
        os.remove("image/splash.img")
    showinfo("删除splash.img")

def getcmd(cmd):
    try:
        ret = subprocess.Popen(cmd,shell=False,
                 stdin=subprocess.PIPE,
                 stdout=subprocess.PIPE,
                 stderr=subprocess.STDOUT)
        for i in iter(ret.stdout.readline,b""):
            return (i.decode("gb2312","ignore").strip())
    except subprocess.CalledProcessError as e:
        for i in iter(e.stdout.readline,b""):
            return (e.decode("gb2312","ignore").strip())

def findport():
    # miflash的lsusb二进制程序，可以检测到9008端口
    # 不能用来检查adb端口
    buf = getcmd("bin/lsusb")
    if buf:
        if not buf.find("9008") == -1:
            port = buf.split(" ")[-1].strip("(").strip(")")
            return port
        else:
            showinfo("Port not found")
            return False
    else:
        showinfo("Cannot found any port")
        return False

def __flashit():
    buf = getcmd("bin/adb get-state")
    if buf == 'device':
        showinfo("获取到设备")
        user = getcmd("bin/adb shell su -c whoami")
        if not user == 'root':
            showinfo("未获取到root权限")
            return False
        else:
            showinfo("成功获取root权限")
            runcmd("bin/adb push image\\splash.img /data/local/tmp/splash.img")
            runcmd("bin/adb shell su -c dd if=/data/local/tmp/splash.img of=/dev/block/bootdevice/by-name/splash")
            runcmd("bin/adb shell rm -f /data/local/tmp/splash.img")
            showinfo("使用root刷入结束")
            return True
    elif buf == 'recovery':
        showinfo("设备处于recovery模式")
        runcmd("adb push image\\splash.img /tmp/splash.img")
        runcmd("bin/adb shell dd if=/tmp/splash.img of=/dev/block/bootdevice/by-name/splash")
        runcmd("bin/adb shell rm -f /tmp/splash.img")
        showinfo("在recovery模式下刷入结束")
    elif findport():
        port = findport()
        showinfo("检测到9008端口哦")
        showinfo("开始刷入")
        runcmd("bin/QSaharaServer.exe -s 13:image\\prog_emmc_firehose_8909w_ddr.mbn -p \\\\.\\%s" %(port))
        runcmd("bin/fh_loader.exe --port=\\\\.\\%s --sendxml=rawprogram0.xml --search_path=%s" %(port, os.path.abspath("./image")))
        showinfo("刷入结束，请手动重启")
    else:
        showinfo("使用定义好的方法未能发现设备")
        showinfo("请检查设备权限或连接")

def flashit():
    th = threading.Thread(target=__flashit)
    th.start()

def refresh():
    while(refreshflag):
        if os.path.isfile("pic/splash1.png"):
            try:
                img1 = ImageTk.PhotoImage(Image.open("pic/splash1.png").resize((160, 180), Image.ANTIALIAS))
                label1.configure(image=img1)
                label1.image = img1
            except:
                break
        if os.path.isfile("pic/splash2.png"):
            try:
                img2 = ImageTk.PhotoImage(Image.open("pic/splash2.png").resize((160, 180), Image.ANTIALIAS))
                label2.configure(image=img2)
                label2.imgge = img2
            except:
                break
        time.sleep(3)

def threfresh():
    th = threading.Thread(target=refresh)
    th.start()

text = tk.Text(root, width=180, height=6, relief=tk.SUNKEN)
text.pack(side=tk.BOTTOM, expand=tk.NO, fill=tk.BOTH)

sys.stdout = StdoutRedirector()

root.geometry("%sx%s" %(uiwidth,uiheight))
root.title(WINDOWTITLE)

frame = ttk.Frame(root)

frame1 = ttk.LabelFrame(frame, text="功能", labelanchor="nw", relief=tk.SUNKEN, borderwidth=1)
frame2 = ttk.LabelFrame(frame, text="预览", labelanchor="nw", relief=tk.SUNKEN, borderwidth=1)

button1 = ttk.Button(frame1, text='解析', width=15, command=decrypt)
#button2 = ttk.Button(frame1, text='刷新', width=15, command=refresh)
button3 = ttk.Button(frame1, text='打包', width=15, command=encrypt)
button4 = ttk.Button(frame1, text='清理', width=15, command=cleanup)
button5 = ttk.Button(frame1, text='刷入', width=15, command=flashit)

button1.pack(side=tk.TOP, expand=tk.YES, padx=5)
#button2.pack(side=tk.TOP, expand=tk.YES, padx=5)
button3.pack(side=tk.TOP, expand=tk.YES, padx=5)
button4.pack(side=tk.TOP, expand=tk.YES, padx=5)
button5.pack(side=tk.TOP, expand=tk.YES, padx=5)

frame1.pack(side=tk.LEFT, expand=tk.NO, fill=tk.BOTH)
frame2.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)
frame.pack(side=tk.TOP, expand=tk.YES, fill=tk.BOTH)

label1 = ttk.Label(frame2)
label2 = ttk.Label(frame2)
label1.pack(side=tk.LEFT, expand=tk.YES)
label2.pack(side=tk.LEFT, expand=tk.YES)
threfresh()
showinfo("此工具为免费工具，花钱买了你就是大傻逼")
showinfo("此工具支持仅支持png格式")
showinfo("工具版本 ： %s" %(VERSION))
showinfo("工具作者 ： %s" %(AUTHOR))
root.mainloop()
refreshflag = False