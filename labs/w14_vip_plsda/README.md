# W14 VIP、PLS-DA 與離群值 / VIP, PLS-DA and outlier diagnostics

## Student entry points
- `tour.html`：中文導覽，約 4:49；`tour.en.html`：English tour, about 4:27.
- `vip_plsda_lab.html`：中文六幕互動；`vip_plsda_lab.en.html`：English six-act lab.
- Standalone lab pages are offline/no-CDN. Full lesson slides retain their pre-existing external font/Chart.js dependencies.

## Exact course datasets
All three original NB12 CSVs are **simulated teaching spectra, not actual food-testing measurements**:
- `data/nb12_demo_spectra_vip.csv`: 80 samples × 81 variables, acidity response. 60 training / 20 held-out samples, seed 14.
- `data/nb12_demo_spectra_oils.csv`: 90 samples × 70 variables, six oil classes. Stratified 63 training / 27 held-out samples, seed 1.
- `data/nb12_demo_spectra_outlier.csv`: 48 samples × 50 variables; fit PCA only on the 40 rows marked calibration, project all others without refitting.

Numeric PCA/PLS calculations are performed in the browser; bundled source values and deterministic split/fold indices document provenance, not precomputed VIP/classification curves. Exact source hashes and independent Python references are in `animations/numerical-reference.json`.

## Six acts
1. 正確 VIP 與 extra-sum bug / VIP formula checks and the extra-sum bug
2. 波長篩選與選擇偏誤 / Variable selection and fold-local validation
3. one-hot 與 PLS-DA / One-hot targets, PLS2 scores and argmax
4. 混淆矩陣與逐類指標 / Confusion matrix, sensitivity and specificity
5. 校正 PCA 的 T²／Q / Calibration-only PCA and complementary diagnostics
6. 模型適用性與證據紀錄 / Applicability and investigation evidence

## Interpretation safeguards
- VIP is nonnegative, not direction, causality or a significance test. VIP>1 is a heuristic. `mean(VIP²)=1` applies to the **whole set** of modeled variables, not any extracted subset.
- The identity is necessary but not sufficient: all VIPs equal one pass it but are not proof of a correct implementation. The demonstrated extra-sum bug on 81 variables gives every VIP=9 and mean(VIP²)=81.
- NB12's selected-model CV uses a mask chosen on all training data; disclose that this selection sees validation-fold labels. Compare with fold-local reselection at prespecified settings. Do not present fixed-mask CV as unbiased or retune against test RMSEP.
- PLS-DA regresses six one-hot columns simultaneously, `scale=False` per NB12; scores are **not probabilities**, and argmax determines the predicted class.
- Accuracy can hide weak sensitivity: the baseline test gets 24/27 correct, while ROO sensitivity is only 2/4. Inspect classwise metrics and sample counts.
- T² measures retained score-space distance; Q measures squared reconstruction residual. Both derive from one fitted calibration PCA, but answer different questions.
- At k=2/n=40, the approximate T² calibration limit is 6.6604; the new-sample version multiplies by (n+1)/n to 6.8269. Jackson–Mudholkar approximate Q limit is 0.00118257. Limits are model-specific approximations, not universal accept/reject rules or proof of a measurement fault.
- Investigate flagged samples and retain evidence; do not silently delete points. Instrument shifts may yield high Q despite ordinary scores. This lab does not certify food authenticity, safety, production quality or cross-instrument transfer.
- Orange's beginner route is PCA plus logistic regression, not PLS-DA; fitting PCA on all data before classifier CV leaks information. Fit dimensionality reduction within training folds. Apply Domain projections alone do not compute the full Q diagnostic.

## Baseline reproduction
- VIP regression: full 81-variable model LV4, RMSECV 0.1756 / RMSEP 0.1658; VIP>1 selects 18 variables, selected LV3, fixed-mask RMSECV 0.2256 / RMSEP 0.1329. Conflicting CV/test changes are not evidence of universal superiority.
- PLS-DA: calibration CV chooses LV6; independent 27-sample confusion matrix matches NB12, accuracy 88.9%.
- T²/Q: leverage example has high T² but low Q; instrument-shift examples have high Q. All values and plots are specific to simulated datasets.

## Video and reproducibility
Two 1280×720 12 fps H.264/AAC videos contain complete narration and burned-in captions. Optional WebVTT is off by default to avoid duplicate subtitles; SRT, narration scripts, storyboard, posters and timing are provided.

From repository root:
```bash
uv venv .venv-w14 --python 3.12
uv pip install --python .venv-w14/bin/python pillow numpy scipy scikit-learn playwright
.venv-w14/bin/python -m playwright install chromium
.venv-w14/bin/python tests/test_w14_vip_plsda.py
.venv-w14/bin/python scripts/verify_w14_media.py
```
Chromium dependencies must exist on the host or be supplied by `LD_LIBRARY_PATH`. Media tests require ffmpeg/ffprobe. The renderer `scripts/render_w14.py` uses `scripts/course_video_common.py`, WSL Windows System.Speech voices Microsoft Hanhan Desktop / Microsoft Zira Desktop, and Microsoft JhengHei. Intermediates remain in scratch, and speech cache hashes include text+voice.

## Verification scope
- 21 tests passed (16 numerical, 5 browser), including PLS1 LV1–8, true joint PLS2 LV2–8, per-LV confusion matrices, fold-local selection, held-out independence, PCA projectors/reconstruction, and SciPy T²/Q limits for k1–4.
- Chinese/English desktop/mobile checks cover all controls, threshold infeasibility, lock/exposure history, persistence/reset and five download types; zero external requests/browser errors. Direct file:// opening is tested. Mobile horizontal overflow is strictly checked.
- Final MP4s fully decode; complete audio, 13 VTT cues each, playback, media keyboard isolation, hidden-slide pause, lazy iframe and home links pass. Exact media hashes are in `scripts/w14-media-verification.json`.
- Numerical tests additionally require Node.js. Browser coverage is Chromium only; Safari/Firefox and physical mobile devices have not been tested.

## Publication
W14 tour/lab follow the opening hook at `index.html#s2` / `index.html#s3`, with English equivalents and course-home entries. This is an independent branch based on main; W11–W13 are not regenerated or silently merged. A feature PR must be authorized, merged and deployed before it appears on the live GitHub Pages course.
