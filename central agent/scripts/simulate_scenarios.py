import pandas as pd
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import json
import os
import sys

sys.path.append(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'backend_agent'))

from app.services.routing import get_ors_matrices

# --- Parametres economiques (ajustables) ---
FUEL_CONSUMPTION_L_PER_100KM = 6.5
FUEL_PRICE_PER_L = 2.2
AMORTISSEMENT_PER_KM = 0.213
VEHICLE_DAILY_FIXED_AMORT = 0

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CSV_PATH = os.path.join(PROJECT_ROOT, "data", "fixed_database_large.csv")
if not os.path.exists(CSV_PATH):
    CSV_PATH = os.path.join(PROJECT_ROOT, "data", "fixed_database_large.csv")

dfc = pd.read_csv(CSV_PATH)
ENTREPOT = (36.82857, 10.20616)
tous_les_points = [ENTREPOT] + list(zip(dfc['lat'], dfc['lon']))

print("Calculating ORS distance and duration matrices...")
dm, tm = get_ors_matrices(tous_les_points)

def solve_vrp(
    num_veh,
    limit,
    fixed_cost,
    balance=False,
    max_time_h=12,
    solver_time_s=3,
    force_active_vehicles=None,
):
    manager = pywrapcp.RoutingIndexManager(len(dm), num_veh, 0)
    routing = pywrapcp.RoutingModel(manager)

    def safe_node(index):
        try:
            return manager.IndexToNode(int(index))
        except Exception:
            return None
    
    def dist_cb(from_idx, to_idx):
        from_node = safe_node(from_idx)
        to_node = safe_node(to_idx)
        if from_node is None or to_node is None:
            return 10**9
        return int(dm[from_node][to_node])

    def time_cb(from_idx, to_idx):
        from_node = safe_node(from_idx)
        to_node = safe_node(to_idx)
        if from_node is None or to_node is None:
            return 10**9
        return int(tm[from_node][to_node])
    
    transit_cb_idx = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb_idx)
    
    if fixed_cost > 0:
        routing.SetFixedCostOfAllVehicles(fixed_cost)

    # Force the activation of N vehicles by forbidding empty routes for those vehicles.
    if force_active_vehicles is not None:
        force_count = min(int(force_active_vehicles), int(num_veh))
        for v in range(force_count):
            start_v = routing.Start(v)
            end_v = routing.End(v)
            routing.solver().Add(routing.NextVar(start_v) != end_v)
    
    routing.AddDimension(transit_cb_idx, 0, limit, True, 'Distance')
    dist_dim = routing.GetDimensionOrDie('Distance')
    if balance:
        dist_dim.SetGlobalSpanCostCoefficient(100)

    time_cb_idx = routing.RegisterTransitCallback(time_cb)
    routing.AddDimension(time_cb_idx, 0, int(max_time_h * 3600), True, 'Time')
    time_dim = routing.GetDimensionOrDie('Time')
        
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = int(solver_time_s)
    
    sol = routing.SolveWithParameters(search_parameters)
    if not sol:
        return None
    
    active_veh = 0
    tot_dist = 0
    tot_time = 0
    dists = []
    times = []
    for v in range(num_veh):
        idx = routing.Start(v)
        d = 0
        while not routing.IsEnd(idx):
            prev = idx
            idx = sol.Value(routing.NextVar(idx))
            d += dm[manager.IndexToNode(prev)][manager.IndexToNode(idx)]
        if d > 0:
            active_veh += 1
            tot_dist += d
            dists.append(d / 1000.0)
            veh_time_h = sol.Value(time_dim.CumulVar(idx)) / 3600.0
            tot_time += veh_time_h
            times.append(round(veh_time_h, 2))
    return {
        "active_vehicles": active_veh,
        "total_distance_km": round(tot_dist / 1000.0, 3),
        "total_time_h": round(tot_time, 2),
        "distances_per_veh_km": dists,
        "times_per_veh_h": times
    }


