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
│  PHASE 1 │  │  PHASE 2 │   │  PHASE 3     │
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

### PHASE 1: Static Intelligence & Data Preparation (Python)

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

### PHASE 2: Agent Modeling & Cost Calculator (AI Core)

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

**Example:**
- New package adds 4 km to route
- Fuel consumption: 0.5 L/km × 4 km = 2 L
- At 1.0 TND/L → **Bid: 2.0 TND + service_fee**

#### Eligibility Checks
1. **Capacity Check:** `package_size ≤ remaining_capacity`
2. **Autonomy Check:** `total_distance ≤ fuel_reserve / fuel_rate`
3. **Time Check:** `delivery_time ≤ remaining_window`

**File:** `agent_swarm/agent.py`

---

### PHASE 3: V2V Communication & Auction System (MQTT)

**Objective:** Handle dynamic package allocation and real-time alerts without human intervention.

#### MQTT Broker & Topics

| Topic | Publisher | Subscribers | Purpose |
|-------|-----------|-------------|---------|
| `wassel/auctions/new_package` | Admin/System | All Agents | Announce new delivery task |
| `wassel/auctions/bids/<package_id>` | Agents | System | Submit cost bid |
| `wassel/auctions/awarded/<package_id>` | System | Winner Agent | Award delivery |
| `wassel/v2v/alerts/traffic` | All Agents | All Agents | Report traffic/obstacles |
| `wassel/v2v/alerts/accident` | Agents/External | All Agents | Emergency rerouting trigger |
| `wassel/v2v/status` | Agents | Dashboard | Real-time fleet status |

#### Auction Algorithm Flow

```
1. NEW PACKAGE ANNOUNCED
   └─> System publishes on wassel/auctions/new_package
       Payload: {package_id, pickup, delivery, weight, volume, deadline}

2. AGENT EVALUATION (LOCAL IA)
   └─> Each agent receives announcement
   └─> Calculates insertion_cost (≤50ms target)
   └─> Checks eligibility constraints
   └─> Returns bid or rejects

3. BIDDING PHASE
   ├─> Agent 1: "2.0 TND"
   ├─> Agent 2: "2.5 TND"
   ├─> Agent 3: "1.8 TND" ← LOWEST
   └─> Agent N: "Reject (No capacity)"

4. AWARD ASSIGNMENT
   └─> System assigns to Agent 3
   └─> Updates route dynamically
   └─> Confirms via wassel/auctions/awarded/<package_id>

5. REAL-TIME UPDATES
   └─> Driver app refreshes route
   └─> Dashboard updates KPIs
```

#### Auction Algorithm Details

**Question:** How sophisticated should the bidding be?
- **Option A (Simple):** Fixed cost = distance + time penalty
- **Option B (Optimal):** Include:
  - Opportunity cost (impacts future bids)
  - Service level (priority packages premium)
  - Driver preferences (cross-zone aversion)
- **Recommended:** Start with Option A, transition to Option B with historical data

**File:** `network/main.py`

---

### PHASE 4: Dynamic Planning & Real-Time Adaptation

**Objective:** Handle new packages and adapt to changing conditions.

#### Dynamic Rerouting Triggers
- ✅ New package won in auction
- 🚧 Traffic alert on planned route
- 🚧 Road closure/accident notification
- 🚧 Driver manual reroute request

#### Real-Time Updates to Driver App
- New package added to route
- ETA recalculated
- Turn-by-turn directions updated
- Fuel/autonomy warning if needed

---

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

## ❓ Frequently Asked Questions

### Zone Management
**Q: How many zones should we create?**
A: Start with `√(total_packages_per_day / 10)` zones. Adjust based on geographic density and truck availability.

**Q: Can drivers serve multiple zones?**
A: Yes, but optimize carefully. Multi-zone routes increase complexity but improve utilization.

**Q: What's the optimal zone radius?**
A: 20-50 km depending on urban density. Urban areas: 20-30 km | Rural: 40-50 km

### Auction Algorithm
**Q: Why use auctions instead of centralized assignment?**
A: Auctions reduce latency, empower drivers with autonomy, and naturally balance load.

**Q: What if no agent bids on a package?**
A: Escalate to secondary assignment logic or request admin intervention.

---

## 🔐 Security & Privacy

- ✅ MQTT over TLS for encrypted communication
- ✅ Package data anonymization in logs
- ✅ Driver authentication via mobile app tokens
- ✅ Audit trail for all transactions

---

## 📞 Contact & Support

For questions or issues:
- 📧 Technical: [your-email]
- 📱 Support: [your-contact]

---

## 📝 License

[Your License Here]

---

**Last Updated:** March 2026
**Version:** 1.0.0-beta
**Status:** In Development - Phase 3 (V2V Communication)
