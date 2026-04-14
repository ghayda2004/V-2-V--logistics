import os
import sys
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

# Ajout du chemin parent pour import absolu via sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.domain.models import Base, Driver, Package, MissionSchema, RouteStop, PackageDetail, Livraison
from app.services.profitability import calculate_net_profit
from app.services.routing import get_ors_distance_matrix, optimize_routes
from sqlalchemy import create_engine
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

# --- Nouvelle Route: Schéma de mission du véhicule 1 ---

@app.get("/api/v1/route/vehicle1", response_model=MissionSchema)
def get_vehicle_mission():
    """
    Retourne le schéma de mission dynamique pour le véhicule 1.
    Les objets retournés sont automatiquement validés par Pydantic (MissionSchema).
    """
    db = SessionLocal()
    try:
        # 1. Fetch data from DB
        livraisons = db.query(Livraison).filter(Livraison.lat.isnot(None), Livraison.lon.isnot(None)).all()
        
        if not livraisons:
            raise HTTPException(status_code=404, detail="No valid livraisons found in the database.")
            
        # 2. Prepare coordinates for routing (Start with a virtual depot at the first stop or a fixed location)
        # Let's use a fixed depot for Tunis as an example
        depot = (36.8065, 10.1815) # Tunis center (lat, lon)
        
        locations = [depot]
        for liv in livraisons:
            locations.append((liv.lat, liv.lon))
            
        # 3. Get Distance Matrix
        matrix = get_ors_distance_matrix(locations)
        if not matrix:
            raise HTTPException(status_code=500, detail="Failed to get distance matrix from routing service.")
            
        # 4. Optimize Routes
        # We assume 1 vehicle for this endpoint
        routes_summary = optimize_routes(matrix, num_vehicles=1, depot_index=0)
        if not routes_summary or not routes_summary.get('routes') or 0 not in routes_summary['routes']:
            raise HTTPException(status_code=500, detail="Route optimization failed.")
            
        optimized_route_indices = routes_summary['routes'][0]['path_indices']
        total_distance = routes_summary['routes'][0]['path_distance_m'] / 1000.0
        
        # 5. Build the MissionSchema
        planned_stops = []
        
        # Depot Pickup
        planned_stops.append(
            RouteStop(
                stop_id=0,
                lat=depot[0],
                lon=depot[1],
                stop_type="PICKUP",
                eta=datetime.now().strftime("%Y-%m-%dT%H:00:00Z"), # Mocked ETA
                packages=[
                    PackageDetail(
                        package_id="DEPOT-PICKUP",
                        action_type="PICKUP",
                        address="Entrepôt Central",
                        weight_kg=0.0,
                        time_window="08:00-09:00"
                    )
                ],
                instructions="Chargement initial"
            )
        )
        
        # Iterate through the optimized indices (excluding the start and end depot 0)
        for i, node_index in enumerate(optimized_route_indices[1:-1]):
            # node_index - 1 because depot is index 0 in locations, and livraisons is 0-indexed
            liv = livraisons[node_index - 1] 
            
            planned_stops.append(
                RouteStop(
                    stop_id=i+1,
                    lat=liv.lat,
                    lon=liv.lon,
                    stop_type="DELIVERY",
                    eta=datetime.now().strftime("%Y-%m-%dT%H:00:00Z"), # Mock ETA
                    packages=[
                        PackageDetail(
                            package_id=str(liv.reference) if liv.reference else f"LIV-{liv.id}",
                            action_type="DROPOFF",
                            address=str(liv.adresse_destinataire),
                            weight_kg=liv.poids if liv.poids else 0.0,
                            time_window="09:00-18:00"
                        )
                    ],
                    instructions=f"Client: {liv.type_client}" if liv.type_client else "Aucune instruction"
                )
            )

        return MissionSchema(
            vehicle_id="V_1",
            driver_name="Chauffeur 1",
            shift_start=datetime.now().isoformat(),
            mandatory_break_time=datetime.now().isoformat(),
            total_distance_km=total_distance,
            planned_stops=planned_stops
        )
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