def enrich_with_economics(result):
    if result is None:
        return None

    distance_km = float(result["total_distance_km"])
    active_vehicles = int(result["active_vehicles"])

    fuel_l = distance_km * FUEL_CONSUMPTION_L_PER_100KM / 100.0
    fuel_cost = fuel_l * FUEL_PRICE_PER_L
    amort_km_cost = distance_km * AMORTISSEMENT_PER_KM
    fixed_amort_cost = active_vehicles * VEHICLE_DAILY_FIXED_AMORT
    total_cost = fuel_cost + amort_km_cost + fixed_amort_cost

    result["economics"] = {
        "fuel_l": round(fuel_l, 2),
        "fuel_cost": round(fuel_cost, 2),
        "amortissement_km_cost": round(amort_km_cost, 2),
        "amortissement_fixed_cost": round(fixed_amort_cost, 2),
        "total_operating_cost": round(total_cost, 2),
    }
    return result


def gains_vs_baseline(base_result, scenario_result):
    if base_result is None or scenario_result is None:
        return None

    base_e = base_result["economics"]
    scen_e = scenario_result["economics"]

    return {
        "km_saved": round(base_result["total_distance_km"] - scenario_result["total_distance_km"], 3),
        "fuel_l_saved": round(base_e["fuel_l"] - scen_e["fuel_l"], 2),
        "fuel_cost_saved": round(base_e["fuel_cost"] - scen_e["fuel_cost"], 2),
        "amortissement_saved": round(
            (base_e["amortissement_km_cost"] + base_e["amortissement_fixed_cost"]) -
            (scen_e["amortissement_km_cost"] + scen_e["amortissement_fixed_cost"]),
            2,
        ),
        "total_cost_saved": round(base_e["total_operating_cost"] - scen_e["total_operating_cost"], 2),
        "vehicles_saved": base_result["active_vehicles"] - scenario_result["active_vehicles"],
    }


def print_scenario(name, result):
    print(f"\n{name}")
    if result is None:
        print("  -> Aucune solution (contraintes trop strictes)")
        return

    eco = result["economics"]
    print(f"  Vehicules actifs    : {result['active_vehicles']}")
    print(f"  Distance totale km  : {result['total_distance_km']}")
    print(f"  Temps total h       : {result['total_time_h']}")
    print(f"  Carburant (L)       : {eco['fuel_l']}")
    print(f"  Cout carburant      : {eco['fuel_cost']}")
    print(f"  Amortissement km    : {eco['amortissement_km_cost']}")
    print(f"  Amortissement fixe  : {eco['amortissement_fixed_cost']}")
    print(f"  Cout total scenario : {eco['total_operating_cost']}")


def auto_tune_forced_vehicles(base_params, forced_count, tag):
    """Trouve une configuration faisable en forcant l'activation d'un nombre de vehicules."""
    distance_limits = [
        base_params["limit"],
        300000,
        450000,
        600000,
    ]
    time_limits = [base_params["max_time_h"], 14, 18, 24]
    solver_times = [2]

    candidates = []
    for dist_limit in distance_limits:
        for max_time_h in time_limits:
            for solver_time_s in solver_times:
                params = dict(base_params)
                params["limit"] = dist_limit
                params["max_time_h"] = max_time_h
                params["solver_time_s"] = solver_time_s
                params["force_active_vehicles"] = int(forced_count)
                result = enrich_with_economics(solve_vrp(**params))
                if result is not None:
                    candidates.append((result["economics"]["total_operating_cost"], params, result))
                    print(
                        f"Auto-tuning {tag} early selected params: "
                        f"limit={params['limit']} m, max_time_h={params['max_time_h']}, "
                        f"solver_time_s={params['solver_time_s']}, force_active_vehicles={params['force_active_vehicles']}"
                    )
                    return params, result

    if not candidates:
        print(
            f"Auto-tuning {tag}: no feasible configuration found with forced "
            f"{forced_count} vehicles up to 1000 km and 30 h."
        )
        return None, None

    candidates.sort(key=lambda x: x[0])
    best = candidates[0]
    print(
        f"Auto-tuning {tag} selected params: "
        f"limit={best[1]['limit']} m, max_time_h={best[1]['max_time_h']}, "
        f"solver_time_s={best[1]['solver_time_s']}, force_active_vehicles={best[1]['force_active_vehicles']}"
    )
    return best[1], best[2]


