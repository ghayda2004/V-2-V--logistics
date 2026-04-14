import sys
import os
import pandas as pd
from sqlalchemy.orm import sessionmaker

# Ajouter le backend agent au sys.path pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend_agent')))

# Importer vos configs et modèles existants
from app.core.config import settings
from app.domain.models import Base, Livraison
from sqlalchemy import Column, Integer, String, Float, create_engine

# Connexion DB
engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def run_import():
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'fixed_database.csv')
    print(f"Lecture du CSV depuis: {csv_path} ...")
    
    # Lecture Pandas (on gère doucement les accents)
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    # S'assurer que la table est créée dans la BDD (crée si elle n'existe pas)
    Base.metadata.create_all(engine)
    
    # Nettoyer d'abord si on re-run le script
    session.query(Livraison).delete()
    print("Table livraisons nettoyée pour l'import frais.")

    # Transformer le DF Pandas en liste de dictionnaires pour SQLAlchemy
    count = 0
    records = []
    
    for _, row in df.iterrows():
        # Traitement léger des noms de colonnes mal encodées (ExpÃ©diteur -> Expediteur)
        expediteur = row.get("ExpÃ©diteur", row.get("Expéditeur", ""))
        date_crea = row.get("Date de crÃ©ation", row.get("Date de création", ""))

        record = Livraison(
            reference=str(row.get('Reference', '')),
            adresse_depart="Entrepôt", # L'adresse par défaut ajoutée !!
            adresse_destinataire=str(row.get('Adresse destinataire', '')),
            contenu=str(row.get('Contenu', '')),
            poids=float(row.get('Poids', 0.0)) if pd.notnull(row.get('Poids')) else None,
            statut=str(row.get('Statut', '')),
            gouvernorat=str(row.get('Gouvernorat', '')),
            prix_total=float(row.get('Prix Total', 0.0)) if pd.notnull(row.get('Prix Total')) else None,
            lat=float(row.get('lat', 0.0)) if pd.notnull(row.get('lat')) else None,
            lon=float(row.get('lon', 0.0)) if pd.notnull(row.get('lon')) else None,
            expediteur=str(expediteur),
            date_creation=str(date_crea),
            frais_livraison_tnd=float(row.get('Frais_Livraison_TND', 0.0)) if pd.notnull(row.get('Frais_Livraison_TND')) else None,
            priorite=str(row.get('Priorite', '')),
            mode_paiement=str(row.get('Mode_Paiement', '')),
            type_client=str(row.get('Type_Client', ''))
        )
        records.append(record)
        count += 1
        
        # Batch commit every 100
        if count % 100 == 0:
            session.add_all(records)
            session.commit()
            records = []
            print(f"[{count}] lignes importées...")
            
    # Commit final du reste
    if records:
        session.add_all(records)
        session.commit()
        
    print(f"Terminé ! {count} livraisons importées dans la BDD PostgreSQL avec succès.")
    session.close()

if __name__ == '__main__':
    run_import()