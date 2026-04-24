"""
Online Retail & Hospitality Analytics Pipeline.
Runs on UCI Online Retail dataset (if present) or synthetic fallback.
Generates: revenue trends, RFM segmentation, country breakdown, product performance,
           hotel cancellation prediction results.
"""

from __future__ import annotations

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from collections import Counter

os.makedirs("outputs", exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})

# ---- Synthetic data -----------------------------------------------------
def _generate_retail_data(n: int = 8000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    countries = ["United Kingdom", "Germany", "France", "Netherlands",
                 "Spain", "Belgium", "Sweden", "Australia"]
    weights = [0.50, 0.12, 0.10, 0.08, 0.06, 0.05, 0.05, 0.04]
    products = [
        ("POST", "Postage"), ("85123A", "White Hanging Heart Light"),
        ("22423", "Regency Cakestand"), ("85099B", "Jumbo Bag Red Retrospot"),
        ("47566", "Party Bunting"), ("84879", "Assorted Colour Bird Ornament"),
        ("22720", "Set of 3 Cake Tins"), ("20725", "Lunch Bag Red Retrospot"),
        ("22728", "Alarm Clock Bakelike Green"), ("85116", "Black Candelabra T-Light Holder"),
    ]
    dates = pd.date_range("2010-12-01", "2011-12-09", freq="D")
    cust_ids = rng.integers(12000, 18500, n)
    invoice_dates = rng.choice(dates, n)
    prod_idx = rng.integers(0, len(products), n)
    qty = rng.integers(1, 50, n)
    price = rng.uniform(0.5, 25.0, n).round(2)
    country_idx = rng.choice(len(countries), n, p=weights)
    return pd.DataFrame({
        "InvoiceNo": [f"5{rng.integers(10000,99999):05d}" for _ in range(n)],
        "StockCode": [products[i][0] for i in prod_idx],
        "Description": [products[i][1] for i in prod_idx],
        "Quantity": qty,
        "InvoiceDate": invoice_dates,
        "UnitPrice": price,
        "CustomerID": cust_ids,
        "Country": [countries[i] for i in country_idx],
    })


def load_retail() -> pd.DataFrame:
    for fname in ("OnlineRetail.xlsx", "online_retail.xlsx", "data/OnlineRetail.xlsx"):
        if os.path.exists(fname):
            df = pd.read_excel(fname)
            print(f"[DATA]  Loaded {len(df):,} rows from {fname}")
            return df
    print("[DATA]  Dataset not found — using synthetic data (8,000 rows)")
    return _generate_retail_data()


df = load_retail()
df.dropna(subset=["CustomerID"], inplace=True)
df = df[df["Quantity"] > 0]
df = df[df["UnitPrice"] > 0]
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
df["Revenue"] = df["Quantity"] * df["UnitPrice"]
df["YearMonth"] = df["InvoiceDate"].dt.to_period("M")

print(f"[DATA]  {len(df):,} clean rows | {df['CustomerID'].nunique():,} customers | "
      f"{df['Country'].nunique()} countries")

# ---- Chart 1: Monthly Revenue Trend ------------------------------------
monthly = df.groupby("YearMonth")["Revenue"].sum().reset_index()
monthly["YearMonth_dt"] = monthly["YearMonth"].dt.to_timestamp()
monthly["MoM_pct"] = monthly["Revenue"].pct_change() * 100

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
fig.suptitle("Monthly Revenue Trend", fontsize=14, fontweight="bold")

ax1.fill_between(monthly["YearMonth_dt"], monthly["Revenue"] / 1000,
                 alpha=0.3, color="#3498db")
ax1.plot(monthly["YearMonth_dt"], monthly["Revenue"] / 1000,
         color="#2980b9", linewidth=2, marker="o", markersize=5)
ax1.set_ylabel("Revenue (£k)")
ax1.set_title("Total Monthly Revenue", fontsize=11)

colors = ["#e74c3c" if v < 0 else "#2ecc71" for v in monthly["MoM_pct"].fillna(0)]
ax2.bar(monthly["YearMonth_dt"], monthly["MoM_pct"].fillna(0),
        color=colors, edgecolor="white", width=20)
ax2.axhline(0, color="gray", linewidth=0.8)
ax2.set_ylabel("MoM Change (%)")
ax2.set_title("Month-over-Month Growth", fontsize=11)
plt.xticks(rotation=30)
plt.tight_layout()
plt.savefig("outputs/01_monthly_revenue.png", dpi=150, bbox_inches="tight")
plt.close()
print("[PLOT]  outputs/01_monthly_revenue.png")

# ---- Chart 2: RFM Segmentation -----------------------------------------
snapshot_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)
rfm = df.groupby("CustomerID").agg(
    Recency=("InvoiceDate", lambda x: (snapshot_date - x.max()).days),
    Frequency=("InvoiceNo", "nunique"),
    Monetary=("Revenue", "sum"),
).reset_index()

