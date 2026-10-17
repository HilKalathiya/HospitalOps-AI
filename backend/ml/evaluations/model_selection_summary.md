# HospitalOps AI — Forecasting Benchmark & Model Selection Report

> **Generated at:** 2026-10-17 13:04:11 UTC  
> **Report ID:** `10682c5c-d231-4dc3-ab36-7a961ff2da43`  
> **Total Runs Evaluated:** 118  

## 1. Selected Winner Summary

All models were evaluated using chronological walk-forward splits. **Selection was performed strictly on validation MAE (tie-breaker: validation RMSE).** Held-out test split metrics are reported for transparent, unbiased generalization verification.

| Dataset | Target | Horizon | Winner Model | Winner Config | Val MAE | Test MAE | Test RMSE | Test sMAPE | Test MAPE |
|:---|:---|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|
| HERO_DMC | `daily_admissions` | **1d** | **ARIMA** | `sarima_1_0_0_7` | 2.32 | 3.57 | 4.06 | 13.53% | 13.19% |
| HERO_DMC | `daily_admissions` | **7d** | **ARIMA** | `arima_1_1_1` | 2.73 | 5.62 | 6.48 | 23.99% | 27.24% |
| HERO_DMC | `daily_admissions` | **14d** | **BASELINE** | `moving_average_w28` | 5.42 | 6.08 | 7.61 | 24.17% | 29.80% |
| HERO_DMC | `daily_admissions` | **30d** | **ARIMA** | `arima_1_1_1` | 5.06 | 5.25 | 6.85 | 22.28% | 29.80% |
| NHSN_HRD | `icu_beds_occupied` | **1w** | **BASELINE** | `naive` | 1944.50 | 5053.00 | 6909.52 | 2.39% | 2.38% |
| NHSN_HRD | `icu_beds_occupied` | **2w** | **BASELINE** | `moving_average_w4` | 2678.10 | 3635.68 | 4324.78 | 1.71% | 1.72% |
| NHSN_HRD | `icu_beds_occupied` | **4w** | **BASELINE** | `moving_average_w4` | 1574.25 | 3174.43 | 3795.19 | 1.50% | 1.49% |

---

## 2. Detailed Leaderboard per Horizon

### HERO_DMC — daily_admissions (Horizon: 1d)

| Rank | Status | Model Type | Configuration | Val MAE | Val RMSE | Test MAE | Test RMSE | Test sMAPE | Test MAPE |
|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | ✅ SUCCESS | arima | `sarima_1_0_0_7` | 2.32 | 3.28 | 3.57 | 4.06 | 13.53% | 13.19% |
| 2 | ✅ SUCCESS | baseline | `naive` | 3.15 | 3.59 | 3.18 | 3.50 | 6.73% | 6.59% |
| 3 | ✅ SUCCESS | arima | `arima_1_1_1` | 5.30 | 6.44 | 6.27 | 7.15 | 25.01% | 26.22% |
| 4 | ✅ SUCCESS | baseline | `moving_average_w7` | 5.30 | 6.44 | 6.22 | 7.69 | 24.74% | 30.32% |
| 5 | ✅ SUCCESS | baseline | `moving_average_w28` | 5.32 | 6.54 | 5.89 | 7.43 | 23.50% | 29.01% |
| 6 | ✅ SUCCESS | baseline | `moving_average_w14` | 5.39 | 6.54 | 5.86 | 7.55 | 23.36% | 29.05% |
| 7 | ✅ SUCCESS | baseline | `seasonal_naive_p7` | 6.21 | 7.60 | 6.72 | 8.65 | 26.88% | 31.40% |
| 8 | ✅ SUCCESS | arima | `arima_1_0_0` | 6.33 | 8.75 | 10.59 | 11.47 | 42.93% | 42.17% |
| - | ❌ FAILED | prophet | `prophet_default` | - | - | - | - | - | - |
| - | ❌ FAILED | prophet | `prophet_weekly_only` | - | - | - | - | - | - |
| - | ⚠️ MISSING | lstm | `lstm_h32_l2_e15` | - | - | - | - | - | - |

### HERO_DMC — daily_admissions (Horizon: 7d)

