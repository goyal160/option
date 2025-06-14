import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
from nsepython import nse_optionchain_scrapper

# Disable SSL verification globally for NSE
original_get = requests.get
def unsafe_get(*args, **kwargs):
    kwargs['verify'] = False
    return original_get(*args, **kwargs)
requests.get = unsafe_get

st.set_page_config(page_title="Iron Condor Visualizer", layout="wide")
st.title("📊 Safe Strangle Option Selling Strategy (Live from NSE)")

# Layout columns
col1, col2 = st.columns([1, 2])

with col1:
    symbol = st.selectbox("Select Index", ["NIFTY", "BANKNIFTY"])

    try:
        data = nse_optionchain_scrapper(symbol)

        if not data or 'records' not in data or 'underlyingValue' not in data['records']:
            st.error("⚠️ Failed to fetch live data from NSE. Please retry after a few seconds.")
            st.stop()

        spot = data['records']['underlyingValue']

        expiries = data['records']['expiryDates']
        expiry = st.selectbox("Select Expiry Date", expiries)

        width = st.slider("Width from ATM (in ₹)", 50, 500, 100, step=50)
        dte = st.slider("Days to Expiry (DTE)", 1, 30, 5)

        atm = round(spot / 50) * 50
        strikes = {
            "PE_BUY": atm - 2 * width,
            "PE_SELL": atm - width,
            "CE_SELL": atm + width,
            "CE_BUY": atm + 2 * width
        }

        def get_contract_details(strike, opt_type):
            for d in data['records']['data']:
                if d['strikePrice'] == strike and d.get(opt_type):
                    return d[opt_type]['lastPrice'], d[opt_type].get('openInterest', 'N/A'), d[opt_type].get('changeinOpenInterest', 'N/A')
            return 0, 'N/A', 'N/A'

        pb, pb_oi, pb_coi = get_contract_details(strikes["PE_BUY"], 'PE')
        ps, ps_oi, ps_coi = get_contract_details(strikes["PE_SELL"], 'PE')
        cs, cs_oi, cs_coi = get_contract_details(strikes["CE_SELL"], 'CE')
        cb, cb_oi, cb_coi = get_contract_details(strikes["CE_BUY"], 'CE')

        net_credit = (ps - pb) + (cs - cb)
        lot_size = 50 if symbol == "NIFTY" else 15

        max_profit = net_credit * lot_size
        max_loss = (width - net_credit) * lot_size
        be_low = strikes['PE_SELL'] - net_credit
        be_high = strikes['CE_SELL'] + net_credit

        spot_input = st.slider("Select Spot Price", int(spot - 3 * width), int(spot + 3 * width), int(spot), step=10)

        payoff_at_spot = (
            max(0, strikes['PE_BUY'] - spot_input) - pb +
            -max(0, strikes['PE_SELL'] - spot_input) + ps +
            -max(0, spot_input - strikes['CE_SELL']) + cs +
            max(0, spot_input - strikes['CE_BUY']) - cb
        ) * lot_size

        st.metric("Max Profit", f"₹{max_profit:.2f}")
        st.metric("Max Loss", f"₹{max_loss:.2f}")
        st.metric("Lower Breakeven", f"₹{be_low:.2f}")
        st.metric("Upper Breakeven", f"₹{be_high:.2f}")
        st.metric(f"P&L at Spot ₹{spot_input}", f"₹{payoff_at_spot:.2f}")

        st.markdown("### Option Leg Details")
        st.markdown(f"- **Buy PE {strikes['PE_BUY']}**: ₹{pb} | OI: {pb_oi} | Chg OI: {pb_coi}")
        st.markdown(f"- **Sell PE {strikes['PE_SELL']}**: ₹{ps} | OI: {ps_oi} | Chg OI: {ps_coi}")
        st.markdown(f"- **Sell CE {strikes['CE_SELL']}**: ₹{cs} | OI: {cs_oi} | Chg OI: {cs_coi}")
        st.markdown(f"- **Buy CE {strikes['CE_BUY']}**: ₹{cb} | OI: {cb_oi} | Chg OI: {cb_coi}")

    except Exception as e:
        st.error(f"Error loading data: {e}")

with col2:
    try:
        st.markdown(f"### Spot Price: ₹{spot}")
        st.markdown(f"### Net Credit: ₹{net_credit:.2f} × {lot_size} = ₹{net_credit * lot_size:.2f}")

        x = np.arange(spot - 3 * width, spot + 3 * width, 1)
        y = []
        for price in x:
            payoff = 0
            payoff += max(0, strikes['PE_BUY'] - price) - pb
            payoff += -max(0, strikes['PE_SELL'] - price) + ps
            payoff += -max(0, price - strikes['CE_SELL']) + cs
            payoff += max(0, price - strikes['CE_BUY']) - cb
            y.append(payoff * lot_size)

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name='Payoff', line=dict(color='blue')))

        fig.add_vline(x=strikes['PE_BUY'], line=dict(color='red', dash='dash'), annotation_text='PE Buy', annotation_position='top left')
        fig.add_vline(x=strikes['PE_SELL'], line=dict(color='green', dash='dash'), annotation_text='PE Sell', annotation_position='top left')
        fig.add_vline(x=strikes['CE_SELL'], line=dict(color='green', dash='dash'), annotation_text='CE Sell', annotation_position='top right')
        fig.add_vline(x=strikes['CE_BUY'], line=dict(color='red', dash='dash'), annotation_text='CE Buy', annotation_position='top right')
        fig.add_vline(x=be_low, line=dict(color='orange', dash='dot'), annotation_text=f'Lower BE: ₹{be_low:.0f}', annotation_position='bottom left')
        fig.add_vline(x=be_high, line=dict(color='orange', dash='dot'), annotation_text=f'Upper BE: ₹{be_high:.0f}', annotation_position='bottom right')

        fig.add_trace(go.Scatter(x=[spot_input], y=[payoff_at_spot], mode='markers+text', name='Selected Spot', text=[f"₹{payoff_at_spot:.0f}"], textposition="top center", marker=dict(color='black', size=10)))

        fig.add_trace(go.Scatter(
            x=np.concatenate([[x[0]], x[x < be_low], [x[x < be_low][-1]]]) if np.any(x < be_low) else [],
            y=np.concatenate([[0], np.array(y)[x < be_low], [0]]) if np.any(x < be_low) else [],
            fill='toself', fillcolor='rgba(255,0,0,0.1)', line=dict(color='rgba(255,0,0,0)'), showlegend=True, name='Max Loss Zone'
        ))
        fig.add_trace(go.Scatter(
            x=np.concatenate([[x[x <= be_high][0]], x[(x >= be_low) & (x <= be_high)], [x[x <= be_high][-1]]]) if np.any((x >= be_low) & (x <= be_high)) else [],
            y=np.concatenate([[0], np.array(y)[(x >= be_low) & (x <= be_high)], [0]]) if np.any((x >= be_low) & (x <= be_high)) else [],
            fill='toself', fillcolor='rgba(0,255,0,0.1)', line=dict(color='rgba(0,255,0,0)'), showlegend=True, name='Max Profit Zone'
        ))

        fig.update_layout(title="Iron Condor Payoff at Expiry",
                          xaxis_title="Underlying Price at Expiry",
                          yaxis_title="P&L (₹)",
                          showlegend=True,
                          height=600)

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Visualization Error: {e}")