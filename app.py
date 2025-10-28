import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
import os
import datetime

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
    """Fetches the current GBP to EUR exchange rate."""
    try:
        # Using a reliable public exchange rate API
        res = requests.get("https://api.exchangerate.host/convert", params={"from": "GBP", "to": "EUR"})
        res.raise_for_status()
        data = res.json()
        if data.get("success", True):
            # Using a fallback rate if API data is missing
            return float(data.get("info", {}).get("rate", 1.17))
    except Exception:
        # Fallback rate if API call fails
        pass
    return 1.17

def read_matrix_excel(path, sheet=DEFAULT_SHEET):
    """Reads the cost matrix from the Excel file and converts it to a tidy DataFrame."""
    try:
        df = pd.read_excel(path, sheet_name=sheet, header=None, engine="openpyxl")
    except KeyError:
        # Handle case where the sheet name is wrong
        st.error(f"Sheet '{sheet}' not found in the Excel file.")
        return pd.DataFrame()
        
    max_col = df.shape[1]
    # Row 0 contains the sizes (Column headers in original matrix)
    sizes = df.iloc[0, :].tolist()
    
    # Extract data from specific rows based on the original layout
    monkey_prices = df.iloc[5, :].tolist() if df.shape[0] > 5 else [None] * max_col
    monkey_postage = df.iloc[6, :].tolist() if df.shape[0] > 6 else [None] * max_col
    artelo_prices = df.iloc[8, :].tolist() if df.shape[0] > 8 else [None] * max_col
    artelo_postage = df.iloc[9, :].tolist() if df.shape[0] > 9 else [None] * max_col

    tidy = []
    for i, s in enumerate(sizes):
        # Skip empty or non-numeric size columns
        if pd.isna(s):
            continue
        try:
            size_val = float(s)
            size_int = int(round(size_val))
        except:
            continue
            
        # Helper function to convert value to float or None
        def safe_float(val, fallback=None):
            return fallback if pd.isna(val) else float(val)

        row = {
            "size_cm2": size_int,
            "monkey_price_gbp": safe_float(monkey_prices[i]),
            "monkey_postage_gbp": safe_float(monkey_postage[i]),
            "artelo_price_eur": safe_float(artelo_prices[i]),
            "artelo_postage_eur": safe_float(artelo_postage[i]),
        }
        tidy.append(row)
    return pd.DataFrame(tidy).sort_values("size_cm2").reset_index(drop=True)

def compute_cost_for_choice(row, printer, gbp_to_eur_rate):
    """Calculates the base cost (Print + Postage) in EUR."""
    price_gbp = row["monkey_price_gbp"]
    postage_gbp = row["monkey_postage_gbp"]
    price_eur = row["artelo_price_eur"]
    postage_eur = row["artelo_postage_eur"]
    
    if printer == "Monkey Puzzle":
        if price_gbp is None:
             return None, None, None, None, None # total, postage_eur, original_price_local, original_postage_local, print_cost_eur
        
        # Use a fallback postage if not specified
        if postage_gbp is None:
            postage_gbp = 6.5
            
        total_gbp = price_gbp + postage_gbp
        total_eur = total_gbp * gbp_to_eur_rate
        postage_eur = postage_gbp * gbp_to_eur_rate
        print_cost_eur = price_gbp * gbp_to_eur_rate
        
        return round(total_eur, 2), round(postage_eur, 2), price_gbp, postage_gbp, round(print_cost_eur, 2)
        
    elif printer == "Artelo":
        if price_eur is None:
            return None, None, None, None, None # total, postage_eur, original_price_local, original_postage_local, print_cost_eur

        # Use a fallback postage if not specified
        if postage_eur is None:
            postage_eur = 15
            
        total_eur = price_eur + postage_eur
        # Prices are already in EUR
        return round(total_eur, 2), round(postage_eur, 2), price_eur, postage_eur, price_eur
        
    else:
        return None, None, None, None, None

# MODIFIED: Added tax_percent parameter
def calc_final_price(base_cost_eur, profit_percent, min_profit_eur, etsy_fee_percent, tax_percent):
    """Calculates final selling price based on all costs, desired profit, and fees/taxes."""
    # 1. Calculate the minimum desired profit amount
    desired_profit_amt = max(base_cost_eur * profit_percent, min_profit_eur)
    
    # 2. Calculate the total fee/tax deduction rate
    total_deduction_rate = etsy_fee_percent + tax_percent
    
    # 3. Denominator for the price calculation: 1 - (Etsy Fee % + Tax %)
    # This ensures the desired profit is met after all percentage-based deductions on turnover
    denominator = (1 - total_deduction_rate)
    
    if denominator <= 0:
        return None, None, None # final_price, profit_eur, tax_eur
        
    # 4. Calculate the final price (turnover)
    final_price = (base_cost_eur + desired_profit_amt) / denominator
    
    # 5. Calculate the tax amount based on final price
    tax_eur = final_price * tax_percent
    
    # 6. Calculate the final profit earned (must match or exceed desired_profit_amt)
    # Profit = Final Price - Etsy Fee - Tax - Base Cost
    etsy_fee_value = final_price * etsy_fee_percent
    profit_eur = final_price - etsy_fee_value - tax_eur - base_cost_eur
    
    return round(final_price, 2), round(profit_eur, 2), round(tax_eur, 2)

