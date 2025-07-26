# 台羅拼音轉台語點字線上工具（TJ to Taigu/Taigi Braille Converter on Web）

## 開發者
Lîm Akâu（林阿猴） & KimTsio（金蕉）

---

## 使用方式
1. **輸入方式**：請輸入台羅拼音的正常聲調標示方式，**不使用數字調號**。
   - 範例：`guá sī tâi-uân-lâng`
2. **輸入規範**：
   - 一律使用 **小寫字母輸入**。
   - **組合字詞請使用連字符 `-`**。
   - 標點符號目前尚無統一點字規則，請以空格分隔。

---

## 系統需求
- Python 3.10 以上
- 套件需求：詳見 `requirements.txt`

---

## 啟動方式
```bash
### 安裝相依套件
pip install -r requirements.txt

### 啟動伺服器
python app.py
```
然後用瀏覽器開啟：http://localhost:5000

---

## 版權與使用條款
## 📄 授權 License

MIT License – 歡迎自由使用與修改，請保留原始出處說明。

Copyright © 2025 Lîm Akâu & KimTsio