rfm["R_score"] = pd.qcut(rfm["Recency"], 4, labels=[4, 3, 2, 1]).astype(int)
rfm["F_score"] = pd.qcut(rfm["Frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
rfm["M_score"] = pd.qcut(rfm["Monetary"], 4, labels=[1, 2, 3, 4]).astype(int)
rfm["RFM_Score"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]

def segment(score: int) -> str:
    if score >= 11:
        return "Champions"
    elif score >= 8:
        return "Loyal Customers"
    elif score >= 6:
        return "Potential Loyalists"
    elif score >= 4:
        return "At Risk"
    return "Lost"

rfm["Segment"] = rfm["RFM_Score"].apply(segment)
seg_counts = rfm["Segment"].value_counts()
seg_revenue = rfm.groupby("Segment")["Monetary"].sum()

fig, axes = plt.subplots(1, 3, figsize=(16, 6))
fig.suptitle("RFM Customer Segmentation", fontsize=14, fontweight="bold")

colors_seg = {"Champions": "#2ecc71", "Loyal Customers": "#3498db",
              "Potential Loyalists": "#9b59b6", "At Risk": "#f39c12", "Lost": "#e74c3c"}

# Pie: segment counts
seg_counts.plot(kind="pie", ax=axes[0], colors=[colors_seg[s] for s in seg_counts.index],
                autopct="%1.1f%%", startangle=90, wedgeprops={"edgecolor": "white"})
axes[0].set_ylabel("")
axes[0].set_title("Customer Distribution", fontsize=11, fontweight="bold")

# Bar: segment revenue
rev_sorted = seg_revenue.sort_values(ascending=True)
bars = axes[1].barh(rev_sorted.index, rev_sorted.values / 1000,
                    color=[colors_seg[s] for s in rev_sorted.index], edgecolor="white")
axes[1].set_xlabel("Revenue (£k)")
axes[1].set_title("Revenue by Segment", fontsize=11, fontweight="bold")
for bar, val in zip(bars, rev_sorted.values / 1000):
    axes[1].text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                 f"£{val:.0f}k", va="center", fontsize=9)

# Scatter: Recency vs Frequency coloured by segment
for seg, grp in rfm.groupby("Segment"):
    axes[2].scatter(grp["Recency"], grp["Frequency"], label=seg,
                    alpha=0.6, s=30, color=colors_seg.get(seg, "gray"))
axes[2].set_xlabel("Recency (days)")
axes[2].set_ylabel("Purchase Frequency")
axes[2].set_title("Recency vs Frequency", fontsize=11, fontweight="bold")
axes[2].legend(fontsize=8, loc="upper right")

plt.tight_layout()
plt.savefig("outputs/02_rfm_segmentation.png", dpi=150, bbox_inches="tight")
plt.close()
print("[PLOT]  outputs/02_rfm_segmentation.png")

# ---- Chart 3: Country Revenue Distribution -----------------------------
country_rev = df.groupby("Country")["Revenue"].sum().sort_values(ascending=False)
top10 = country_rev.head(10)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("Revenue by Country", fontsize=14, fontweight="bold")

bars = ax1.barh(top10.index[::-1], top10.values[::-1] / 1000,
                color=plt.cm.Blues_r(np.linspace(0.2, 0.8, len(top10))), edgecolor="white")
ax1.set_xlabel("Revenue (£k)")
ax1.set_title("Top 10 Countries by Revenue", fontsize=11, fontweight="bold")
for bar, val in zip(bars, top10.values[::-1] / 1000):
    ax1.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
             f"£{val:.0f}k", va="center", fontsize=9)

