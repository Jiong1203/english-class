# English Corner

使用 Claude Code 自動擷取每日 English Corner 學習記錄，並以靜態網站呈現，部署於 GitHub Pages。

## 網站預覽

左側欄位顯示日期選單，點選日期後右側呈現當天所有 English Corner 內容。

---

## 如何運作

每次與 Claude Code 的對話結束時，全域 Stop hook 會自動觸發 Python 腳本，從 session transcript 中擷取所有 `**English Corner:**` 區塊，並依日期儲存至 `src/English_YYYYMMDD.md`，同時更新 `src/index.json`。

```
使用者與 Claude 對話結束
         │
         ▼
  Stop hook 觸發（~/.claude/settings.json）
         │
         ▼
  .claude/save_english_corner.py
         │
         ├─► src/English_YYYYMMDD.md   (新增或 append)
         └─► src/index.json            (日期清單更新)
```

---

## 換新電腦快速設定

### 1. 安裝 Python

下載並安裝 [Python 3.12+](https://www.python.org/downloads/)。

安裝時勾選：
- **Add Python to PATH**
- **Install py launcher for all users**

安裝完成後，找到 Python 執行檔路徑，例如：
```
C:\Users\<你的帳號>\AppData\Local\Programs\Python\Python3xx\python.exe
```

### 2. 設定全域 Stop hook

編輯 `~/.claude/settings.json`（Windows 通常是 `C:\Users\<帳號>\.claude\settings.json`），加入以下 hook：

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"C:/Users/<帳號>/AppData/Local/Programs/Python/Python3xx/python.exe\" \"D:/my/sideProject/english-class/.claude/save_english_corner.py\" 2>/dev/null || true",
            "timeout": 30,
            "statusMessage": "Saving English Corner...",
            "async": true
          }
        ]
      }
    ]
  }
}
```

> 注意：將 `<帳號>` 與 `Python3xx` 替換為你的實際路徑。

### 3. 確認腳本路徑

腳本位於本專案的 `.claude/save_english_corner.py`，確保 clone 後路徑正確，或修改腳本頂端的 `OUTPUT_DIR`：

```python
OUTPUT_DIR = Path("D:/my/sideProject/english-class/src")
```

### 4. 驗證設定

克隆此 repo 並進入任一有 Claude Code 的專案進行對話，對話結束後確認：

```
D:\my\sideProject\english-class\src\
├── index.json
└── English_YYYYMMDD.md
```

若檔案出現，代表設定正確。

---

## 部署至 GitHub Pages

1. 將此 repo 推上 GitHub
2. 前往 **Settings → Pages**
3. Source 選擇 `main` branch，根目錄 `/`
4. 儲存後等待部署，網址為 `https://<username>.github.io/english-class/`

> 每次新增當天記錄後，commit 並 push，GitHub Pages 即自動更新。

---

## 本機預覽

由於瀏覽器安全限制，直接開啟 `index.html` 無法讀取 `src/` 下的檔案，需透過本機伺服器：

```bash
# Python
python -m http.server 8080

# Node.js
npx serve .
```

開啟 `http://localhost:8080` 即可預覽。

---

## 檔案結構

```
english-class/
├── index.html                        # 靜態網站主頁
├── src/
│   ├── index.json                    # 日期清單（自動維護）
│   └── English_YYYYMMDD.md           # 每日 English Corner 記錄
├── .claude/
│   ├── save_english_corner.py        # Stop hook 腳本
│   └── settings.local.json          # 專案本地設定
└── README.md
```
