# W4 第 19 頁 Bland–Altman 旁白 / slide-19 narration

- 聲音 Voice: ElevenLabs **IAN** (`voice_id` `tSv4yoTPFFmCMaJpNf0A`), model `eleven_v3`，中英同一聲音（同 W1、W11–W16 導覽）。
- `texts.json`：每段旁白的文字；中文 `tts` 欄位是送給配音的同音字版本（軸→妯），字幕/檢查用 `text`。
- 檔名：`<lang>-0N` ＝第 N 步一進來的提問旁白；`<lang>-1N` ＝第 N 步揭曉後的解說（N＝4、5、6）。
  （不用 `04r` 之類字尾：`vo_tools.py` 會把結尾字母當成重錄版本。）
- 旁白裡說「自動滴定 / the automatic method」不說 PASCO，之後換儀器不必重錄。
- 投影片用的檔案：`labs/w04_titration/audio/ba_<key>.mp3`，由這裡的原檔轉出：
  `ffmpeg -i <key>.mp3 -af atempo=0.95 -ac 1 -ar 44100 -b:a 64k ../../../labs/w04_titration/audio/ba_<key>.mp3`
- 檢查：`PYTHONUTF8=1 python scripts/vo_tools.py check scripts/vo/w04ba`
- 投影片產生器：`scripts/build_w04_bland_altman.py`（只在本機，`.gitignore` 的 `build_*.py` 不收；從 BA 投影片加入前的版本重建：
  `git restore --source=5279c8c^ -- labs/w04_titration/index.html labs/w04_titration/index.en.html` 後執行）。
Voice generated with ElevenLabs.