def build_comparison_rows(scenarios, comparison):
    rows = []
    for key, cfg in scenarios.items():
        result = comparison[key]["result"]
        gains = comparison[key]["gains_vs_baseline"]

        if result is None:
            rows.append({
                "scenario_key": key,
                "scenario_label": cfg["label"],
                "status": "infeasible",
                "active_vehicles": None,
                "total_distance_km": None,
                "total_time_h": None,
                "fuel_l": None,
                "fuel_cost": None,
                "amortissement_km_cost": None,
                "amortissement_fixed_cost": None,
                "total_operating_cost": None,
                "km_saved_vs_baseline": None,
                "fuel_cost_saved_vs_baseline": None,
                "amortissement_saved_vs_baseline": None,
                "total_cost_saved_vs_baseline": None,
            })
            continue

        eco = result["economics"]
        rows.append({
            "scenario_key": key,
            "scenario_label": cfg["label"],
            "status": "feasible",
            "active_vehicles": result["active_vehicles"],
            "total_distance_km": result["total_distance_km"],
            "total_time_h": result["total_time_h"],
            "fuel_l": eco["fuel_l"],
            "fuel_cost": eco["fuel_cost"],
            "amortissement_km_cost": eco["amortissement_km_cost"],
            "amortissement_fixed_cost": eco["amortissement_fixed_cost"],
            "total_operating_cost": eco["total_operating_cost"],
            "km_saved_vs_baseline": gains["km_saved"] if gains else 0.0,
            "fuel_cost_saved_vs_baseline": gains["fuel_cost_saved"] if gains else 0.0,
            "amortissement_saved_vs_baseline": gains["amortissement_saved"] if gains else 0.0,
            "total_cost_saved_vs_baseline": gains["total_cost_saved"] if gains else 0.0,
        })

    return rows


