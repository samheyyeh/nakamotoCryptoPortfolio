from flask import Flask, render_template, request, redirect, url_for, session
from ethDashboard import get_eth_holdings
from solanaDashboard import get_sol_holdings
from auth import init_db, log_user
from dotenv import load_dotenv
import os

load_dotenv()
init_db()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session handling

DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD")

@app.route('/', methods=['GET', 'POST'])
def login():
    error = False
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')

        if password == DASHBOARD_PASSWORD:
            session['username'] = username
            log_user(username)
            return redirect(url_for('home'))
        else:
            error = True

    return render_template("login.html", error=error)


@app.route('/dashboard')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template("index.html")


@app.route('/eth', methods=['POST'])
def eth_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    address = request.form.get("address").strip()
    if not address:
        return "No address provided", 400

    data = get_eth_holdings(address)
    return render_template("eth.html", data=data, address=address)

@app.route('/sol', methods=['POST'])
def sol_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    address = request.form.get("address").strip()
    if not address:
        return "No address provided", 400

    data = get_sol_holdings(address)
    return render_template("sol.html", data=data, address=address)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
