# W15 代糖專題 I：設計、配製與量測 / Sweetener preparation and measurement

## Student entry points
- `tour.html`：中文導覽，約 5:04；`tour.en.html`：English tour, about 4:43.
- `sweetener_lab.html`：中文六幕互動；`sweetener_lab.en.html`：English six-act preparation/QC lab.
- Standalone lab pages are offline/no-CDN. Full course slides retain their pre-existing external font/Chart.js dependencies. W15 concerns design, preparation and measurement; PLS/NNLS modeling belongs to W16.

## Provenance and blind-sample handling
The 25 calibration formulations are extracted exactly from `data/nb13_demo_spectra.csv`: A and S levels 0/2.5/5/7.5/10 % w/w, CAL ID `5*i+j`, and filler E = 100−A−S. The proposed physical preparation allocation is G`1+((j−i) mod 5)`, matching the W15 lesson; it is not the source dataset's placeholder group=0.

The full NB13 file contains 68 rows, including prior reference/unknown roles; **those 68 rows are not the W15 measurement count**. W15 plans 25 calibration bottles + 7 blind bottles = 32, each visiting 6 stations with 2 reloads: 384 separate spectra. Replicates are not independent physical bottles and must stay grouped in W16 validation.

Student preparation records withhold the seven blind concentrations. The bundle contains the calibration-only `animations/calibration-design.csv`, not the original full NB13 CSV with public simulated blind answers. Real class blind concentrations remain with the TA until W16. Simulated source values and teaching calculations are not actual class measurements.

## Six acts
1. 全因子與混淆 / Full factorial versus confounded designs
2. 拉丁分工與全班合併 / Latin allocation and combining the complete design
3. 實際秤重、不確定度與幾何稀釋 / Actual masses, uncertainty and geometric dilution
4. 隨機分架與時間漂移 / Random racks and drift confounding
5. 六站輪轉、檔案與時間預算 / Six-station rotation, file manifests and timing
6. 重裝 SD／RSD 與 QC / Reload sample SD, RSD and within-bottle QC

## Scientific conventions and limits
- The balanced 25-point target design has corr(A,S)=0 and rank 3 including an intercept. A 1:1 diagonal is rank deficient for separating the two effects. Orthogonality does not guarantee adequate spectral signal, chemical specificity or model validity; actual weighed fractions should be rechecked.
- E is a closure remainder, not a third independent factor. Each preparation group covers both factor levels, but individual-group correlation need not be zero. Combine all 25 formulations rather than treating each group's five bottles as a complete calibration design.
- Actual w/w fractions use the sum of all **actual** masses. CAL-17 example: A=0.1523, S=0.0997, E=1.7489 g; total=2.0009 g; A≈7.6116%, S≈4.9828%, E≈87.4057%.
- The illustrative rectangular balance half-width ±0.1 mg implies u=0.1/√3≈0.057735 mg. Balance readability alone does not establish this uncertainty. Relative u(m_A)≈0.03791%, while u(A fraction)≈0.002684 percentage points under independent equal mass-error assumptions. Shared-denominator effects are propagated through derivatives with respect to all three masses; correlated systematic balance errors are not included in that simple model.
- Geometric dilution accounts for both sweeteners and all filler. Mass conservation and correct procedure do not establish powder homogeneity; reload variability and representative sampling still need evaluation.
- Seeded randomization reduces systematic run-order alignment but cannot guarantee removal of drift in every realized order. White references address instrument response, not mixture uniformity. Any drift illustration is a conceptual simulation, not measured instrument behavior.
- Rack sizes are 6/6/5/5/5/5. In synchronized rotation each round is paced by the largest rack. At 1.5 min/spectrum, 2 reloads and 1 min reference per round: (6×2×1.5+1)×6=114 min, versus 115 min available. The per-station summed workload is 102 min; it differs from synchronized elapsed time. At 2 min/spectrum the synchronized estimate is 150 min. Extra handling delays are not included; ask the TA rather than skipping bottles/reloads.
- Sample SD uses n−1. For a pair, SD=|x1−x2|/√2; 102/98 give SD and RSD≈2.828 (mean100). Five illustrative reloads 102/98/105/95/100 give sample SD/RSD≈3.808. RSD is undefined when the mean is zero. Pool within-bottle variation separately from between-formulation differences; two reloads alone give a noisy variance estimate.
- No universal solubility/LOD, RSD acceptance threshold or guaranteed Raman-vs-NIR ranking is asserted. Verify feasibility on actual instruments with appropriate low-level/blank samples. No real pilot is claimed to have been performed by this software.
- Avoid powder inhalation and consumption of lab samples. Follow institutional handling/laser procedures; Raman is TA-operated in the lesson plan. This is not food authenticity or safety certification.

## Video and reproducibility
Separate 1280×720, 12 fps H.264/AAC videos include full narration and burned-in captions. Optional WebVTT is off by default to avoid duplicate captions; SRT, narration, storyboard, posters and timing are provided. The numerical preparation reference contains only calibration designs and illustrative calculations, never blind truths.

From repository root:
```bash
uv venv .venv-w15 --python 3.12
uv pip install --python .venv-w15/bin/python pillow numpy scipy playwright
.venv-w15/bin/python -m playwright install chromium
.venv-w15/bin/python tests/test_w15_sweetener.py
.venv-w15/bin/python scripts/verify_w15_media.py
```
Chromium libraries must be available on the host or supplied through `LD_LIBRARY_PATH`; media verification requires ffmpeg/ffprobe. Narration is ElevenLabs voice **IAN** (`eleven_v3`, slowed 5 % with ffmpeg `atempo=0.95`), the same voice as the earlier weekly tours, for both Chinese and English. The chosen takes are kept in `scripts/vo/w15/` (`texts.json` holds the subtitle text and, for Chinese, a `tts` spelling with homophones that IAN reads correctly, e.g. 譜→普, 確認→卻任; subtitles always use the original text). `scripts/render_w15.py` reads those MP3s, needs ffmpeg and Microsoft JhengHei, and runs on Windows or WSL with `PYTHONUTF8=1`; changing a narration line makes the renderer stop until that take is regenerated and checked with `scripts/vo_tools.py`. Voice generated with ElevenLabs.

## Verification scope
- 14 tests pass: 10 independent numerical tests and 4 bilingual desktop/mobile browser tests. Coverage includes source design parity, correlations/rank, Latin allocation, finite-difference uncertainty/covariance, mixing mass conservation, seeded randomization, all 384 unique measurements, synchronized timing and sample-SD/pooled QC edge cases.
- Offline browser tests cover controls, feedback/reflections, persistence/reset, actual downloads, withheld blind labels and strict mobile width. No external requests or JavaScript errors were observed.
- Both final MP4s fully decode with complete audio and 12 VTT cues each. Desktop/mobile playback, hidden-slide pause, keyboard isolation, homepage links and lazy lab iframe pass; exact media hashes are recorded in `scripts/w15-media-verification.json`.
- Chromium tested; Safari/Firefox and physical mobile devices have not been tested. Numerical JavaScript tests also require Node.js.

## Publication
Video/lab are inserted after the W15 hook at `index.html#s2` / `index.html#s3`, with English counterparts and homepage links. This is an independent branch based on main; pending W11–W14 PRs are not silently merged. An open PR must be authorized, merged and deployed before changes appear on the live GitHub Pages course.
