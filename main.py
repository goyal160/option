import requests
from nsepython import nse_optionchain_scrapper
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

# Monkey patch to bypass SSL verification for NSEPython
original_get = requests.get
def unsafe_get(*args, **kwargs):
    kwargs['verify'] = False
    return original_get(*args, **kwargs)
requests.get = unsafe_get

st.set_page_config(layout="wide")
st.title("🦅 Iron Condor Payoff Visualizer - NSE Options")

# Get data
symbol = "NIFTY"
try:
    data = nse_optionchain_scrapper(symbol)
except Exception as e:
    st.error(f"Error fetching data: {e}")
    st.stop()

# Spot price and expiry options
spot = data['records']['underlyingValue']
expiry_list = data['records']['expiryDates']
expiry_selected = st.selectbox("Select Expiry", expiry_list)
dte = st.slider("Days to Expiry (for simulation)", 0, 30, 0)

st.markdown(f"**Spot Price:** ₹{spot:.2f}")

# Strike setup
atm = round(spot / 50) * 50
width = st.selectbox("Strike Width", [50, 100, 150, 200], index=1)
strikes = {
    "PE_BUY": atm - 2 * width,
    "PE_SELL": atm - width,
    "CE_SELL": atm + width,
    "CE_BUY": atm + 2 * width
}

# Price fetcher
def get_price(strike, opt_type, expiry):
    for d in data['records']['data']:
        if d['strikePrice'] == strike and d['expiryDate'] == expiry:
            if opt_type in d and d[opt_type]:
                return d[opt_type]['lastPrice']
    return 0

# Premiums
pb = get_price(strikes["PE_BUY"], 'PE', expiry_selected)
ps = get_price(strikes["PE_SELL"], 'PE', expiry_selected)
cs = get_price(strikes["CE_SELL"], 'CE', expiry_selected)
cb = get_price(strikes["CE_BUY"], 'CE', expiry_selected)
net_credit = (ps - pb) + (cs - cb)
lotsize = 50
max_loss = width - net_credit
lower_be = strikes["PE_SELL"] - net_credit
upper_be = strikes["CE_SELL"] + net_credit

# Output
st.subheader("📊 Iron Condor Details")
st.write(f"**Sell PE {strikes['PE_SELL']}** @ ₹{ps:.2f}, **Buy PE {strikes['PE_BUY']}** @ ₹{pb:.2f}")
st.write(f"**Sell CE {strikes['CE_SELL']}** @ ₹{cs:.2f}, **Buy CE {strikes['CE_BUY']}** @ ₹{cb:.2f}")
st.write(f"**Net Credit:** ₹{net_credit * lotsize:.2f}")
st.write(f"**Max Profit:** ₹{net_credit * lotsize:.2f}")
st.write(f"**Max Loss:** ₹{-max_loss * lotsize:.2f}")
st.write(f"**Breakeven Range:** ₹{lower_be:.0f} to ₹{upper_be:.0f}")

# Payoff Calculation
x = np.arange(atm - 400, atm + 401, 10)
payoff = []
for s in x:
    pe_buy = max(strikes["PE_BUY"] - s, 0) - pb
    pe_sell = max(strikes["PE_SELL"] - s, 0) - ps
    ce_sell = max(s - strikes["CE_SELL"], 0) - cs
    ce_buy = max(s - strikes["CE_BUY"], 0) - cb
    total = pe_buy - pe_sell - ce_sell + ce_buy
    payoff.append(total * lotsize)

# Plotting
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(x, payoff, label='Payoff', color='blue')
ax.axhline(0, color='black', linestyle='--')
ax.axvline(atm, color='gray', linestyle='--', label=f"ATM: {atm}")
ax.axvline(lower_be, color='orange', linestyle='--', label=f"Lower BE: {lower_be:.0f}")
ax.axvline(upper_be, color='orange', linestyle='--', label=f"Upper BE: {upper_be:.0f}")
ax.axvspan(strikes["PE_SELL"], strikes["CE_SELL"], color='green', alpha=0.2, label='Max Profit Zone')
ax.axvspan(x[0], strikes["PE_BUY"], color='red', alpha=0.1, label='Max Loss Zone')
ax.axvspan(strikes["CE_BUY"], x[-1], color='red', alpha=0.1)

ax.set_title(f"Iron Condor Payoff - Expiry: {expiry_selected} | DTE: {dte}")
ax.set_xlabel("Spot Price")
ax.set_ylabel("P&L (₹)")
ax.grid(True)
ax.legend()
st.pyplot(fig)