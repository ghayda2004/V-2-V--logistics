# 🚚 Les Agents Intelligents - V2V Logistics Communication System

An intelligent vehicle-to-vehicle communication platform for autonomous logistics optimization using multi-agent systems and real-time auctions.

## 📋 Project Overview

**Les Agents Intelligents** transforms fleet management by treating each vehicle as an autonomous agent capable of:
- 🤖 Calculating its own operational costs
- 📡 Communicating with other agents via MQTT
- 🤝 Bidding on new packages in real-time
- 🗺️ Optimizing dynamic delivery routes

### Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Admin Dashboard (React)                   │
│              - Monitor fuel economies                         │
│              - Add/manage new packages                        │
└────────────────────┬────────────────────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     ▼               ▼               ▼
┌──────────┐  ┌──────────┐   ┌──────────────┐
│          │  │          |   │              │
│ Static   │  │Agents &  │   │V2V Network   │
│Intel     │  │Calculat  │   │(MQTT)        │
└──────────┘  └──────────┘   └──────────────┘
     │               │               │
     └───────────────┼───────────────┘
                     │
     ┌───────────────┴───────────────┐
     ▼                               ▼
┌─────────────────┐        ┌──────────────────┐
│  VRP Optimizer  │        │ Agent Swarm      │
│ (OR-Tools)      │        │ (Driver App IA)  │
└─────────────────┘        └──────────────────┘
```

---

## 🎯 Project Phases

### Static Intelligence & Data Preparation (Python)

**Objective:** Transform raw data into optimized delivery missions.

#### 1. Geo-Intelligence & Data Cleaning
- **Tools:** Pandas, GeoPy
- **Tasks:**
  - ✅ Clean dataset (already completed)
  - ✅ Convert addresses to GPS coordinates (Lat/Long)
  - Extract temporal patterns from delivery windows

#### 2. Dynamic Zoning Algorithm (K-Means Clustering)
- **Objective:** Divide delivery area into dynamic zones based on daily package density
- **Key Questions to Resolve:**
  - **Zone Division Strategy:** Should zones be optimized for:
    - Even distribution of packages per zone?
    - Balanced travel times?
    - Truck capacity constraints?
  - **Multi-Zone Assignment:** Can drivers serve multiple zones?
    - Yes: Enables cross-zone routing optimization
    - Consideration: May increase complexity in real-time rerouting
  - **Zone Constraints:**
    - Max packages per zone: `min(truck_capacity, cluster_density)`
    - Max distance per zone: Should relate to fuel autonomy and delivery time windows
    - Recommended: 20-50 km radius per zone depending on urban density

#### 3. Fleet Optimization (VRP - Vehicle Routing Problem)
- **Tools:** Google OR-Tools
- **Inputs:** Zoned packages, truck capacities, fuel constraints
- **Outputs:** Initial routes for each vehicle
- **Metrics:**
  - Base consumption = Distance × fuel_rate

**Files:** `static/data_clean.py`, `static/dispatch.py`

---

###  Agent Modeling & Cost Calculator (AI Core)

**Objective:** Make each vehicle "aware" of its operational costs and capabilities.

#### Agent Attributes
Each truck maintains real-time awareness of:
- **ID:** Unique vehicle identifier
- **GPS Position:** Real-time location
- **Capacity Remaining:** Volume/weight still available
- **Current Route:** Active delivery tasks
- **Fuel Level:** Autonomy calculation
- **Time Window:** Available working hours

#### Cost Calculation Engine (Haversine Formula)

When a new package arrives, the agent calculates the **insertion cost**:

```
insertion_cost = {
  distance_km: haversine(current_pos, package_pickup, package_delivery),
  time_minutes: distance_km / avg_speed + service_time,
  fuel_liters: distance_km * fuel_consumption_rate,
  cost_tnd: fuel_liters * fuel_price_per_liter
}
```


#### Eligibility Checks
1. **Capacity Check:** `package_size ≤ remaining_capacity`
2. **Autonomy Check:** `total_distance ≤ fuel_reserve / fuel_rate`
3. **Time Check:** `delivery_time ≤ remaining_window`

**File:** `agent_swarm/agent.py`

---

###  V2V Communication & Auction System (MQTT)

**Objective:** Handle dynamic package allocation and real-time alerts without human intervention.



#### Auction Algorithm Flow

```



## 📁 Project Structure

```
agentic/
├── static/                    # PHASE 1: Data & Fleet Optimization
│   ├── data_clean.py         # Geo-intelligence, data cleaning
│   ├── dispatch.py           # VRP optimization, initial routing
│   └── zones/                # Zone definitions (dynamic output)
│
├── agent_swarm/              # PHASE 2: Agent Core
│   ├── agent.py              # Agent class, cost calculator
│   ├── auction.py            # Bidding logic (TBD)
│   └── eligibility.py        # Constraint checking (TBD)
│
├── network/                  # PHASE 3: MQTT Communication
│   ├── main.py               # MQTT broker integration
│   ├── topics.py             # Topic definitions
│   └── protocols.py          # Message serialization (TBD)
│
├── dashboard/                # Admin Dashboard (React/Figma)
│   └── [Frontend files]
│
└── README.md                 # This file
```

---

## 🔧 Technical Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Data Processing | Python + Pandas | Dataset management |
| Geolocation | GeoPy | GPS coordinate conversion |
| Clustering | Scikit-learn (K-Means) | Dynamic zoning |
| VRP Solver | Google OR-Tools | Initial route planning |
| Agent IA | Python/Dart | Local cost calculation |
| Communication | MQTT (Mosquitto/HiveMQ) | Real-time V2V |
| Frontend | React + Figma | Admin dashboard |
| Frontend | Flutter/React Native | Driver mobile app |
| Database | Firebase/PostgreSQL | Fleet state persistence |

---

## 🚀 Getting Started

### Prerequisites
```bash
Python 3.8+
pip install pandas geopython google-ortools scikit-learn paho-mqtt
```

### Setup

1. **Data Preparation:**
   ```bash
   cd static/
   python data_clean.py  # Clean and geocode addresses
   python dispatch.py    # Generate initial routes
   ```

2. **Agent Configuration:**
   - Update truck profiles in `agent_swarm/agent.py`
   - Configure fuel consumption rates
   - Set capacity constraints

3. **MQTT Broker:**
   ```bash
   docker run -it -p 1883:1883 eclipse-mosquitto
   ```

4. **Start Agents:**
   ```bash
   cd agent_swarm/
   python agent.py --truck_id T001
   ```

---

## 📊 Key Metrics & KPIs

| Metric | Formula | Target |
|--------|---------|--------|
| **Fuel Efficiency** | Total_Distance / Total_Liters | Minimize |
| **Delivery Rate** | Completed / Total | >95% |
| **Avg Insertion Cost** | Sum_Bids / New_Packages | Minimize |
| **Auction Response Time** | Bid_Time | <50ms |
| **Route Optimization** | (Initial_Distance - Final_Distance) / Initial_Distance | >15% |

---


## 🔐 Security & Privacy

- ✅ MQTT over TLS for encrypted communication
- ✅ Package data anonymization in logs
- ✅ Driver authentication via mobile app tokens

---


**Status:** In Development - Phase 3 (V2V Communication)
