import pandas as pd
from geopy.distance import geodesic
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import json

dfc = pd.read_csv("fixed_database_large.csv")
ENTREPOT = (36.82857, 10.20616)
tous_les_points = [ENTREPOT] + list(zip(dfc['lat'], dfc['lon']))

def create_distance_matrix(points):
    matrix = []
    for i in range(len(points)):
        row = [int(geodesic(points[i], points[j]).meters) if i != j else 0 for j in range(len(points))]
        matrix.append(row)
    return matrix

print("Calculating distance matrix...")
dm = create_distance_matrix(tous_les_points)

def solve_vrp(num_veh, limit, fixed_cost, balance=False):
    manager = pywrapcp.RoutingIndexManager(len(dm), num_veh, 0)
    routing = pywrapcp.RoutingModel(manager)
    
    def dist_cb(from_idx, to_idx):
        return dm[manager.IndexToNode(from_idx)][manager.IndexToNode(to_idx)]
    
    transit_cb_idx = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb_idx)
    
    if fixed_cost > 0:
        routing.SetFixedCostOfAllVehicles(fixed_cost)
    
    routing.AddDimension(transit_cb_idx, 0, limit, True, 'Distance')
    dist_dim = routing.GetDimensionOrDie('Distance')
    if balance:
        dist_dim.SetGlobalSpanCostCoefficient(100)
        
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 5
    
    sol = routing.SolveWithParameters(search_parameters)
    if not sol:
        return None
    
    active_veh = 0
    tot_dist = 0
    dists = []
    for v in range(num_veh):
        idx = routing.Start(v)
        d = 0
        while not routing.IsEnd(idx):
            prev = idx
            idx = sol.Value(routing.NextVar(idx))
            d += routing.GetArcCostForVehicle(prev, idx, v)
        if d > 0:
            active_veh += 1
            tot_dist += d
            dists.append(d / 1000.0)
    return {"active_vehicles": active_veh, "total_distance_km": tot_dist / 1000.0, "distances_per_veh_km": dists}

print("Running Scenario 1: 1 Vehicle (Infinite Capacity to show baseline distance)")
s1 = solve_vrp(1, 1000000, 0)
print(s1)

print("Running Scenario 1b: 1 Vehicle (Strict 150km Limit - Should Fail)")
s1b = solve_vrp(1, 150000, 0)
print(s1b)

print("Running Scenario 2: 2 Vehicles Optimization")
s2 = solve_vrp(2, 200000, 25000)
print(s2)

print("Running Scenario 4: Max 5 Vehicles, Let AI Optimize with Cost Penalty")
s4 = solve_vrp(5, 200000, 25000)
print(s4)

with open("sim_results.json", "w") as f:
    json.dump({'1_car': s1, '1_car_strict': s1b, '2_cars': s2, '5_cars': s3}, f)
