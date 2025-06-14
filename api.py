from flask import Flask, jsonify, request
from flask_cors import CORS
import requests, os

app = Flask(__name__)
CORS(app)  # Allow all origins; tighten later if needed

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/90.0.4430.93 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nseindia.com/"
}

@app.route('/option_chain', methods=['GET'])
def option_chain():
    symbol = request.args.get('symbol', 'NIFTY')
    url = f'https://www.nseindia.com/api/option-chain-indices?symbol={symbol.upper()}'
    
    session = requests.Session()
    session.headers.update(NSE_HEADERS)

    try:
        # Step 1: Get homepage to set cookies
        session.get("https://www.nseindia.com", timeout=5)

        # Step 2: Get data
        response = session.get(url, timeout=10, verify=False)
        data = response.json()

        if 'records' in data:
            return jsonify(data)
        else:
            return jsonify({"error": "Invalid response format from NSE"}), 500

    except Exception as e:
        return jsonify({"error": f"Failed to fetch data: {str(e)}"}), 500

# Add this block at the bottom
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)