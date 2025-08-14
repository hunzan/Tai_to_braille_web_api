import os
from flask import request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from converter import convert_text_to_braille
from dotenv import load_dotenv
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, MessageAction
)

load_dotenv()

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 🔸 記錄使用者輸入模式
user_modes = {}  # {user_id: 'tl' 或 'poj'}


def line_callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip().lower()

    # 🔸 處理指令
    if user_message in ["poj", "白話字", "白話"]:
        user_modes[user_id] = "poj"
        reply = "✅ 已切換為 POJ 輸入模式"

    elif user_message in ["tl", "台羅", "台羅拼音", "台羅音"]:
        user_modes[user_id] = "tl"
        reply = "✅ 已切換為台羅拼音輸入模式"

    elif user_message in ["目前模式", "模式", "mode"]:
        mode = user_modes.get(user_id, "tl")
        reply = f"目前輸入模式：{'台羅拼音' if mode == 'tl' else 'POJ'}"

    elif user_message == "更新資料":
        reload_data()
        reply = "📦 已重新載入 JSON 資料表！"

    elif user_message in ["說明", "幫助", "help", "指令", "金蕉"]:
        # 🔸 傳送帶按鈕的快速選單
        reply = "選擇輸入模式👉"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=reply,
                quick_reply=QuickReply(
                    items=[
                        QuickReplyButton(action=MessageAction(label="🍌台羅", text="台羅")),
                        QuickReplyButton(action=MessageAction(label="🧋POJ", text="白話字")),
                        QuickReplyButton(action=MessageAction(label="🔎目前模式", text="模式")),
                    ]
                )
            )
        )
        return  # 已回覆，不繼續下面程式

    else:
        # 🔸 正常轉換文字
        input_mode = user_modes.get(user_id, "tl")  # 預設台羅
        result = convert_text_to_braille(user_message, input_mode)
        reply = f"🔄 轉換結果：\n{result}"

    # 🔸 回覆訊息（除了說明與贊助以外）
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

