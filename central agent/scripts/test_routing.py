import json
import os
import sys
import pandas as pd

# Add backend_agent to python path so we can import from app.*
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(project_root, 'backend_agent'))

from app.services.routing import get_ors_matrices, optimize_routes
from app.services.messaging import generate_google_maps_url

def test_routing():
    # 1. Path to your database (Make sure you moved it to 'data/' earlier)
    csv_path = os.path.join("data", "C:\\Users\\User\\OneDrive\\Documents\\GitHub\\V-2-V--logistics\\central agent\\data\\fixed_database_large.csv")
    
    # Fallback to the smaller database if the large one isn't found
    if not os.path.exists(csv_path):
        csv_path = os.path.join("data", "fixed_database_large.csv")
        
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # 2. Extract valid points
    df = df.dropna(subset=['lat', 'lon'])
    
    # NOTE: The free tier of OpenRouteService limits matrix requests to 50x50 points at a time.
    # For a quick test, we will limit our deliveries to just 15 points.
    df_subset = df.head(60)
    
    # The main warehouse coordinates
    entrepot = (36.82857, 10.20616)
    
    # Combine the depot as the first point, followed by the deliveries
    points = [entrepot] + list(zip(df_subset['lat'], df_subset['lon']))
    print(f"\nTesting with {len(points)} points (1 Depot + {len(df_subset)} Deliveries)...")
    
    # 3. Call OpenRouteService (This will fail if ORS_API_KEY in .env is not set correctly)
    try:
        print("Calling OpenRouteService for real road distances/durations...")
        distance_matrix, duration_matrix = get_ors_matrices(points)
        print("Successfully retrieved distance and duration matrices!")
    except Exception as e:
        print(f"\n[ERROR] Failed to get distances from ORS: {e}")
        print("Make sure you added your ORS_API_KEY to the .env file!")
        return

    # 4. Optimize Routes using OR-Tools
    print("\nRunning Google OR-Tools optimization...")
    num_vehicles = 6
    
    result = optimize_routes(
        distance_matrix=distance_matrix, 
        duration_matrix=duration_matrix,
        num_vehicles=num_vehicles, 
        depot_index=0, 
        max_distance=150000, # 150 km max per vehicle
        max_route_duration_s=6 * 3600
    )

    # 5. Display the results
    if result:
        print("\n=== ROUTING RESULTS ===")
        print(f"Total distance driven : {result['total_distance'] / 1000:.2f} km")
        print(f"Vehicles used         : {result['vehicles_used']} out of {num_vehicles}")
        
        for v_id, route_info in result['routes'].items():
            # Route indices correspond to the order in the 'points' array
            # 0 is the depot, 1 is the first delivery, etc.
            
            # Extract the actual coordinates for this driver's route
            driver_route_cords = [points[i] for i in route_info['path_indices']]
            
            # Generate the Clickable Google Maps URL
            gmaps_link = generate_google_maps_url(driver_route_cords)
            outputs_dir = os.path.join(project_root, "outputs")
            os.makedirs(outputs_dir, exist_ok=True)
            routing_json_path = os.path.join(outputs_dir, "routing_results.json")
            with open(routing_json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Saved routing results to {routing_json_path}")
            print(f"\n  -> Vehicle {v_id+1}:")
            print(f"     Distance: {route_info['path_distance_m'] / 1000:.2f} km")
            print(f"     Deliveries: {len(route_info['path_indices']) - 2}")
            print(f"     Stops sequence: {' -> '.join(map(str, route_info['path_indices']))}")
            print(f"     🔗 GOOGLE MAPS GPS LINK:")
            print(f"        {gmaps_link}")
    else:
        print("\n[FAILED] OR-Tools could not find a solution (try increasing max_distance or num_vehicles).")

if __name__ == "__main__":
    test_routing()
