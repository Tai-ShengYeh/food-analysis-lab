# 方向確認

- 日期：2026-10-13
- 使用者原話：「也依照前面的模式制作教學動畫」——沿用 W1 的決定：手繪草圖風（同 W3）、MP4＋嵌入投影片、ElevenLabs 配音（IAN）、約 2 分鐘。
- 定案：sketch-board；hero element＝醋酸滴定曲線（跨兩幕一筆一筆長出來）與錐形瓶（透明→粉紅）
- 套用指令：`python ~/.claude/skills/code-animation-explainer/scripts/style_apply.py sketch-board --local-fonts --out style/`

## TREATMENT
結構：問題→嘗試→答案。兩杯 pH 相同的飲料 → pH 與可滴定酸度的差別 → 先標定 NaOH → 滴定曲線（緩衝區、半當量點、當量點、酚酞）→ 深色樣品改用電位滴定 → 算 % 酸 → 方法比較（r vs Bland–Altman）→ 片尾提問。
開場：兩個同樣 pH 3.5 的杯子（與 W1 開場不同）
招牌鏡頭：滴定曲線一筆畫到當量點時鏡頭跟著往上推；最後拉遠看全圖。
