# W11 光譜前處理與相似度 / Preprocessing and spectral similarity

## 學生使用 / Student entry points
- `tour.html`：中文導覽（約 2:49）；`tour.en.html`：English tour (about 2:42).
- `preprocess_lab.html`：中文六幕互動實驗；`preprocess_lab.en.html`：English interactive lab.
- 互動實驗可直接在瀏覽器開啟，無 CDN 或網路依賴。學生資料只儲存在該瀏覽器；CSV 與 JSON 可下載，沒有上傳功能。
- The standalone interactive pages run offline. The full lesson slides retain their existing external Chart.js/font dependencies.

## 六幕 / Six acts
1. 原始光譜與干擾 / Raw spectra and interference
2. 中值/MAD 尖峰移除 / Median-MAD despiking
3. ALS 基線與 λ、p / ALS baseline and parameter tradeoffs
4. SNV 與 population SD / SNV and population SD
5. SG 平滑、一/二階導數 / SG smoothing and first/second derivatives
6. 四指標 Top-3、歧義、混合與庫外情境 / Four metrics, top three, ambiguity, mixtures, out-of-library samples

每幕包含預測、可調參數、即時曲線與計算、解釋與個人紀錄。All spectra are seeded synthetic teaching examples, not measured chemical references. A/B/C/A′ are abstract library labels. No universal similarity threshold is claimed, and signal coefficients are not mass fractions. This lab is not a validated food identity or safety test and does not implement NNLS quantification or real-data import.

## 影片 / Video package
1280×720, 12 fps, H.264 + AAC. Separate Traditional Chinese and English narration; complete burned-in narration captions, optional VTT, downloadable SRT, scripts, storyboard and measured cue timing in `animations/`. The optional VTT track is off by default to avoid duplicate captions.

## Reproduce and verify (repository root)
```bash
uv venv .venv-w11 --python 3.12
uv pip install --python .venv-w11/bin/python pillow numpy scipy playwright
.venv-w11/bin/python -m playwright install chromium
.venv-w11/bin/python tests/test_w11_preprocess.py
.venv-w11/bin/python scripts/verify_w11_media.py
```
Chromium system libraries must be installed or supplied through `LD_LIBRARY_PATH`; no privileged changes are made by these scripts. `ffmpeg` and `ffprobe` must be on PATH. Media verification saves exact-MP4 SHA-256 and browser checks in `scripts/w11-media-verification.json`, screenshots in the Hermes scratch folder.

To rerender the bilingual tours:
```bash
.venv-w11/bin/python scripts/render_w11.py
```
The renderer currently requires WSL with Windows System.Speech voices Microsoft Hanhan Desktop and Microsoft Zira Desktop, and Microsoft JhengHei at the Windows font path or the documented user font cache. Audio stays in scratch; text+voice hashes invalidate stale speech cache. It is not a cross-platform TTS installer.

## Verification scope
- 389 interactive assertions, independent SciPy ALS/SG comparisons, four language/viewport combinations, offline interaction and actual downloads.
- Both videos fully decoded with ffmpeg; complete audio timing and VTT cues checked.
- Chromium desktop/mobile playback, native subtitle cue loading, video key isolation, hidden-slide pause, lazy iframe and course homepage links checked.
- Safari/Firefox and real mobile devices have not been tested.
- Added to the W11 deck directly after the blind-powder hook: `index.html#s2` video, `index.html#s3` interactive lab. No earlier weeks were regenerated.
- Publication requires the feature PR to be merged and GitHub Pages to deploy; a feature branch alone is not the live course.
