import streamlit as st
import pandas as pd

# --- Load Excel Data ---
import pandas as pd
import streamlit as st

@st.cache_data
def load_data():
    file_path = "print_costs.xlsx"
    df = pd.read_excel(file_path, header=None)
    return df

df = load_data()

# --- UI ---
st.title("Etsy Price Calculator")

# --- User Inputs ---
st.header("Input")
size_options = ["21x30", "30x40", "45x60", "60x80"]
selected_size = st.selectbox("Choose print size", size_options)
desired_profit_percent = st.number_input("Desired profit (%)", value=35, step=1) / 100
min_profit = st.number_input("Minimum profit (€)", value=7.0, step=0.5)
printer = st.selectbox("Choose printer", ["Monkey Puzzle", "Artelo"])
paper = st.selectbox("Paper type", ["Museum Heritage 310gsm", "Cold Press"])

# --- Size Area Lookup ---
size_to_area = {"21x30": 630, "30x40": 1200, "45x60": 2700, "60x80": 4800}
area = size_to_area[selected_size]

# --- Read Prices from Excel ---
if printer == "Monkey Puzzle":
    print_cost = df.iloc[5, int(area / 100) - 1]
    postage = 6.5
else:
    print_cost = df.iloc[7, int(area / 100) - 1]
    postage = df.iloc[8, int(area / 100) - 1]

# --- Etsy Current Price (Row 13) ---
try:
    etsy_price = df.iloc[13, int(area / 100) - 1]
    etsy_price_display = f"{etsy_price:.2f} €" if pd.notna(etsy_price) else "Not set yet"
except Exception:
    etsy_price_display = "Not set yet"

# --- Fee Calculation ---
etsy_fee_rate = 0.15
etsy_fee = (print_cost + postage) * etsy_fee_rate

# --- Desired Profit ---
desired_profit = max(min_profit, (print_cost + postage) * desired_profit_percent)

# --- Recommended Price ---
recommended_price = print_cost + postage + etsy_fee + desired_profit

# --- Output ---
st.header("Output")
st.write(f"**Etsy current price:** {etsy_price_display}")

st.write("### Calculation Summary")
st.markdown(
    f"""
    **print cost + postage + etsy fees + desired profit = recommended price**  
    **{print_cost:.2f}€ + {postage:.2f}€ + {etsy_fee:.2f}€ + {desired_profit:.2f}€ = {recommended_price:.2f}€**
    """
)

st.success(f"✅ Recommended Etsy Price: **{recommended_price:.2f} €**")
