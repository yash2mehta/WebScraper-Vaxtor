from bs4 import BeautifulSoup
import pandas as pd
import re
from urllib.parse import urljoin
from config import VAXTOR_URL, IMAGES_DIR
from browser import BrowserSession

def check_table_data(soup):
    table = soup.find("table", class_="table table-bordered table-hover table-condensed")
    if not table:
        return False
    
    tbody = table.find("tbody")
    if not tbody:
        return False
    
    visible_rows = [tr for tr in tbody.find_all("tr", recursive=False) 
                   if not tr.get("hidden")]
    
    return len(visible_rows) > 0

def download_image(driver, url, plate_number):
    try:
        clean_plate = re.sub(r'[<>:"/\\|?*]', '', plate_number)
        filename = f"{clean_plate}.jpg"
        filepath = os.path.join(IMAGES_DIR, filename)
        
        if os.path.exists(filepath):
            return True
            
        driver.get(url)
        img_element = driver.find_element(By.TAG_NAME, "img")
        if img_element:
            img_element.screenshot(filepath)
            print(f"✅ Downloaded image for plate {plate_number}")
            return True
        else:
            print(f"❌ No image found for plate {plate_number}")
            return False
                
    except Exception as e:
        print(f"❌ Failed to download image for plate {plate_number}: {str(e)}")
        return False

def scrape_data_from_soup(soup, driver):
    if not check_table_data(soup):
        print("❌ No data found in table")
        return None
    
    print("✅ Data found in table, proceeding with extraction...")
    
    table = soup.find("table", class_="table table-bordered table-hover table-condensed")
    if not table:
        return None
    
    target_headers = ['Plate', 'Make', 'Model']
    headers = []
    header_indices = {}
    
    for i, th in enumerate(table.find("thead").find_all("th")):
        header_text = th.get_text(strip=True)
        if not th.get("hidden") and header_text in target_headers:
            headers.append(header_text)
            header_indices[header_text] = i
    
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
            
            plate_index = header_indices.get('Plate')
            if plate_index is not None and plate_index < len(all_cells):
                plate_cell = all_cells[plate_index]
                plate_number = plate_cell.get_text(strip=True)
            
            if not plate_number:
                continue
                
            print(f"\n📝 Processing plate {plate_number} ({processed_rows}/{total_rows})")
            
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
                    absolute_url = urljoin(VAXTOR_URL, image_url)
                    if download_image(driver, absolute_url, plate_number):
                        successful_images += 1
                    else:
                        failed_images += 1
            
            if row_data and row_data[0]:
                data_rows.append(row_data)
                
        except Exception as e:
            print(f"Warning: Error processing row: {e}")
            failed_images += 1
            continue
    
    print(f"\n=== Processing Summary ===")
    print(f"Total rows processed: {processed_rows}")
    print(f"Successful image downloads: {successful_images}")
    print(f"Failed image downloads: {failed_images}")
    print("=" * 25)
    
    if not data_rows:
        return None
            
    df = pd.DataFrame(data_rows, columns=headers)
    
    if 'Make' in df.columns:
        df['Make'] = df['Make'].replace('', pd.NA)
    if 'Model' in df.columns:
        df['Model'] = df['Model'].replace('', pd.NA)
    
    return df 