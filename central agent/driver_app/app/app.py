from flask import Flask, render_template, request, redirect, session, url_for
from functools import wraps
import requests
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_livraison'

# URL du backend agent (FastAPI par défaut sur 8000)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'driver_name' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        
        try:
            res = requests.post(f"{BACKEND_URL}/driver/login", json={"name": username, "password": password}, timeout=10)
            if res.status_code == 200:
                data = res.json()
                session['driver_id'] = data['id']
                session['driver_name'] = data['name']
                return redirect(url_for('driver_dashboard'))
            else:
                detail = None
                try:
                    payload = res.json()
                    if isinstance(payload, dict):
                        detail = payload.get('detail')
                except ValueError:
                    detail = None

                if not detail:
                    detail = res.text.strip() or "Erreur inconnue"

                if res.status_code >= 500:
                    error = f"Erreur serveur ({res.status_code}) : {detail}"
                elif res.status_code == 401:
                    error = "Nom d'utilisateur ou mot de passe incorrect."
                else:
                    error = f"Erreur ({res.status_code}) : {detail}"
        except requests.exceptions.RequestException:
            error = "Impossible de contacter l'Agent Central."
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('driver_name', None)
    session.pop('driver_id', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def driver_dashboard():
    # Récupérer les colis et le schéma
    try:
        driver_id = session.get('driver_id')
        response = requests.get(f"{BACKEND_URL}/route/driver/{driver_id}", timeout=30)
        response.raise_for_status() 
        mission_data = response.json()
        error_msg = None
    except requests.exceptions.RequestException as e:
        mission_data = None
        error_msg = f"Impossible de contacter l'Agent Central. L'API est injoignable ou désactivée. ({str(e)})"

    return render_template('index.html', driver_name=session.get('driver_name'), mission=mission_data, error=error_msg)

@app.route('/mission')
@login_required
def fetch_mission():
    try:
        # Appel à l'API de l'agent central (FastAPI) pour récupérer le schéma du véhicule 1
        driver_id = session.get('driver_id')
        response = requests.get(f"{BACKEND_URL}/route/driver/{driver_id}", timeout=30)
        response.raise_for_status() 
        mission_data = response.json()
        error_msg = None
    except requests.exceptions.RequestException as e:
        mission_data = None
        error_msg = f"Impossible de contacter l'Agent Central. L'API est injoignable ou désactivée. ({str(e)})"
        
    return render_template('mission.html', mission=mission_data, error=error_msg, driver_name=session.get('driver_name'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)