# -----------------------
# UI
# -----------------------
st.title("CoffeeAvocado — Print Pricing Helper")
st.markdown("Upload your `print_costs.xlsx` or use the default. Use the tabs below to calculate pricing or view the full database.")

# Upload or load default excel
uploaded_file = st.file_uploader("Upload print_costs.xlsx (optional, sheet 'costs')", type=["xlsx"])

costs_df = pd.DataFrame() # Initialize costs_df

if uploaded_file:
    try:
        with BytesIO(uploaded_file.read()) as b:
            costs_df = read_matrix_excel(b)
        if not costs_df.empty:
            st.success("Excel uploaded and processed successfully.")
            st.write("Data preview:", costs_df.head())
    except Exception as e:
        st.error(f"Failed to read uploaded Excel: {e}")
        st.stop()
else:
    # Logic for loading default file if upload is skipped and file exists
    if os.path.exists(DEFAULT_EXCEL_PATH):
        try:
            costs_df = read_matrix_excel(DEFAULT_EXCEL_PATH)
            if not costs_df.empty:
                st.success("Loaded default Excel file.")
                st.write("Sample data:", costs_df.head())
        except Exception as e:
            st.error(f"Failed to read default Excel: {e}")
            st.stop()
    else:
        st.warning(f"No file at {DEFAULT_EXCEL_PATH} and no file uploaded. Using empty dataset.")
        costs_df = pd.DataFrame(columns=["size_cm2","monkey_price_gbp","monkey_postage_gbp","artelo_price_eur","artelo_postage_eur"])


# Fetch exchange rate
gbp_to_eur_rate = fetch_gbp_to_eur_rate()
current_date = datetime.date.today().strftime("%Y-%m-%d")
st.sidebar.metric("Live GBP → EUR rate", f"{gbp_to_eur_rate:.4f} (as of {current_date})")

# Tabs for main calculation and database viewing
tab1, tab2 = st.tabs(["Calculate Price", "View Database"])

