import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import json

file_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_raw/retail/bike_standardized.csv"
df = pd.read_csv(file_path)

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["year"] = df["date"].dt.year
df = df[df["year"] == 2023].copy()

df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

df = df.dropna(subset=["date", "revenue", "quantity"])
df = df[df["quantity"] > 0]

df["month"] = df["date"].dt.to_period("M").astype(str)

monthly = df.groupby("month").agg(
    total_revenue=("revenue", "sum"),
    total_quantity=("quantity", "sum")
).sort_index()

monthly["price"] = monthly["total_revenue"] / monthly["total_quantity"]

monthly["revenue_change"] = monthly["total_revenue"].diff()

monthly["quantity_effect"] = (
    (monthly["total_quantity"] - monthly["total_quantity"].shift(1))
    * monthly["price"].shift(1)
)

monthly["price_effect"] = (
    (monthly["price"] - monthly["price"].shift(1))
    * monthly["total_quantity"]
)

def label_driver(row):
    if pd.isna(row["revenue_change"]):
        return ""
    if abs(row["quantity_effect"]) > abs(row["price_effect"]):
        return "Volume-driven"
    return "Price-driven"

monthly["main_driver"] = monthly.apply(label_driver, axis=1)

result = monthly[["revenue_change", "quantity_effect", "price_effect", "main_driver"]]
#print(result.round(2))

reg_df = df.copy()
reg_df = reg_df[(reg_df["revenue"] > 0) & (reg_df["quantity"] > 0)].copy()

reg_df["week"] = reg_df["date"].dt.to_period("W").astype(str)

# 先做单笔交易价格
reg_df["unit_price"] = reg_df["revenue"] / reg_df["quantity"]

reg_df["price_tier"] = reg_df.groupby("category")["unit_price"].transform(
    lambda x: pd.qcut(x, 3, labels=["Low", "Mid", "High"], duplicates="drop")
)


cat_week_df = reg_df.groupby(["week", "category", "price_tier"]).agg(
    total_revenue=("revenue", "sum"),
    total_quantity=("quantity", "sum"),
    transaction_count=("quantity", "size"),
    mean_unit_price=("unit_price", "mean"),
    median_price=("unit_price", "median"),
    price_std=("unit_price", "std"),
    min_price=("unit_price", "min"),
    max_price=("unit_price", "max"),
    p25_price=("unit_price", lambda x: x.quantile(0.25)),
    p75_price=("unit_price", lambda x: x.quantile(0.75))
).reset_index()

cat_week_df["avg_price"] = cat_week_df["total_revenue"] / cat_week_df["total_quantity"]

cat_week_df = cat_week_df[
    (cat_week_df["total_quantity"] > 0) &
    (cat_week_df["avg_price"] > 0)
].copy()

cat_week_df["price_std"] = cat_week_df["price_std"].fillna(0)

cat_week_df["month"] = pd.to_datetime(
    cat_week_df["week"].str[:10]
).dt.to_period("M").astype(str)

cat_week_df["log_total_quantity"] = np.log(cat_week_df["total_quantity"])
cat_week_df["log_avg_price"] = np.log(cat_week_df["avg_price"])

tier_summary = cat_week_df.groupby(["category", "price_tier"]).agg(
    n_weeks=("week", "count"),
    avg_price=("avg_price", "mean"),
    avg_quantity=("total_quantity", "mean"),
    avg_revenue=("total_revenue", "mean")
).reset_index()

print(tier_summary.round(2).to_string(index=False))


tier_count = cat_week_df.groupby(["category", "price_tier"]).agg(
    n_weeks=("week", "count")
).reset_index()

tier_model_summary = []

for (cat, tier) in cat_week_df[["category", "price_tier"]].drop_duplicates().values:
    sub = cat_week_df[
        (cat_week_df["category"] == cat) &
        (cat_week_df["price_tier"] == tier)
    ].copy()

    if len(sub) < 6:
        print(f"\n=== {cat} | {tier} ===")
        print("Not enough data points for regression.")
        continue

    model = smf.ols(
        formula="log_total_quantity ~ log_avg_price + C(month)",
        data=sub
    ).fit()

    print(f"\n=== {cat} | {tier} ===")
    print(model.summary())

    tier_model_summary.append({
        "category": cat,
        "price_tier": tier,
        "n_obs": len(sub),
        "price_coef": model.params.get("log_avg_price", np.nan),
        "price_pvalue": model.pvalues.get("log_avg_price", np.nan),
        "r_squared": model.rsquared,
        "adj_r_squared": model.rsquared_adj
    })

tier_model_summary_df = pd.DataFrame(tier_model_summary)

print("\n" + "="*80)
print("TIER-LEVEL MODEL SUMMARY")
print("="*80)
print(tier_model_summary_df.round(6).to_string(index=False))

optimizable_groups = tier_model_summary_df[
    (tier_model_summary_df["price_coef"] < 0) &
    (tier_model_summary_df["price_pvalue"] < 0.10)
].copy()

