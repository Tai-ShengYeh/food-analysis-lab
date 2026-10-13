# w02_noodle_msi.csv

麵條在 28 °C 乾燥過程中的 8 個取樣點（脫濕軌跡），供 W2 延伸活動
[`labs/w02_moisture/isotherm.html`](../labs/w02_moisture/isotherm.html)、NB02 第 7 節與 EX02 工作表「8_吸濕曲線」使用。**真實量測數據。**

| 欄位 | 說明 |
|---|---|
| `time` | 取樣時間（`final` 為乾燥終點） |
| `aw` | 水活性 |
| `oven_wb` / `oven_db` | 105 °C 烘箱法水分：濕基 %／乾基 g 水 / g 乾物 |
| `fd660_wb` / `fd660_db` | FD-660 紅外線水分計：濕基 %／乾基 g/g |

乾基 = 濕基 % ÷ (100 − 濕基 %)。

使用限制：a<sub>w</sub> 只涵蓋 0.558–0.867，沒有 BET 適用範圍（a<sub>w</sub> 0.05–0.45）的點；
GAB 擬合得到 X<sub>m</sub> ≈ 0.057 g/g，但 C 不可估計，X<sub>m</sub> 屬外插。
活動中的低 a<sub>w</sub> 補點是模擬值，不在這個檔案裡。
