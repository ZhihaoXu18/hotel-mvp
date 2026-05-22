import pandas as pd
import glob
import os

input_file = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_raw/retail/bike_sales_100k.csv"
output_path = "/Users/zhihaoxu/Desktop/Project:Code/hotel-mvp/data_raw/retail/bike_standardized.csv"

df = pd.read_csv(input_file, skiprows=1)

standard_df = pd.DataFrame()

standard_df["date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce");
standard_df["quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
standard_df["unit_price"] = pd.to_numeric(df["Price"], errors="coerce")
standard_df["revenue"] = standard_df["unit_price"] * standard_df["quantity"]
standard_df["category"] = df["Bike_Model"].astype(str).str.strip()

standard_df = standard_df.dropna(subset=["date", "revenue", "quantity", "category"])
standard_df = standard_df[standard_df["quantity"] > 0]
standard_df = standard_df[standard_df["revenue"] > 0]
standard_df = standard_df[standard_df["category"] != ""]

standard_df = standard_df[["date", "revenue", "quantity", "category"]]

standard_df.to_csv(output_path, index=False)

print("Saved to:")
print(output_path)

print("\nPreview:")
print(standard_df.head())

print("\nShape:")
print(standard_df.shape)