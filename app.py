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
                        etsy_price_val = df_full.iloc[12, costs_df.index[costs_df["size_cm2"] == row["size_cm2"]][0]]
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
                        <h4 style='color: #ff8f00; margin-top: 0;'>Current Etsy Listing</h4>
                        <p style='font-size: 1.1em;'>
                            <b>Etsy Price:</b> {etsy_price_display}<br>
                            <b>Current Profit:</b> {current_profit_display}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
