# W16 代糖建模與預測 / Sweetener modeling and prediction

## Student entry points
- `tour.html`：中文導覽，約 5:09；`tour.en.html`：English narrated tour, about 4:31.
- `sweetener_model_lab.html`：中文六幕互動；`sweetener_model_lab.en.html`：English six-act numerical modeling lab.
- Standalone lab pages work offline without CDN. Full lesson slides retain existing external Chart.js/font dependencies.

## Exact source and independence
Use the original `data/nb13_demo_spectra.csv` and notebook `NB13_sweetener_model.ipynb`: **simulated Raman785 teaching data, not actual W15 class measurements or a validated food assay**.
- 25 calibration bottles × 2 reloads = 50 spectra.
- 7 blind-test bottles × 2 reloads = 14 spectra.
- 3 pure-reference spectra and 1 simulated commercial challenge; full file has 68 rows × 71 spectral variables.
- Cross-validation uses `sample_id` (25 leave-one-bottle-out folds), not the preparation-group column `group`. Replicates stay together. Independent bottle counts differ from spectrum-row counts.
- The W16 demonstration intentionally includes the public notebook's simulated blind answers so test errors can be calculated. A pipeline-lock/reveal exercise teaches evaluation discipline, not secrecy or cryptographic access control. Actual classroom blind answers must follow the TA's release procedure.

## Six acts
1. 合併資料、分組與封閉性 / Dataset roles, bottle grouping and closure
2. 兩個 PLS1 與校正 CV 選擇 / Two PLS1s and calibration-only selection
3. VIP 與填充劑的間接線索 / VIP and indirect filler information
4. 原始參考 NNLS 與係數尺度 / Reference NNLS and coefficient interpretation
5. 折外預測 LOD／LOQ 近似 / Approximate detection/quantification estimates
6. 校正 PCA 適用域與誠實報告 / Calibration-only domain diagnostics and reporting

## Numerical conventions
**PLS:** one separate PLS1 per analyte, default `scale=True`: X and y means and sample SDs are fitted within each training fold. Compare LV1–8 and two rowwise input routes: raw, or subtract `(mean(first5)+mean(last5))/2`, then divide by the row's sum of absolute corrected values. The notebook chooses preprocessing using aspartame calibration RMSECV, then chooses each analyte's LV. No PLS2 superiority experiment is claimed.

**VIP:** normalized squared weights weighted by LV-explained response sum of squares; `mean(VIP²)=1` for all modeled variables. It is nonnegative importance, not direction, causality, chemical specificity or a formal significance test. Erythritol bands can be indirectly predictive because E=100−A−S. Changing filler can break that relationship even when the target concentrations remain in range.

**NNLS:** raw pure-reference columns for aspartame, sucralose, erythritol plus a constant offset, all four coefficients constrained nonnegative, exactly matching NB13's `scipy.optimize.nnls`. There is **no sum-to-one constraint**. Coefficients are spectral contributions, not automatically mass fractions. Multiplication by 100 reproduces this simulation's reference-scale convention only. Independent reference normalization changes coefficient units; an identical residual does not justify treating normalized-reference coefficients as percentages. Missing components/nonlinear response can invalidate a chemically appealing fit.

**LOD/LOQ:** use sample SD (`ddof=1`) of out-of-fold predictions for the ten zero-analyte calibration rows (five formulations, two reloads), and OLS slope of OOF prediction against reference. LOD≈3.3σ0/slope; LOQ≈10σ0/slope, requiring a positive meaningful slope. The other sweetener varies within those zero-analyte rows. These are pedagogical multivariate approximations, not formal method validation or guaranteed quantification capability. Reported errors are w/w **percentage points**, not relative percent error.

**Domain:** fit mean-centered PCA on calibration spectra only, using the selected input route; project other spectra without refitting. T² measures score-space distance, Q squared reconstruction residual. Approximate training F-limit and new-sample F-limit are distinct; Jackson–Mudholkar uses discarded eigenvalues and distribution assumptions. With raw input/k3: training T²≈8.7648, new-sample T²≈8.9401, Q≈0.0043888. Neither threshold is a universal food-safety rule. The exposed raw k2 setting has nonpositive JM shape h (about −0.29125); the UI explicitly warns that this tail approximation is unreliable rather than presenting the finite cutoff as validated.

## Independently reproduced default values
Raw input, 4 LV per PLS1:
- Aspartame: RMSEC 0.4011, grouped RMSECV 0.7111, blind RMSEP 0.5571, bias −0.1657 percentage points, RPD 2.7800.
- Sucralose: RMSEC 0.3112, grouped RMSECV 0.6303, blind RMSEP 0.5030, bias +0.4049 percentage points, RPD 3.8021.
- NNLS blind RMSEP A/S: 0.9784 / 0.7683 percentage points, on the same 14 spectra.
- Aspartame approximate LOD/LOQ: 2.6809 / 8.1241%; sucralose: 2.8618 / 8.6720%.
- Commercial challenge: raw PLS gives A≈48.2056%, T²≈223.6143, Q≈3.1295. This raw numerical output is shown as a **failure diagnostic, not a reportable concentration**.

All exact numbers, curves, input hash and independent Python references are in `animations/model-reference.json`. This result does not prove PLS always beats NNLS. Seven independent blind bottles are a small validation set; RPD and approximate LOD/LOQ do not certify production use.

## Reporting order
1. Check model/matrix/instrument applicability and calibration range first. If outside, withhold concentration and record the investigation reason.
2. If within, inspect the prediction against LOD/LOQ and flag negative or out-of-range outputs; do not infer nondetection solely from a package-label value.
3. A below-LOQ numeric teaching estimate must be qualified, not presented as validated quantification. Even above the approximate LOQ, intended-use validation remains necessary.
4. Retain preprocessing/LVs, errors, bias, RPD context, VIP, NNLS scales/residuals, uncertainty/limitations and decision rationale for the W17 model card.

## Media and reproduction
Two 1280×720, 12 fps H.264/AAC videos include complete narration and burned-in captions. Optional WebVTT is off by default; SRT, posters, storyboard, narration and timing accompany the package.
```bash
uv venv .venv-w16 --python 3.12
uv pip install --python .venv-w16/bin/python pillow numpy scipy scikit-learn playwright
.venv-w16/bin/python -m playwright install chromium
.venv-w16/bin/python tests/test_w16_sweetener_model.py
.venv-w16/bin/python scripts/verify_w16_media.py
```
Run from the repository root; supply Chromium native dependencies or a local `LD_LIBRARY_PATH`. Media tests require ffmpeg/ffprobe. Narration is ElevenLabs voice **IAN** (`eleven_v3`, slowed 5 % with ffmpeg `atempo=0.95`), the same voice as the earlier weekly tours, for both Chinese and English. The chosen takes are kept in `scripts/vo/w16/` (`texts.json` holds the subtitle text and, for Chinese, a `tts` spelling with homophones that IAN reads correctly, e.g. 譜→普, 確認→卻任; subtitles always use the original text). `scripts/render_w16.py` reads those MP3s, needs ffmpeg and Microsoft JhengHei, and runs on Windows or WSL with `PYTHONUTF8=1`; changing a narration line makes the renderer stop until that take is regenerated and checked with `scripts/vo_tools.py`. Voice generated with ElevenLabs.

## Publication
W16 video/lab follow the opening hook at `index.html#s2` and `index.html#s3`, with English counterparts and homepage entries. Work starts from the deployed W11–W15 main revision and does not regenerate earlier weeks. An open feature PR is not live until an authorized merge and successful Pages deployment are verified.
