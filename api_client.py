import requests
from config import LOCAL_ENDPOINT_URL

def send_to_local_endpoint(plate, make, model):
    try:
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
        print(f"URL: {LOCAL_ENDPOINT_URL}")
        print(f"Data: {data}")
        print("=======")
        
        response = requests.post(
            LOCAL_ENDPOINT_URL,
            json=data,
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200 or response.status_code == 201:
            print(f"✅ Post Request of License Plate {plate}, Make {make} and Model {model} has been sent")
        else:
            print(f"❌ Failed to send data to local endpoint. Status code: {response.status_code}")
            print(f"Response content: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 5 seconds")
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error - Is the server running at {LOCAL_ENDPOINT_URL}?")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending request: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}") 