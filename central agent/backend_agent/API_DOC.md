# Documentation API de l'Agent Central (Backend)

Cette documentation décrit les interactions (contrats REST API) entre l'Agent Central et ses deux clients : **Driver App** (Interface véhicule) et **Admin Dashboard** (Interface gestionnaire).

## 1. Flow du Driver App (Application Véhicule)

### `POST /api/v1/driver/shift/start`
- **Description** : Le chauffeur démarre sa journée, déclenchant le suivi des heures de travail.
- **Request Body** : `{"driver_id": "D123"}`
- **Response** : `{"status": "active", "start_time": "...", "max_shift_hours": 8}`

### `GET /api/v1/driver/route`
- **Description** : Renvoie la route optimisée du chauffeur, mise à jour (Météo/Trafic via Google Maps).
- **Params** : `driver_id=D123`, `lat=...`, `lon=...`
- **Response** : `[{"leg": "A->B", "distance": "5km", "eta": "10mins", "traffic_status": "Heavy"}]`

### `POST /api/v1/driver/package/status`
- **Description** : Met à jour l'état d'un colis (Chargement > Route > Livré).
- **Request Body** : `{"driver_id": "D123", "package_id": "P987", "status": "DELIVERED", "timestamp": "...", "lat": "...", "lon": "..."}`
- **Response** : `{"profit_updated": true, "ack": "success"}`

### `GET /api/v1/driver/alerts/fatigue`
- **Description** : Renvoie les alertes de pauses basées sur le temps conduit vs la réglementation du travail.
- **Response** : `{"break_recommended": true, "reason": "Driving > 4 consecutive hours"}`

---

## 2. Flow du Admin Dashboard (Dashboard Manager)

### `GET /api/v1/admin/fleet/tracking`
- **Description** : Renvoie la position de toute la flotte, l'état du trafic, et les retards éventuels.
- **Response** : `[{"driver_id": "D123", "route_progress": "45%", "eta_delay": "15mins", "lat": "...", "lon": "..."}]`

### `GET /api/v1/admin/kpi/profitability`
- **Description** : Récupère le profit agrégé temps réel pour une flotte, via les fonctions du backend_agent.
- **Response** : `{"total_revenue": 1050.50, "total_costs": 405.20, "net_profit": 645.30}`

### `POST /api/v1/admin/dispatch/dynamic-pickup`
- **Description** : Simule l'attribution d'un nouveau pickup dynamique à un chauffeur proche, en évaluant la rentabilité.
- **Request Body** : `{"package_id": "NEW001", "lat": "...", "lon": "...", "value": 25.0}`
- **Response** : `{"assigned_driver": "D123", "marginal_profit": 12.50, "accepted": true}`

## Principes de Séparation (Clean Architecture)
- Toutes les opérations intensives (Google Maps Matrix, météo, algorithme de routing) sont gérées dans le `/backend_agent`.
- Les interfaces `/driver_app` et `/admin_dashboard` ne font qu'afficher de la data récupérée depuis `/api/v1/...` ou envoyer des événements métiers (comme le scan d'un colis).