with tab1:
    if costs_df.empty:
        st.error("Cannot proceed with calculation. Please upload a valid print_costs.xlsx file.")
    else:
        # Option to use predefined sizes or manual input
        col_use, col_tax_info = st.columns([0.5, 0.5])
        with col_use:
            use_predefined = st.checkbox("Use predefined print sizes", value=True)
        with col_tax_info:
            st.caption("Tax Note: Micro-entreprise BIC (Vente de Biens) Social/Tax is approx. 13.1%.")
            
        if use_predefined:
            selected_size_str = st.selectbox("Select size", OFFERED_SIZES)
            size_map = {
                "21x30": (21, 30),
                "30x40": (30, 40),
                "45x60": (45, 60),
                "60x80": (60, 80),
            }
            width_cm, height_cm = size_map.get(selected_size_str, (10, 30))
        else:
            width_cm = st.number_input("Width (cm)", min_value=1, value=10, step=1)
            height_cm = st.number_input("Height (cm)", min_value=1, value=30, step=1)

        chosen_size_cm2 = width_cm * height_cm

        st.subheader(f"Print Area: {width_cm} x {height_cm} cm ({chosen_size_cm2} cm²)")

        if chosen_size_cm2:
            row_match = costs_df[costs_df["size_cm2"] == chosen_size_cm2]
            
            if row_match.empty:
                # Find the closest size in the database
                closest_idx = (costs_df["size_cm2"] - chosen_size_cm2).abs().idxmin()
                row = costs_df.iloc[closest_idx]
                closest_size = row["size_cm2"]
                st.warning(f"Size {chosen_size_cm2} cm² not found. Using closest available size: {closest_size} cm².")
            else:
                row = row_match.iloc[0]
            
            # --- Inputs for calculation parameters ---
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                printer_choice = st.selectbox("Printer", ["Monkey Puzzle", "Artelo"])
            with col2:
                profit_percent_input = st.number_input("Desired Profit (%)", min_value=0.0, max_value=100.0, value=35.0, step=1.0)
            with col3:
                min_profit_eur = st.number_input("Minimum profit (€)", min_value=0.0, value=7.0, step=0.5)
            with col4:
                etsy_fee_percent_input = st.number_input("Etsy Fee (%)", min_value=0.0, max_value=100.0, value=15.0, step=1.0)
            
            # --- NEW TAX INPUT ---
            tax_percent_input = st.number_input(
                "Business Tax/Cotisations Sociales (%) (French BIC Micro-entreprise)", 
                min_value=0.0, 
                max_value=100.0, 
                value=12.3, 
                step=0.1
            )

            # Convert percentages to decimals
            profit_percent = profit_percent_input / 100
            etsy_fee_percent = etsy_fee_percent_input / 100
            tax_percent = tax_percent_input / 100

            # --- Calculate Costs ---
            base_cost_eur, postage_eur, original_price, original_postage, print_cost_eur = compute_cost_for_choice(row, printer_choice, gbp_to_eur_rate)

            if base_cost_eur is None:
                st.error(f"Cost data missing for size {row['size_cm2']} cm² with {printer_choice}.")
            else:
                # Calculate final price and breakdown
                # MODIFIED: Passing tax_percent and receiving tax_eur
                final_price, profit_eur, tax_eur = calc_final_price(
                    base_cost_eur, 
                    profit_percent, 
                    min_profit_eur, 
                    etsy_fee_percent, 
                    tax_percent
                )
                
                if final_price is None:
                    st.error(f"Cannot calculate final price. The total percentage of fees ({etsy_fee_percent_input:.1f}% Etsy + {tax_percent_input:.1f}% Tax) exceeds 100%. Adjust your fee/tax rates or desired profit.")
                    st.stop()

                # Calculate final fee values based on the calculated final price (Turnover)
                etsy_fee_value = final_price * etsy_fee_percent
                
                # Calculate total money paid out (Base Cost + Etsy Fee + Tax)
                total_outgoings_eur = base_cost_eur + etsy_fee_value + tax_eur

                # --- Display breakdown ---
                st.subheader("Price Calculation Summary")
                
                # Display base print cost (The base currency is also shown)
                st.markdown(f"**1. Base Print Cost (€):** **€{print_cost_eur:.2f}** "
                            f"(<i>{printer_choice} print cost: {original_price:.2f} {('£' if printer_choice == 'Monkey Puzzle' else '€')}</i>)", 
                            unsafe_allow_html=True)
                            
                # Display postage cost
                st.markdown(f"**2. Postage Cost (€):** **€{postage_eur:.2f}** "
                            f"(<i>{printer_choice} postage cost: {original_postage:.2f} {('£' if printer_choice == 'Monkey Puzzle' else '€')}</i>)", 
                            unsafe_allow_html=True)
                
                st.markdown(f"---")
                st.markdown(f"**Total Base Cost (1 + 2):** **€{base_cost_eur:.2f}**")
                st.markdown(f"---")
                
                # Display fees and taxes based on final price
                st.markdown(f"**3. Etsy Fee ({etsy_fee_percent_input:.1f}% of Final Price):** **€{etsy_fee_value:.2f}**")
                
                # NEW: Display Tax
                st.markdown(f"**4. Business Tax ({tax_percent_input:.1f}% of Final Price):** **€{tax_eur:.2f}**")
                st.markdown(f"---")

                # Display final results
                st.markdown(
                    f"""
                    <div style='background-color: #e0f7fa; padding: 15px; border-radius: 10px; border-left: 5px solid #00bcd4;'>
                        <h4 style='color: green; margin-top: 0;'>Final Recommendation</h4>
                        <p style='font-size: 1.2em; color: green;'>
                            **Recommended Selling Price (Turnover):** **€{final_price:.2f}**
                        </p>
                        <p style='font-size: 1.1em; color: green;'>
                            Total Outgoings (Base Cost + Fees + Tax): **€{total_outgoings_eur:.2f}**
                        </p>
                        <p style='color: green; font-weight: bold; font-size: 1.1em;'>
                            Final Profit (Net of ALL Costs and Taxes): **€{profit_eur:.2f}**
                        </p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )


with tab2:
    st.subheader("Full Database")
    st.markdown("This table is derived from your uploaded/default Excel file (`print_costs.xlsx`).")
    st.dataframe(costs_df, use_container_width=True)
  
  # -----------------------------
# NEW SECTION: Current Etsy Listing
# -----------------------------
# Try to get Etsy price from row 13 (index 12 because zero-based)
try:
    etsy_price_val = df.iloc[12, costs_df.columns.get_loc(row.name)]  # fallback if structure known
except Exception:
    # Safer method: reload Excel sheet and get row 13 manually
    try:
        df_full = pd.read_excel(DEFAULT_EXCEL_PATH, sheet_name=DEFAULT_SHEET, header=None, engine="openpyxl")
        etsy_price_val = df_full.iloc[13, costs_df.index[costs_df["size_cm2"] == row["size_cm2"]][0]]
    except Exception:
        etsy_price_val = None

# If Etsy price missing or NaN
if pd.isna(etsy_price_val):
    etsy_price_display = "Not Set"
    current_profit_display = "N/A"
else:
    etsy_price_val = float(etsy_price_val)
    etsy_price_display = f"€{etsy_price_val:.2f}"
    current_profit_val = etsy_price_val - total_outgoings_eur
    current_profit_display = f"€{current_profit_val:.2f}"

st.markdown(
    f"""
    <div style='background-color: #fff9e6; padding: 15px; border-radius: 10px; border-left: 5px solid #ffb300; margin-top: 20px;'>
        <h4 style='color: orange; margin-top: 0;'>Current Etsy Listing</h4>
        <p style='font-size: 1.1em;'>
            <b>Etsy Price:</b> {etsy_price_display}<br>
            <b>Current Profit:</b> {current_profit_display}
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
