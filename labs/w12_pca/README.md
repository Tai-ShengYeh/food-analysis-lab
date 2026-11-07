# W12 主成分分析：食用油 / PCA: edible oils

## 開啟教材 / Student entry points
- `tour.html`：中文導覽，約 3:39；`tour.en.html`：English narrated tour, about 3:31.
- `pca_lab.html`：中文六幕互動實驗；`pca_lab.en.html`：English six-act lab.
- 獨立互動實驗無 CDN，可離線開啟。Standalone lab pages work offline. The full lesson slides retain their existing external Chart.js/font dependencies.

## 原始資料與限制 / Data and limitations
Use the exact repository `data/nb10_demo_spectra.csv` also embedded in notebook NB10: 18 spectra (six oils, three replicates) by 60 spectral variables, 900–1800 cm⁻¹. These are **simulated teaching data**, not real food authenticity measurements. Oil labels are for plot colors and interpretation, not numeric PCA input.

The browser performs genuine PCA calculations, not cached score plots. Autoscale follows the lesson's sample standard deviation (`ddof=1`); NB10's Python autoscale code uses population SD (`ddof=0`). The lab identifies this convention explicitly: with the same complete sample set this changes absolute autoscaled eigenvalues, not the explained-variance ratios or loading directions. Scores locate samples; loadings weight variables. Explained variance is not classification accuracy. Component signs are arbitrary; scores and loadings can flip together without changing the model. Never exclude a point simply to make clusters look better: inspect its spectrum and records, document the reason, and actually refit.

The PEA_r3 example contains an injected measurement artifact. In centered PCA on the exact CSV:
- PC1/PC2/PC3 explain about 46.3%/28.3%/23.0%.
- PEA_r3 contributes about 74.0% of the full-data PC2 score sum of squares.
- After documented exclusion and refitting, PC1/PC2 explain about 63.5%/33.2%.
- The largest absolute PC2 loading shifts from 1159.322 to 1525.424 cm⁻¹.

These percentages are specific to this demonstration CSV, not universal properties of oils or PCA. The exact input SHA-256 and independently computed numbers are in `animations/pca-reference.json`.

## 六幕 / Six acts
1. 光譜與樣品×波數矩陣 / Spectra and the sample-variable matrix
2. 轉動投影方向 / Rotating a two-variable projection
3. 中心化與 autoscale / Centering versus autoscaling
4. Scores 與 loadings / Sample positions and variable weights
5. Scree 與重建 / Explained variance and reconstruction
6. PEA_r3 調查與重新 fit / Outlier investigation and refitting

Predictions, explanations, controls, plots and exportable records support student reasoning. This is not a validated oil classifier, adulteration detector, or food-safety test.

## Video package
Separate Chinese and English MP4s, 1280×720, 12 fps, H.264/AAC, complete narration and burned-in text. SRT downloads and optional WebVTT tracks are provided; native subtitles are off by default to avoid duplication. Narration, storyboard, posters, PCA reference values and measured timing are under `animations/`.

## Reproduce (repository root)
```bash
uv venv .venv-w12 --python 3.12
uv pip install --python .venv-w12/bin/python pillow numpy scipy playwright
.venv-w12/bin/python -m playwright install chromium
.venv-w12/bin/python tests/test_w12_pca.py
.venv-w12/bin/python scripts/verify_w12_media.py
```
Chromium native dependencies must be available on the host or supplied through `LD_LIBRARY_PATH`. Verification does not install system packages. Media checks require ffmpeg/ffprobe on PATH, and record exact final MP4 hashes in `scripts/w12-media-verification.json`.

Rerender with `scripts/render_w12.py`. It currently requires WSL and Windows System.Speech voices Microsoft Hanhan Desktop / Microsoft Zira Desktop, plus Microsoft JhengHei. Audio/intermediate files remain in scratch, with text+voice hashes to invalidate stale speech cache. This is not a cross-platform TTS installer.

## Verification scope
- `tests/test_w12_pca.py`: 846 assertions passed, including exact CSV parity, independent NumPy SVD comparisons for centered/autoscaled full/refit data, reconstruction, every control, prediction feedback, persistence/reset, exclusion-reason guard and four actual downloads.
- Chinese/English at desktop 1440×1000 and mobile 390×844: zero JavaScript errors, zero HTTP(S) requests for offline labs.
- Both final MP4s fully decoded; complete narration, 11 VTT cues per language, desktop/mobile playback, keyboard isolation, hidden-video pause, home links and iframe integration passed.
- Visual checks covered encoded scenes, captions and browser layout. Safari/Firefox and physical mobile devices have not been tested.

## Course integration and publication
W12 video and lab are inserted immediately after the lesson hook, at `index.html#s2` and `index.html#s3` (English equivalents also supplied). Course home has both entry links. No other weeks are regenerated. The W12 change is an independent PR based on main; W11 is not silently included or merged. An open PR is **not** the live GitHub Pages course.
