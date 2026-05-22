import pandas as pd
import numpy as np
import statsmodels.formula.api as smf


file_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_raw/hotel_standardized_2025.csv"
df = pd.read_csv(file_path)

df["date"] = pd.to_datetime(df["date"], errors="coerce")
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

reg_df["price_per_unit"] = reg_df["revenue"] / reg_df["quantity"]
reg_df = reg_df[reg_df["price_per_unit"] > 0].copy()

reg_df["log_revenue"] = np.log(reg_df["revenue"])
reg_df["log_price_per_unit"] = np.log(reg_df["price_per_unit"])

price_model = smf.ols(
    formula="log_price_per_unit ~ C(quantity) + C(month)",
    data=reg_df
).fit()

#print("\nPRICE EFFICIENCY MODEL")
#print(price_model.summary())

df["week"] = df["date"].dt.to_period("W").astype(str)
df["booking_price_per_night"] = df["revenue"] / df["quantity"]

df["price_band"] = df.groupby("week")["booking_price_per_night"].transform(
    lambda x: pd.qcut(x, q=3, labels=["Low", "Medium", "High"], duplicates="drop")
)

weekly_band_summary = df.groupby(["week", "price_band"], observed=False).agg(
    booking_count=("quantity", "size"),
    total_quantity=("quantity", "sum"),
    avg_quantity=("quantity", "mean"),
    avg_price=("booking_price_per_night", "mean"),
    total_revenue=("revenue", "sum")
).reset_index()

#print("\nSAME-WEEK PRICE BAND ANALYSIS")
#print(weekly_band_summary.head(10).round(2).to_string(index=False))

band_df = weekly_band_summary.copy()

band_df = band_df[
    (band_df["total_quantity"] > 0) &
    (band_df["avg_price"] > 0)
].copy()

band_df["log_total_quantity"] = np.log(band_df["total_quantity"])
band_df["log_avg_price"] = np.log(band_df["avg_price"])

band_model = smf.ols(
    formula="log_total_quantity ~ log_avg_price + C(week)",
    data=band_df
).fit()

# print(band_model.summary())

band_df = weekly_band_summary.copy()
band_df = band_df[
    (band_df["booking_count"] > 0) &
    (band_df["avg_price"] > 0)
].copy()

band_df["log_booking_count"] = np.log(band_df["booking_count"])
band_df["log_avg_price"] = np.log(band_df["avg_price"])

band_model_booking = smf.ols(
    formula="log_booking_count ~ log_avg_price + C(week)",
    data=band_df
).fit()

# print(band_model_booking.summary())

band_df["log_avg_quantity"] = np.log(band_df["avg_quantity"])

stay_model = smf.ols(
    formula="log_avg_quantity ~ log_avg_price + C(week)",
    data=band_df
).fit()

# print(stay_model.summary())

def predict_revenue(price, week_value):
    new_df = pd.DataFrame({
        "log_avg_price": [np.log(price)],
        "week": [week_value]
    })

    log_booking_pred = band_model_booking.predict(new_df).iloc[0]
    log_quantity_pred = stay_model.predict(new_df).iloc[0]

    booking_pred = np.exp(log_booking_pred)
    quantity_pred = np.exp(log_quantity_pred)

    revenue_pred = price * booking_pred * quantity_pred
    return revenue_pred

weekly_price_range = df.groupby("week")["booking_price_per_night"].quantile([0.1, 0.9]).unstack()
weekly_price_range.columns = ["p10", "p90"]
weekly_price_range = weekly_price_range.reset_index()

results = []

for _, row in weekly_price_range.iterrows():
    w = row["week"]
    low = row["p10"]
    high = row["p90"]  # ceiling
    
    n_grid = 20
    candidate_prices = np.linspace(low, high, n_grid)

    week_results = []
    for p in candidate_prices:
        rev = predict_revenue(p, w)
        week_results.append({"price": p, "revenue": rev})

    week_df = pd.DataFrame(week_results)
    week_df_sorted = week_df.sort_values("revenue", ascending=False).reset_index(drop=True)
     
    best = week_df_sorted.iloc[0]
    second = week_df_sorted.iloc[1]
    third = week_df_sorted.iloc[2]

    baseline_price = df.loc[df["week"] == w, "booking_price_per_night"].mean()
    baseline_revenue = predict_revenue(baseline_price, w)

    uplift_abs = third["revenue"] - baseline_revenue
    uplift_pct = uplift_abs / baseline_revenue * 100 if baseline_revenue != 0 else np.nan


    results.append({
        "week": w,
        "baseline_price": baseline_price,
        "baseline_revenue": baseline_revenue,
        "recommended_price": third["price"],   # 稳妥
        "uplift_abs": uplift_abs,
        "uplift_pct": uplift_pct,
        "max_price": best["price"],            # 极限
    })

weekly_recommendation = pd.DataFrame(results)

print("\n===== Weekly Recommendation with Uplift =====")
print(weekly_recommendation.round(2).to_string(index=False))
