# HK-Link Logistics Management System (LMS) — v4.0 Full-Stack Edition

## 快速啟動方式 (How to Run)

### Windows 使用者（一鍵啟動）
1. 解壓縮整個資料夾。
2. 確認電腦已安裝 Python（在終端機輸入 `python --version` 確認）。
3. 直接雙擊 **`start_windows.bat`**，系統會自動安裝 Flask、啟動伺服器並用瀏覽器開啟 `http://127.0.0.1:5000`！

### 手動啟動（Windows / Mac / Linux）
```bash
pip install -r requirements.txt
python app.py
```
打開瀏覽器前往：`http://127.0.0.1:5000`

---

## 測試登入帳號 (Demo Accounts)

| 角色 (Role) | 帳號 (Username) | 密碼 (Password) | 權限說明 |
|---|---|---|---|
| **Admin / Manager** | `admin` | `admin123` | 完整權限：KPI 儀表板、訂單 CRUD、派車、匯出 `.sqlite`、重設資料庫 |
| **Driver (Hui Ka Hing 許家興)** | `driver_hui` | `driver123` | 司機專屬權限：只看到指派給 `DRV-308 (TRK-NT-308)` 的包裹並更新狀態 |
| **Driver (Chan Tai Man 陳大文)** | `driver_chan` | `driver123` | 司機專屬權限：只看到 `DRV-101 (TRK-HK-101)` 的包裹 |
| **Customer Portal** | *(免登入 Public)* | *(無需密碼)* | 直接查詢包裹進度（例如 `LMS-2026-004`）與測試無效單號 `LMS-9999-404` |