print("\n" + "=" * 80)
print("GROUPS ELIGIBLE FOR OPTIMIZATION")
print("=" * 80)
print(optimizable_groups.round(4).to_string(index=False))

optimization_results = []

for _, row in optimizable_groups.iterrows():
    cat = row["category"]
    tier = row["price_tier"]

    sub = cat_week_df[
        (cat_week_df["category"] == cat) &
        (cat_week_df["price_tier"] == tier)
    ].copy()

    if len(sub) < 10:
        continue

    model = smf.ols(
        formula="log_total_quantity ~ log_avg_price + C(month)",
        data=sub
    ).fit()

    # 历史合理价格范围：10% 到 90% 分位数
    price_min = sub["avg_price"].quantile(0.10)
    price_max = sub["avg_price"].quantile(0.90)

    if pd.isna(price_min) or pd.isna(price_max) or price_min >= price_max:
        continue

    candidate_prices = np.linspace(price_min, price_max, 50)

    # 先固定在该组最常见月份
    base_month = sub["month"].mode()[0]

    sim_rows = []

    for p in candidate_prices:
        temp = pd.DataFrame({
            "log_avg_price": [np.log(p)],
            "month": [base_month]
        })

        pred_log_q = model.predict(temp).iloc[0]
        pred_q = np.exp(pred_log_q)
        pred_rev = p * pred_q

        sim_rows.append({
            "candidate_price": p,
            "predicted_quantity": pred_q,
            "predicted_revenue": pred_rev
        })

    sim_df = pd.DataFrame(sim_rows)

    best_idx = sim_df["predicted_revenue"].idxmax()
    best_row = sim_df.loc[best_idx]

    baseline_price = sub["avg_price"].mean()
    baseline_quantity = sub["total_quantity"].mean()
    baseline_revenue = sub["total_revenue"].mean()

    uplift_abs = best_row["predicted_revenue"] - baseline_revenue
    uplift_pct = uplift_abs / baseline_revenue * 100 if baseline_revenue > 0 else np.nan

    optimization_results.append({
    "category": cat,
    "baseline_revenue": baseline_revenue,
    "optimal_price": best_row["candidate_price"],
    "optimal_revenue": best_row["predicted_revenue"],
    "uplift_pct": uplift_pct
})

optimization_results_df = pd.DataFrame(optimization_results)

print("\n" + "=" * 100)
print("OPTIMIZATION RESULTS - CASE 1")
print("=" * 100)
print(optimization_results_df.round(2).to_string(index=False))

optimization_json = optimization_results_df.round(2).to_dict(orient="records")

print("\nOptimization JSON preview:")
print(optimization_json)

optimization_json_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_out/optimization_results.json"

with open(optimization_json_path, "w", encoding="utf-8") as f:
    json.dump(optimization_json, f, indent=4, ensure_ascii=False)

print("\nOptimization JSON file saved:")
print(optimization_json_path)

scenario_groups = tier_model_summary_df[
    ~(
        (tier_model_summary_df["price_coef"] < 0) &
        (tier_model_summary_df["price_pvalue"] < 0.10)
    )
].copy()

scenario_results = []

for _, row in scenario_groups.iterrows():
    cat = row["category"]
    tier = row["price_tier"]

    sub = cat_week_df[
        (cat_week_df["category"] == cat) &
        (cat_week_df["price_tier"] == tier)
    ].copy()

    if len(sub) < 10:
        continue

    model = smf.ols(
        formula="log_total_quantity ~ log_avg_price + C(month)",
        data=sub
    ).fit()

    base_month = sub["month"].mode()[0]

    p25 = sub["avg_price"].quantile(0.25)
    p50 = sub["avg_price"].quantile(0.50)
    p75 = sub["avg_price"].quantile(0.75)

    price_points = {
        "Low": p25,
        "Mid": p50,
        "High": p75
    }

    scenario_row = {
        "category": cat,
        "price_tier": tier
    }

    revenue_list = []

    for label, p in price_points.items():
        temp = pd.DataFrame({
            "log_avg_price": [np.log(p)],
            "month": [base_month]
        })

        pred_log_q = model.predict(temp).iloc[0]
        pred_q = np.exp(pred_log_q)
        pred_rev = p * pred_q

        scenario_row[f"{label.lower()}_price"] = p
        scenario_row[f"{label.lower()}_revenue"] = pred_rev
        revenue_list.append(pred_rev)

    rev_range_pct = (
        (max(revenue_list) - min(revenue_list)) / np.mean(revenue_list) * 100
        if np.mean(revenue_list) > 0 else np.nan
    )

    if rev_range_pct < 3:
        decision = "Keep current pricing"
    elif scenario_row["high_revenue"] == max(revenue_list):
        decision = "Test slightly higher price"
    elif scenario_row["low_revenue"] == max(revenue_list):
        decision = "Test slightly lower price"
    else:
        decision = "Stay near mid-price"

    scenario_row["revenue_range_pct"] = rev_range_pct
    scenario_row["decision"] = decision

    scenario_results.append(scenario_row)

scenario_results_df = pd.DataFrame(scenario_results)

