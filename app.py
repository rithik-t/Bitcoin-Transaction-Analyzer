from flask import Flask, request, jsonify, render_template
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Function to get Bitcoin transaction details using Blockstream API
def get_transaction(txid):
    url = f"https://blockstream.info/api/tx/{txid}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise error for bad responses (4xx, 5xx)
        data = response.json()

        # Extract sender addresses
        sender_addresses = set()
        total_input = 0
        for vin in data.get("vin", []):
            if "prevout" in vin and "scriptpubkey_address" in vin["prevout"]:
                sender_addresses.add(vin["prevout"]["scriptpubkey_address"])
                total_input += vin["prevout"]["value"]

        # Extract receiver addresses
        receiver_addresses = set()
        total_output = 0
        for vout in data.get("vout", []):
            if "scriptpubkey_address" in vout:
                receiver_addresses.add(vout["scriptpubkey_address"])
                total_output += vout["value"]

        # Fetch Bitcoin price in USD
        btc_price = get_btc_price()

        result = {
            "Transaction ID": data.get("txid"),
            "Block Height": data.get("status", {}).get("block_height", "Unconfirmed"),
            "Total BTC Transferred": total_output / 100000000,  # Convert satoshis to BTC
            "Total Input BTC": total_input / 100000000,
            "Total Output BTC": total_output / 100000000,
            "Fees (BTC)": data.get("fee", 0) / 100000000,
            "Sender Addresses": list(sender_addresses),
            "Receiver Addresses": list(receiver_addresses),
            "Timestamp": data.get("status", {}).get("block_time", "Pending"),
            "BTC Price (USD)": btc_price
        }
        return result

    except requests.exceptions.Timeout:
        return {"error": "API request timed out. Try again later."}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP Error: {e.response.status_code}"}
    except requests.exceptions.RequestException:
        return {"error": "Failed to connect to API. Check your internet or API status."}
    except Exception as e:
        return {"error": f"Invalid Transaction ID or API issue: {str(e)}"}

# Function to get the current BTC price from CoinGecko API
def get_btc_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["bitcoin"]["usd"]
    except:
        return "Price unavailable"

# Home route to render HTML page
@app.route('/')
def home():
    return render_template("index.html")

# API endpoint to fetch transaction details
@app.route('/analyze', methods=['POST'])
def analyze():
    txid = request.form.get('txid')  # Get transaction ID from form
    if not txid:
        return jsonify({"error": "No transaction ID provided"})
    
    result = get_transaction(txid)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
