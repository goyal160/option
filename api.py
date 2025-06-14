from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/option_chain/<symbol>')
def get_option_chain(symbol):
    try:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol.upper()}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://www.nseindia.com"
        }
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)