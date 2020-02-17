import os
import sys
from datetime import datetime
from argparse import ArgumentParser
from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

import requests
from bs4 import BeautifulSoup
import re
import json

app = Flask(__name__)

userID_list = []#"U105f65be46024a1d2d18720b4a00fc59"
#settings = []#二次元配列　["返答状態","地域","毎朝か雨か","時刻"] ["0","343","朝","6"]
japanArea = {"兵庫":"332","徳島":"343"}

channel_secret = "09d2874b5026d10099df6dfab0779680"
channel_access_token = "aSdfRn+ksO/d/WJsHUT9Vr0pi4LbkuEkM9f0VHM586fAlooA/lL5eTP3iE8dKXJw3Txw4N2w1vmy2xD29K7lK39res1A8+IDeeFq+SNh807Afre0fDfdTnt1TPWBKbHyBZ12BlMy0R4OEZkduZ7JPgdB04t89/1O/w1cDnyilFU="
line_bot_api = LineBotApi(channel_access_token)

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

"""
LINEからのwebhook
"""
@app.route("/callback", methods=['POST'])
def callback():
    # リクエストヘッダーから署名検証のための値を取得
    signature = request.headers['X-Line-Signature']
    # リクエストボディを取得
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # 署名を検証し、問題なければhandleに定義されている関数を呼び出す
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:#エラーが出た時400と返す
        abort(400)
    return 'OK'

"""
LINEでMassageEvent(テキストメッセージが送信された時)が起こった時呼び出される
"""
@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    userID = line_bot_api.get_profile(event.source.user_id).user_id
    #try:
    """
    with open("lineBotWether.json", "r") as f: #jsonファイルを取得
        settings = json.load(f)
        
        try:
            settings_userID = [d.get('userID') for d in settings]
            indexNum = settings_userID.index(userID)
        except:
            indexNum = -1
    """
    with open("lineBotWeather.json", "r") as f: #jsonファイルを取得
        settings = json.load(f)
        print("open")
        print(settings)
        try:
            settings_userID = [d.get('userID') for d in settings]
            indexNum = settings_userID.index(userID)
        except:
            indexNum = -1
        
    """
    except:
        settings = []
        indexNum = -1"""

    messageText = event.message.text
    

    if indexNum == -1:            #友達登録して初めての送信の場合
        null = {"userID":userID,  #ユーザーID
                "state":"0",      #状態 0=応答状態 1=地域の設定 2=毎朝か雨の日の設定 10=各種設定
                "area":"343",     #地域
                "time":"毎朝"}   #初期値
        settings.append(null)
        
        sendText = "userIDを登録しました \n「今日」 を入力すると今日の天気が \n 「明日」 は明日の天気が \n 「明後日」 は明後日の天気が \n 「設定」 では各種設定が行えます \n\n ＊通信は平文(非暗号化)になっているので重要な情報などは送らないでください。＊"
        
    else: #１度登録すれば以降はここを通る
        stateNum = settings[indexNum]["state"] #状態
        if stateNum == "0":                    #通常はここを通る
            sendText = get_web(messageText,indexNum,settings)
            
        elif stateNum == "1":                  #地域の設定
            try:
                settings[indexNum]["area"] = japanArea[messageText]
                sendText = messageText + "に設定しました"
            except:
                messageText = "もう一度入力してください"
                
            settings[indexNum]["state"] = "0"
            
        elif num == "2":                       #毎朝か雨の日
            if messageText.find("毎") != -1 or messageText.find("朝") != -1:
                settings[indexNum]["time"] = "毎朝"
                sendText = "毎朝通知に設定しました"
            elif messageText.find("雨") != -1:
                settings[indexNum]["time"] = "雨"
                sendText = "雨の日だけ通知に設定しました"
                
            settings[indexNum]["state"] = "0"
        
        elif num == "10":#設定を送信した時、次に発信されたコメントがここを通る
            if event.message.text.find("1") != -1:
                settings[indexNum]["state"] = "1"
                sendText = "地域の設定を始めます \n お住まいの都道府県を入力してください \n 徳島、兵庫のみの対応"
            
            elif event.message.text.find("2") != -1:
                settings[indexNum]["state"] = "2"
                sendText = "毎朝か雨の日だけ通知を送るかの設定をします"
            
            elif event.message.text.find("戻る") != -1:
                settings[indexNum]["state"] = "0"
                sendText = "戻りました"
                
            else:
                sendText = "変更したい箇所を教えてください \n 「1」 を入力すると地域の設定 \n 「2」 は毎朝か雨の日だけの通知設定 \n 「3」 は通知時刻の変更 \n 「戻る」 戻ることができます"
        else:
            sendText = "ERRORです"
    
    #jsonに書き込む
    with open("lineBotWeather.json", "w") as f:
        print(settings)
        json.dump(settings, f)
        
    #入力された内容(event.message.text)に応じて返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(sendText)
    )

def get_web(massageText,indexNum,settings):
    url = "https://www.jma.go.jp/jp/yoho/"+settings[indexNum]["area"]+".html"
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    bs = BeautifulSoup(response.text, 'html.parser')
    
    if massageText.find("今日") != -1:
        word = str(bs.select(".weather")[0])
        returnText = "今日の天気は "+word[word.find('title') + 7:word.find('/',word.find('title')) -1]
        
    elif massageText.find("明日") != -1:
        word = str(bs.select(".weather")[1])
        returnText = "明日の天気は　"+word[word.find('title') + 7:word.find('/',word.find('title')) -1]
        
    elif massageText.find("明後日") != -1:
        word = str(bs.select(".weather")[2])
        returnText = "明後日の天気は "+word[word.find('title') + 7:word.find('/',word.find('title')) -1]
        
    elif massageText.find("設定") != -1:
        settings[indexNum]["state"] = "10"
        returnText = "変更したい箇所を教えてください \n 1 を入力すると地域の設定 \n 2 は毎朝か雨の日だけの通知設定 \n 3 は通知時刻の変更 \n 「戻る」 戻ることができます"
    else:
        returnText = "今日、明日、明後日と打ち込むと徳島の天気を表示します。"
    return returnText


def second_method():
    with open("lineBotWeather.json", "r") as f: #jsonファイルを取得
        settings = json.load(f)
        print("settings")
        print(settings)
        
    for i in range(len(settings)):
        try:
            userID = settings[i]["userID"]
            print(userID)
            returnText = get_web("今日",i,settings)
            
            if settings[i]["time"] == "雨":
                if returnText.find("雨") != -1:
                    returnText = "今日は雨です。傘が必要になりそうですね。\n 今日の天気は" + returnText + "です。"
            print(returnText)
            line_bot_api.multicast([userID], TextSendMessage(text=returnText))
            print(returnText)
        except:
            print("second_method ERROR")
    
if __name__ == "__main__": #正しいファイル拡張子で実行されているか識別
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

