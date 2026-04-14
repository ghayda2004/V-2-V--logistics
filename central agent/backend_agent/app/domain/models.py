from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Driver(Base):
    __tablename__ = 'drivers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    status = Column(String(50), default='OFF_DUTY') 
    current_lat = Column(Float, nullable=True)
    current_lon = Column(Float, nullable=True)
    shift_start = Column(DateTime, nullable=True)
    
    packages = relationship('Package', back_populates='driver')

class Package(Base):
    __tablename__ = 'packages'
    
    id = Column(Integer, primary_key=True)
    destination_address = Column(String(255), nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lon = Column(Float, nullable=False)
    status = Column(String(50), default='PENDING') 
    delivery_time = Column(DateTime, nullable=True)
    revenue = Column(Float, nullable=False, default=0.0)
    
    driver_id = Column(Integer, ForeignKey('drivers.id'), nullable=True)
    driver = relationship('Driver', back_populates='packages')

class Livraison(Base):
    __tablename__ = 'livraisons'

    id = Column(Integer, primary_key=True, autoincrement=True)
    reference = Column(String(50), nullable=True)
    adresse_depart = Column(String(255), default='Entrepôt', nullable=False)
    adresse_destinataire = Column(String(255), nullable=True)
    contenu = Column(String(500), nullable=True)
    poids = Column(Float, nullable=True)
    statut = Column(String(100), nullable=True)
    gouvernorat = Column(String(100), nullable=True)
    prix_total = Column(Float, nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    expediteur = Column(String(255), nullable=True)
    date_creation = Column(String(100), nullable=True)
    frais_livraison_tnd = Column(Float, nullable=True)
    priorite = Column(String(50), nullable=True)
    mode_paiement = Column(String(100), nullable=True)
    type_client = Column(String(100), nullable=True)

# --- Schémas Pydantic pour validation JSON FastAPI ---

class PackageDetail(BaseModel):
    package_id: str
    action_type: str # "PICKUP" ou "DROPOFF"
    address: str
    weight_kg: float
    time_window: str # Ex: "10:00-12:00"

class RouteStop(BaseModel):
    stop_id: int
    lat: float
    lon: float
    stop_type: str  # "DELIVERY", "PICKUP", "BREAK"
    eta: str
    packages: List[PackageDetail] = []
    instructions: Optional[str] = None

class MissionSchema(BaseModel):
    vehicle_id: str
    driver_name: str
    shift_start: str
    mandatory_break_time: str
    total_distance_km: float
    planned_stops: List[RouteStop]


