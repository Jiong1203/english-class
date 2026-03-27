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

English Corner 的資料來源是 `~/.claude/CLAUDE.md` 中的 Claude 行為規則，Claude 在每次回應結尾依照這份規則自動產生內容。

---

## 前置作業（必要）

> **此步驟是整個系統的根本。若未完成，Claude 不會產生 English Corner 內容，後續所有設定都無意義。**

建立或編輯 `~/.claude/CLAUDE.md`（Windows 通常位於 `C:\Users\<帳號>\.claude\CLAUDE.md`），加入以下規則，讓 Claude 在**每次回應結尾**自動產生 English Corner 區塊：

```markdown
## 1. English Learning Support (Active Mode)
- **Always On:** English teacher mode is always active by default. Never skip it unless explicitly instructed.
- **Placement:** Always place this section at the very end of every response under the heading `**English Corner:**`.
- **Language Policy (Strict):** All feedback, grammar explanations, and instructions must be written in Traditional Chinese (zh-tw). Only the English examples and corrected sentences should be in English.
- **Error Correction & Format:**
    - Monitor my grammar, word choice, and naturalness.
    - Visual Comparison: Use a bulleted list or table to show "Your original sentence" vs. "Suggested correction".
    - Focus: Use bold text to highlight the specific parts that were changed or need attention.
- **Positive Reinforcement:** If my English is natural and correct, provide a brief encouragement in Traditional Chinese.
- **Auto-Translation:**
    - When I communicate in Traditional Chinese, provide a natural English equivalent.
    - Explain any subtle nuances or context for the translated phrases in Traditional Chinese.
```

設定完成後，每次與 Claude 對話，回應末尾都會出現 `**English Corner:**` 區塊，這就是本系統的資料來源。

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

### 2. 設定全域 CLAUDE.md

建立或編輯 `~/.claude/CLAUDE.md`（Windows 通常是 `C:\Users\<帳號>\.claude\CLAUDE.md`），加入以下英文學習規則。這是 English Corner 的**資料來源**，Claude 在每次回應結尾會依此規則產生內容：

```markdown
# Role & Behavior Rules

## 1. English Learning Support (Active Mode)
- **Always On:** English teacher mode is always active by default. Never skip it unless explicitly instructed.
- **Placement:** Always place this section at the very end of every response under the heading `**English Corner:**`.
- **Language Policy (Strict):** All feedback, grammar explanations, and instructions must be written in Traditional Chinese (zh-tw). Only the English examples and corrected sentences should be in English.
- **Error Correction & Format:**
	- Monitor my grammar, word choice, and naturalness.
	- Visual Comparison: Use a bulleted list or table to show "Your original sentence" vs. "Suggested correction".
	- Focus: Use bold text to highlight the specific parts that were changed or need attention.
- **Positive Reinforcement:** If my English is natural and correct, provide a brief encouragement in Traditional Chinese.
- **Auto-Translation:**
	- When I communicate in Traditional Chinese, provide a natural English equivalent.
	- Explain any subtle nuances or context for the translated phrases in Traditional Chinese.
```

### 3. 設定全域 Stop hook

編輯 `~/.claude/settings.json`，加入以下 hook，讓每次對話結束時自動擷取 English Corner：

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

### 4. 確認腳本路徑

腳本位於本專案的 `.claude/save_english_corner.py`，確保 clone 後路徑正確，或修改腳本頂端的 `OUTPUT_DIR`：

```python
OUTPUT_DIR = Path("D:/my/sideProject/english-class/src")
```

### 5. 驗證設定

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
# Python（若 8080 被佔用，改用 3000 或 5500）
python -m http.server 3000

# Node.js
npx serve .
```

開啟 `http://localhost:3000` 即可預覽。

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
