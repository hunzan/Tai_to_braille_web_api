import os
import unicodedata
import logging, traceback
from flask import request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from dotenv import load_dotenv
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, MessageAction
)

# 👇 顯式從 converter 匯入需要的函式
from converter import convert_text_to_braille, reload_data

load_dotenv()
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 🔸 記錄使用者輸入模式
user_modes = {}  # {user_id: 'tl' 或 'poj'}

# 👉 全形→半形對照（常見中文標點）
FULL2HALF = str.maketrans({
    '，': ',', '。': '.', '：': ':', '；': ';', '！': '!', '？': '?',
    '（': '(', '）': ')', '【': '[', '】': ']', '「': '"', '」': '"',
    '『': '"', '』': '"', '、': ',', '—': '-', '～': '~', '．': '.', '‧': '.',
    '　': ' ',  # 全形空白
    '…': '...',  # 把單字元刪節號轉成三點
})

def normalize_text(s: str) -> str:
    # 1) Unicode 正規化（避免看似相同字元不同碼位）
    s = unicodedata.normalize('NFC', s or "")
    # 2) 常見全形→半形；保留標點
    s = s.translate(FULL2HALF)
    # 3) 收尾空白
    return s.strip()

def line_callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    raw_text = event.message.text or ""
    cmd = raw_text.strip().lower()  # 僅用於指令判斷；實際轉換不用它

    try:
        # 🔸 處理指令
        if cmd in ["poj", "白話字", "白話"]:
            user_modes[user_id] = "poj"
            reply = "✅ 已切換為 POJ 輸入模式"

        elif cmd in ["tl", "台羅", "台羅拼音", "台羅音"]:
            user_modes[user_id] = "tl"
            reply = "✅ 已切換為台羅拼音輸入模式"

        elif cmd in ["目前模式", "模式", "mode"]:
            mode = user_modes.get(user_id, "tl")
            reply = f"目前輸入模式：{'台羅拼音' if mode == 'tl' else 'POJ'}"

        elif cmd == "更新資料":
            try:
                reload_data()
                reply = "📦 已重新載入資料表！"
            except Exception as e:
                logger.error("reload_data() 失敗: %s\n%s", e, traceback.format_exc())
                reply = "⚠️ 重新載入失敗，請稍後再試"

        elif cmd in ["說明", "幫助", "help", "指令", "金蕉"]:
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
            return  # 已回覆

        else:
            # 🔸 正常轉換
            input_mode = user_modes.get(user_id, "tl")  # 預設台羅
            normalized = normalize_text(raw_text)

            # 🔑 用「關鍵字參數」呼叫，與 converter 新介面對齊
            result = convert_text_to_braille(text=normalized, input_type=input_mode)

            if not result or not str(result).strip():
                raise ValueError("Empty result from convert_text_to_braille")

            reply = f"🔄 轉換結果：\n{result}"

        # 統一回覆
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )

    except Exception as e:
        logger.error("處理訊息失敗: %s\n%s", e, traceback.format_exc())
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="抱歉，轉換失敗，工程蕉已在查 🔧")
        )

