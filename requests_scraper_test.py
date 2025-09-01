# This script scrapes a table of PGA Tour stats by directly accessing the
# JSON endpoint, which is a more efficient method for this website.
#
# Before running this script, you must install the required libraries:
# pip install requests

import requests
import json
import os

def explore_json_structure(data, indent=0, max_depth=3):
    """
    Recursively explores and prints the structure of a JSON object.

    Args:
        data (dict or list): The JSON data to explore.
        indent (int): The current indentation level.
        max_depth (int): The maximum depth to explore.
    """
    if indent > max_depth:
        return

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(' ' * indent + f"- {key}:")
                explore_json_structure(value, indent + 2, max_depth)
            else:
                # Truncate long values for readability
                truncated_value = str(value)[:50] + '...' if len(str(value)) > 50 else str(value)
                print(' ' * indent + f"- {key}: {type(value).__name__} = {truncated_value}")

    elif isinstance(data, list):
        if len(data) > 0:
            print(' ' * indent + f"- List of {len(data)} items:")
            # Explore the first item of the list
            explore_json_structure(data[0], indent + 2, max_depth)

def get_pga_stats_json(url):
    """
    Fetches the JSON data directly from the PGA Tour stats endpoint.

    Args:
        url (str): The URL of the JSON endpoint.

    Returns:
        dict: The parsed JSON data. Returns None on failure.
    """
    try:
        # Define headers to mimic a web browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0',
            'Accept': 'application/json',
            'Referer': 'https://www.pgatour.com/stats'
        }
        
        print(f"Attempting to fetch data from: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an exception for bad status codes

        print("Data fetched successfully, parsing JSON...")
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching the URL: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None    
print(json.dumps(json_data['pageProps']['pageContext'], indent=2))

def extract_player_stats(data):
    """
    Extracts player statistics from the JSON data.

    Args:
        data (dict): The full JSON data from the endpoint.

    Returns:
        list: A list of dictionaries containing player stats.
    """
    player_data = []
    # Navigate the nested JSON structure to find the table rows.
    # Based on the provided snippet, the data seems to be located at
    # data['pageProps']['pageContext']['statsDetails']['rows'].
    # This path might vary, so you might need to adjust it.
    try:
        rows = data['pageProps']['pageContext']['statsDetails']['rows']
        
        for row in rows:
            # Each row is a dictionary with a 'values' list.
            # The structure of this list corresponds to the columns in the table.
            values = row.get('values', [])
            
            # The order of values in the list corresponds to the table columns.
            # Based on the URL for Driving Distance (101), we can infer the order.
            # Example values: rank, name, avg, total, rounds
            stats = {
                'Rank': values[0].get('value'),
                'Player': row.get('player', {}).get('displayName'),
                'Total Strokes': values[1].get('value'),
                'Total Adjustment': values[2].get('value'),
                'Total Rounds': values[3].get('value')
            }
            player_data.append(stats)
            
    except (KeyError, IndexError) as e:
        print(f"Error navigating JSON structure: {e}")
        return []
    
    return player_data

if __name__ == '__main__':
    # URL for PGA Tour Driving Distance stats. Note that the statId is part of the URL.
    # The example URL you provided was for statId 120, so we'll use that.
    stat_id = "120"
    url = f"https://www.pgatour.com/_next/data/pgatour-prod-2.5.0/en/stats/detail/{stat_id}.json?statId={stat_id}"
    
    # Get the raw JSON data
    json_data = get_pga_stats_json(url)

    if json_data:
        # Explore the structure of the JSON to understand what we have
        print("\n--- JSON Structure Preview (first 3 levels) ---")
        explore_json_structure(json_data)
        
        # Extract the specific player stats
        scraped_data = extract_player_stats(json_data)
        
        if scraped_data:
            # Print the data as a JSON object with indentation for readability
            print("\n" + "-"*30)
            print("Scraped Player Data (JSON Output)")
            print("-" * 30)
            print(json.dumps(scraped_data, indent=4))
        else:
            print("\nFailed to extract player stats.")
    else:
        print("Scraping failed.")
