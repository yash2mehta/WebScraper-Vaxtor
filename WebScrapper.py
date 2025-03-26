from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
from datetime import datetime
import os

# --- Config ---
VAXTOR_URL = "http://169.254.206.95/local/Vaxreader/index.html#/"
DATA_DIR = "vaxtor_data"  # Directory to store data files

# Create data directory if it doesn't exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

class BrowserSession:
    def __init__(self):
        self.driver = None
        self.setup_browser()
    
    def setup_browser(self):
        """Initialize the browser once"""
        try:
            options = Options()
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            print("✅ Browser initialized successfully")
            
            # Initial login
            if not self.initial_login():
                raise Exception("Failed to perform initial login")
                
        except Exception as e:
            print(f"❌ Failed to initialize browser: {str(e)}")
            self.driver = None
    
    def initial_login(self):
        """Perform initial login"""
        try:
            username = "root"
            password = "pass"
            url_parts = VAXTOR_URL.split("//")
            auth_url = f"{url_parts[0]}//{username}:{password}@{url_parts[1]}"
            self.driver.get(auth_url)
            return True
        except Exception as e:
            print(f"❌ Login failed: {str(e)}")
            return False
    
    def refresh_and_get_data(self):
        """Refresh page and get new data"""
        try:
            print("🔄 Refreshing page...")
            self.driver.refresh()
            
            # Wait for data to load after refresh
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Plates')]"))
            )
            print("✅ 'Plates' section loaded.")
            
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
            )
            print("✅ Table rows found.")
            
            # Give extra time for data to load
            time.sleep(5)
            
            # Get the page source with new data
            return BeautifulSoup(self.driver.page_source, "lxml")
            
        except Exception as e:
            print(f"❌ Refresh failed: {str(e)}")
            return None
    
    def quit(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("✅ Browser closed")

def check_table_data(soup):
    """Check if table has data"""
    table = soup.find("table", class_="table table-bordered table-hover table-condensed")
    if not table:
        return False
    
    # Check if there are any non-hidden rows in tbody
    tbody = table.find("tbody")
    if not tbody:
        return False
    
    visible_rows = [tr for tr in tbody.find_all("tr", recursive=False) 
                   if not tr.get("hidden")]
    
    return len(visible_rows) > 0

def scrape_data(max_retries=3, retry_delay=5):
    for attempt in range(max_retries):
        try:
            print(f"\nAttempt {attempt + 1} of {max_retries}")
            
            # Setup Chrome
            options = Options()
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            
            # Handle login
            if not handle_login(driver):
                driver.quit()
                continue
            
            # Wait for Plates section
            try:
                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Plates')]"))
                )
                print("✅ 'Plates' section loaded.")
                
                # Additional wait for table data
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
                )
                print("✅ Table rows found.")
                
                # Extra delay to ensure data is loaded
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ Wait failed: {str(e)}")
                driver.quit()
                continue
            
            # Parse page
            soup = BeautifulSoup(driver.page_source, "lxml")
            driver.quit()
            
            # Verify table has data
            if not check_table_data(soup):
                print("❌ No data found in table, retrying...")
                time.sleep(retry_delay)
                continue
            
            print("✅ Data found in table, proceeding with extraction...")
            
            table = soup.find("table", class_="table table-bordered table-hover table-condensed")
            
            # Extract headers and their positions
            target_headers = ['Plate', 'Make', 'Model']
            headers = []
            header_indices = {}  # Store position of each target header
            
            for i, th in enumerate(table.find("thead").find_all("th")):
                header_text = th.get_text(strip=True)
                if not th.get("hidden") and header_text in target_headers:
                    headers.append(header_text)
                    header_indices[header_text] = i
            
            print("\n=== Headers to extract ===")
            print(headers)
            print("Header positions:", header_indices)
            
            # Extract rows
            data_rows = []
            for tr in table.find("tbody").find_all("tr", recursive=False):
                if tr.get("hidden"):
                    continue
                
                all_cells = tr.find_all("td", recursive=False)
                if not all_cells:  # Skip if row has no cells
                    continue
                    
                try:
                    row_data = []
                    # Extract data for each target header
                    for header in headers:
                        index = header_indices[header]
                        if index < len(all_cells):
                            td = all_cells[index]
                            text = td.get_text(strip=True)
                            
                            if header == 'Plate':
                                if not text:  # Skip row if plate is empty
                                    continue
                            else:  # Make and Model
                                text = None if not text else text
                                
                            row_data.append(text)
                        else:
                            row_data.append(None)
                    
                    if row_data and row_data[0]:  # Only add if we have a plate number
                        data_rows.append(row_data)
                        
                except Exception as e:
                    print(f"Warning: Error processing row: {e}")
                    continue
            
            if not data_rows:
                print("❌ No valid data rows found, retrying...")
                time.sleep(retry_delay)
                continue
                
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            
            # Replace empty strings with None/NaN in Make and Model columns
            if 'Make' in df.columns:
                df['Make'] = df['Make'].replace('', pd.NA)
            if 'Model' in df.columns:
                df['Model'] = df['Model'].replace('', pd.NA)
            
            return df  # Successful execution
            
        except Exception as e:
            print(f"❌ Error during attempt {attempt + 1}: {str(e)}")
            time.sleep(retry_delay)
            continue
    
    print("❌ All retry attempts failed")
    return None

