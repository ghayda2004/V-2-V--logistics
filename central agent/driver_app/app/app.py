from flask import Flask, render_template
import requests
import os

app = Flask(__name__)

# URL du backend agent (FastAPI par défaut sur 8000)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")

@app.route('/')
def driver_dashboard():
    return render_template('index.html')

@app.route('/mission')
def fetch_mission():
    try:
        # Appel à l'API de l'agent central (FastAPI) pour récupérer le schéma du véhicule 1
        response = requests.get(f"{BACKEND_URL}/route/vehicle1", timeout=30)
        response.raise_for_status() 
        mission_data = response.json()
        error_msg = None
    except requests.exceptions.RequestException as e:
        mission_data = None
        error_msg = f"Impossible de contacter l'Agent Central. L'API est injoignable ou désactivée. ({str(e)})"
        
    return render_template('mission.html', mission=mission_data, error=error_msg)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)