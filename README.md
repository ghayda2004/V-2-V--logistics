# V2V Logistics - Pipeline Orchestrator

A production-ready pipeline system for intelligent vehicle-to-vehicle delivery routing, optimization, and profitability analysis.

## Architecture Overview

The system is built with **clean separation of concerns**, following the single-responsibility principle:

### Modules

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE ORCHESTRATOR                      │
│                      (pipeline.py)                            │
│  Coordinates all steps: data → routing → analysis → storage  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │              │
   ┌────▼────┐    ┌────▼────┐   ┌────▼────┐   ┌────▼──────┐
   │ DATA    │    │ ROUTING  │   │PROFITA-│   │ DASHBOARD │
   │ READER  │    │          │   │ BILITY │   │   API     │
   │         │    │          │   │        │   │           │
   │ .get_   │    │ .get_ors │   │.calc_  │   │ /routes   │
   │ orders()│    │ _distance│   │profit  │   │ /driver   │
   │         │    │          │   │        │   │           │
   └────┬────┘    │ .optimize│   └────┬───┘   └───────────┘
        │         │ _routes()│        │
     CSV/DB       │          │        │ 
                  └────┬─────┘   PostgreSQL
                       │
                  ORS API/
                  Haversine
```

### Module Responsibilities

1. **`data_reader.py`** - Data Access Layer
   - Fetches orders and drivers from PostgreSQL or CSV
   - Provides automatic fallback between sources
   - Returns unified data format

2. **`routing.py`** - Distance & Route Optimization
   - Calculates distance matrices (ORS API + Haversine fallback)
   - Optimizes route assignments using greedy nearest-neighbor
   - Returns optimized routes with distance/duration metrics

3. **`profitability.py`** - Financial Analysis
   - Calculates revenue, costs, and profit margins per route
   - Computes profit scores (0-100 scale)
   - Generates aggregate summary statistics

4. **`pipeline.py`** - Main Orchestrator
   - Executes 6-step workflow
   - Handles errors gracefully at each step
   - Persists results to PostgreSQL
   - Provides comprehensive logging

5. **`dashboard_api.py`** - Read-Only FastAPI
   - Manager dashboard: `/routes` (all routes with metrics)
   - Route detail: `/routes/{route_id}` (complete breakdown)
   - Driver dashboard: `/driver/{driver_id}/route` (assigned route only)

## Installation

```bash
# Clone repository
git clone https://github.com/ghayda2004/V-2-V--logistics.git
cd V-2-V--logistics

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/v2v_logistics

# CSV Fallback Data
CSV_ORDERS_PATH=./data/orders.csv
CSV_DRIVERS_PATH=./data/drivers.csv

# OpenRouteService API (optional)
ORS_API_KEY=your_ors_api_key_here

# Profitability Rates (TND - Tunisian Dinar)
FUEL_RATE_PER_KM=0.15
HOURLY_RATE=8.5
HANDLING_COST_PER_STOP=1.5

# API
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

## Usage

### Run Complete Pipeline

```bash
# Use best available source (DB, then CSV fallback)
python pipeline.py

# Force CSV source
python pipeline.py --source csv

# Force DB source
python pipeline.py --source db

# Dry run (no database persistence)
python pipeline.py --dry-run
```

**Output Example:**
```
============================================================
STEP 1: Fetch orders and drivers
============================================================
✓ Loaded 27 orders and 5 drivers from auto

============================================================
STEP 2: Calculate distance matrix
============================================================
✓ Distance matrix calculated (ors source)

============================================================
STEP 3: Optimize routes
============================================================
✓ Generated 5 optimized routes

============================================================
STEP 4: Calculate profitability metrics
============================================================
✓ Profitability calculated - Total profit: 845.50TND, Margin: 32.4%

============================================================
STEP 5: Persist to database
============================================================
✓ Persisted 5 routes and 25 stops to database

============================================================
STEP 6: Summary Report
============================================================
Total Routes: 5
Total Revenue: 2609.00 TND
Total Cost: 1763.50 TND
Total Profit: 845.50 TND
Average Margin: 32.4%
Average Profit Score: 75.3/100
Profitable Routes: 5/5
```

### Run Dashboard API

```bash
python dashboard_api.py
```

Server starts on `http://localhost:8000`

**API Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Manager Dashboard

```
GET /routes
  Query parameters:
    - skip=0, limit=100
    - profit_min=0, profit_max=100
  
  Response: [RouteSummary]
  {
    route_id, driver_id, distance_km, duration_minutes,
    stops_count, total_weight_kg, utilization_pct,
    total_revenue, profit_score, margin_pct
  }

GET /routes/{route_id}
  Response: RouteDetail
  {
    route_id, driver_id, distance_km, duration_minutes,
    stops_count, total_weight_kg, utilization_pct,
    stops: [Stop],
    profitability: {total_revenue, total_cost, margin_pct, ...}
  }
```

### Driver Dashboard

```
GET /driver/{driver_id}/route
  Response: RouteDetail | null
  (Returns only assigned route with all stops)
```

### Health Check

```
GET /health
  Response: {status, timestamp, database}
```

## Pipeline Workflow

### Step 1: Data Retrieval
```python
orders, drivers = data_reader.get_orders(), data_reader.get_drivers()
# Returns unified format regardless of source (DB or CSV)
```

