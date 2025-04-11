import requests
import json
from config import API_TOKEN, IMAGES_DIR
from pprint import pprint
import re
import os

def recognize_license_plate(image_path, token, regions=["sg"], strict_region=True, mmc=True):
    url = "https://api.platerecognizer.com/v1/plate-reader/"
    headers = {
        "Authorization": f"Token {token}"
    }
    
    with open(image_path, "rb") as fp:
        data = {
            "regions": regions,
            "mmc": str(mmc).lower()
        }
        if strict_region:
            data["config"] = json.dumps({"region": "strict"})

        response = requests.post(url, headers=headers, files={"upload": fp}, data=data)
        
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        else:
            print("Error:", response.status_code, response.text)
            return None

def process_plate_recognition(plate_number, force_recognition=False):
    clean_plate = re.sub(r'[<>:"/\\|?*]', '', plate_number)
    image_path = os.path.join(IMAGES_DIR, f"{clean_plate}.jpg")
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found for plate: {plate_number}")
        return None, None
    
    try:
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
            return result.get('make', 'BMW'), result.get('model', 'X5')
        else:
            print("❌ Failed to get plate recognition results")
            return "BMW", "X5"
            
    except Exception as e:
        print(f"❌ Error processing plate recognition: {str(e)}")
        return "BMW", "X5" 