def export_gains_chart_html(rows, output_path):
    gain_rows = [r for r in rows if r["status"] == "feasible"]
    if not gain_rows:
        return

    max_abs = 1.0
    for r in gain_rows:
        max_abs = max(max_abs, abs(float(r["total_cost_saved_vs_baseline"] or 0.0)))

    bars_html = []
    for r in gain_rows:
        val = float(r["total_cost_saved_vs_baseline"] or 0.0)
        width_pct = int((abs(val) / max_abs) * 100)
        color = "#2a9d8f" if val >= 0 else "#e63946"
        bars_html.append(
            f"""
            <div class=\"row\">
              <div class=\"label\">{r['scenario_key']}</div>
              <div class=\"bar-wrap\"><div class=\"bar\" style=\"width:{width_pct}%;background:{color};\"></div></div>
              <div class=\"val\">{val:.2f}</div>
            </div>
            """
        )

    html = f"""
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>Simulation Gains Chart</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background:#f7f7f9; color:#1f2937; }}
    h2 {{ margin-bottom: 6px; }}
    p {{ color:#4b5563; }}
    .card {{ background:white; border:1px solid #e5e7eb; border-radius:10px; padding:16px; max-width:920px; }}
    .row {{ display:grid; grid-template-columns: 160px 1fr 120px; gap:10px; align-items:center; margin:10px 0; }}
    .label {{ font-weight:600; }}
    .bar-wrap {{ background:#eef2f7; border-radius:6px; height:18px; overflow:hidden; }}
    .bar {{ height:100%; border-radius:6px; }}
    .val {{ text-align:right; font-family: monospace; }}
  </style>
</head>
<body>
  <h2>Gains vs Baseline (Total Cost Saved)</h2>
  <p>Positive = saving, Negative = more expensive than baseline.</p>
  <div class=\"card\">{''.join(bars_html)}</div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


SCENARIOS = {
    "1_car": {
        "label": "Scenario 1: 1 Vehicle (AI choice)",
        "params": {"num_veh": 1, "limit": 1000000, "fixed_cost": 0, "max_time_h": 24},
    },
    "2_cars_forced": {
        "label": "Scenario 2: Force 2 Vehicles",
        "params": {"num_veh": 2, "limit": 200000, "fixed_cost": 25000, "max_time_h": 12},
        "force_active_vehicles": 2,
    },
    "3_cars_forced": {
        "label": "Scenario 3: Force 3 Vehicles",
        "params": {"num_veh": 3, "limit": 200000, "fixed_cost": 25000, "max_time_h": 12},
        "force_active_vehicles": 3,
    },
    "5_cars_forced": {
        "label": "Scenario 4: Force 5 Vehicles",
        "params": {"num_veh": 5, "limit": 200000, "fixed_cost": 25000, "max_time_h": 12},
        "force_active_vehicles": 5,
    },
}


raw_results = {}
scenario_meta = {}
for key, cfg in SCENARIOS.items():
    if key.endswith("_forced"):
        forced_count = int(cfg.get("force_active_vehicles", cfg["params"].get("num_veh", 1)))
        print(f"Running {cfg['label']} with forced usage + auto-tuning...")
        tuned_params, tuned_result = auto_tune_forced_vehicles(cfg["params"], forced_count, key)
        raw_results[key] = tuned_result
        scenario_meta[key] = {
            "autotuned": True,
            "forced": True,
            "forced_vehicles": forced_count,
            "base_params": cfg["params"],
            "params_used": tuned_params,
        }
    else:
        print(f"Running {cfg['label']}...")
        raw_results[key] = enrich_with_economics(solve_vrp(**cfg["params"]))
        scenario_meta[key] = {
            "autotuned": False,
            "forced": False,
            "base_params": cfg["params"],
            "params_used": cfg["params"],
        }

baseline = raw_results["1_car"]
comparison = {}
for key, result in raw_results.items():
    comparison[key] = {
        "result": result,
        "gains_vs_baseline": gains_vs_baseline(baseline, result) if key != "1_car" else None,
    }

# Choix du meilleur scenario: minimiser le cout total parmi les scenarios faisables
feasible = {k: v for k, v in raw_results.items() if v is not None}
best_key = None
if feasible:
    best_key = min(feasible.keys(), key=lambda k: feasible[k]["economics"]["total_operating_cost"])

for key, cfg in SCENARIOS.items():
    print_scenario(cfg["label"], raw_results[key])
    gains = comparison[key]["gains_vs_baseline"]
    if gains:
        print(
            "  Gains vs baseline   : "
            f"km={gains['km_saved']}, fuel(L)={gains['fuel_l_saved']}, "
            f"fuel_cost={gains['fuel_cost_saved']}, amort={gains['amortissement_saved']}, "
            f"total={gains['total_cost_saved']}, vehicules={gains['vehicles_saved']}"
        )

if best_key:
    print(f"\nBest scenario selected by simulation: {SCENARIOS[best_key]['label']} ({best_key})")

rows = build_comparison_rows(SCENARIOS, comparison)
table_df = pd.DataFrame(rows)

COMPARISON_CSV_PATH = os.path.join(PROJECT_ROOT, "data", "sim_comparison.csv")
COMPARISON_TXT_PATH = os.path.join(PROJECT_ROOT, "data", "sim_comparison.txt")
GAINS_HTML_PATH = os.path.join(PROJECT_ROOT, "data", "sim_gains.html")

table_df.to_csv(COMPARISON_CSV_PATH, index=False)
with open(COMPARISON_TXT_PATH, "w", encoding="utf-8") as f:
    f.write(table_df.to_string(index=False))

export_gains_chart_html(rows, GAINS_HTML_PATH)

print(f"\nComparative table saved to: {COMPARISON_CSV_PATH}")
print(f"Text table saved to: {COMPARISON_TXT_PATH}")
print(f"Gains chart saved to: {GAINS_HTML_PATH}")

OUTPUT_PATH = os.path.join(PROJECT_ROOT, "data", "sim_results.json")
payload = {
    "scenarios": {k: {"label": SCENARIOS[k]["label"], **comparison[k]} for k in SCENARIOS.keys()},
    "scenario_meta": scenario_meta,
    "best_scenario": {
        "key": best_key,
        "label": SCENARIOS[best_key]["label"] if best_key else None,
        "reason": "minimum total_operating_cost among feasible scenarios",
    },
    "artifacts": {
        "comparison_csv": COMPARISON_CSV_PATH,
        "comparison_txt": COMPARISON_TXT_PATH,
        "gains_chart_html": GAINS_HTML_PATH,
    },
    "economic_parameters": {
        "fuel_consumption_l_per_100km": FUEL_CONSUMPTION_L_PER_100KM,
        "fuel_price_per_l": FUEL_PRICE_PER_L,
        "amortissement_per_km": AMORTISSEMENT_PER_KM,
        "vehicle_daily_fixed_amort": VEHICLE_DAILY_FIXED_AMORT,
    },
}

with open(OUTPUT_PATH, "w") as f:
    json.dump(payload, f, indent=2)

print(f"\nSimulation results saved to: {OUTPUT_PATH}")
