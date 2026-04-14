import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import time
from geopy.geocoders import Nominatim, ArcGIS
from geopy.extra.rate_limiter import RateLimiter
from geopy.exc import (
    GeocoderTimedOut,
    GeocoderUnavailable,
    GeocoderServiceError,
    GeocoderRateLimited,
)

# 1) GÃ©ocodeurs
osm = Nominatim(user_agent="delivery_tunis_v1")
arc = ArcGIS(timeout=10)

# Ralentisseurs
geocode_osm = RateLimiter(
    osm.geocode,
    min_delay_seconds=3.0,
    error_wait_seconds=10.0,
    max_retries=1,
    swallow_exceptions=False,
)

geocode_arc = RateLimiter(
    arc.geocode,
    min_delay_seconds=1.0,
    error_wait_seconds=5.0,
    max_retries=1,
    swallow_exceptions=False,
)

# 2) Charger le dataset
df = pd.read_csv(r"C:\Users\User\OneDrive\Documents\GitHub\V-2-V--logistics\central agent\Copie de client_data.csv")

print("Colonnes:", list(df.columns))
print("Nb lignes:", len(df))

_cache_gps = {}


def _try_geocode_osm(query: str):
    return geocode_osm(query, timeout=10, country_codes="tn", limit=1)


def _try_geocode_arc(query: str):
    # ArcGIS ne supporte pas country_codes comme Nominatim
    return geocode_arc(query)


def choisir_service():
    """Choisit un service de gÃ©ocodage qui rÃ©pond (OSM puis ArcGIS)."""
    test_query = "Tunis, Tunisia"

    try:
        loc = _try_geocode_osm(test_query)
        if loc:
            print("Service gÃ©ocodage: Nominatim (OSM)")
            return "osm"
    except GeocoderRateLimited:
        print("Nominatim: rate-limited (429) â€” fallback ArcGIS")
    except Exception as e:
        print("Nominatim indisponible:", repr(e))

    try:
        loc = _try_geocode_arc(test_query)
        if loc:
            print("Service gÃ©ocodage: ArcGIS")
            return "arc"
    except Exception as e:
        print("ArcGIS indisponible:", repr(e))

    return None


def obtenir_gps(adresse, service: str):
    if pd.isna(adresse):
        return None, None

    adresse = str(adresse).strip()
    if not adresse:
        return None, None

    key = adresse.lower()
    if key in _cache_gps:
        return _cache_gps[key]

    query = f"{adresse}, Tunis, Tunisia"

    try:
        if service == "osm":
            location = _try_geocode_osm(query)
        elif service == "arc":
            location = _try_geocode_arc(query)
        else:
            location = None

        if location:
            res = (location.latitude, location.longitude)
            _cache_gps[key] = res
            return res
    except GeocoderRateLimited as e:
        wait_s = (getattr(e, "retry_after", None) or 60) + 1
        print(f"Rate limited (429). Pause {wait_s}s...")
        time.sleep(wait_s)
    except (GeocoderTimedOut, GeocoderUnavailable):
        pass
    except GeocoderServiceError:
        pass

    _cache_gps[key] = (None, None)
    return None, None


adresses = df["Adresse destinataire"].fillna("").astype(str).str.strip()
adresses_non_vides = adresses[adresses != ""]
uniques = pd.unique(adresses_non_vides)

print("Nb adresses non vides:", len(adresses_non_vides))
print("Nb adresses uniques:", len(uniques))

service = choisir_service()

if service is None:
    print("Aucun service de gÃ©ocodage disponible. df_map restera vide.")
else:
    print("GÃ©ocodage en cours...")
    for i, adr in enumerate(uniques, start=1):
        obtenir_gps(adr, service)
        if i % 10 == 0:
            print(f"Progress: {i}/{len(uniques)} adresses gÃ©ocodÃ©es")


def _lat_lon_from_cache(adr):
    adr = str(adr).strip()
    if not adr:
        return None, None
    return _cache_gps.get(adr.lower(), (None, None))


df[["lat", "lon"]] = adresses.apply(lambda x: pd.Series(_lat_lon_from_cache(x)))

df_map = df.dropna(subset=["lat", "lon"]).copy()
print(f"SuccÃ¨s : {len(df_map)} adresses localisÃ©es sur {len(df)}.")

if len(df_map) == 0:
    exemples = uniques[:10].tolist() if len(uniques) else []
    print("Exemples d'adresses (10 premiÃ¨res uniques):", exemples)


def estimer_poids(contenu):
    if pd.isna(contenu) or contenu == "":
        return 0.5

    texte = str(contenu).lower()

    categories = {
        'sac': 1.5,
        'talon': 1.2,
        'chaussures': 1.3,
        'coffret': 2.0,
        'burkini': 0.7,
        'vÃªtements': 0.8,
        'robe': 0.6,
        'accessoires': 0.3,
        'brume': 0.4,
        'makeup': 0.2,
        'maquillage': 0.2,
        'skin care': 0.5,
        'produit': 0.4,
        'casque': 0.5,
        'lunettes': 0.2
    }

    for mot, poids in categories.items():
        if mot in texte:
            return poids

    return 0.5