| Rank | Status | Model Type | Configuration | Val MAE | Val RMSE | Test MAE | Test RMSE | Test sMAPE | Test MAPE |
|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | ✅ SUCCESS | arima | `arima_1_1_1` | 2.73 | 3.59 | 5.62 | 6.48 | 23.99% | 27.24% |
| 2 | ✅ SUCCESS | baseline | `moving_average_w28` | 5.38 | 6.59 | 6.01 | 7.49 | 23.90% | 29.36% |
| 3 | ✅ SUCCESS | baseline | `moving_average_w7` | 5.63 | 6.83 | 6.06 | 7.79 | 24.11% | 29.82% |
| 4 | ✅ SUCCESS | baseline | `moving_average_w14` | 5.68 | 6.92 | 5.88 | 7.59 | 23.46% | 28.96% |
| 5 | ✅ SUCCESS | baseline | `naive` | 6.16 | 7.59 | 6.78 | 8.69 | 27.14% | 31.70% |
| 6 | ✅ SUCCESS | arima | `arima_1_0_0` | 6.26 | 7.76 | 7.12 | 8.71 | 33.75% | 28.82% |
| 7 | ✅ SUCCESS | arima | `sarima_1_0_0_7` | 6.71 | 6.96 | 6.46 | 8.29 | 27.41% | 26.42% |
| 8 | ✅ SUCCESS | baseline | `seasonal_naive_p7` | 7.59 | 9.29 | 8.00 | 10.28 | 31.53% | 36.77% |
| - | ❌ FAILED | prophet | `prophet_weekly_only` | - | - | - | - | - | - |
| - | ❌ FAILED | prophet | `prophet_default` | - | - | - | - | - | - |
| - | ⚠️ MISSING | lstm | `lstm_h32_l2_e15` | - | - | - | - | - | - |

### HERO_DMC — daily_admissions (Horizon: 14d)

| Rank | Status | Model Type | Configuration | Val MAE | Val RMSE | Test MAE | Test RMSE | Test sMAPE | Test MAPE |
|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | ✅ SUCCESS | baseline | `moving_average_w28` | 5.42 | 6.70 | 6.08 | 7.61 | 24.17% | 29.80% |
| 2 | ✅ SUCCESS | arima | `arima_1_1_1` | 5.51 | 6.82 | 4.40 | 5.35 | 18.76% | 21.54% |
| 3 | ✅ SUCCESS | baseline | `moving_average_w14` | 5.70 | 7.07 | 6.13 | 7.62 | 24.44% | 29.74% |
| 4 | ✅ SUCCESS | baseline | `moving_average_w7` | 6.04 | 7.44 | 6.12 | 7.86 | 24.37% | 29.70% |
| 5 | ✅ SUCCESS | baseline | `naive` | 7.12 | 8.75 | 6.95 | 9.02 | 27.60% | 31.76% |
| 6 | ✅ SUCCESS | baseline | `seasonal_naive_p7` | 8.32 | 9.93 | 7.61 | 9.51 | 30.09% | 34.52% |
| 7 | ✅ SUCCESS | arima | `sarima_1_0_0_7` | 10.60 | 11.56 | 5.90 | 6.98 | 26.66% | 24.71% |
| 8 | ✅ SUCCESS | arima | `arima_1_0_0` | 12.89 | 14.66 | 8.46 | 9.88 | 43.10% | 34.68% |
| - | ❌ FAILED | prophet | `prophet_weekly_only` | - | - | - | - | - | - |
| - | ❌ FAILED | prophet | `prophet_default` | - | - | - | - | - | - |
| - | ⚠️ MISSING | lstm | `lstm_h32_l2_e15` | - | - | - | - | - | - |

### HERO_DMC — daily_admissions (Horizon: 30d)

| Rank | Status | Model Type | Configuration | Val MAE | Val RMSE | Test MAE | Test RMSE | Test sMAPE | Test MAPE |
|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | ✅ SUCCESS | arima | `arima_1_1_1` | 5.06 | 6.21 | 5.25 | 6.85 | 22.28% | 29.80% |
| 2 | ✅ SUCCESS | baseline | `moving_average_w14` | 5.62 | 6.85 | 6.35 | 8.06 | 25.10% | 31.15% |
| 3 | ✅ SUCCESS | baseline | `moving_average_w7` | 5.64 | 6.89 | 6.54 | 8.15 | 25.81% | 31.51% |
| 4 | ✅ SUCCESS | baseline | `moving_average_w28` | 5.68 | 6.96 | 6.31 | 7.90 | 25.01% | 30.67% |
| 5 | ✅ SUCCESS | baseline | `seasonal_naive_p7` | 7.55 | 8.98 | 8.86 | 10.54 | 35.55% | 40.98% |
| 6 | ✅ SUCCESS | baseline | `naive` | 7.72 | 9.52 | 8.46 | 10.41 | 32.99% | 37.12% |
| 7 | ✅ SUCCESS | arima | `sarima_1_0_0_7` | 10.10 | 11.30 | 9.34 | 10.90 | 43.31% | 38.00% |
| 8 | ✅ SUCCESS | arima | `arima_1_0_0` | 14.87 | 16.36 | 16.15 | 18.45 | 93.17% | 60.28% |
| - | ❌ FAILED | prophet | `prophet_default` | - | - | - | - | - | - |
| - | ❌ FAILED | prophet | `prophet_weekly_only` | - | - | - | - | - | - |
| - | ⚠️ MISSING | lstm | `lstm_h32_l2_e15` | - | - | - | - | - | - |

