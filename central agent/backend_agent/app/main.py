import os
import sys
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

# Ajout du chemin parent pour import absolu via sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.domain.models import Base, Driver, Package, MissionSchema, RouteStop, PackageDetail, Livraison
from app.services.profitability import calculate_net_profit
from app.services.routing import get_ors_matrices, optimize_routes
from sqlalchemy import create_engine, func, String, cast
from sqlalchemy.orm import sessionmaker

# Configuration SQLAlchemy standard pour FastAPI
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Logistics Central Agent API")

# On autorise les requêtes (appels API) venant des différentes interfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Surcharge la création des tables au démarrage
    Base.metadata.create_all(bind=engine)

class LoginRequest(BaseModel):
    name: str
    password: str

class DriverCreate(BaseModel):
    name: str
    password: str


@app.get("/api/v1/drivers")
def list_drivers():
    """Retourne la liste des chauffeurs pour les interfaces (admin, dispatch, etc.)."""
    db = SessionLocal()
    try:
        drivers = db.query(Driver).order_by(Driver.id.asc()).all()
        return [
            {
                "id": d.id,
                "name": d.name,
                "status": d.status,
            }
            for d in drivers
        ]
    finally:
        db.close()

@app.post("/api/v1/drivers")
def create_driver(driver: DriverCreate = Body(...)):
    """ Endpoint pour ajouter un nouveau chauffeur dans la base de données. """
    db = SessionLocal()
    try:
        driver_name = (driver.name or "").strip()
        driver_password = (driver.password or "").strip()
        if not driver_name or not driver_password:
            raise HTTPException(status_code=400, detail="Le nom et le mot de passe sont obligatoires.")

        # Vérifier si le chauffeur existe déjà
        normalized_name = "".join(driver_name.split()).lower()
        existing_driver = (
            db.query(Driver)
            .filter(func.replace(func.lower(func.trim(Driver.name)), " ", "") == normalized_name)
            .first()
        )
        if existing_driver:
            raise HTTPException(status_code=400, detail="Ce chauffeur existe déjà.")
            
        new_driver = Driver(name=driver_name, password=driver_password)
        db.add(new_driver)
        db.commit()
        db.refresh(new_driver)
        return {"message": "Chauffeur créé avec succès", "driver": {"id": new_driver.id, "name": new_driver.name}}
    finally:
        db.close()

@app.post("/api/v1/driver/login")
def login_driver(req: LoginRequest = Body(...)):
    """ Endpoint pour authentifier le chauffeur depuis la base de données. """
    db = SessionLocal()
    try:
        req_name = (req.name or "").strip()
        req_password = (req.password or "").strip()
        if not req_name or not req_password:
            raise HTTPException(status_code=400, detail="Le nom et le mot de passe sont obligatoires.")

        normalized_req_name = "".join(req_name.split()).lower()
        driver = (
            db.query(Driver)
            .filter(
                func.replace(func.lower(func.trim(Driver.name)), " ", "") == normalized_req_name,
                func.trim(cast(Driver.password, String)) == req_password,
            )
            .first()
        )
        if not driver:
            raise HTTPException(status_code=401, detail="Nom d'utilisateur ou mot de passe incorrect.")
        return {"id": driver.id, "name": driver.name, "status": driver.status}
    finally:
        db.close()


