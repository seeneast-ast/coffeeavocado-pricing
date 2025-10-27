import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
import os
import math

# -----------------------
# Config / Defaults
# -----------------------
DEFAULT_EXCEL_PATH = "print_costs.xlsx"  # default path
DEFAULT_SHEET = "costs"
OFFERED_SIZES = ["21x30", "30x40", "45x60", "60x80"]

st.set_page_config(page_title="CoffeeAvocado — Print Pricing", layout="wide")

# -----------------------
# Helpers
# -----------------------
@st.cache_data(ttl=60 * 60)
def fetch_gbp_to_eur_rate():
    try:
        res = requests.get("https://api.exchangerate.host/convert", params={"from":"GBP","to":"EUR"})
        data = res.json()
        if data.get("success", True):
            return float(data.get("result", 1.17))
    except Exception:
        pass
    return 1.17

@st.cache_data(ttl=60 * 60)
def fetch_usd_to_eur_rate():
    try:
        res = requests.get("https://api.exchangerate.host/convert", params={"from":"USD","to":"EUR"})
        data = res.json()
        if data.get("success", True):
            return float(data.get("result", 0.86))
    except Exception:
        pass
    return 0.86

def read_matrix_excel(path, sheet=DEFAULT_SHEET):
    df = pd.read_excel(path, sheet_name=sheet, header=None, engine="openpyxl")
    max_col = df.shape[1]
    sizes = df.iloc[0, :].tolist()
    monkey_prices = [None] * max_col
    monkey_postage = [None] * max_col
    artelo_prices = [None] * max_col
    artelo_postage = [None] * max_col

    if df.shape[0] > 5:
        monkey_prices = df.iloc[5, :].tolist()
    if df.shape[0] > 6:
        monkey_postage = df.iloc[6, :].tolist()
    if df.shape[0] > 8:
        artelo_prices = df.iloc[8, :].tolist()
    if df.shape[0] > 9:
        artelo_postage = df.iloc[9, :].tolist()

    tidy = []
    for i, s in enumerate(sizes):
        if pd.isna(s):
            continue
        try:
            size_val = float(s)
            size_int = int(round(size_val))
        except:
            continue
        row = {
            "size_cm2": size_int,
            "monkey_price_gbp": None if pd.isna(monkey_prices[i]) else float(monkey_prices[i]),
            "monkey_postage_gbp": None if pd.isna(monkey_postage[i]) else float(monkey_postage[i]),
            "artelo_price_usd": None if pd.isna(artelo_prices[i]) else float(artelo_prices[i]),
            "artelo_postage_usd": None if pd.isna(artelo_postage[i]) else float(artelo_postage[i]),
        }
        tidy.append(row)
    return pd.DataFrame(tidy).sort_values("size_cm2").reset_index(drop=True)

def compute_cost_for_choice(row, printer, gbp_to_eur_rate, usd_to_eur_rate):
    if printer == "Monkey Puzzle":
        price_gbp = row["monkey_price_gbp"]
        postage_gbp = row["monkey_postage_gbp"]
        if price_gbp is None:
            return None
        if postage_gbp is None:
            postage_gbp = 0.0
        total_gbp = price_gbp + postage_gbp
        total_eur = total_gbp * gbp_to_eur_rate
        return round(total_eur, 2)
    elif printer == "Artelo":
        price_usd = row["artelo_price_usd"]
        postage_usd = row["artelo_postage_usd"]
        if price_usd is None:
            return None
        if postage_usd is None:
            postage_usd = 0.0
        total_usd = price_usd + postage_usd
        total_eur = total_usd * usd_to_eur_rate
        return round(total_eur, 2)
    else:
        return None

def calc_final_price(base_cost_eur, profit_percent, min_profit_eur, etsy_fee_percent):
    desired_profit_amt = max(base_cost_eur * profit_percent, min_profit_eur)
    denominator = (1 - etsy_fee_percent)
    if denominator <= 0:
        return None, None
    final_price = (base_cost_eur + desired_profit_amt) / denominator
    profit_eur = final_price * (1 - etsy_fee_percent) - base_cost_eur
    return round(final_price, 2), round(profit_eur, 2)

