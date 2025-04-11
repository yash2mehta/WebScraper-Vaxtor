# Vaxtor Web Scraper

## Overview
The Vaxtor Web Scraper is an automated system that:
- Continuously monitors a Vaxtor web interface for license plate data
- Captures and processes license plate images
- Performs plate recognition to identify vehicle make and model
- Sends the processed data to a remote server
- Saves data locally for record-keeping

The system runs on a 5-second interval by default and includes built-in error handling and retry mechanisms.

## Installation and Setup

### Prerequisites
- Python 3.x installed on your system
- Latest version of Google Chrome browser
- Git installed on your system
- AWS account with EC2 instance access
- Ethernet connection for camera setup

### Software Installation
1. Clone this repository to your local system
2. Install required Python packages:
   ```
   pip install -r requirements.txt
   ```
   This will install:
   - selenium (4.18.1)
   - webdriver-manager (4.0.1)
   - beautifulsoup4 (4.12.3)
   - pandas (2.2.1)
   - requests (2.31.0)

### AWS Server Setup
1. Log in to AWS and navigate to EC2 Instances
2. Start the Vaxtor_Server instance
3. Connect to the instance and execute:
   ```
   sudo su
   cd LATEST_SERVER
   cd Vaxtor-Server
   git pull
   source venv/bin/activate
   python app.py
   ```

### Configuration
Edit the following in `config.py`:
- `VAXTOR_URL`: Update with your local Vaxtor system URL
- `LOCAL_ENDPOINT_URL`: Set to your AWS instance URL (http://XX.XX.XX.XX:5000)
- `API_TOKEN`: Update if the PlateRecognizer token changes

## Running the System

### Starting the Scraper
1. Ensure the AWS server is running
2. Open a terminal in the project directory
3. Run the main script:
   ```
   python main.py
   ```

### Monitoring the System
- The scraper will run continuously, checking for new data every 5 seconds
- Console output will show:
  - Scraping attempts and results
  - New data detection
  - Plate recognition processing
  - Data saving status

### Viewing Results
Access the following URLs in your browser:
- http://XX.XX.XX.XX:5000/home/platerecognizer
- http://XX.XX.XX.XX:5000/platerecognizer-record-latest

## Troubleshooting

### Common Errors and Solutions

#### Browser Initialization Issues
- **Error**: "Failed to start browser"
- **Solution**: 
  - Ensure Chrome is installed and up to date
  - Check if ChromeDriver is compatible with your Chrome version
  - Verify no other Chrome instances are running

#### Connection Issues
- **Error**: "Failed to refresh data" or "Connection error"
- **Solution**:
  - Verify network connectivity
  - Check if the Vaxtor system is accessible
  - Ensure AWS server is running and accessible

#### Plate Recognition Failures
- **Error**: "Failed to get plate recognition results"
- **Solution**:
  - Verify API token is valid
  - Check image quality and format
  - Ensure proper lighting conditions

#### Data Processing Issues
- **Error**: "Failed to extract data"
- **Solution**:
  - Check if the Vaxtor interface structure has changed
  - Verify table elements are present
  - Ensure proper permissions for data saving

### System Recovery
- The system includes automatic retry mechanisms (3 attempts)
- After 3 consecutive failures, the browser session is recreated
- If issues persist, restart the scraper and AWS server

### Camera Setup
1. Connect the camera to your laptop with an Ethernet port (ensure all lights are green on the switch)
2. Open AXIS IP Utility on your laptop
3. Click on the camera and wait for it to load the URL (click Continue Anyway if any errors occur on UI)
4. Launch the Vaxtor URL in your browser
5. Scan the license plate and verify it appears on:
   - http://XX.XX.XX.XX:5000/home/platerecognizer
   - http://XX.XX.XX.XX:5000/platerecognizer-record-latest

---
*This guide provides a comprehensive overview of the Web Scraper system designed for Vaxtor. For additional support or specific issues, please contact the development team.*
