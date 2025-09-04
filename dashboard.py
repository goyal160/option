import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =======================
# NSE Session Manager
# =======================
_session = None

def get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/115.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
            "Connection": "keep-alive"
        })

        # Warm up session
        _session.get("https://www.nseindia.com", timeout=10, verify=False)
    return _session

def nsefetch(url: str):
    """Fetch NSE API data with persistent session & auto-refresh cookies"""
    s = get_session()
    try:
        r = s.get(url, timeout=10, verify=False)
        if r.status_code in [401, 403]:
            global session
            session = None
            s = get_session()
            r = s.get(url, timeout=10, verify=False)

        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise RuntimeError(f"Error fetching NSE data: {e}")


# ---------- Get Option Chain ----------
def get_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    data = nsefetch(url)
    records = []
    spot_price = data["records"]["underlyingValue"]

    for expiry_data in data["records"]["data"]:
        expiry = expiry_data["expiryDate"]
        strike = expiry_data["strikePrice"]
        ce_data = expiry_data.get("CE", {})
        pe_data = expiry_data.get("PE", {})

        if ce_data:
            records.append({
                "expiry": expiry,
                "strike": strike,
                "type": "CE",
                "OI": ce_data.get("openInterest", 0),
                "ChgOI": ce_data.get("changeinOpenInterest", 0),
                "LTP": ce_data.get("lastPrice", 0),
                "IV": ce_data.get("impliedVolatility", 0)
            })
        if pe_data:
            records.append({
                "expiry": expiry,
                "strike": strike,
                "type": "PE",
                "OI": pe_data.get("openInterest", 0),
                "ChgOI": pe_data.get("changeinOpenInterest", 0),
                "LTP": pe_data.get("lastPrice", 0),
                "IV": pe_data.get("impliedVolatility", 0)
            })

    return pd.DataFrame(records), spot_price

# ---------- Add Signal Logic ----------
def add_signals(df):
    signals = []
    for _, row in df.iterrows():
        if row["type"] == "CE":
            if row["ChgOI"] > 0:
                signals.append("Bearish (Call Writing)")
            elif row["ChgOI"] < 0:
                signals.append("Bullish (Call Short Covering)")
            else:
                signals.append("Neutral")
        else:  # PE
            if row["ChgOI"] > 0:
                signals.append("Bullish (Put Writing)")
            elif row["ChgOI"] < 0:
                signals.append("Bearish (Put Long Unwinding)")
            else:
                signals.append("Neutral")
    df["Signal"] = signals
    return df

# ---------- Streamlit UI ----------
st.set_page_config(layout="wide")
st.title("📊 NSE Option Chain Dashboard")

symbol = st.selectbox("Select Index", ["NIFTY", "BANKNIFTY"])

try:
    df, spot = get_option_chain(symbol)
    st.success(f"Spot Price of {symbol}: {spot}")

    # Expiry filter
    expiries = sorted(df["expiry"].unique())
    expiry_choice = st.selectbox("Select Expiry", expiries)
    df = df[df["expiry"] == expiry_choice]

    # Limit strikes ±1000 around spot
    df = df[(df["strike"] >= spot - 1000) & (df["strike"] <= spot + 1000)]

    # Add signals
    df = add_signals(df)

    # Support & Resistance
    ce_data = df[df["type"] == "CE"].sort_values("strike")
    pe_data = df[df["type"] == "PE"].sort_values("strike")

    if not ce_data.empty and not pe_data.empty:
        top_resistance = ce_data.loc[ce_data["OI"].idxmax()]
        top_support = pe_data.loc[pe_data["OI"].idxmax()]

        st.subheader("📌 Market Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Spot Price", f"{spot}")
        col2.metric("Strongest Resistance", f"{int(top_resistance['strike'])} CE (OI={top_resistance['OI']})")
        col3.metric("Strongest Support", f"{int(top_support['strike'])} PE (OI={top_support['OI']})")

    # Table
    st.subheader("Option Chain Data")
    st.dataframe(df.sort_values(["strike", "type"]).reset_index(drop=True), height=500)

    # ---------- Charts ----------
    st.subheader("Charts")

    # OI Line Chart
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(ce_data["strike"], ce_data["OI"], color="red", marker="o", label="Call OI")
    ax1.plot(pe_data["strike"], pe_data["OI"], color="green", marker="o", label="Put OI")
    ax1.axvline(x=spot, color="blue", linestyle="--", label="Spot Price")
    ax1.set_title("Call vs Put Open Interest (Line Chart)")
    ax1.set_xlabel("Strike Price")
    ax1.set_ylabel("Open Interest")
    ax1.legend()
    st.pyplot(fig1)

    # IV vs Strike Chart
    fig2, ax2 = plt.subplots(figsize=(12, 5))
    ax2.plot(ce_data["strike"], ce_data["IV"], color="red", marker="o", label="Call IV")
    ax2.plot(pe_data["strike"], pe_data["IV"], color="green", marker="o", label="Put IV")
    ax2.axvline(x=spot, color="blue", linestyle="--", label="Spot Price")
    ax2.set_title("Implied Volatility vs Strike Price")
    ax2.set_xlabel("Strike Price")
    ax2.set_ylabel("Implied Volatility (%)")
    ax2.legend()
    st.pyplot(fig2)

except Exception as e:
    st.error(f"Error fetching data: {e}")