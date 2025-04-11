from datetime import datetime
import time
from bs4 import BeautifulSoup
from browser import BrowserSession
from scraper import scrape_data_from_soup
from data_processor import compare_dataframes, save_data, should_process_plate_recognition
from plate_recognizer import process_plate_recognition
from api_client import send_to_local_endpoint
from config import SCRAPING_INTERVAL, MAX_RETRIES, RETRY_DELAY

def process_new_data(changed_df, force_recognition=False):
    if changed_df is None or changed_df.empty:
        return
    
    print("\n=== New Changes Detected ===")
    print(f"Number of changed/new rows: {len(changed_df)}")
    print("\nChanged/New Records:")
    print(changed_df)
    
    if not changed_df.empty:
        most_recent = changed_df.iloc[0]
        plate_number = most_recent['Plate']
        
        if should_process_plate_recognition(most_recent, force_recognition):
            print(f"\n🔍 Processing plate {plate_number} - Make or Model is missing:")
            print(f"Current Make: {most_recent.get('Make', 'None')}")
            print(f"Current Model: {most_recent.get('Model', 'None')}")
            
            # Start timing plate recognition
            plate_recognition_start = time.time()
            make, model = process_plate_recognition(plate_number, force_recognition)
            plate_recognition_time = time.time() - plate_recognition_start
            print(f"\n⏱️ Plate recognition took: {plate_recognition_time:.2f} seconds")
            
            # Start timing local endpoint
            local_endpoint_start = time.time()
            send_to_local_endpoint(plate_number, make, model)
            local_endpoint_time = time.time() - local_endpoint_start
            print(f"⏱️ Local endpoint took: {local_endpoint_time:.2f} seconds")
            
            # Print total time
            total_time = plate_recognition_time + local_endpoint_time
            print(f"⏱️ Total processing time: {total_time:.2f} seconds")
        else:
            print(f"\nℹ️ Skipping plate recognition for {plate_number} - both Make and Model exist:")
            print(f"Make: {most_recent.get('Make')}")
            print(f"Model: {most_recent.get('Model')}")
            
            # Only time local endpoint when skipping plate recognition
            local_endpoint_start = time.time()
            send_to_local_endpoint(
                plate_number,
                most_recent.get('Make'),
                most_recent.get('Model')
            )
            local_endpoint_time = time.time() - local_endpoint_start
            print(f"⏱️ Local endpoint took: {local_endpoint_time:.2f} seconds")
    
    print("=" * 50)

def continuous_scraping(interval=SCRAPING_INTERVAL, force_recognition=False):
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
            for attempt in range(MAX_RETRIES):
                print(f"\n=== Attempt {attempt + 1} of {MAX_RETRIES} ===")
                
                try:
                    page_source = browser.refresh_and_get_data()
                    if not page_source:
                        raise Exception("Failed to refresh data")
                    
                    soup = BeautifulSoup(page_source, "lxml")
                    result_df = scrape_data_from_soup(soup, browser.driver)
                    if result_df is None:
                        raise Exception("Failed to extract data")
                    
                    changed_df, is_different = compare_dataframes(previous_df, result_df)
                    if is_different:
                        process_new_data(changed_df, force_recognition)
                    
                    print("\n📊 Current DataFrame:")
                    if result_df.empty:
                        print("DataFrame is empty!")
                    else:
                        print(f"Shape: {result_df.shape}")
                        print(result_df)
                    
                    success = True
                    consecutive_failures = 0
                    
                    if not result_df.empty:
                        if not is_different:
                            print("\nℹ️ No changes in data")
                        else:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            save_data(result_df, timestamp)
                            print("\n✅ New data saved")
                            previous_df = result_df.copy()
                    
                    break
                    
                except Exception as e:
                    print(f"❌ Attempt {attempt + 1} failed: {str(e)}")
                    if attempt < MAX_RETRIES - 1:
                        print(f"⏳ Waiting {RETRY_DELAY} seconds before retry...")
                        time.sleep(RETRY_DELAY)
                    
                    if not browser.force_recreate_session():
                        print("❌ Failed to recreate session")
                        continue
            
            if not success:
                consecutive_failures += 1
                print(f"\n⚠️ All {MAX_RETRIES} attempts failed")
                
                if consecutive_failures >= 3:
                    print("⚠️ Multiple consecutive failures detected. Recreating browser session...")
                    browser.quit()
                    browser = BrowserSession()
                    if not browser.driver:
                        print("❌ Failed to recreate browser session. Exiting...")
                        break
                    consecutive_failures = 0
            
            print(f"\n⏳ Waiting {interval} seconds until next scrape...")
            print("=" * 50)
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n⚠️ Stopping by user request")
        if previous_df is not None:
            print("\n📊 Last successful DataFrame:")
            print(previous_df)
    finally:
        browser.quit()

if __name__ == "__main__":
    continuous_scraping(force_recognition=False) 