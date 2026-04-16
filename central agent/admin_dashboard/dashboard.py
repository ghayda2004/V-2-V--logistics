from flask import Flask, render_template
import os

app = Flask(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")


@app.route("/")
def admin_dashboard():
    return render_template("index.html", backend_url=BACKEND_URL)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
