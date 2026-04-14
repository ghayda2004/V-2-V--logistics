from datetime import datetime, timedelta

def calculate_net_profit(
    base_revenue: float, 
    distance_km: float, 
    estimated_time_hours: float, 
    fuel_cost_per_km: float = 0.15,
    driver_hourly_wage: float = 15.0,
    vehicle_wear_per_km: float = 0.05,
    tolls_and_fees: float = 0.0
) -> dict:
    """
    Calcule le bénéfice net d'un trajet ou d'une collecte dynamique.
    Ceci est utilisé pour valider un pick-up & drop-off dynamique.
    """
    # Calcul des coûts
    fuel_cost = distance_km * fuel_cost_per_km
    wear_cost = distance_km * vehicle_wear_per_km
    labor_cost = estimated_time_hours * driver_hourly_wage
    
    total_costs = fuel_cost + wear_cost + labor_cost + tolls_and_fees
    net_profit = base_revenue - total_costs
    profit_margin = (net_profit / base_revenue) * 100 if base_revenue > 0 else 0.0
    
    return {
        "net_profit": round(net_profit, 2),
        "total_costs": round(total_costs, 2),
        "profit_margin_percentage": round(profit_margin, 2),
        "breakdown": {
            "revenue": base_revenue,
            "fuel_cost": round(fuel_cost, 2),
            "labor_cost": round(labor_cost, 2),
            "wear_cost": round(wear_cost, 2),
            "tolls_and_fees": tolls_and_fees
        },
        "is_profitable": net_profit > 0
    }

def evaluate_dynamic_pickup(
    current_route_profit: float, 
    new_distance_km: float, 
    new_time_hours: float, 
    new_package_revenue: float
) -> bool:
    """
    Évalue si l'ajout d'une nouvelle collecte (Pick-up dynamique) 
    augmente le profit global de la tournée.
    """
    marginal_profit = calculate_net_profit(
        base_revenue=new_package_revenue,
        distance_km=new_distance_km,
        estimated_time_hours=new_time_hours
    )
    
    return marginal_profit["is_profitable"]
