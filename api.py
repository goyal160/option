from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import urllib3

app = Flask(__name__)
CORS(app)

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/option-chain"
}

@app.route('/')
def index():
    return "✅ NSE Option Chain API is running."

@app.route('/get_option_chain', methods=['GET'])
def get_option_chain():
    symbol = request.args.get('symbol', 'NIFTY').upper()
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"

    try:
        session = requests.Session()
        session.headers.update(NSE_HEADERS)

        # Step 1: Set cookies via NSE homepage
        session.get("https://www.nseindia.com", timeout=5, verify=False)

        # Step 2: Get live option chain
        response = session.get(url, timeout=10, verify=False)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": f"NSE returned status code {response.status_code}"}), 500

    except Exception as e:
        return jsonify({"error": f"Failed to fetch data: {str(e)}"}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)