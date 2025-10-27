import streamlit as st
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

st.set_page_config(page_title="Artelo Price Estimator", page_icon="🎨", layout="centered")

st.title("🎨 Artelo Price Estimator")
st.write("Estimate missing prices using a simple linear regression model.")

# --- Data section ---
st.subheader("1️⃣ Enter known data points")
x_values = st.text_input("Enter your x values (comma separated):", "600, 1200, 2400, 4800, 7000")
y_values = st.text_input("Enter corresponding prices:", "244, 1139, 2000, 4000, 7000")

try:
    x = np.array([float(i.strip()) for i in x_values.split(",")]).reshape(-1, 1)
    y = np.array([float(i.strip()) for i in y_values.split(",")])
except:
    st.error("⚠️ Please make sure you only use numbers separated by commas.")
    st.stop()

# --- Model section ---
model = LinearRegression()
model.fit(x, y)
r2 = model.score(x, y)
coef = model.coef_[0]
intercept = model.intercept_

st.write(f"**Regression equation:** y = {coef:.2f}x + {intercept:.2f}")
st.write(f"**R² value:** {r2:.3f}")

# --- Prediction section ---
st.subheader("2️⃣ Predict a new value")
x_new = st.number_input("Enter a new x value to predict:", min_value=0.0, value=1000.0)
y_pred = model.predict(np.array([[x_new]]))[0]
st.success(f"Estimated price for x = {x_new:.0f} → **{y_pred:.0f}**")

# --- Visualization ---
st.subheader("3️⃣ Visualization")
fig, ax = plt.subplots()
ax.scatter(x, y, color="blue", label="Known points")
ax.plot(x, model.predict(x), color="red", label="Regression line")
ax.scatter([x_new], [y_pred], color="green", s=100, label="Prediction")
ax.legend()
ax.set_xlabel("x (input)")
ax.set_ylabel("Price (y)")
ax.grid(True)
st.pyplot(fig)
