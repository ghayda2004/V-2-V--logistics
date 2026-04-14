import openrouteservice
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

def get_ors_distance_matrix(points_lat_lon):
    """
    Calls OpenRouteService to get the real driving distance matrix.
    :param points_lat_lon: list of tuples (latitude, longitude)
    :return: 2D list of distances (in meters)
    """
    # OpenRouteService expects coordinates in [longitude, latitude] format
    coords_lon_lat = [[lon, lat] for lat, lon in points_lat_lon]
    
    # Initialize the client using API key from .env settings
    client = openrouteservice.Client(key=settings.ORS_API_KEY)
    
    try:
        logger.info(f"Requesting ORS distance matrix for {len(coords_lon_lat)} points...")
        # Request distance matrix using driving-car profile
        result = client.distance_matrix(
            locations=coords_lon_lat,
            profile='driving-car',
            metrics=['distance'] # 'duration' can also be added here
        )
        return result['distances']
        
    except openrouteservice.exceptions.ApiError as e:
        logger.error(f"OpenRouteService API Error: {e}")
        # En dev, pour eviter de bloquer si lapi key expire, on fait une fallback mathématique (a vol d oiseau):
        logger.warning("Fallback sur la distance mathématique (Haversine estimée)...")
        matrix = []
        for l1 in points_lat_lon:
            row = []
            for l2 in points_lat_lon:
                distance_m = (((l1[0] - l2[0])**2 + (l1[1] - l2[1])**2)**0.5) * 111000 
                row.append(int(distance_m))
            matrix.append(row)
        return matrix
def optimize_routes(distance_matrix, num_vehicles, depot_index=0, max_distance=150000):
    """
    Uses Google OR-Tools to solve the Vehicle Routing Problem using the REAL distance matrix.
    
    :param distance_matrix: 2D list of distances in meters
    :param num_vehicles: total available drivers/vehicles
    :param depot_index: The index of the warehouse (usually 0)
    :param max_distance: Maximum distance a vehicle can travel (in meters)
    """
    logger.info("Initializing OR-Tools Routing Model...")
    
    # OR-Tools routing manager setup
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), num_vehicles, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        # Convert routing var indices to matrix indices
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # Return distance. OR-Tools uses integers internally, so we cast float to int.
        return int(distance_matrix[from_node][to_node])

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # 1. Fixed cost to minimize the number of vehicles used
    COUT_FIXE_VEHICULE = 25000 
    routing.SetFixedCostOfAllVehicles(COUT_FIXE_VEHICULE)

    # 2. Add distance dimension (so no vehicle drives forever)
    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        0,              # no slack
        max_distance,   # vehicle maximum travel distance in meters
        True,           # start cumul to zero
        dimension_name
    )

    # Search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 5

    logger.info("Solving route optimization...")
    solution = routing.SolveWithParameters(search_parameters)

    # If the solver fails to find a solution (e.g., max_distance is too low)
    if not solution:
        logger.warning("No optimal solution found by OR-Tools.")
        return None

    # Parse and extract assignments
    routes_summary = {
        'total_distance': 0,
        'vehicles_used': 0,
        'routes': {}
    }

    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        route_sequence = []
        route_distance = 0

        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_sequence.append(node_index)
            
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            # Get Arc Cost (distance) for this segment
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
            
        # Add the final return to the depot
        route_sequence.append(manager.IndexToNode(index))
        
        # If the route contains anything more than start -> end depot
        if len(route_sequence) > 2:
            routes_summary['vehicles_used'] += 1
            routes_summary['total_distance'] += route_distance
            routes_summary['routes'][vehicle_id] = {
                'path_indices': route_sequence,
                'path_distance_m': route_distance
            }

    return routes_summary
