# 食品分析實驗（Food Analysis Lab）

大學部食品分析實驗課的公開教材：每週實驗投影片、Google Colab 數據品管筆記本，以及工廠影片導入對照表。教材以 Nielsen's *Food Analysis* 6th ed. 為主軸。

- 課程入口（每週教材）：https://tai-shengyeh.github.io/food-analysis-lab/
- 實驗影片對照表：https://tai-shengyeh.github.io/food-analysis-lab/video-map.html
- 學期規劃：https://tai-shengyeh.github.io/food-analysis-lab/plan.html

## Colab 筆記本

| 週 | 筆記本 | 開啟 |
|---|---|---|
| W1 | NB01 容量器具校正：平均、SD、RSD、95% 信賴區間、準確度 vs 精密度 | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB01_volumetric_calibration.ipynb) |
| W2 | NB02 水分與水活性：濕基／乾基、恆重、烘箱 vs 紅外線配對比較 | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB02_moisture_aw.ipynb) |
| W3 | NB03 灰分與鈉離子：稀釋倍數、NaCl 換算、標準添加回收、漂移檢查 | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB03_ash_sodium.ipynb) |
| W4 | NB04 滴定：KHP 標定、微分找當量點、Bland–Altman 方法比較 | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB04_titration.ipynb) |
| W5 | NB05 凱氏法：%N、換算係數、回收率、三聚氰胺 | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB05_kjeldahl_protein.ipynb) |
| W6 | NB06 脂肪：粗脂肪、濕基換算、Soxhlet 偏差、Pearson square | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB06_fat_soxhlet.ipynb) |
| W7 | NB07 糖：檢量線、殘差與缺適性、LOD／LOQ、Brix vs 總糖 | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB07_sugar_phenolsulfuric.ipynb) |
| W8 | NB08 能力試驗：Grubbs、ANOVA、z-score、管制圖、不確定度、放行判定 | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB08_proficiency_qc.ipynb) |
| W11 | NB09 光譜前處理與相似度：基線、SNV、微分、光譜庫比對、NNLS | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB09_preprocess_similarity.ipynb) |
| W12 | NB10 PCA：食用油分類、分數圖、loadings、離群值 | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB10_pca.ipynb) |
| W13 | NB11 PLS 醋酸定量：分組交叉驗證、RMSEP、RPD | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB11_pls_acetic.ipynb) |
| W14 | NB12 VIP、PLS-DA、T² 與 Q 離群值 | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB12_vip_plsda_outliers.ipynb) |
| W16 | NB13 代糖建模：PLS vs NNLS、VIP 對照特徵峰、適用範圍 | [Colab](https://colab.research.google.com/github/Tai-ShengYeh/food-analysis-lab/blob/main/notebooks/NB13_sweetener_model.ipynb) |

光譜筆記本（NB09–NB13）共用同一種 CSV 格式：一列一條光譜，前面是描述欄（sample_id、group、instrument、rep 與目標值），後面是以波長或拉曼位移為欄名的數值欄；也能讀 SpectraView 匯出的 rows 格式。

筆記本內建的是**模擬教學資料**，不是真實量測值。做作業時請依筆記本說明換成全班的實際數據。

各週筆記本共用同一種長格式資料欄位：`group, student, item, rep, value, unit, temp_C, note`。

## 相關教材

- [Nielsen 各章互動投影片](https://tai-shengyeh.github.io/food-analysis-decks/)
- [食品分析統計（FAS）](https://tai-shengyeh.github.io/food-analysis-statistics/)
- [化學計量學教學（chemometrics-teaching）](https://tai-shengyeh.github.io/chemometrics-teaching/)
- [SpectraView 光譜工具](https://github.com/Tai-ShengYeh/spectraview)
