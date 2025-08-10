import os
import json
from dotenv import load_dotenv

load_dotenv()

# 🔹 載入 JSON 資料
DATA_DIR = os.path.join(os.path.dirname(__file__), 'braille_data')
CONSONANTS_FILE = os.path.join(DATA_DIR, 'consonants.json')
VOWELS_FILE = os.path.join(DATA_DIR, 'vowels_all.json')
RUSHIO_FILE = os.path.join(DATA_DIR, 'rushio_syllables.json')
NASAL_FILE = os.path.join(DATA_DIR, 'nasal_table.json')
POJ_DIFF_FILE = os.path.join(DATA_DIR, 'tl_to_poj_diff.json')
PUNCTUATION_FILE = os.path.join(DATA_DIR, 'punctuation.json')

# ✅ 全域變數初始化
def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def reload_data():
    global consonants, vowels, rushio, nasal, tl_to_poj, poj_to_tl, sorted_poj_keys, punctuation_map, punct_chars

    consonants = load_json(CONSONANTS_FILE)
    vowels = load_json(VOWELS_FILE)
    rushio = load_json(RUSHIO_FILE)
    nasal = load_json(NASAL_FILE)
    tl_to_poj = load_json(POJ_DIFF_FILE)
    poj_to_tl = {v: k for k, v in tl_to_poj.items()}
    sorted_poj_keys = sorted(poj_to_tl.keys(), key=lambda x: -len(x))

    # 標點
    punctuation_map = load_json(PUNCTUATION_FILE)
    # 建立可辨識的所有標點字元集合（含全形/半形）
    punct_chars = set(punctuation_map.keys())

def tokenize(text):
    tokens = []
    buf = []

    def flush_word():
        if buf:
            tokens.append(("word", "".join(buf)))
            buf.clear()

    i = 0
    while i < len(text):
        ch = text[i]

        # 空白（保留原樣，避免 split() 把多空白吃掉）
        if ch.isspace():
            flush_word()
            j = i
            while j < len(text) and text[j].isspace():
                j += 1
            tokens.append(("space", text[i:j]))
            i = j
            continue

        # 標點（包含全形/半形；依你的 punctuation.json）
        if ch in punct_chars:
            flush_word()
            tokens.append(("punct", ch))
            i += 1
            continue

        # 其他字元視為字詞的一部分（含 a-z、數字、變音、及連字符）
        buf.append(ch)
        i += 1

    flush_word()
    return tokens

# ✅ 啟動時就先載入
reload_data()

def poj_to_tl_text(text):
    # 🧠 預處理：ⁿ 換成 nn
    text = text.replace("ⁿ", "nn")

    # 🔁 使用排序過的 key，確保長的字串先被處理（避免 ua 被 oa 取代）
    for poj in sorted_poj_keys:
        text = text.replace(poj, poj_to_tl[poj])

    return text

# 🔹 切音節函式
def split_syllables(word):
    # 優先使用連字符來斷音節
    return word.split('-')
    i = 0

    while i < len(word):
        match = None  # ✅ 初始化匹配變數

        # 先檢查 rushio_syllables 是否獨立匹配
        for r in sorted(rushio.keys(), key=lambda x: -len(x)):
            if word[i:].startswith(r):
                result.append(r)
                i += len(r)
                match = r
                break

        # 再檢查 vowels 是否能獨立匹配
        for v in sorted(vowels.keys(), key=lambda x: -len(x)):
            if word[i:].startswith(v):
                result.append(v)
                i += len(v)
                match = v  # ✅ 確保 match 存的是字串，而非布林值
                break

        # 然後檢查 consonants + vowels / nasal / rushio
        for c in sorted(consonants.keys(), key=lambda x: -len(x)):
            if word[i:].startswith(c):
                for v in sorted(vowels.keys(), key=lambda x: -len(x)):
                    if word[i + len(c):].startswith(v):
                        match = c + v
                        break
                for r in sorted(rushio.keys(), key=lambda x: -len(x)):
                    if word[i + len(c):].startswith(r):
                        match = c + r
                        break
                for n in sorted(nasal.keys(), key=lambda x: -len(x)):
                    if word[i + len(c):].startswith(n):
                        match = c + n
                        break
                if match:
                    result.append(match)
                    i += len(match)
                    break

        if match is None:
            result.append('[錯誤]')
            break

    return result

# 🔹 轉換為點字（包含純母音含聲調處理）
def convert_syllable(s):
    # 直接對應整個音節（完整拼音）優先處理
    if s in nasal:
        return "⠠" + nasal[s]["dots"]
    if s in rushio:
        return rushio[s]["dots"]
    if s in vowels:
        return vowels[s]["dots"]

    # 嘗試分拆子音與母音（或鼻音）
    for c in sorted(consonants.keys(), key=lambda x: -len(x)):
        if s.startswith(c):
            rest = s[len(c):]
            if rest in vowels:
                return consonants[c]["dots"] + vowels[rest]["dots"]
            elif rest in rushio:
                return consonants[c]["dots"] + rushio[rest]["dots"]
            elif rest in nasal:
                return "⠠" + consonants[c]["dots"] + nasal[rest]["dots"]

    # 補上沒聲母的純母音（含聲調）處理
    if s in vowels:
        return vowels[s]["dots"]

    # 無法處理的音節
    return '[錯誤]'

def convert_text_to_braille(text, input_type="tl"):
    text = text.rstrip("\n")  # 保留內文空白但去掉檔尾多餘換行

    # 先做 POJ→TL（在「明眼字」層處理）
    if input_type == "poj":
        text = text.replace('ⁿ', 'nn')
        for poj in sorted_poj_keys:
            tl = poj_to_tl[poj]
            text = text.replace(poj, tl)

    tokens = tokenize(text)
    out = []

    for kind, val in tokens:
        if kind == "space":
            out.append(val)
        elif kind == "punct":
            # 沒在表裡就原樣保留（方便漸進擴充）
            out.append(punctuation_map.get(val, val))
        else:  # "word"
            # 逐詞處理（詞內用 '-' 當音節連字符）
            # 注意：若你之後要支援「減號」做真正的標點，應在 tokenize 裡把獨立的 '-' 判成 punct
            pieces = val.split('-') if val else []
            if pieces:
                braille = ''.join(convert_syllable(s) or '[錯誤]' for s in pieces)
                out.append(braille)
            else:
                out.append(val)

    return ''.join(out)

