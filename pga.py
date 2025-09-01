import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re

url = "https://www.pgatour.com/stats/detail/120"
headers = {"User-Agent": "Mozilla/5.0"}

r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, "html.parser")

# Find the script tag containing the data
script_tags = soup.find_all("script", id="__NEXT_DATA__")
if script_tags:
    script_content = script_tags[0].string
    try:
        # Parse the JSON data
        page_data = json.loads(script_content)
        
        # Navigate to the player data
        queries = page_data["props"]["pageProps"]["dehydratedState"]["queries"]
        
        # Find the statDetails query
        stat_data = None
        for query in queries:
            if "statDetails" in str(query.get("queryKey", [])):
                try:
                    # The rows are directly under state.data.rows
                    stat_data = query["state"]["data"]["rows"]
                    break
                except KeyError:
                    print("Could not access rows in query")
                    continue
        
        if stat_data:
            # Extract player data
            player_data = []
            for row in stat_data:
                if row.get("__typename") == "StatDetailsPlayer":
                    player_info = {
                        "rank": row.get("rank"),
                        "player_name": row.get("playerName"),
                        "country": row.get("country"),
                        "player_id": row.get("playerId")
                    }
                    
                    # Extract stats
                    for stat in row.get("stats", []):
                        stat_name = stat.get("statName")
                        stat_value = stat.get("statValue")
                        
                        if stat_name == "Avg":
                            player_info["scoring_avg"] = stat_value
                        elif stat_name == "Total Strokes":
                            player_info["total_strokes"] = stat_value
                        elif stat_name == "Total Adjustment":
                            player_info["total_adjustment"] = stat_value
                        elif stat_name == "Total Rounds":
                            player_info["total_rounds"] = stat_value
                    
                    player_data.append(player_info)
            
            # Create DataFrame
            df = pd.DataFrame(player_data)
            
            print(f"Found {len(df)} players")
            print("\nTop 10 players by scoring average:")
            print(df.head(10).to_string(index=False))
            
            # Save to CSV
            df.to_csv("pga_scoring_average_2025.csv", index=False)
            print(f"\nData saved to pga_scoring_average_2025.csv")
            
        else:
            print("Could not find stat details data in the page")
            
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        
else:
    print("Could not find data script tag")
    print("Available script tags:", len(soup.find_all("script")))
