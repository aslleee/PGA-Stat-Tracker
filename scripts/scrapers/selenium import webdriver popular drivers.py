from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import pandas as pd

web = 'https://pgaclubtracker.com/clubhead_types/most-popular-golf-drivers-on-tour'
path = r'C:\Users\hkh82\OneDrive\Desktop\Codes\chromedriver-win64\chromedriver.exe'
service = Service(executable_path=path)
driver = webdriver.Chrome(service=service)

driver.get(web)

# Parse page source with BeautifulSoup
soup = BeautifulSoup(driver.page_source, "html.parser")

# Find the stats table
table = soup.find("table")
if table:
    headers = [th.text.strip() for th in table.find_all("th")]
    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.text.strip() for td in tr.find_all("td")]
        if cells:
            rows.append(cells)
    # Save to CSV
    df = pd.DataFrame(rows, columns=headers)
    df.to_csv("most_popular_golf_drivers.csv", index=False)
    print("Scraping complete. Data saved to most_popular_golf_drivers.csv.")
else:
    print("No table found on the page.")

driver.quit()