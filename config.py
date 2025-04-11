import os

# URLs
VAXTOR_URL = "http://169.254.206.95/local/Vaxreader/index.html#/"

# Directories
DATA_DIR = "vaxtor_data"
IMAGES_DIR = "Vaxtor_Images"

# API Configuration
API_TOKEN = "210ed0449ee06e8d9bcee4a67c742814e4e7366e"
LOCAL_ENDPOINT_URL = "http://13.238.255.9:5000/platerecognizer-alpr"

# Browser Configuration
BROWSER_OPTIONS = {
    "disable_gpu": True,
    "no_sandbox": True,
    "headless": True,
    "window_size": "1920,1080",
    "disable_dev_shm_usage": True,
    "disable_browser_side_navigation": True,
    "disable_features": "VizDisplayCompositor"
}

# Scraping Configuration
SCRAPING_INTERVAL = 5  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Create directories if they don't exist
for directory in [DATA_DIR, IMAGES_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory) 