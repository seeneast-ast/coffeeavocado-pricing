import streamlit as st
import pandas as pd
from forex_python.converter import CurrencyRates

# ---- Config ----
EXCEL_FILE = "print_costs.xlsx"
BIC_ABATEMENT = 0.71   # 71% of profit is taxable
BIC_TAX_RATE = 0.11    # 11% average rate after abatement
DEFAULT_PROFIT_MARGIN = 0.15  # 15%

# ---- Load Data ----
@st.cache_data
def load_data():
    df = pd.read_excel(EXCEL_FILE, header=None)
    return df

# ---- Currency conversion ----
@st.cache_data
def get_gbp_to_eur():
    try:
        c = CurrencyRates()
        return c.get_rate('GBP', 'EUR')
    except Exception:
        # fallback rate if no internet or API issue
        return 1.17

# ---- Compute pricing ----
def compute_price(print_cost, postage, etsy_fee, profit_margin, bic_tax):
    subtotal = print_cost + postage
    etsy_fees = subtotal * etsy_fee
    profit = subtotal * profit_margin
    bic_tax_amount = profit * BIC_ABATEMENT * BIC_TAX_RATE
    total = subtotal + etsy_fees + profit + bic_tax_amount
    return total, etsy_fees, profit, bic_tax_amount

# ---- App Layout ----
st.title("🖼️ Etsy Price Calculator")

st.markdown("Upload your updated Excel file if needed:")
uploaded = st.file_uploader("Upload Excel", type=["xlsx"], key="uploader")
if uploaded:
    df = pd.read_excel(uploaded, header=None)
else:
    df = load_data()

gbp_to_eur = get_gbp_to_eur()
st.write(f"💱 Current GBP → EUR rate: **{gbp_to_eur:.2f}**")

sizes = ["21x30", "30x40", "45x60", "60x80"]
selected_size = st.selectbox("Select a print size", sizes)

# Match sizes to cm²
size_to_area = {"21x30": 630, "30x40": 1200, "45x60": 2700, "60x80": 4800}
area = size_to_area[selected_size]

# Read Excel rows
monkey_price = df.iloc[5, int(area / 100 - 3)] if len(df.columns) > int(area / 100 - 3) else None
artelo_price = df.iloc[7, int(area / 100 - 3)] if len(df.columns) > int(area / 100 - 3) else None
etsy_current = df.iloc[13, int(area / 100 - 3)] if len(df.columns) > int(area / 100 - 3) else None

# Monkey Puzzle postage £6.50 → EUR
monkey_postage = 6.5 * gbp_to_eur
artelo_postage = 15 if area < 3000 else 20

st.subheader("💡 Pricing comparison")

etsy_fee_rate = st.number_input("Etsy fees (%)", value=15.0, step=0.5) / 100
profit_margin = st.number_input("Desired profit (%)", value=15.0, step=0.5) / 100

if artelo_price is not None and not pd.isna(artelo_price):
    artelo_total, etsy_fees, profit, tax = compute_price(
        artelo_price, artelo_postage, etsy_fee_rate, profit_margin, BIC_TAX_RATE
    )
else:
    artelo_total = None

if monkey_price is not None and not pd.isna(monkey_price):
    monkey_total, _, _, _ = compute_price(
        monkey_price * gbp_to_eur, monkey_postage, etsy_fee_rate, profit_margin, BIC_TAX_RATE
    )
else:
    monkey_total = None

# ---- Display Results ----
st.write(f"### {selected_size} — {area} cm²")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Artelo:**")
    if artelo_total:
        st.write(f"Print cost: {artelo_price:.2f} €")
        st.write(f"Postage: {artelo_postage:.2f} €")
        st.write(f"Etsy fee: {(etsy_fee_rate*100):.1f}% → {etsy_fees:.2f} €")
        st.write(f"Profit margin: {(profit_margin*100):.1f}% → {profit:.2f} €")
        st.write(f"BIC tax: {tax:.2f} €")
        st.markdown(f"**Recommended Etsy price: {artelo_total:.2f} €**")
    else:
        st.write("Not set yet.")

with col2:
    st.markdown("**Monkey Puzzle:**")
    if monkey_total:
        st.write(f"Print cost: {monkey_price:.2f} £ → {(monkey_price * gbp_to_eur):.2f} €")
        st.write(f"Postage: £6.50 → {monkey_postage:.2f} €")
        st.markdown(f"**Recommended Etsy price: {monkey_total:.2f} €**")
    else:
        st.write("Not set yet.")

if etsy_current is not None and not pd.isna(etsy_current):
    st.write(f"🛒 **Current Etsy price:** {etsy_current:.2f} €")
else:
    st.write("🛒 **Current Etsy price:** Not set yet")
