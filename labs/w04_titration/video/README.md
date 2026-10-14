# W4 課前導覽動畫：pH 一樣，為什麼酸度不一樣？

約 1 分 46 秒、手繪草圖風（同 W1、W3），用 [code-animation-explainer](https://github.com/FW1201/code-animation-explainer) skill 製作：腳本與分鏡 → 風格 tokens → ElevenLabs 配音＋讀音檢核 → 逐字對時字幕 → 逐格渲染。

| 檔案 | 內容 |
|---|---|
| `script.md`、`storyboard.json` | 逐字旁白與分鏡（字幕以 `narration` 為準，`tts` 是送配音的寫法） |
| `facts.md` | 片中每個數字的出處（對回 W4 投影片） |
| `direction-approved.md` | 風格與結構的決定 |
| `compositions/curve.js` | 滴定曲線與一階導數（0.075 M 醋酸 25 mL／0.1 M NaOH，電荷平衡式；同投影片第 6 頁） |
| `compositions/w04.html` | 動畫本體（GSAP 時間軸＋Rough.js 手繪，`?t=秒數` 可看任一格） |
| `style/`、`fonts/`、`vendor/` | 風格 tokens、筆順資料、字型子集、GSAP |
| `vo/raw/*.mp3` | 採用的配音（聲音 IAN，eleven_v3） |
| `captions/` | 字幕（SRT）與時間軸 |
| `deliver/` | YouTube 用的 SRT 與說明欄 |

## 重新產生影片

需要 skill（放在 `~/.claude/skills/code-animation-explainer/`，或設定 `CAE_SCRIPTS` 指向它的 `scripts/`）、ffmpeg、Node 22＋playwright、`pip install sherpa-onnx pypinyin numpy`。

```bash
for i in 0 1 2 3 4 5 6 7 8; do ffmpeg -y -i vo/raw/s$i.mp3 -af atempo=0.95 -ar 44100 -ac 1 vo/s$i.wav; done
python3 $CAE_SCRIPTS/align_audio.py storyboard.json --vo vo/ --asr   # 逐字對時
python3 build.py                                                      # 字幕＋compositions/timing.js
python3 mix.py                                                        # 配音＋配樂 → out/mix.wav
node $CAE_SCRIPTS/render_seek.mjs compositions/w04.html out/w04_titration.mp4 --audio out/mix.wav --crf 20
```

改了旁白就重錄那一幕、重跑上面步驟；畫面用 `AT("幕", "關鍵字")` 對時，會自動跟上新的配音時間。