def save_data(df, timestamp):
    """Save data to CSV and JSON with timestamp"""
    if df is not None and not df.empty:
        filename = f"vaxtor_data_{timestamp}"
        df.to_csv(f"{DATA_DIR}/{filename}.csv", index=False)
        df.to_json(f"{DATA_DIR}/{filename}.json", orient="records", indent=2)
        return True
    return False

def scrape_data_from_soup(soup):
    """Extract data from BeautifulSoup object"""
    if not check_table_data(soup):
        print("❌ No data found in table")
        return None
    
    print("✅ Data found in table, proceeding with extraction...")
    
    table = soup.find("table", class_="table table-bordered table-hover table-condensed")
    if not table:
        return None
    
    # Extract headers and their positions
    target_headers = ['Plate', 'Make', 'Model']
    headers = []
    header_indices = {}
    
    for i, th in enumerate(table.find("thead").find_all("th")):
        header_text = th.get_text(strip=True)
        if not th.get("hidden") and header_text in target_headers:
            headers.append(header_text)
            header_indices[header_text] = i
    
    # Extract rows
    data_rows = []
    for tr in table.find("tbody").find_all("tr", recursive=False):
        if tr.get("hidden"):
            continue
        
        all_cells = tr.find_all("td", recursive=False)
        if not all_cells:
            continue
            
        try:
            row_data = []
            for header in headers:
                index = header_indices[header]
                if index < len(all_cells):
                    td = all_cells[index]
                    text = td.get_text(strip=True)
                    
                    if header == 'Plate':
                        if not text:
                            continue
                    else:
                        text = None if not text else text
                        
                    row_data.append(text)
                else:
                    row_data.append(None)
            
            if row_data and row_data[0]:
                data_rows.append(row_data)
                
        except Exception as e:
            print(f"Warning: Error processing row: {e}")
            continue
    
    if not data_rows:
        return None
            
    # Create DataFrame
    df = pd.DataFrame(data_rows, columns=headers)
    
    # Replace empty strings with None/NaN
    if 'Make' in df.columns:
        df['Make'] = df['Make'].replace('', pd.NA)
    if 'Model' in df.columns:
        df['Model'] = df['Model'].replace('', pd.NA)
    
    return df

def continuous_scraping(interval=30, max_retries=3, retry_delay=5):
    """Continuous scraping with single browser session"""
    print(f"\n=== Starting continuous scraping (every {interval} seconds) ===")
    
    browser = BrowserSession()
    if not browser.driver:
        print("❌ Failed to start browser")
        return
    
    previous_df = None
    consecutive_failures = 0
    scrape_count = 0
    
    try:
        while True:
            scrape_count += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n🔄 Scrape #{scrape_count} at {current_time}")
            
            success = False
            for attempt in range(max_retries):
                print(f"\n=== Attempt {attempt + 1} of {max_retries} ===")
                
                try:
                    # Get fresh data
                    soup = browser.refresh_and_get_data()
                    if not soup:
                        raise Exception("Failed to refresh data")
                    
                    # Use the common scraping function
                    result_df = scrape_data_from_soup(soup)
                    if result_df is None:
                        raise Exception("Failed to extract data")
                    
                    # Print the DataFrame
                    print("\n📊 Current DataFrame:")
                    if result_df.empty:
                        print("DataFrame is empty!")
                    else:
                        print(f"Shape: {result_df.shape}")
                        print(result_df)
                        # print("\nDataFrame Info:")
                        # print(result_df.info())
                    
                    # If we get here, the scrape was successful
                    success = True
                    consecutive_failures = 0  # Reset failure counter
                    
                    # Save if data changed
                    if not result_df.empty:
                        if previous_df is not None and result_df.equals(previous_df):
                            print("\nℹ️ No changes in data")
                        else:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            save_data(result_df, timestamp)
                            print("\n✅ New data saved")
                            previous_df = result_df.copy()
                    
                    break  # Exit retry loop on success
                    
                except Exception as e:
                    print(f"❌ Attempt {attempt + 1} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        print(f"⏳ Waiting {retry_delay} seconds before retry...")
                        time.sleep(retry_delay)
            
            if not success:
                consecutive_failures += 1
                print(f"\n⚠️ All {max_retries} attempts failed")
                
                # If we have too many consecutive failures, try to recreate browser session
                if consecutive_failures >= 3:
                    print("⚠️ Multiple consecutive failures detected. Recreating browser session...")
                    browser.quit()
                    browser = BrowserSession()
                    if not browser.driver:
                        print("❌ Failed to recreate browser session. Exiting...")
                        break
                    consecutive_failures = 0
            
            print(f"\n⏳ Waiting {interval} seconds until next scrape...")
            print("=" * 50)  # Visual separator between scrapes
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n⚠️ Stopping by user request")
        if previous_df is not None:
            print("\n📊 Last successful DataFrame:")
            print(previous_df)
    finally:
        browser.quit()

if __name__ == "__main__":
    continuous_scraping(interval=5)