from flask import Flask, render_template, request
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(dotenv_path=".env")

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def convert():
    result = None
    error = None

    if request.method == "POST":
        try:
            amount = float(request.form["amount"])
            from_currency = request.form["from_currency"].upper()
            to_currency = request.form["to_currency"].upper()

            # Get API key from .env
            API_KEY = os.getenv("EXCHANGE_API_KEY")
            
            if not API_KEY:
                error = "API key not found. Check your .env file."
            else:
                url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{from_currency}"
                response = requests.get(url)
                data = response.json()

                if "conversion_rates" not in data:
                    error = "Invalid response from exchange rate API."
                elif to_currency not in data["conversion_rates"]:
                    error = "Invalid target currency code."
                else:
                    rate = data["conversion_rates"][to_currency]
                    result = amount * rate

        except ValueError:
            error = "Please enter a valid numeric amount."
        except Exception as e:
            error = f"Unexpected error: {str(e)}"

    # Always return a response
    return render_template("index.html", result=result, error=error)


if __name__ == "__main__":
    app.run(debug=True)
