import streamlit as st
import pandas as pd
import numpy as np
from forex_python.converter import CurrencyRates
import math

st.set_page_config(page_title="Etsy Price Calculator", page_icon="🧾", layout="centered")

DEFAULT_EXCEL_PATH = "print_costs.xlsx"
DEFAULT_SHEET = 0
DEFAULT_ETSY_FEE = 0.15

OFFERED_SIZES = ["21x30", "30x40", "45x60", "60x80"]


# --- Read Excel ------------------------------------------------------------
@st.cache_data
def read_matrix_excel(path, sheet=DEFAULT_SHEET):
    try:
        df = pd.read_excel(path, sheet_name=sheet, header=None, engine="openpyxl")
    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return pd.DataFrame()

    max_col = df.shape[1]
    sizes = df.iloc[0, :].tolist()

    monkey_prices = df.iloc[5, :].tolist() if df.shape[0] > 5 else [None] * max_col
    monkey_postage = df.iloc[6, :].tolist() if df.shape[0] > 6 else [None] * max_col
    artelo_prices = df.iloc[8, :].tolist() if df.shape[0] > 8 else [None] * max_col
    artelo_postage = df.iloc[9, :].tolist() if df.shape[0] > 9 else [None] * max_col
    etsy_prices = df.iloc[12, :].tolist() if df.shape[0] > 12 else [None] * max_col  # row 13

    tidy = []
    for i, s in enumerate(sizes):
        if pd.isna(s):
            continue
        try:
            size_val = float(s)
            size_int = int(round(size_val))
        except:
            continue

        def safe_float(v):
            return None if pd.isna(v) else float(v)

        tidy.append({
            "size_cm2": size_int,
            "monkey_price_gbp": safe_float(monkey_prices[i]),
            "monkey_postage_gbp": safe_float(monkey_postage[i]),
            "artelo_price_eur": safe_float(artelo_prices[i]),
            "artelo_postage_eur": safe_float(artelo_postage[i]),
            "etsy_price_eur": safe_float(etsy_prices[i]),
        })

    return pd.DataFrame(tidy).sort_values("size_cm2").reset_index(drop=True)


# --- Save Etsy Prices ------------------------------------------------------
def save_matrix_excel(path, df_tidy):
    try:
        original = pd.read_excel(path, sheet_name=DEFAULT_SHEET, header=None, engine="openpyxl")
        for _, row in df_tidy.iterrows():
            match = np.where(original.iloc[0, :] == row["size_cm2"])[0]
            if len(match) > 0:
                col_index = match[0]
                original.iloc[12, col_index] = row["etsy_price_eur"]
        original.to_excel(path, sheet_name=DEFAULT_SHEET, index=False, header=False, engine="openpyxl")
        st.success("✅ Etsy prices saved to Excel!")
    except Exception as e:
        st.error(f"Failed to save Excel file: {e}")


# --- Calculations ----------------------------------------------------------
def calculate_price(print_cost, postage, desired_profit_pct, min_profit, etsy_fee):
    subtotal = print_cost + postage
    desired_profit_value = max(subtotal * desired_profit_pct, min_profit)
    total_before_fee = subtotal + desired_profit_value
    recommended_price = total_before_fee / (1 - etsy_fee)
    etsy_fee_value = recommended_price * etsy_fee
    return {
        "print_cost": round(print_cost, 2),
        "postage": round(postage, 2),
        "etsy_fee": round(etsy_fee_value, 2),
        "desired_profit": round(desired_profit_value, 2),
        "recommended_price": math.ceil(recommended_price)
    }


# --- UI -------------------------------------------------------------------
st.title("🧾 Etsy Print Price Calculator")

tab1, tab2 = st.tabs(["💰 Price Calculator", "📊 Database"])

costs_df = read_matrix_excel(DEFAULT_EXCEL_PATH)

# === TAB 1 : Price Calculator =============================================
with tab1:
    st.subheader("Price Estimator")

    printer = st.selectbox("Choose printer:", ["Monkey Puzzle", "Artelo"])
    choice_type = st.radio("How do you want to choose the size?", ["Choose from offered sizes", "Enter custom size"])

    if choice_type == "Choose from offered sizes":
        selected_size = st.selectbox("Select a print size:", OFFERED_SIZES)
        width_cm, height_cm = map(int, selected_size.split("x"))
        area = width_cm * height_cm
    else:
        width_cm = st.number_input("Width (cm)", min_value=1, value=30, step=1)
        height_cm = st.number_input("Height (cm)", min_value=1, value=40, step=1)
        area = width_cm * height_cm

        if st.button("➕ Add to predefined sizes"):
            new_size = f"{width_cm}x{height_cm}"
            if new_size not in OFFERED_SIZES:
                OFFERED_SIZES.append(new_size)
                st.success(f"Added {new_size} to offered sizes!")
            else:
                st.info(f"{new_size} already exists.")

    desired_profit_pct = st.slider("Desired profit (%)", 10, 100, 35)
    min_profit = st.number_input("Minimum profit (€)", min_value=0.0, value=7.0, step=0.5)

    st.markdown("---")

    match = costs_df[costs_df["size_cm2"] == area]
    if match.empty:
        st.warning("This size is not yet defined in your Excel file.")
    else:
        row = match.iloc[0]
        if printer == "Artelo":
            print_cost = row["artelo_price_eur"] or 0
            postage = row["artelo_postage_eur"] or 0
        else:
            print_cost = row["monkey_price_gbp"] or 0
            postage = row["monkey_postage_gbp"] or 0

        if pd.isna(print_cost):
            st.warning("No print cost set yet for this size.")
        else:
            result = calculate_price(print_cost, postage, desired_profit_pct / 100, min_profit, DEFAULT_ETSY_FEE)

            st.metric("📏 Print Area", f"{area} cm²")
            st.metric("💶 Recommended Etsy Price", f"{result['recommended_price']} €")

            st.markdown("---")
            st.markdown("**Breakdown:**")
            st.write(f"Print cost: **{result['print_cost']} €**")
            st.write(f"Postage: **{result['postage']} €**")
            st.write(f"Etsy fees (15%): **{result['etsy_fee']} €**")
            st.write(f"Desired profit ({desired_profit_pct}% or min {min_profit} €): **{result['desired_profit']} €**")
            st.markdown("---")
            st.markdown(f"**Print cost + postage + Etsy fees + desired profit = {result['recommended_price']} €**")


# === TAB 2 : Database ======================================================
with tab2:
    st.subheader("Full Database (Editable Etsy Prices)")
    st.markdown("Below are your production costs and current Etsy listing prices. Edit Etsy prices directly if needed.")

    editable_df = st.data_editor(
        costs_df,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "size_cm2": "Size (cm²)",
            "etsy_price_eur": st.column_config.NumberColumn("Etsy Price (€)", help="Edit and save your Etsy prices here."),
        },
        hide_index=True,
        disabled=["size_cm2", "monkey_price_gbp", "monkey_postage_gbp", "artelo_price_eur", "artelo_postage_eur"],
    )

    if st.button("💾 Save Etsy Prices to Excel"):
        save_matrix_excel(DEFAULT_EXCEL_PATH, editable_df)
