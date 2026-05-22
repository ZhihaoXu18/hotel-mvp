import pandas as pd
import json

file_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_raw/retail/bike_standardized.csv"

df = pd.read_csv(file_path)

results = {}


df["date"] = pd.to_datetime(df["date"], errors="coerce")

df["year"] = df["date"].dt.year
df = df[df["year"] == 2023].copy()

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["unit_price"] = df["revenue"] / df["quantity"]
df["month"] = df["date"].dt.to_period("M").astype(str)

print("Columns:")
print(df.columns.tolist())

print("\nShape:")
print(df.shape)

print("\n=== 1. SCALE ===")
print("Total revenue:", round(df["revenue"].sum(), 2))
print("Total quantity:", round(df["quantity"].sum(), 2))
print("Number of transactions:", len(df))
print("Average booking value:", round(df["revenue"].mean(), 2))
print("Average unit price:", round(df["unit_price"].mean(), 2))
print("Number of categories:", df["category"].nunique())

results["scale"] = {
    "total_revenue": round(df["revenue"].sum(), 2),
    "total_quantity": round(df["quantity"].sum(), 2),
    "number_of_transactions": int(len(df)),
    "average_booking_value": round(df["revenue"].mean(), 2),
    "average_unit_price": round(df["unit_price"].mean(), 2),
    "number_of_categories": int(df["category"].nunique())
}

print("\n=== 2. REVENUE QUALITY ===")
print("Mean revenue:", round(df["revenue"].mean(), 2))
print("Median revenue:", round(df["revenue"].median(), 2))
print("Mean unit price:", round(df["unit_price"].mean(), 2))
print("Median unit price:", round(df["unit_price"].median(), 2))

revenue_cv = df["revenue"].std() / df["revenue"].mean()
unit_price_cv = df["unit_price"].std() / df["unit_price"].mean()

print("Revenue coefficient of variation:", round(revenue_cv, 4))
print("Unit price coefficient of variation:", round(unit_price_cv, 4))

monthly_summary = df.groupby("month").agg(
    total_revenue=("revenue", "sum"),
    total_quantity=("quantity", "sum")
).sort_index()

monthly_summary["avg_unit_price"] = (
    monthly_summary["total_revenue"] / monthly_summary["total_quantity"]
)

monthly_summary["revenue_mom_growth"] = monthly_summary["total_revenue"].pct_change()
monthly_summary["quantity_mom_growth"] = monthly_summary["total_quantity"].pct_change()
monthly_summary["unit_price_mom_growth"] = monthly_summary["avg_unit_price"].pct_change()

results["revenue_quality"] = {
    "mean_revenue": round(df["revenue"].mean(), 2),
    "median_revenue": round(df["revenue"].median(), 2),
    "mean_unit_price": round(df["unit_price"].mean(), 2),
    "median_unit_price": round(df["unit_price"].median(), 2),
    "revenue_cv": round(revenue_cv, 4),
    "unit_price_cv": round(unit_price_cv, 4)
}

print("\n=== 3. VOLUME-PRICE STRUCTURE ===")
print(monthly_summary)

results["volume_price_structure"] = monthly_summary.round(4).reset_index().to_dict(orient="records")

print("\n=== 4. MOMENTUM AND SEASONALITY ===")

strongest_month = monthly_summary["total_revenue"].idxmax()
weakest_month = monthly_summary["total_revenue"].idxmin()
highest_volume_month = monthly_summary["total_quantity"].idxmax()
highest_price_month = monthly_summary["avg_unit_price"].idxmax()

print("Strongest month by revenue:", strongest_month)
print("Weakest month by revenue:", weakest_month)
print("Highest volume month:", highest_volume_month)
print("Highest price month:", highest_price_month)

unit_price_std = df["unit_price"].std()
p10 = df["unit_price"].quantile(0.10)
p90 = df["unit_price"].quantile(0.90)

low_price_share = (df["unit_price"] <= p10).mean()
high_price_share = (df["unit_price"] >= p90).mean()

results["momentum_and_seasonality"] = {
    "strongest_month_by_revenue": strongest_month,
    "weakest_month_by_revenue": weakest_month,
    "highest_volume_month": highest_volume_month,
    "highest_price_month": highest_price_month
}


print("\n=== 5. PRICE TIER COMPARISON ===")

low_cutoff = df["unit_price"].quantile(0.20)
high_cutoff = df["unit_price"].quantile(0.80)

low_price_df = df[df["unit_price"] <= low_cutoff]
high_price_df = df[df["unit_price"] >= high_cutoff]

print("Low-price transactions avg unit price:", round(low_price_df["unit_price"].mean(), 2))
print("Low-price transactions avg quantity:", round(low_price_df["quantity"].mean(), 2))
print("Low-price transactions avg revenue:", round(low_price_df["revenue"].mean(), 2))
print("Low-price transactions count:", len(low_price_df))

print("High-price transactions avg unit price:", round(high_price_df["unit_price"].mean(), 2))
print("High-price transactions avg quantity:", round(high_price_df["quantity"].mean(), 2))
print("High-price transactions avg revenue:", round(high_price_df["revenue"].mean(), 2))
print("High-price transactions count:", len(high_price_df))

results["price_tier_comparison"] = {
    "low_price_transactions": {
        "avg_unit_price": round(low_price_df["unit_price"].mean(), 2),
        "avg_quantity": round(low_price_df["quantity"].mean(), 2),
        "avg_revenue": round(low_price_df["revenue"].mean(), 2),
        "count": int(len(low_price_df))
    },
    "high_price_transactions": {
        "avg_unit_price": round(high_price_df["unit_price"].mean(), 2),
        "avg_quantity": round(high_price_df["quantity"].mean(), 2),
        "avg_revenue": round(high_price_df["revenue"].mean(), 2),
        "count": int(len(high_price_df))
    }
}

print("\n=== 6. CATEGORY DEPENDENCE ===")

category_summary = df.groupby("category")[["revenue", "quantity"]].sum().sort_values("revenue", ascending=False)

top_category = category_summary.index[0]
top_revenue_share = category_summary.iloc[0]["revenue"] / df["revenue"].sum()
top_quantity_share = category_summary.iloc[0]["quantity"] / df["quantity"].sum()

top3_revenue_share = category_summary.head(3)["revenue"].sum() / df["revenue"].sum()

print("Top 3 categories revenue share:", f"{top3_revenue_share:.1%}")

print("Top category by revenue:", top_category)
print("Top category revenue share:", f"{top_revenue_share:.3%}")
print("Top category quantity share:", f"{top_quantity_share:.3%}")

results["category_dependence"] = {
    "top_3_categories_revenue_share": round(top3_revenue_share, 4),
    "top_category_by_revenue": top_category,
    "top_category_revenue_share": round(top_revenue_share, 4),
    "top_category_quantity_share": round(top_quantity_share, 4)
}

json_output_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_out/business_summary.json"

with open(json_output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False, default=str)
    
print("\nBusiness summary JSON file saved:")
print(json_output_path)