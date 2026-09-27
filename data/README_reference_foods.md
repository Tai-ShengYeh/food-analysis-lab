# reference_foods.json / reference_foods.csv

食物成分參考值，供 NB03（灰分與鈉）與 NB08（能力試驗）的「用資料庫檢查我的實驗數據合理嗎？」段落使用。
由教師端腳本 `colab_notebooks/build_reference_foods.py` 直接從官方檔案產生。**沒有任何數字是手打或教學假設值。**
重新產生的指令：`python build_reference_foods.py --spot-check`。

## 來源與授權

| 資料庫 | 版本 | 取得方式 | 授權 |
|---|---|---|---|
| USDA FoodData Central, SR Legacy | 2018-04（SR 最終版） | 官方 bulk CSV `FoodData_Central_sr_legacy_food_csv_2018-04.zip`（https://fdc.nal.usda.gov/download-datasets） | 公共領域 / CC0 1.0 |
| USDA FoodData Central, Foundation Foods | 2026-04-30 | 官方 bulk CSV `FoodData_Central_foundation_food_csv_2026-04-30.zip` | 公共領域 / CC0 1.0 |
| 衛生福利部食品藥物管理署 食品營養成分資料庫（TFND） | 以 data.gov.tw 詮釋資料的更新時間為準（每 3 個月更新，見 `meta.sources`） | 開放資料 CSV：https://data.fda.gov.tw/data/opendata/export/20/csv（= data.gov.tw 資料集 8543「食品營養成分資料集」，FDA InfoId 20） | 政府資料開放授權條款第1版，**使用時須註明出處** |

TFND 出處標示：資料來源為衛生福利部食品藥物管理署「食品營養成分資料庫」（政府資料開放平臺 data.gov.tw 資料集 8543），依政府資料開放授權條款第1版釋出。

## JSON 結構

```text
{
  "meta": {
    "built": "YYYY-MM-DD",
    "units": "per 100 g edible portion (sodium in mg, everything else in g)",
    "sources": [ {db, dataset, release, url, file, licence, [attribution]} , ... ],
    "nutrients": { "<key>": {"unit", "usda_nutrient_id": [...], "tfnd_item"} },
    "fields": {...}, "notes": [...]
  },
  "foods": [
    { "key": "whole_milk_powder", "name_zh": "全脂奶粉", "name_en": "...", "tags": [...],
      "variability_note": "品牌/配方差異提醒",
      "entries": [
        { "db": "USDA", "dataset": "SR Legacy" | "Foundation", "id": 170876, "name": "...",
          "match": "exact" | "closest", "match_note": "...", "n_factor": 6.38,
          "nutrients": { "water": {"value", "unit", "n", "min", "max", "median", "nutrient_id", "derivation"}, ... } },
        { "db": "TFND", "dataset": "食品營養成分資料集", "id": "L0200101", "name": "全脂奶粉",
          "name_en", "description", "category", "record_type", "match", "n_factor": null,
          "nutrients": { "water": {"value", "unit", "n", "sd", "tfnd_item"}, ... } }
      ] }
  ]
}
```

營養素鍵值：`water`、`protein`、`fat`、`ash`、`carbohydrate`（USDA 為差減法碳水化合物；TFND 為總碳水化合物）、`sugars_total`（USDA 用 nutrient 2000 或 Foundation 的 1063；TFND 為糖質總量）、`sodium`（mg）。

- `n`：USDA 為 data_points，TFND 為樣本數。n = 0 代表不是直接分析值，請看 `derivation`。
- `sd`：只有 TFND 提供。`min`/`max`/`median`：只有 USDA 部分品項提供。
- `n_factor`：USDA 的氮換算蛋白質係數。TFND 開放資料沒有提供，所以一律填 `null`，不推定為 6.25。

CSV 是同樣內容的扁平版，每一列是一個 食品 × 資料庫品項 × 營養素。

## 使用注意

- `match = closest` 代表只是最接近的品項，例如 USDA *Sugars, brown* 是美式紅糖，並不是台灣的黑糖。比較前請先讀 `match_note` 與 `variability_note`。
- 170876 的正式名稱是 *Milk, dry, whole, with added vitamin D*。*without added vitamin D* 的是 173454，兩者一般成分數值相同，所以兩筆都收錄。
- SR Legacy 全脂奶粉的 `sugars_total`（38.42）等於它的差減法碳水化合物（derivation NR），是推導值，不是實際分析的乳糖。
- 筆記本中的「合理範圍」另外加上教學預設容許差（見 `_dbcheck_common.py` 的 `DB_DEFAULT_TOL`）。這是教學假設，不屬於資料庫本身。