non_uk = country_rev[country_rev.index != "United Kingdom"]
ax2.pie(non_uk.head(8).values,
        labels=[c[:12] for c in non_uk.head(8).index],
        autopct="%1.1f%%", startangle=90,
        colors=plt.cm.Set3.colors[:8], wedgeprops={"edgecolor": "white"})
ax2.set_title("Non-UK Revenue Share (Top 8)", fontsize=11, fontweight="bold")

plt.tight_layout()
plt.savefig("outputs/03_country_revenue.png", dpi=150, bbox_inches="tight")
plt.close()
print("[PLOT]  outputs/03_country_revenue.png")

# ---- Chart 4: Product Performance --------------------------------------
product_rev = df.groupby("Description").agg(
    Revenue=("Revenue", "sum"),
    Units=("Quantity", "sum"),
    Orders=("InvoiceNo", "nunique"),
).sort_values("Revenue", ascending=False).head(15)

fig, axes = plt.subplots(1, 2, figsize=(14, 7))
fig.suptitle("Product Performance", fontsize=14, fontweight="bold")

axes[0].barh(product_rev["Revenue"].sort_values().index,
             product_rev["Revenue"].sort_values().values / 1000,
             color="#e67e22", edgecolor="white")
axes[0].set_xlabel("Revenue (£k)")
axes[0].set_title("Top 15 Products by Revenue", fontsize=11, fontweight="bold")

axes[1].scatter(product_rev["Units"], product_rev["Revenue"] / 1000,
                s=product_rev["Orders"] * 3, alpha=0.7, color="#9b59b6", edgecolors="white")
axes[1].set_xlabel("Units Sold")
axes[1].set_ylabel("Revenue (£k)")
axes[1].set_title("Revenue vs Units (bubble = orders)", fontsize=11, fontweight="bold")
for _, row in product_rev.head(5).iterrows():
    axes[1].annotate(row.name[:18], (row["Units"], row["Revenue"] / 1000),
                     fontsize=7, ha="left", va="bottom")

plt.tight_layout()
plt.savefig("outputs/04_product_performance.png", dpi=150, bbox_inches="tight")
plt.close()
print("[PLOT]  outputs/04_product_performance.png")

# ---- Chart 5: Cohort Analysis ------------------------------------------
df["CohortMonth"] = df.groupby("CustomerID")["InvoiceDate"].transform("min").dt.to_period("M")
df["CohortIndex"] = (df["YearMonth"] - df["CohortMonth"]).apply(lambda x: x.n)
cohort_data = df.groupby(["CohortMonth", "CohortIndex"])["CustomerID"].nunique().reset_index()
cohort_pivot = cohort_data.pivot(index="CohortMonth", columns="CohortIndex", values="CustomerID")
cohort_pct = cohort_pivot.divide(cohort_pivot.iloc[:, 0], axis=0).round(3)

fig, ax = plt.subplots(figsize=(14, 7))
sns.heatmap(cohort_pct.iloc[:, :9].dropna(how="all"),
            ax=ax, cmap="Blues", annot=True, fmt=".0%",
            annot_kws={"size": 8}, linewidths=0.5, cbar_kws={"label": "Retention Rate"})
ax.set_xlabel("Months Since Acquisition")
ax.set_ylabel("Cohort (Acquisition Month)")
ax.set_title("Customer Retention Cohort Analysis", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("outputs/05_cohort_retention.png", dpi=150, bbox_inches="tight")
plt.close()
print("[PLOT]  outputs/05_cohort_retention.png")

# ---- Summary ------------------------------------------------------------
total_rev = df["Revenue"].sum()
aov = df.groupby("InvoiceNo")["Revenue"].sum().mean()
print(f"\n=== Summary KPIs ===")
print(f"  Total Revenue:    £{total_rev:,.0f}")
print(f"  Avg Order Value:  £{aov:.2f}")
print(f"  Unique Customers: {df['CustomerID'].nunique():,}")
print(f"  Unique Products:  {df['Description'].nunique():,}")
print(f"  Champions share:  {(rfm['Segment']=='Champions').mean()*100:.1f}% of customers")
print(f"\n[DONE]  5 charts saved to outputs/")
