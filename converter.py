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

# ── 規則集合（模組層，避免作用域問題） ────────────────────────────────
# 需要在點字後面補「點字空格」的明眼標點（只對這些補）
NEED_SPACE_AFTER_PUNCT = {
    '，', ',', '；', ';', '。', '.', '！', '!', '？', '?',
    '...', '」', '』', '”', '’', ')', '）', ']', '】', '}'
}
# 句末標點（遇到後引號/括號時要抑制補空格）
SENTENCE_ENDERS = {'。', '.', '！', '!', '？', '?'}
# 後引號 / 括號（它們本身會補點字空格）
CLOSERS = {'」', '』', '”', '’', ')', '）', ']', '】', '}'}
# （若你的文本會用到「【」，視需求自行加入 NEED_SPACE_AFTER_PUNCT / CLOSERS）

# ✅ 全域變數初始化
def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def reload_data():
    global consonants, vowels, rushio, nasal, tl_to_poj, poj_to_tl, sorted_poj_keys
    global punctuation_map, punct_first_chars, punct_keys_sorted

    consonants = load_json(CONSONANTS_FILE)
    vowels = load_json(VOWELS_FILE)
    rushio = load_json(RUSHIO_FILE)
    nasal = load_json(NASAL_FILE)
    tl_to_poj = load_json(POJ_DIFF_FILE)
    poj_to_tl = {v: k for k, v in tl_to_poj.items()}
    sorted_poj_keys = sorted(poj_to_tl.keys(), key=lambda x: -len(x))

    # 標點（映射：明眼 -> 點字）
    punctuation_map = load_json(PUNCTUATION_FILE)
    # 最長優先鍵清單（支援 multi-char，如 "..."）
    punct_keys_sorted = sorted(punctuation_map.keys(), key=len, reverse=True)
    # 首字快篩，加速檢測
    punct_first_chars = {k[0] for k in punct_keys_sorted}

def tokenize(text):
    """
    斷成三類 token：
      - ("word", <字串>)
      - ("space", <原樣空白/換行>)
      - ("punct", <原樣標點字串>)  ← 支援多字元（如 "..."）
    """
    tokens = []
    buf = []

    def flush_word():
        if buf:
            tokens.append(("word", "".join(buf)))
            buf.clear()

    i, n = 0, len(text)
    while i < n:
        ch = text[i]

        # 空白（保留原樣，避免 split() 把多空白吃掉）
        if ch.isspace():
            flush_word()
            j = i
            while j < n and text[j].isspace():
                j += 1
            tokens.append(("space", text[i:j]))
            i = j
            continue

        # 標點（最長優先；支援 multi-char，例如 "..."）
        if ch in punct_first_chars:
            matched = False
            for key in punct_keys_sorted:  # 長 -> 短
                L = len(key)
                if i + L <= n and text[i:i+L] == key:
                    flush_word()
                    tokens.append(("punct", key))
                    i += L
                    matched = True
                    break
            if matched:
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
    # （以下預留原先進階斷音，未啟用）

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

    for idx, (kind, val) in enumerate(tokens):
        if kind == "space":
            out.append(val)

        elif kind == "punct":
            # 轉成點字（若表中沒有就原樣保留）
            braille_punct = punctuation_map.get(val, val)

            # 是否需要在這顆標點後面補「點字空格」
            add_braille_space = val in NEED_SPACE_AFTER_PUNCT

            # 若是句末標點，且後面緊接著「後引號/括號」，就不要在句末標點後加空格
            if add_braille_space and val in SENTENCE_ENDERS:
                # 往後看下一個「非空白」token
                j = idx + 1
                while j < len(tokens) and tokens[j][0] == "space":
                    j += 1
                if j < len(tokens) and tokens[j][0] == "punct" and tokens[j][1] in CLOSERS:
                    add_braille_space = False

            out.append(braille_punct)
            if add_braille_space:
                out.append('\u2800')  # 點字空格（U+2800）

        else:  # "word"
            # 逐詞處理（詞內用 '-' 當音節連字符）
            pieces = val.split('-') if val else []
            if pieces:
                braille = ''.join(convert_syllable(s) or '[錯誤]' for s in pieces)
                out.append(braille)
            else:
                out.append(val)

    return ''.join(out)