def is_terrestre_tunis(lat, lon):
    # Boîte englobante
    if not (36.50 <= lat <= 37.00 and 9.80 <= lon <= 10.40):
        return False
    
    # Frontière côtière beaucoup plus stricte pour éviter la mer (du Nord au Sud)
    # Golfe de Tunis au-dessus de Raoued/Gammarth
    if lat >= 36.93 and lon > 10.15: return False          
    if lat >= 36.90 and lon > 10.20: return False          # Nord de la Marsa et Raoued
    
    if 36.85 <= lat < 36.90 and lon > 10.27: return False  # Gammarth / Carthage 
    if 36.80 <= lat < 36.85 and lon > 10.29: return False  # La Goulette
    if 36.75 <= lat < 36.80 and lon > 10.28: return False  # Radès
    if 36.70 <= lat < 36.75 and lon > 10.32: return False  # Ezzahra / Hammam Lif
    if 36.65 <= lat < 36.70 and lon > 10.40: return False  # Borj Cédria
    
    # Sebkhet Ariana (Grand lac au nord de l'aéroport)
    if (36.87 <= lat <= 36.92) and (10.18 <= lon <= 10.26):
        return False

    # Lac de Tunis
    if (36.80 <= lat <= 36.84) and (10.22 <= lon <= 10.28): 
        return False
        
    # Sebkhet Sejoumi (lac au sud ouest de Tunis)
    if (36.73 <= lat <= 36.77) and (10.14 <= lon <= 10.19): 
        return False

    return True


def generer_date_aleatoire(date_base="2025-11-01"):
    heure = random.randint(8, 17)
    minute = random.randint(0, 59)
    seconde = random.randint(0, 59)

    date_obj = datetime.strptime(date_base, "%Y-%m-%d") + timedelta(
        hours=heure, minutes=minute, seconds=seconde
    )
    return date_obj.strftime("%Y-%m-%dT%H:%M:%S+01:00")


def generer_donnees_supp(df_reel, n_points=30):
    if df_reel is None or df_reel.empty:
        return pd.DataFrame()

    nouveaux_colis = []
    
    for k in range(n_points):
        base = df_reel.sample(1).iloc[0]

        for _ in range(50):
            # Augmenté la variation à environ 20-30 km pour bien s'étaler sur tout le Grand Tunis
            lat_v = base["lat"] + np.random.uniform(-0.25, 0.25)
            lon_v = base["lon"] + np.random.uniform(-0.25, 0.25)
            if is_terrestre_tunis(lat_v, lon_v):
                break

        contenu = random.choice(
            ["VÃªtements", "Accessoires", "Chaussures", "Coffret", "Skin Care", "Ã‰lectronique", "Livres"]
        )
        poids = estimer_poids(contenu)

        nouveaux_colis.append(
            {
                "Reference": f"{random.randint(100000000000, 999999999999)}",
                "ExpÃ©diteur": "Boutique",
                "Adresse destinataire": f"Zone {base['Adresse destinataire']}",
                "Contenu": contenu,
                "Poids": poids,
                "Date de crÃ©ation": generer_date_aleatoire(),
                "lat": lat_v,
                "lon": lon_v,
                "Gouvernorat": "Grand Tunis",
                "Statut": random.choice(["En attente", "En cours", "PrÃªt pour livraison"]),
            }
        )

    return pd.DataFrame(nouveaux_colis)


def enrichir_colonnes(df):
    df = df.copy()
    
    poids_num = pd.to_numeric(df["Poids"], errors='coerce').fillna(0.5)
    df["Frais_Livraison_TND"] = (7.0 + (poids_num * 1.5)).round(2)
    
    conditions = [
        poids_num <= 0.5,
        poids_num >= 2.0
    ]
    choices = ["Express", "Basique"]
    df["Priorite"] = np.select(conditions, choices, default="Standard")
    
    df["Mode_Paiement"] = np.random.choice(
        ["Paiement Ã  la livraison", "Carte Bancaire", "Virement"], 
        size=len(df), 
        p=[0.7, 0.2, 0.1]
    )
    
    df["Type_Client"] = np.random.choice(
        ["B2C (Particulier)", "B2B (Professionnel)"], 
        size=len(df), 
        p=[0.85, 0.15]
    )
    
    return df


if __name__ == "__main__":
    df1 = generer_donnees_supp(df_map, 40)  # On génère 40 points très éloignés
    dfc = pd.concat([df_map, df1], ignore_index=True)

    masque_terrestre = dfc.apply(lambda row: is_terrestre_tunis(row["lat"], row["lon"]), axis=1)
    dfc = dfc[masque_terrestre].copy()

    dfc = enrichir_colonnes(dfc)

    if "Date de crÃ©ation" in dfc.columns:
        dfc["Date de crÃ©ation"] = dfc["Date de crÃ©ation"].fillna(generer_date_aleatoire())
        dfc = dfc.sort_values(by="Date de crÃ©ation")

    print(f"Total des commandes ajustÃ© Ã  : {len(dfc)} lignes.")
    
    # Save to a fixed database (CSV file)
    output_path = r"C:\Users\User\OneDrive\Documents\GitHub\V-2-V--logistics\central agent\fixed_database_large.csv"
    dfc.to_csv(output_path, index=False)
    print(f"Base de donnÃ©es fixe sauvegardÃ©e sous : {output_path}")