def _build_driver_mission(db, driver_id: int) -> MissionSchema:
    """Construit la mission d'un chauffeur en attribuant les livraisons entre chauffeurs via le routing."""
    drivers = db.query(Driver).order_by(Driver.id.asc()).all()
    target_driver = db.query(Driver).filter(Driver.id == driver_id).first()

    if not target_driver:
        raise HTTPException(status_code=404, detail="Chauffeur introuvable.")
    if not drivers:
        raise HTTPException(status_code=404, detail="Aucun chauffeur disponible.")

    livraisons = db.query(Livraison).filter(Livraison.lat.isnot(None), Livraison.lon.isnot(None)).all()
    if not livraisons:
        raise HTTPException(status_code=404, detail="Aucune livraison valide trouvée.")

    # Depot central fixe (Tunis)
    depot = (36.8065, 10.1815)
    locations = [depot] + [(liv.lat, liv.lon) for liv in livraisons]
    distance_matrix, duration_matrix = get_ors_matrices(locations)
    if not distance_matrix or not duration_matrix:
        raise HTTPException(status_code=500, detail="Impossible de calculer les matrices ORS.")

    # Multi-vehicle routing: OR-Tools choisit le nombre de véhicules réellement nécessaires
    routes_summary = optimize_routes(
        distance_matrix=distance_matrix,
        duration_matrix=duration_matrix,
        num_vehicles=len(drivers),
        depot_index=0,
        max_distance=180000,
        max_route_duration_s=9 * 3600,
    )
    if not routes_summary:
        raise HTTPException(status_code=500, detail="Route optimization failed.")

    # Mapping routes utilisées -> chauffeurs (indépendant des slots internes OR-Tools)
    assigned_nodes_by_driver_id = {d.id: [] for d in drivers}
    route_metrics_by_driver_id = {
        d.id: {"distance_m": 0, "duration_s": 0} for d in drivers
    }

    used_routes = [routes_summary["routes"][k] for k in sorted(routes_summary.get("routes", {}).keys())]
    for idx, vehicle_route in enumerate(used_routes):
        if idx >= len(drivers):
            break
        drv = drivers[idx]
        assigned_nodes = [node for node in vehicle_route.get("path_indices", []) if node != 0]
        assigned_nodes_by_driver_id[drv.id] = assigned_nodes
        route_metrics_by_driver_id[drv.id] = {
            "distance_m": int(vehicle_route.get("path_distance_m", 0)),
            "duration_s": int(vehicle_route.get("path_duration_s", 0)),
        }

    assigned_nodes = assigned_nodes_by_driver_id.get(target_driver.id, [])

    # Construction des arrêts mission du chauffeur ciblé
    planned_stops = [
        RouteStop(
            stop_id=0,
            lat=depot[0],
            lon=depot[1],
            stop_type="PICKUP",
            eta=datetime.now().strftime("%Y-%m-%dT%H:00:00Z"),
            packages=[
                PackageDetail(
                    package_id="DEPOT-PICKUP",
                    action_type="PICKUP",
                    address="Entrepôt Central",
                    weight_kg=0.0,
                    time_window="08:00-09:00",
                )
            ],
            instructions="Chargement initial",
        )
    ]

    for i, node_index in enumerate(assigned_nodes):
        liv = livraisons[node_index - 1]
        planned_stops.append(
            RouteStop(
                stop_id=i + 1,
                lat=liv.lat,
                lon=liv.lon,
                stop_type="DELIVERY",
                eta=datetime.now().strftime("%Y-%m-%dT%H:00:00Z"),
                packages=[
                    PackageDetail(
                        package_id=str(liv.reference) if liv.reference else f"LIV-{liv.id}",
                        action_type="DROPOFF",
                        address=str(liv.adresse_destinataire),
                        weight_kg=liv.poids if liv.poids else 0.0,
                        time_window="09:00-18:00",
                    )
                ],
                instructions=f"Client: {liv.type_client}" if liv.type_client else "Aucune instruction",
            )
        )

    total_distance_m = route_metrics_by_driver_id[target_driver.id]["distance_m"]

    return MissionSchema(
        vehicle_id=f"V_{target_driver.id}",
        driver_name=target_driver.name,
        shift_start=datetime.now().isoformat(),
        mandatory_break_time=datetime.now().isoformat(),
        total_distance_km=round(total_distance_m / 1000.0, 2),
        planned_stops=planned_stops,
    )


@app.get("/api/v1/route/driver/{driver_id}", response_model=MissionSchema)
def get_driver_mission(driver_id: int):
    db = SessionLocal()
    try:
        return _build_driver_mission(db, driver_id)
    finally:
        db.close()

# --- Nouvelle Route: Schéma de mission du véhicule 1 ---

@app.get("/api/v1/route/vehicle1", response_model=MissionSchema)
def get_vehicle_mission():
    """Compatibilité: retourne la mission du premier chauffeur enregistré."""
    db = SessionLocal()
    try:
        first_driver = db.query(Driver).order_by(Driver.id.asc()).first()
        if not first_driver:
            raise HTTPException(status_code=404, detail="Aucun chauffeur disponible.")
        return _build_driver_mission(db, first_driver.id)
    finally:
        db.close()

# --- Anciennes Routes (Migrées de Flask) ---

@app.post("/api/v1/driver/shift/start")
def start_shift(data: Dict[str, Any] = Body(...)):
    db = SessionLocal()
    try:
        driver_id = data.get("driver_id")
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        
        if not driver:
            driver = Driver(id=driver_id, name=f"Chauffeur {driver_id}")
            db.add(driver)
            
        driver.status = "ACTIVE"
        driver.shift_start = datetime.now()
        db.commit()
        db.refresh(driver)
        
        return {
            "status": "success", 
            "driver_id": driver.id, 
            "message": "Shift started successfully"
        }
    finally:
        db.close()

@app.post("/api/v1/driver/package/status")
def update_package_status(data: Dict[str, Any] = Body(...)):
    db = SessionLocal()
    try:
        driver_id = data.get("driver_id")
        package_id = data.get("package_id")
        new_status = data.get("status")
        lat = data.get("lat")
        lon = data.get("lon")
        
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        package = db.query(Package).filter(Package.id == package_id).first()
        
        if driver and lat and lon: 
            driver.current_lat = lat
            driver.current_lon = lon
            
        if package:
            package.status = new_status
            if new_status == "DELIVERED":
                package.delivery_time = datetime.now()
                # Recalcul de profit fictif
                profit_data = calculate_net_profit(base_revenue=package.revenue, distance_km=5.0, estimated_time_hours=0.5)
                print(f"[METRIC] Colis {package_id} livré. Profit calculé : {profit_data['net_profit']}€")
                
            db.commit()
            return {"profit_updated": True, "ack": "success", "package_id": package_id}
            
        raise HTTPException(status_code=404, detail="Package not found")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    # Démarre l'API FastAPI sur le port 8000 (standard FastAPI)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

