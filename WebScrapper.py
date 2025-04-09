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
import requests
from urllib.parse import urljoin
import re
from pprint import pprint

# --- Config ---
VAXTOR_URL = "http://169.254.206.95/local/Vaxreader/index.html#/"
DATA_DIR = "vaxtor_data"  # Directory to store data files
IMAGES_DIR = "Vaxtor_Images"  # Directory to store images
# OLD_API_TOKEN = "210ed0449ee06e8d9bcee4a67c742814e4e7366e"  # PlateRecognizer API token
API_TOKEN = "210ed0449ee06e8d9bcee4a67c742814e4e7366e"  # PlateRecognizer API token - Premium

# Create data and images directories if they don't exist
for directory in [DATA_DIR, IMAGES_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_image(driver, url, plate_number):
    """Download image using Selenium's session"""
    try:
        # Clean plate number to make it a valid filename
        clean_plate = re.sub(r'[<>:"/\\|?*]', '', plate_number)
        filename = f"{clean_plate}.jpg"
        filepath = os.path.join(IMAGES_DIR, filename)
        
        # If file already exists, skip download
        if os.path.exists(filepath):
            # print(f"ℹ️ Image for plate {plate_number} already exists")
            return True
            
        # Use Selenium to get the image data
        driver.get(url)
        # Get the page source which should contain the image data
        img_element = driver.find_element(By.TAG_NAME, "img")
        if img_element:
            # Get the image as PNG screenshot
            img_element.screenshot(filepath)
            print(f"✅ Downloaded image for plate {plate_number}")
            return True
        else:
            print(f"❌ No image found for plate {plate_number}")
            return False
                
    except Exception as e:
        print(f"❌ Failed to download image for plate {plate_number}: {str(e)}")
        return False

class BrowserSession:
    def __init__(self):
        self.driver = None
        self.setup_browser()
    
    def setup_browser(self):
        """Initialize the browser once"""
        try:
            # First, make sure any existing driver is properly closed
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            
            options = Options()
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
            # Add additional options to improve stability
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-browser-side-navigation")
            options.add_argument("--disable-features=VizDisplayCompositor")
            
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            print("✅ Browser initialized successfully")
            
            # Initial login
            if not self.initial_login():
                raise Exception("Failed to perform initial login")
                
        except Exception as e:
            print(f"❌ Failed to initialize browser: {str(e)}")
            self.driver = None
    
    def force_recreate_session(self):
        """Force recreation of the entire browser session"""
        print("🔄 Forcing complete session recreation...")
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            
            # Small delay before recreating
            time.sleep(2)
            self.setup_browser()
            return self.driver is not None
            
        except Exception as e:
            print(f"❌ Failed to recreate session: {str(e)}")
            return False
    
    def check_session_valid(self):
        """Check if the current session is valid"""
        try:
            # Try to execute a simple JavaScript to check session
            self.driver.execute_script("return document.readyState")
            return True
        except:
            return False
    
    def refresh_and_get_data(self):
        """Refresh page and get new data"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"\n🔄 Refresh attempt {attempt + 1} of {max_retries}")
                
                # First check if session is valid
                if not self.check_session_valid():
                    print("⚠️ Session invalid, attempting recreation...")
                    if not self.force_recreate_session():
                        raise Exception("Failed to recreate session")
                    print("✅ Session recreated successfully")
                
                # Try to refresh the page
                self.driver.refresh()
                
                # Wait for data to load after refresh
                try:
                    # First wait for the page to be in ready state
                    WebDriverWait(self.driver, 30).until(
                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                    )
                    
                    # Then wait for specific elements
                    WebDriverWait(self.driver, 60).until(
                        EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Plates')]"))
                    )
                    print("✅ 'Plates' section loaded.")
                    
                    WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr"))
                    )
                    print("✅ Table rows found.")
                    
                except Exception as wait_error:
                    print(f"⚠️ Wait error: {str(wait_error)}")
                    # If waiting fails, try to recreate session
                    if self.force_recreate_session():
                        continue
                    else:
                        raise Exception("Failed to recover after wait error")
                
                # Give extra time for data to load
                time.sleep(5)
                
                # Get the page source with new data
                return BeautifulSoup(self.driver.page_source, "lxml")
                
            except Exception as e:
                print(f"❌ Refresh attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    print(f"⏳ Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    
                    # Try complete session recreation before next attempt
                    if not self.force_recreate_session():
                        print("❌ Failed to recreate session")
                        continue
        
        return None
    
    def initial_login(self):
        """Perform initial login"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"🔑 Login attempt {attempt + 1} of {max_retries}")
                username = "root"
                password = "pass"
                url_parts = VAXTOR_URL.split("//")
                auth_url = f"{url_parts[0]}//{username}:{password}@{url_parts[1]}"
                
                self.driver.get(auth_url)
                
                # Wait for page to load completely
                WebDriverWait(self.driver, 30).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                
                # Additional wait to ensure authentication is complete
                time.sleep(3)
                return True
                
            except Exception as e:
                print(f"❌ Login attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"⏳ Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
        return False
    
    def quit(self):
        """Close the browser"""
        try:
            if self.driver:
                self.driver.quit()
                print("✅ Browser closed")
        except Exception as e:
            print(f"⚠️ Error closing browser: {str(e)}")
            # Force quit if normal quit fails
            try:
                self.driver.quit()
            except:
                pass

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

def scrape_data_from_soup(soup, driver):
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
    total_rows = len(table.find("tbody").find_all("tr", recursive=False))
    processed_rows = 0
    successful_images = 0
    failed_images = 0
    
    print(f"\n🔄 Processing {total_rows} rows from the table...")
    
    for tr in table.find("tbody").find_all("tr", recursive=False):
        processed_rows += 1
        
        if tr.get("hidden"):
            continue
        
        all_cells = tr.find_all("td", recursive=False)
        if not all_cells:
            continue
            
        try:
            row_data = []
            plate_number = None
            
            # First get the plate number
            plate_index = header_indices.get('Plate')
            if plate_index is not None and plate_index < len(all_cells):
                plate_cell = all_cells[plate_index]
                plate_number = plate_cell.get_text(strip=True)
            
            if not plate_number:
                continue
                
            print(f"\n📝 Processing plate {plate_number} ({processed_rows}/{total_rows})")
            
            # Extract data for each target header
            for header in headers:
                index = header_indices[header]
                if index < len(all_cells):
                    td = all_cells[index]
                    text = td.get_text(strip=True)
                    
                    if header == 'Plate':
                        if not text:
                            continue
                    else:  # Make and Model
                        text = None if not text else text
                        
                    row_data.append(text)
                else:
                    row_data.append(None)
            
            # Handle image download
            image_index = None
            for i, th in enumerate(table.find("thead").find_all("th")):
                if th.get_text(strip=True) == 'Image':
                    image_index = i
                    break
                    
            if image_index is not None and image_index < len(all_cells):
                image_cell = all_cells[image_index]
                img_tag = image_cell.find('img')
                if img_tag and img_tag.get('src'):
                    image_url = img_tag['src']
                    # Convert relative URL to absolute URL
                    absolute_url = urljoin(VAXTOR_URL, image_url)
                    if download_image(driver, absolute_url, plate_number):
                        successful_images += 1
                    else:
                        failed_images += 1
            
            if row_data and row_data[0]:  # Only add if we have a plate number
                data_rows.append(row_data)
                
        except Exception as e:
            print(f"Warning: Error processing row: {e}")
            failed_images += 1
            continue
    
    # Print summary
    print(f"\n=== Processing Summary ===")
    print(f"Total rows processed: {processed_rows}")
    print(f"Successful image downloads: {successful_images}")
    print(f"Failed image downloads: {failed_images}")
    print("=" * 25)
    
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

def recognize_license_plate(image_path, token, regions=["sg"], strict_region=True, mmc=True):
    url = "https://api.platerecognizer.com/v1/plate-reader/"
    headers = {
        "Authorization": f"Token {token}"
    }
    
    # Open the image file
    with open(image_path, "rb") as fp:
        # Set up the data payload
        data = {
            "regions": regions,       # Specify relevant regions
            "mmc": str(mmc).lower()   # Enable make, model, color detection if set to True
        }
        if strict_region:
            data["config"] = json.dumps({"region": "strict"})  # Enforce strict region matching if needed

        # Send request with file upload
        response = requests.post(url, headers=headers, files={"upload": fp}, data=data)
        
        # Check response status and print results
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        else:
            print("Error:", response.status_code, response.text)
            return None

def compare_dataframes(old_df, new_df):
    """
    Compare two dataframes and return the changed/new rows
    Returns: tuple (changed_df, is_different)
    """
    if old_df is None:
        return new_df, True
    
    if new_df is None:
        return None, False
        
    # Make sure both dataframes have the same columns
    if set(old_df.columns) != set(new_df.columns):
        print("⚠️ Warning: Dataframes have different columns")
        return new_df, True
    
    # Sort both dataframes by index to ensure proper comparison
    old_df = old_df.reset_index(drop=True)
    new_df = new_df.reset_index(drop=True)
    
    # Check if dataframes are identical
    if old_df.equals(new_df):
        return None, False
    
    # Find rows that are in new_df but not in old_df
    changed_rows = pd.concat([new_df, old_df]).drop_duplicates(keep=False)
    
    return changed_rows, True

def should_process_plate_recognition(row_data, force_recognition=False):
    """
    Determine if plate recognition should be performed based on existing data
    
    Args:
        row_data: pandas Series containing the row data
        force_recognition: bool, if True will always perform recognition regardless of existing data
        
    Returns:
        bool: True if plate recognition should be performed
    """
    if force_recognition:
        return True
        
    # Check if either Make or Model is None/NaN/empty string
    is_make_missing = pd.isna(row_data.get('Make')) or str(row_data.get('Make')).strip() == ''
    is_model_missing = pd.isna(row_data.get('Model')) or str(row_data.get('Model')).strip() == ''
    
    # Return True if either Make or Model is missing
    return is_make_missing or is_model_missing

def send_to_local_endpoint(plate, make, model):
    """
    Send plate data to local endpoint
    
    Args:
        plate: str, license plate number
        make: str, vehicle make
        model: str, vehicle model
    """
    try:
        url = "http://13.54.166.90:5000/platerecognizer-alpr"
        data = {
            "plate": plate,
            "make": make,
            "model": model
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        print("\n=== Sending POST Request ===")
        print(f"URL: {url}")
        # print(f"Headers: {headers}")
        print(f"Data: {data}")

        print("=======")
        
        response = requests.post(
            url,
            json=data,
            headers=headers,
            timeout=5  # 5 second timeout
        )
        
        # print(f"Response Status Code: {response.status_code}")
        # print(f"Response Content: {response.text}")
        
        if response.status_code == 200 or response.status_code == 201:
            print(f"✅ Post Request of License Plate {plate}, Make {make} and Model {model} has been sent")
        else:
            print(f"❌ Failed to send data to local endpoint. Status code: {response.status_code}")
            print(f"Response content: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 5 seconds")
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error - Is the server running at {url}?")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending request: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def process_new_data(changed_df, force_recognition=False):
    """
    Process newly detected changes in the data
    
    Args:
        changed_df: DataFrame containing changed/new records
        force_recognition: bool, if True will perform recognition regardless of existing data
    """
    if changed_df is None or changed_df.empty:
        return
    
    print("\n=== New Changes Detected ===")
    print(f"Number of changed/new rows: {len(changed_df)}")
    print("\nChanged/New Records:")
    print(changed_df)
    
    # Get the most recent entry (first row)
    if not changed_df.empty:
        most_recent = changed_df.iloc[0]
        plate_number = most_recent['Plate']
        
        # Check if we should perform recognition - If true, then call Plate Recognition API
        if should_process_plate_recognition(most_recent, force_recognition):
            print(f"\n🔍 Processing plate {plate_number} - Make or Model is missing:")
            print(f"Current Make: {most_recent.get('Make', 'None')}")
            print(f"Current Model: {most_recent.get('Model', 'None')}")
            
            # Construct image path
            clean_plate = re.sub(r'[<>:"/\\|?*]', '', plate_number)
            image_path = os.path.join(IMAGES_DIR, f"{clean_plate}.jpg")
            
            if os.path.exists(image_path):
                try:
                    # Call the plate recognition API
                    result = recognize_license_plate(
                        image_path=image_path,
                        token=API_TOKEN,
                        regions=["sg"],
                        strict_region=True,
                        mmc=True
                    )
                    
                    if result:
                        print("\n=== Plate Recognition Results ===")
                        pprint(result)
                        
                        # Extract make and model from recognition results
                        # If PlateRecognizer doesn't recognize make/model, use defaults
                        make = result.get('make', 'Toyota')  # Default to Toyota if not recognized
                        model = result.get('model', 'Corolla')  # Default to Corolla if not recognized
                        
                        # Send data to local endpoint with either recognized or default values
                        send_to_local_endpoint(plate_number, make, model)
                    else:
                        print("❌ Failed to get plate recognition results")
                        # Use default values if recognition fails
                        send_to_local_endpoint(plate_number, "Toyota", "Corolla")
                        
                except Exception as e:
                    print(f"❌ Error processing plate recognition: {str(e)}")
                    # Use default values if there's an error
                    send_to_local_endpoint(plate_number, "Toyota", "Corolla")
            else:
                print(f"❌ Image not found for plate: {plate_number}")
        else:
            print(f"\nℹ️ Skipping plate recognition for {plate_number} - both Make and Model exist:")
            print(f"Make: {most_recent.get('Make')}")
            print(f"Model: {most_recent.get('Model')}")
            
            # Send existing data to local endpoint
            send_to_local_endpoint(
                plate_number,
                most_recent.get('Make'),
                most_recent.get('Model')
            )
    
    print("=" * 50)

def continuous_scraping(interval=10, max_retries=3, retry_delay=5, force_recognition=False):
    """
    Continuous scraping with single browser session
    
    Args:
        interval: int, seconds between scrapes
        max_retries: int, maximum number of retry attempts
        retry_delay: int, seconds to wait between retries
        force_recognition: bool, if True will perform recognition regardless of existing data
    """
    print(f"\n=== Starting continuous scraping (every {interval} seconds) ===")
    print(f"Force recognition mode: {'ON' if force_recognition else 'OFF'}")
    
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
                    
                    # Use the common scraping function with browser driver
                    result_df = scrape_data_from_soup(soup, browser.driver)
                    if result_df is None:
                        raise Exception("Failed to extract data")
                    
                    # Compare with previous data and process changes
                    changed_df, is_different = compare_dataframes(previous_df, result_df)
                    if is_different:
                        process_new_data(changed_df, force_recognition)
                    
                    # Print the DataFrame
                    print("\n📊 Current DataFrame:")
                    if result_df.empty:
                        print("DataFrame is empty!")
                    else:
                        print(f"Shape: {result_df.shape}")
                        print(result_df)
                    
                    # If we get here, the scrape was successful
                    success = True
                    consecutive_failures = 0  # Reset failure counter
                    
                    # Save if data changed
                    if not result_df.empty:
                        if not is_different:
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
                    
                    # Try complete session recreation before next attempt
                    if not browser.force_recreate_session():
                        print("❌ Failed to recreate session")
                        continue
            
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
    continuous_scraping(interval=5, force_recognition = False)