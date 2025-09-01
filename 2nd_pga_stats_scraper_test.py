# This script scrapes a table of PGA Tour stats from a dynamic website
# using the Python libraries Selenium, BeautifulSoup, and pandas.
#
# Before running this script, you must have Google Chrome installed on your system.
# Then, install the required Python libraries using pip:
# pip install selenium beautifulsoup4 pandas webdriver-manager

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import json
import time

def get_pga_stats_table(url):
    """
    Scrapes a table from a given URL using Selenium to handle dynamic content
    and returns the data as a list of dictionaries.
    
    Args:
        url (str): The URL of the webpage to scrape.
        
    Returns:
        list: A list of dictionaries, where each dictionary represents a player's
              stats. Returns an empty list if the table is not found or an
              error occurs.
    """
    driver = None
    try:
        # Set up headless mode to run the browser without a visible GUI
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        # Install and initialize the Chrome WebDriver
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        print("Opening browser and navigating to URL...")
        driver.get(url)

        # Use an explicit wait to ensure the table content has loaded.
        # This selector targets the tbody, as the entire table content is loaded
        # dynamically. The `css-0` class is specific to the current site structure.
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'tbody.css-0'))
        )
        print("Page loaded successfully, extracting HTML...")

        # Get the page source after the dynamic content has been rendered
        html = driver.page_source
        
        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Find the tbody element to iterate through the player rows
        tbody = soup.find('tbody', class_='css-0')
        
        if not tbody:
            print("Error: Could not find the stats table on the page.")
            return []

        # List to store the scraped player data
        player_stats = []
        
        # Extract rows from the table body
        for tr in tbody.find_all('tr'):
            cells = tr.find_all('td')
            if len(cells) >= 6:
                # Based on the provided HTML structure, the data is in
                # specific td and nested span elements.
                rank = cells[0].get_text(strip=True)
                player_name = cells[2].find('span', class_='css-1osk6s4').get_text(strip=True)
                driving_distance = cells[3].find('span', class_='css-1vm150x').get_text(strip=True)
                
                player_stats.append({
                    "rank": rank,
                    "player_name": player_name,
                    "driving_distance_yards": driving_distance
                })
        
        return player_stats

    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        return []
    finally:
        if driver:
            driver.quit()
            print("Browser closed.")

if __name__ == '__main__':
    # URL for PGA Tour Driving Distance stats
    url = "https://www.pgatour.com/stats/detail/101"
    
    print(f"Attempting to scrape data from: {url}")
    scraped_data = get_pga_stats_table(url)

    if scraped_data:
        # Print the data as a JSON object with indentation for readability
        print("\n--- Scraped Data (JSON Output) ---")
        print(json.dumps(scraped_data, indent=4))
    else:
        print("Scraping failed.")
