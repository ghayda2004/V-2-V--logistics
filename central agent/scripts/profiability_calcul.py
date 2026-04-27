import json
import os
import sys

# Add backend_agent to python path so we can import from app.*
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(project_root, 'backend_agent'))

from app.services.profitability import calculate_net_profit

DELIVERY_PRICE_DT = 9

outputs_dir = os.path.join(project_root, "outputs")
routing_json_path = os.path.join(outputs_dir, "routing_results.json")
profit_json_path = os.path.join(outputs_dir, "profitability_results.json")

with open(routing_json_path, "r", encoding="utf-8") as f:
    routing = json.load(f)

profitability = {}
routes = routing.get("routes", {})
for v_id, route in routes.items():
    deliveries = len(route["path_indices"]) - 2
    base_revenue = deliveries * DELIVERY_PRICE_DT
    distance_km = route["path_distance_m"] / 1000
    time_hours = route["path_duration_s"] / 3600

    profitability[v_id] = calculate_net_profit(
        base_revenue=base_revenue,
        distance_km=distance_km,
        estimated_time_hours=time_hours
    )

with open(profit_json_path, "w", encoding="utf-8") as f:
    json.dump(profitability, f, ensure_ascii=False, indent=2)

print(f"Saved profitability results to {profit_json_path}")