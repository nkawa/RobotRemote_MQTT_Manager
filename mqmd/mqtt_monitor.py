from dotenv import load_dotenv


import os
import json
import sys
import time
from datetime import datetime
from paho.mqtt import client as mqtt


load_dotenv()  # take environment variables from .env

MQTT_SERVER = os.getenv('MQTT_SERVER', '192.168.5.254')
MQTT_PORT = 1883

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

STORAGE_DIR = "storage"

SEPARATE_FILE_SEC = 50   # ５０秒ごとにファイルを分ける

class MQTTMonitor:
    def __init__(self):
        self.client = None
        self.storage = None
        self.last_filetime = 0
        self.playing = False
        self.status = "Init"
        self.count = 0

    def update_storage(self):
        if self.storage is not None:
            self.storage.close()

        # フォルダ・ファイル名を決定
        now = datetime.now()
        st_dir = os.path.join(STORAGE_DIR, now.strftime("%Y%m%d"))
        os.makedirs(st_dir,exist_ok=True)
        file_name = os.path.join(st_dir,now.strftime("%H%M%S")+".txt")
        self.last_filetime = now.timestamp()

        # 新しいファイルをオープン
        self.storage = open( file_name, 'w',buffering=1024*512, newline='')

        # -> ここで、RRMQM Webサーバに、新しいfileができたことを通知してもいいかも。
        self.client.publish("mqmd/storage",file_name)
        self.status = "Writing to "+file_name
        
    def write_storage(self, msg):
        now = time.time()
        if self.last_filetime + SEPARATE_FILE_SEC < now:
            self.update_storage()
        self.storage.write(msg+"\n")
        self.count += 1
        self.last_filetime = now

# ブローカーが切断したときの処理, 自動再接続機能付き
    def on_disconnect(self,client, userdata, reasonCode,properties):
        if  reasonCode > 0:
            print("MQTT disconnection:",reasonCode)

        reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
        while reconnect_count < MAX_RECONNECT_COUNT:
            print("%d秒後に再接続します...", reconnect_delay)
            time.sleep(reconnect_delay)
            try:
                self.client.reconnect()
                print("再接続に成功しました！")
                return
            except Exception as err:
                print("%s。再接続に失敗しました。再試行します...", err)

            reconnect_delay *= RECONNECT_RATE
            reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
            reconnect_count += 1
        
        print("%s回の試行後に再接続に失敗しました。終了します...", reconnect_count)

    def on_connect(self,client, userdata, flag, reasonCode, properties):
        print("Connected with reason " + str(reasonCode))  # 接続できた旨表示
        # サブスクライブするトピック
        self.client.subscribe("mqmd/control") # 自分の制御用は常時 subscribe
        self.start_subscribe()

        # ここでsubscribeするトピックを指定
    def start_subscribe(self):
        print("Start Subscribe", "webxr/joint")
        self.client.subscribe("webxr/joint")

    def stop_subscribe(self):
        self.client.unsubscribe("webxr/joint")
        if self.storage is not None:
            self.storage.close()
        self.storage = None
        self.status = "Stop Subscribe"
        self.last_filetime = 0

# ここに保存
    def on_message(self,client, userdata, msg):
        # 自分を制御する topic だけは、区別
        if msg.topic == "mqmd/control":
            print("Control Message",msg.payload)
            js = json.loads(msg.payload)
            if js["command"] == "stop":
                self.stop_subscribe()
                return
            if js["command"] == "start":
                self.start_subscribe()
                return
            if js["command"] == "play": #再生
                self.stop_subscribe()
                self.playing = True
                self.status = "Playing "+js["file"]
                self.play_start(js["file"])
                return
            if js["command"] == "playStop": #再生停止
                self.playing = False
                self.status = "Play stopped"
                return
            
        # とりあえず、全部保存してみよう
        self.write_storage(str(msg.timestamp)+"|"+msg.topic+"|"+msg.payload.decode())
#        print("Message",msg.payload)
#        js = json.loads(msg.payload)

    def play_start(self, file):
        print("Play Start",file)
        startTime = time.time()
        dtime = 0
        with open(file, 'r') as f:
            for line in f:
                if self.play_start == False:
                    break
                items = line.split("|")
                ltime = float(items[0])
                if dtime == 0:
                    dtime = startTime - ltime
                print("Sleep",startTime, ltime, dtime, startTime-ltime-dtime)
                if startTime-ltime > dtime:
                    print("Sleep",startTime, ltime, dtime, startTime-ltime-dtime)
                    time.sleep(startTime-ltime-dtime)

                self.client.publish(items[1],items[2])
                self.count += 1
        #終了したら、subscribeを再開
        print("End playing")
        self.start_subscribe()
 

    def connect_mqtt(self):
        print("Connecting to MQTT Server:",MQTT_SERVER)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)  
        self.client.on_connect = self.on_connect         # 接続時のコールバック関数を登録
        self.client.on_disconnect = self.on_disconnect   # 切断時のコールバックを登録
        self.client.on_message = self.on_message         # メッセージ到着時のコールバック

        self.client.connect(MQTT_SERVER, 1883, 60)

        self.client.loop_start()   # 通信処理開始


if __name__ == '__main__':
    mq = MQTTMonitor()
    mq.connect_mqtt()

    try:
        while True:
            time.sleep(5)
            print(datetime.now(), mq.status, mq.count)
    except KeyboardInterrupt:
        print("Interrupted by Ctrl+C")
        if mq.storage is not None:
            mq.client.disconnect()
            mq.storage.close()