### NHSN_HRD — icu_beds_occupied (Horizon: 1w)

| Rank | Status | Model Type | Configuration | Val MAE | Val RMSE | Test MAE | Test RMSE | Test sMAPE | Test MAPE |
|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | ✅ SUCCESS | baseline | `naive` | 1944.50 | 2657.90 | 5053.00 | 6909.52 | 2.39% | 2.38% |
| 2 | ✅ SUCCESS | baseline | `moving_average_w12` | 3055.67 | 3894.73 | 3737.00 | 4366.55 | 1.76% | 1.77% |
| 3 | ✅ SUCCESS | baseline | `moving_average_w4` | 3073.88 | 3294.70 | 3637.00 | 4720.30 | 1.71% | 1.73% |
| 4 | ✅ SUCCESS | arima | `arima_1_0_0` | 3358.32 | 3731.03 | 7583.72 | 9336.16 | 3.59% | 3.57% |
| 5 | ✅ SUCCESS | arima | `arima_1_1_1` | 3459.69 | 3472.04 | 5731.56 | 6838.60 | 2.70% | 2.72% |
| 6 | ✅ SUCCESS | baseline | `seasonal_naive_p52` | 3747.00 | 4817.62 | 4306.00 | 4520.49 | 2.03% | 2.02% |
| - | ❌ FAILED | prophet | `prophet_yearly_only` | - | - | - | - | - | - |
| - | ⚠️ MISSING | lstm | `lstm_h32_l2_e15` | - | - | - | - | - | - |

### NHSN_HRD — icu_beds_occupied (Horizon: 2w)

| Rank | Status | Model Type | Configuration | Val MAE | Val RMSE | Test MAE | Test RMSE | Test sMAPE | Test MAPE |
|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | ✅ SUCCESS | baseline | `moving_average_w4` | 2678.10 | 3053.36 | 3635.68 | 4324.78 | 1.71% | 1.72% |
| 2 | ✅ SUCCESS | baseline | `seasonal_naive_p52` | 3200.40 | 4545.41 | 4374.00 | 5223.76 | 2.07% | 2.05% |
| 3 | ✅ SUCCESS | arima | `arima_1_1_1` | 3348.22 | 3532.18 | 4192.63 | 5492.85 | 1.98% | 2.01% |
| 4 | ✅ SUCCESS | baseline | `moving_average_w12` | 3640.45 | 4891.26 | 3606.29 | 4042.30 | 1.70% | 1.70% |
| 5 | ✅ SUCCESS | baseline | `naive` | 3832.20 | 4063.13 | 4557.86 | 5802.00 | 2.15% | 2.16% |
| 6 | ✅ SUCCESS | arima | `arima_1_0_0` | 4061.90 | 4358.56 | 3756.49 | 5733.56 | 1.78% | 1.81% |
| - | ❌ FAILED | prophet | `prophet_yearly_only` | - | - | - | - | - | - |
| - | ⚠️ MISSING | lstm | `lstm_h32_l2_e15` | - | - | - | - | - | - |

### NHSN_HRD — icu_beds_occupied (Horizon: 4w)

| Rank | Status | Model Type | Configuration | Val MAE | Val RMSE | Test MAE | Test RMSE | Test sMAPE | Test MAPE |
|:---:|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | ✅ SUCCESS | baseline | `moving_average_w4` | 1574.25 | 2173.04 | 3174.43 | 3795.19 | 1.50% | 1.49% |
| 2 | ✅ SUCCESS | arima | `arima_1_1_1` | 2269.51 | 2874.60 | 3657.99 | 4852.15 | 1.73% | 1.74% |
| 3 | ✅ SUCCESS | arima | `arima_1_0_0` | 2948.41 | 3350.44 | 3264.85 | 5156.00 | 1.54% | 1.57% |
| 4 | ✅ SUCCESS | baseline | `naive` | 4135.20 | 5184.25 | 3522.86 | 4668.28 | 1.67% | 1.67% |
| 5 | ✅ SUCCESS | baseline | `seasonal_naive_p52` | 4263.00 | 4639.69 | 5115.00 | 6076.64 | 2.41% | 2.40% |
| 6 | ✅ SUCCESS | baseline | `moving_average_w12` | 5272.80 | 6517.56 | 3198.68 | 3834.80 | 1.51% | 1.51% |
| - | ❌ FAILED | prophet | `prophet_yearly_only` | - | - | - | - | - | - |
| - | ⚠️ MISSING | lstm | `lstm_h32_l2_e15` | - | - | - | - | - | - |