print("\n" + "=" * 100)
print("SCENARIO SIMULATION RESULTS - CASE 2")
print("=" * 100)

if not scenario_results_df.empty:
    print(scenario_results_df.round(2).to_string(index=False))
else:
    print("No scenario groups found.")

scenario_json = scenario_results_df.round(2).to_dict(orient="records")

print("\nScenario JSON preview:")
print(scenario_json)

scenario_json_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_out/scenario_results.json"

with open(scenario_json_path, "w", encoding="utf-8") as f:
    json.dump(scenario_json, f, indent=4, ensure_ascii=False)

print("\nScenario JSON file saved:")
print(scenario_json_path)


ab_test_input_df = optimization_results_df[
    ["category", "baseline_revenue", "optimal_price", "optimal_revenue", "uplift_pct"]
].copy()

output_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_out/ab_test_input.csv"
ab_test_input_df.to_csv(output_path, index=False)

print("\nA/B test input file saved:")
print(output_path)
print(ab_test_input_df.round(2).to_string(index=False))

scenario_ab_input_df = scenario_results_df.copy()

output_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_out/scenario_ab_input.csv"
scenario_ab_input_df.to_csv(output_path, index=False)

print("\nScenario A/B input file saved:")
print(output_path)
print(scenario_ab_input_df.round(2).to_string(index=False))

# print("\n" + "="*80)
# print("GENERAL FIXED-EFFECTS MODEL")
# print("="*80)

# # 先造一个组合组别变量
# cat_week_df["category_tier"] = (
#     cat_week_df["category"].astype(str) + "_" + cat_week_df["price_tier"].astype(str)
# )

# general_model = smf.ols(
#     formula="""
#     log_total_quantity ~ C(month) + C(category) + C(price_tier) + C(category):C(price_tier)
#     """,
#     data=cat_week_df
# ).fit()

# print(general_model.summary())

# print("\n" + "="*80)
# print("GENERAL MODEL KEY RESULTS")
# print("="*80)
# print(f"Price coefficient: {general_model.params.get('log_avg_price', np.nan):.6f}")
# print(f"Price p-value: {general_model.pvalues.get('log_avg_price', np.nan):.6f}")
# print(f"R-squared: {general_model.rsquared:.6f}")
# print(f"Adj R-squared: {general_model.rsquared_adj:.6f}")

# summary_list = []

# for cat in cat_week_df["category"].unique():
#     sub = cat_week_df[cat_week_df["category"] == cat].copy()

#     # 按价格分三段（低/中/高）
#     sub["price_band"] = pd.qcut(sub["avg_price"], q=3, labels=["Low", "Mid", "High"])

#     grouped = sub.groupby("price_band").agg(
#         avg_price=("avg_price", "mean"),
#         avg_quantity=("total_quantity", "mean"),
#         avg_revenue=("total_revenue", "mean"),
#         weeks=("week", "count")
#     ).reset_index()

#     grouped["category"] = cat
#     summary_list.append(grouped)

# price_band_summary = pd.concat(summary_list)
#print(price_band_summary.round(2).to_string(index=False))

# cat_week_df["price_band"] = (cat_week_df["avg_price"] // 100 * 100).astype(int)

# summary_list = []

# for cat in cat_week_df["category"].unique():
#     sub = cat_week_df[cat_week_df["category"] == cat].copy()

#     grouped = sub.groupby("price_band").agg(
#         avg_price=("avg_price", "mean"),
#         avg_quantity=("total_quantity", "mean"),
#         avg_revenue=("total_revenue", "mean"),
#         weeks=("week", "count")
#     ).reset_index()

#     grouped["category"] = cat
#     summary_list.append(grouped)

# price_band_summary = pd.concat(summary_list)

# print(price_band_summary.round(2).to_string(index=False))

# print("\n" + "="*80)
# print("ENHANCED DEMAND MODEL: control seasonality + product mix proxies")
# print("="*80)

# enhanced_summary_list = []

# for cat in cat_week_df["category"].unique():
#     sub = cat_week_df[cat_week_df["category"] == cat].copy()

#     if len(sub) < 6:
#         print(f"\n=== {cat} ===")
#         print("Not enough data points for regression.")
#         continue

#     model = smf.ols(
#         formula="""
#         log_total_quantity ~ log_avg_price + C(month) + price_std + p25_price + p75_price
#         """,
#         data=sub
#     ).fit()

#     print(f"\n=== {cat} ===")
#     print(model.summary())

#     enhanced_summary_list.append({
#         "category": cat,
#         "n_obs": len(sub),
#         "price_coef": model.params.get("log_avg_price", np.nan),
#         "price_pvalue": model.pvalues.get("log_avg_price", np.nan),
#         "r_squared": model.rsquared,
#         "adj_r_squared": model.rsquared_adj
#     })

# enhanced_summary_df = pd.DataFrame(enhanced_summary_list)

# print("\n" + "="*80)
# print("ENHANCED MODEL SUMMARY")
# print("="*80)
# print(enhanced_summary_df.round(6).to_string(index=False))