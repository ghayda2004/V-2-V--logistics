# V-2-V Logistics

A delivery route optimization and visualization system for the **Grand Tunis** area (Tunisia). This project geocodes customer delivery addresses, augments real data with synthetic points, and generates optimized delivery maps using Google Maps and KML exports.

## Features

- **Address Geocoding** — resolves delivery addresses to GPS coordinates using Nominatim (OpenStreetMap) with an ArcGIS fallback
- **Data Augmentation** — generates additional synthetic delivery points around real locations to reach target coverage
- **Delivery Enrichment** — automatically computes delivery fees, priority levels, payment modes, and client types
- **Map Exports** — produces three outputs:
  - `livraisons_mymaps.kml` — importable into Google My Maps
  - `google_maps_links.html` — a list of direct Google Maps links for each stop
  - `google_maps_livraisons.html` — an interactive Google Maps page (requires an API key) or a no-key instructions page
- **Route Optimization** — uses Google OR-Tools for vehicle routing and delivery scheduling

## Project Structure

```
central agent/
├── delevery allocation.ipynb   # Main notebook: geocoding, augmentation, mapping, routing
├── Copie de client_data.csv    # Real delivery dataset
├── google_maps_links.html      # Generated: per-stop Google Maps links
├── google_maps_livraisons.html # Generated: interactive map page
├── livraisons_mymaps.kml       # Generated: KML file for Google My Maps import
├── package-lock.json           # Node.js dependency lock (tooling)
├── .gitignore
└── .gitattributes
```

## Dataset

`Copie de client_data.csv` contains real delivery records with the following columns:

| Column | Description |
|---|---|
| `Reference` | Unique shipment ID |
| `Expéditeur` | Sender name |
| `Adresse destinataire` | Delivery address |
| `Contenu` | Package contents |
| `Poids` | Weight (kg) |
| `Date de création` | Order creation timestamp |
| `Statut` | Delivery status (e.g., *Livrée*, *Retour livrée*) |
| `Gouvernorat` | Region (e.g., *Grand Tunis*) |
| `Prix Total` | Total price (TND) |

## Requirements

- Python 3.8+
- Jupyter Notebook or JupyterLab

Install Python dependencies:

```bash
pip install pandas numpy geopy folium scikit-learn ortools
```

## Usage

1. Place your delivery CSV file in the `central agent/` directory (or update the file path in the notebook).
2. Open the notebook:
   ```bash
   jupyter notebook "central agent/delevery allocation.ipynb"
   ```
3. Run all cells in order. The notebook will:
   - Geocode delivery addresses (requires an internet connection)
   - Generate and clean delivery data
   - Export the three map files listed above

### Optional: Google Maps API Key

For a fully interactive embedded map, set your key in the notebook:

```python
GOOGLE_MAPS_API_KEY = "AIza...."
```

Without a key, the notebook generates a static instructions page and a KML file you can import into [Google My Maps](https://www.google.com/mymaps).

## Delivery Fee Calculation

Fees are computed automatically per shipment:

```
Frais de livraison = 7.0 TND (base) + 1.5 TND × Poids (kg)
```

## Priority Levels

| Weight | Priority |
|---|---|
| ≤ 0.5 kg | Express |
| 0.5 – 2.0 kg | Standard |
| ≥ 2.0 kg | Basique |

## Coverage Area

The system focuses on the **Grand Tunis** metropolitan area (approximately 36.50°N–37.00°N, 9.80°E–10.40°E), with built-in filters to exclude sea and lake coordinates.
