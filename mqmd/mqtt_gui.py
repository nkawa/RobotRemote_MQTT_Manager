# -*- coding: utf-8 -*-
from threading import Thread
import time
import tkinter as tk
from tkinter import *
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import json
from paho.mqtt import client as mqtt
import re
import requests

#モニタリングを制御するためのGUI

class MQTTWin(object):
    def __init__(self,root):
        self.lastErr = time.time()*1000 # epoch millisecond
        self.root = root
        self.root.title("MQTT record Controller")
        self.root.geometry("600x800")

        self.mqbutton = Button(self.root, text="Connect MQTT", padx=5,
                             command=self.connect_mqtt)
        self.mqbutton.grid(row=0,column=0,padx=2,pady=10)


        self.smbutton = Button(self.root, text="Start MQTT recording", padx=5,
                             command=self.start_recording)
        self.smbutton.grid(row=0,column=1,padx=2,pady=10)


        self.pmbutton = Button(self.root, text="Stop MQTT recording", padx=5,
                             command=self.stop_recording)
        self.pmbutton.grid(row=0,column=3,padx=2,pady=10)

        self.svbutton = Button(self.root, text="Start Video", padx=5,
                             command=self.start_video)
        self.svbutton.grid(row=0,column=4,padx=2,pady=10)

        self.spbutton = Button(self.root, text="Stop Video", padx=5,
                             command=self.stop_video)
        self.spbutton.grid(row=0,column=5,padx=2,pady=10)


#        self.enable.grid(row=0,column=2,padx=2,pady=10)

#        self.mv4button.grid(row=0,column=6,padx=2,pady=10)

 #       self.mv5button = Button(self.root, text="ClearErr", padx=5,
 #                            command=self.clear_error)
 #       self.mv5button.grid(row=0,column=7,padx=2,pady=10)

        self.info_frame = LabelFrame(self.root, text="info", labelanchor="nw",
                                     bg="#FFFFFF", width=550, height=150)
        self.info_frame.grid(row=1, column=0, padx=5,pady=5,columnspan=8)

        self.label_mqtt_mode = Label(self.info_frame, text="")
        self.label_mqtt_mode.place(rely=0.1, x=10)

        self.label_feed_speed = Label(self.info_frame,text="")
        self.label_feed_speed.place(rely=0.1, x=245)


 #       self.xplus = Button(self.root, text="DefaultPose", padx=5,
 #                            command=self.defaultPose)
 #       self.xplus.grid(row=2,column=0,padx=2,pady=10)##
#
 #       self.yplus = Button(self.root, text="SetDefPose", padx=5,
 #                            command=self.setDefPose)
  #      self.yplus.grid(row=2,column=1,padx=2,pady=10)

  #      self.enb = Button(self.root, text="EnableRobot", padx=5,
  #                           command=self.enableRobot)
  #      self.enb.grid(row=2,column=3,padx=2,pady=10)

#        self.enb = Button(self.root, text="DisableRobot", padx=5,
#                             command=self.disableRobot)
#        self.enb.grid(row=2,column=4,padx=2,pady=10)

        self.text_log = tk.scrolledtext.ScrolledText(self.root,width=70,height=60)
        self.text_log.grid(row=3,column =0, padx=10, pady=10,columnspan=7)

        self.text_log.insert(tk.END,"Start!!")

    def log_txt(self,str):
        self.text_log.insert(tk.END,str)


    def stop_recording(self):
        self.client.publish("mqmd/control","{\"command\":\"stop\"}")
        self.label_mqtt_mode
        self.log_txt("Stop MQTT Recording\n")

    def start_recording(self):
        self.client.publish("mqmd/control","{\"command\":\"start\"}")
        self.log_txt("Start MQTT Recording\n")
        

    def stop_video(self):
        self.log_txt("Stop Video Recording\n")

        header = {"x-sora-target":"Sora_20231220.StopRecording"}
        dt = {
            "channel_id" : "sora"
        }
        json_data = json.dumps(dt)
        response = requests.post("http://192.168.5.254:3000", data=json_data, headers=header)
        self.log_txt(response.text)


    def start_video(self):
        self.log_txt("Start Video Recording\n")
        header = {"x-sora-target":"Sora_20231220.StartRecording"}
        dt = {
            "channel_id" : "sora"
        }
        json_data = json.dumps(dt)
        response = requests.post("http://192.168.5.254:3000", data=json_data, headers=header)
        self.log_txt(response.text)

# ブローカーに接続できたときの処理
    def on_connect(self,client, userdata, flag, rc):
        print("Connected with result code " + str(rc))  # 接続できた旨表示
        self.client.subscribe("webxr/pose") #　connected -> subscribe
        self.log_txt("Connected MQTT"+"\n")


# ブローカーが切断したときの処理
    def on_disconnect(self,client, userdata, rc):
        if  rc != 0:
            print("Unexpected disconnection.")


    def on_message(self,client, userdata, msg):
        js = json.loads(msg.payload)
#        print("Message!",js)

        if 'pos' in js:
            x = js['pos']['x']
            y = js['pos']['y']
            z = js['pos']['z']
            xd = js['ori']['x']
            yd = js['ori']['y']
            zd = js['ori']['z']
        else:
            print("JSON",js)
            return
        if self.lx ==0 and self.ly == 0 and self.lz ==0:
            self.lx = x
            self.ly = y
            self.lz = z
            self.lxd = xd
            self.lyd = yd
            self.lzd = zd
        if self.lx != x or self.ly !=y or self.lz != z:
            dx = x-self.lx
            dy = y-self.ly
            dz = z-self.lz
            dxd = xd-self.lxd
            dyd = yd-self.lyd
            dzd = zd-self.lzd
            print(dxd,dyd,dzd)
            sc = 1100  # ちょっと誇張
            dx *= sc
            dy *= sc
            dz *= sc
#            print(dx,dy,dz)

            if 'pad' in js:
                pd = js['pad']
                if pd['bA']:
                    print("reset")
                    self.resetRobot()
                if pd['b0']!=1:
                    self.relativeMove(dx,dy,dz,dxd*180,dyd*180,-dzd*180)

            self.lx = x
            self.ly = y
            self.lz = z
            self.lxd = xd
            self.lyd = yd
            self.lzd = zd


            
    def connect_mqtt(self):
        self.client = mqtt.Client()  
# MQTTの接続設定
        self.client.on_connect = self.on_connect         # 接続時のコールバック関数を登録
        self.client.on_disconnect = self.on_disconnect   # 切断時のコールバックを登録
        self.client.on_message = self.on_message         # メッセージ到着時のコールバック
        self.client.connect("sora2.uclab.jp", 1883, 60)
#  client.loop_start()   # 通信処理開始
        self.client.loop_start()   # 通信処理開始


root = tk.Tk()

mqwin = MQTTWin(root)
mqwin.root.lift()
root.mainloop()