### Step 2: Distance Matrix
```python
distance_matrix = routing.get_ors_distance_matrix(locations)
# OpenRouteService API with Haversine fallback
# Returns: {distances: [[...]], durations: [[...]], source: "ors"|"haversine"}
```

### Step 3: Route Optimization
```python
routes = routing.optimize_routes(orders, drivers, distance_matrix)
# Greedy nearest-neighbor assignment with capacity constraints
# Returns: [{route_id, driver_id, orders, distance_km, duration_minutes, ...}]
```

### Step 4: Profitability Analysis
```python
enriched_routes = profitability.calculate_profitability(routes)
# Calculates: revenue, costs (fuel, labor, handling), margin, profit_score
# Returns: routes + {total_revenue, total_cost, margin_pct, profit_score, breakdown}
```

### Step 5: Database Persistence
```python
# Creates/updates:
# - routes (route headers)
# - route_stops (order assignments)
# - route_profitability (financial metrics)
```

### Step 6: Summary & Reporting
```python
summary = profitability.get_summary(enriched_routes)
# Returns: {total_routes, total_profit, avg_margin_pct, profitable_routes, ...}
```

## Database Schema

### Orders Table
```sql
CREATE TABLE orders (
  id VARCHAR PRIMARY KEY,
  reference VARCHAR,
  address VARCHAR,
  latitude FLOAT,
  longitude FLOAT,
  weight FLOAT,
  revenue FLOAT,
  created_at TIMESTAMP
);
```

### Drivers Table
```sql
CREATE TABLE drivers (
  id VARCHAR PRIMARY KEY,
  name VARCHAR,
  depot_latitude FLOAT,
  depot_longitude FLOAT,
  vehicle_capacity_kg FLOAT,
  daily_hours FLOAT
);
```

### Routes Table
```sql
CREATE TABLE routes (
  id VARCHAR PRIMARY KEY,
  driver_id VARCHAR REFERENCES drivers(id),
  distance_km FLOAT,
  duration_minutes FLOAT,
  stops INT,
  total_weight_kg FLOAT,
  utilization_pct FLOAT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Route Stops Table
```sql
CREATE TABLE route_stops (
  route_id VARCHAR REFERENCES routes(id),
  order_id VARCHAR REFERENCES orders(id),
  sequence INT,
  created_at TIMESTAMP,
  PRIMARY KEY (route_id, order_id)
);
```

### Route Profitability Table
```sql
CREATE TABLE route_profitability (
  route_id VARCHAR PRIMARY KEY REFERENCES routes(id),
  total_revenue FLOAT,
  total_cost FLOAT,
  gross_margin FLOAT,
  margin_pct FLOAT,
  profit_score FLOAT,
  fuel_cost FLOAT,
  labor_cost FLOAT,
  handling_cost FLOAT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

## Cost Calculation Formula

For each route:

```
Fuel Cost = distance_km × FUEL_RATE_PER_KM
Labor Cost = (duration_minutes / 60) × HOURLY_RATE
Handling Cost = stops × HANDLING_COST_PER_STOP

Total Cost = Fuel Cost + Labor Cost + Handling Cost
Gross Margin = Total Revenue - Total Cost
Margin % = (Gross Margin / Total Revenue) × 100
Profit Score = 50 + (Margin % / 2)  [0-100 scale]
```

## Error Handling

All modules include graceful error handling:

- **Data Reader**: Falls back CSV if PostgreSQL unavailable
- **Routing**: Falls back to Haversine if ORS API fails
- **Pipeline**: Logs errors at each step, continues if possible
- **Dashboard API**: Returns 404/500 with descriptive messages

## Logging

Logs are controlled by `LOG_LEVEL` in `.env`:

```
INFO   - Normal operation steps
WARNING - Non-fatal issues (fallbacks)
ERROR  - Failures that stop execution
DEBUG  - Detailed internal state (if enabled)
```

## Performance Considerations

- **Data Fetching**: O(n) where n = number of orders/drivers
- **Distance Matrix**: O(n²) API calls (optimized with batching)
- **Route Optimization**: O(n × m) where m = number of drivers (greedy heuristic)
- **Profitability**: O(n) single pass calculation
- **Database Persistence**: Bulk insert optimized

For 1000 orders and 50 drivers:
- Expected pipeline runtime: 30-60 seconds (depends on ORS API latency)
- Database operations: <5 seconds

## Development

### Testing Pipeline Locally

```python
from pipeline import run_pipeline
from data_reader import get_orders, get_drivers

# Load sample data
orders = get_orders("csv")
drivers = get_drivers("csv")

# Run full pipeline
result = run_pipeline(source="csv", dry_run=True)
print(result["summary"])
```

### Testing API Locally

```bash
# Start API
python dashboard_api.py

# Test endpoints
curl http://localhost:8000/routes
curl http://localhost:8000/routes/route_123
curl http://localhost:8000/driver/driver_1/route
```

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -am "Add feature"`
3. Push to branch: `git push origin feature/your-feature`
4. Open Pull Request

## License

This project is private and internal to V2V Logistics.

## Support

For issues or questions:
- Check logs in `LOG_LEVEL=DEBUG` mode
- Verify `.env` configuration
- Ensure database connectivity
- Check ORS API key validity

---

**Last Updated**: May 5, 2026  
**Version**: 1.0.0
