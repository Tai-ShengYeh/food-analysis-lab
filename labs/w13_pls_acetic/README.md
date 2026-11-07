# W13 PLS 迴歸：醋酸定量 / PLS acidity calibration

## 學生入口 / Student entry points
- `tour.html`：中文導覽，約 4:18；`tour.en.html`：English tour, about 3:53.
- `pls_lab.html`：中文六幕互動實驗；`pls_lab.en.html`：English six-act lab.
- Standalone labs work offline without CDN dependencies. All student notes and exposure history remain in local browser storage; data are not uploaded. Full lesson slides retain existing external Chart.js/font dependencies.

## 課程資料 / Course data
Exact `data/nb11_demo_spectra.csv`, also embedded in NB11: 16 sample_ids × 3 reloads × 60 wavelengths (48×60). **All spectra and reference roles are simulated teaching data, not real measurements.** In particular, the W4 white-vinegar label denotes a simulated check-sample role, not actual student titration results.

White vinegar is pinned to test. Kennard–Stone on the remaining samples' mean raw spectra selects 12 calibration samples / 36 spectra; test has 4 independent samples / 12 spectra. The computed split agrees with `orange/or13_acetic.csv`. Replicates stay together in leave-one-sample_id-out CV.

## 六幕 / Six acts
1. 參考值、稀釋與整組切分 / References, dilution and grouped split
2. 光譜前處理與 PLS 對照 PCA / Preprocessing and supervised directions
3. 分組交叉驗證選 LV / Grouped CV and model complexity
4. 逐列與分組 CV 的外洩比較 / Rowwise versus grouped validation
5. 鎖定設定後揭露測試 / Lock settings before revealing test errors
6. 參考偏差／隨機誤差、適用性與報告 / Reference errors, applicability and reporting

The lab computes genuine PLS1 NIPALS models, not cached result arrays. Controls cover raw/SNV/SG, LV 1–6 and Scale on/off. Predictions, CV tables, original CSV and JSON reports are downloadable. Exposed test results cannot become untouched again by clicking reset: subsequent tuning is flagged as reuse, and exposure survives language changes/reloads/reset. Local storage is an educational aid, not a tamper-proof audit.

## 數值慣例 / Numerical conventions
- SNV: each row's population SD (`ddof=0`).
- SG: 9-point, degree 2, derivative 1, interpolated edges, `delta=1` to reproduce NB11. Values are **per index**, not per nm; rounded wavelength headers are not exactly uniformly spaced.
- PLS: `scale=True` by default; X and y are centered and scaled with training-fold sample SD (`ddof=1`). No held-out fold/test means or scales enter fitting.
- Grouped CV: 12 leave-one-sample_id-out folds on calibration only. Rowwise comparison uses deterministic index-mod-5 folds, not NB11's optional shuffled KFold; rowwise RMSE is not guaranteed to be lower on every dataset.
- Reference-error sensitivity changes calibration y only, sharing perturbations across each sample_id; fixed-seed Gaussian errors are normalized to the selected sample SD. It is a sensitivity experiment, not a reproduction of the original data generator.
- RPD uses sample SD of the 12 test-row references divided by RMSEP; only four independent samples are present. RPD is test-distribution dependent and is not a universal acceptance threshold.

Computed default demo: SNV, Scale on, 2 LV; RMSEC 0.2692, grouped RMSECV 0.3999, RMSEP 0.4272 % w/v, test R² 0.9287, bias −0.0542 % w/v, RPD 3.91. Raw best CV within LV1–6 is LV3 (0.4581); SG best is LV3 (0.4899). Exact values, input SHA-256 and independently computed scikit-learn results are in `animations/pls-reference.json`.

These are not production performance claims. The teaching domain is 0–10 % w/v aqueous acetic acid/vinegar conditions. Matrix changes, instrument changes, reference uncertainty, allowable errors and additional independent samples require validation. Reference random error contributes to expected residual variance but is not an inviolable lower bound on every observed small-sample RMSEP.

## Media and reproduction
Two separate 1280×720, 12 fps H.264/AAC videos, full narration and burned-in captions; optional WebVTT is off by default to avoid duplication. SRT, narration, storyboard, poster and measured timing are in `animations/`.

From the repository root:
```bash
uv venv .venv-w13 --python 3.12
uv pip install --python .venv-w13/bin/python pillow numpy scipy scikit-learn playwright
.venv-w13/bin/python -m playwright install chromium
.venv-w13/bin/python tests/test_w13_pls.py
.venv-w13/bin/python scripts/verify_w13_media.py
```
Chromium host libraries must be available or supplied through `LD_LIBRARY_PATH`. Media tests require ffmpeg/ffprobe. `scripts/render_w13.py` requires WSL Windows System.Speech voices Microsoft Hanhan Desktop / Microsoft Zira Desktop and Microsoft JhengHei; narration cache hashes include text+voice, and intermediates remain in scratch.

## Verification scope
- Six unittest tests pass, including 36 preprocessing/Scale/LV combinations and 432 grouped-CV fold models compared independently with scikit-learn; data/notebook/Orange split parity, SciPy SG, coefficients, predictions and metrics are checked.
- Chinese/English desktop/mobile offline browser checks cover controls, feedback, notes, persistence/reset, test-lock/exposure rules and actual downloads, with zero HTTP(S) requests and browser errors.
- Both final MP4s fully decode; complete audio, 12 VTT cues each, desktop/mobile playback, keyboard isolation, hidden-slide pause, lazy iframe and home links pass. Exact media hashes are in `scripts/w13-media-verification.json`.
- Browser coverage is Chromium only; Safari/Firefox and physical mobile devices have not been tested. Numerical tests also require Node.js to execute the same JavaScript module outside the browser.

## Integration and publication
Video and lab follow the W13 opening hook: `index.html#s2` and `index.html#s3`, with English counterparts. Course homepage links are included. The W13 branch is independent of pending W11/W12 PRs; earlier weeks are not regenerated or silently merged. An open PR is not the live GitHub Pages course.