# -----------------------
# UI
# -----------------------
st.title("CoffeeAvocado — Print Pricing Helper")
st.markdown("Upload your `print_costs.xlsx` or use the default. You can select or input your print size.")

uploaded_file = st.file_uploader("Upload print_costs.xlsx (optional, sheet 'costs')", type=["xlsx"])

if uploaded_file:
    try:
        with BytesIO(uploaded_file.read()) as b:
            costs_df = read_matrix_excel(b)
        st.success("Excel uploaded and processed successfully.")
        st.write("Data preview:", costs_df.head())
    except Exception as e:
        st.error(f"Failed to read uploaded Excel: {e}")
        st.stop()
else:
    if not os.path.exists(DEFAULT_EXCEL_PATH):
        st.warning(f"No file at {DEFAULT_EXCEL_PATH}. Please upload or place your Excel file.")
        costs_df = pd.DataFrame(columns=["size_cm2","monkey_price_gbp","monkey_postage_gbp","artelo_price_usd","artelo_postage_usd"])
    else:
        try:
            costs_df = read_matrix_excel(DEFAULT_EXCEL_PATH)
            st.success("Loaded default Excel file.")
            st.write("Sample data:", costs_df.head())
        except Exception as e:
            st.error(f"Failed to read default Excel: {e}")
            st.stop()

# Fetch exchange rate
gbp_to_eur_rate = fetch_gbp_to_eur_rate()
usd_to_eur_rate = fetch_usd_to_eur_rate()
st.sidebar.metric("Live GBP → EUR rate", f"{gbp_to_eur_rate:.4f}")
st.sidebar.metric("Live USD → EUR rate", f"{usd_to_eur_rate:.4f}")

# Select or input print size
st.subheader("Select or Input Print Size")
size_option = st.selectbox("Choose from offered sizes or input your size:", ["Type your size"] + OFFERED_SIZES)
if size_option == "Type your size":
    size_input = st.number_input("Enter print size (cm²):", min_value=1, step=1)
    chosen_size_cm2 = size_input
else:
    # Parse size from string like "21x30" -> 21*30
    try:
        parts = size_option.split('x')
        if len(parts) == 2:
            w, h = int(parts[0]), int(parts[1])
            chosen_size_cm2 = w * h
        else:
            chosen_size_cm2 = int(size_option)
    except:
        chosen_size_cm2 = None

if chosen_size_cm2:
    row = costs_df[costs_df["size_cm2"] == chosen_size_cm2]
    if row.empty:
        st.error("Size not found in database.")
    else:
        row = row.iloc[0]
        # Inputs
        printer_choice = st.selectbox("Printer", ["Monkey Puzzle", "Artelo"])
        profit_percent = st.number_input("Desired profit %", min_value=0.0, max_value=100.0, value=35.0, step=1.0)
        min_profit_eur = st.number_input("Minimum profit (€)", min_value=0.0, value=7.0, step=0.5)
        etsy_fee_percent = st.number_input("Etsy fee %", min_value=0.0, max_value=100.0, value=15.0, step=1.0) / 100

        # Calculate base cost
        base_cost_eur = compute_cost_for_choice(row, printer_choice, gbp_to_eur_rate, usd_to_eur_rate)
        if base_cost_eur is None:
            st.error("Cost data missing for this size/printer.")
        else:
            final_price, profit_eur = calc_final_price(base_cost_eur, profit_percent/100, min_profit_eur, etsy_fee_percent)

            # Display breakdown
            st.subheader("Cost Breakdown")
            st.write(f"Print cost + Postage (EUR): €{base_cost_eur:.2f}")
            etsy_fee_value = final_price * etsy_fee_percent
            st.write(f"Etsy fee ({int(etsy_fee_percent*100)}%): €{etsy_fee_value:.2f}")
            st.write(f"Profit (€): €{profit_eur:.2f}")
            st.write(f"Final recommended Etsy price: €{final_price:.2f}")

        else:
    st.info("Select or input a valid print size.")
