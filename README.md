## How to Setup this code:

### Pre-requisites:
Git clone this repository in your local file system.

pip install -r requirements.txt of this [folder](https://github.com/yash2mehta/WebScraper-Vaxtor) to install the following libraries:

 1. selenium
 2. beautifulsoup4
 3. pandas
 4. webdriver-manager
 5. lxml

Ensure you have the latest Chrome version installed on your system (necessary for selenium to work)

### AWS:

Login to AWS, go to EC2 Instances, Start Vaxtor_Server instance.

Click on Connect, it will then bring you to a CLI screen.

Type the following in the CLI:
 - `sudo su`
 - `cd LATEST_SERVER`
 - `cd Vaxtor-Server`
 - `git pull`
 - `source venv/bin/activate`
 - `python app.py`

### Within the code:

Refer to your AWS instance Public IPv4 address. To check that the server is working, go to  [http://XX.XX.XX.XX:5000](http://xx.xx.xx.xx:5000/)  on your browser.

Open the following URLs to view the result:
 - [http://XX.XX.XX.XX:5000/home/platerecognizer](http://xx.xx.xx.xx:5000/)
 - [http://XX.XX.XX.XX:5000/platerecognizer-record-latest](http://xx.xx.xx.xx:5000/)

Within the code, edit the following lines which are variable:

 - VAXTOR_URL with the link where Vaxtor is running on your system
 - In send_to_local_endpoint function, replace the url variable with the AWS Instance - [http://XX.XX.XX.XX:5000]
 - Change the API_TOKEN if the PlateRecognizer token has changed

### How to setup Vaxtor (extra):

 1. Connect the camera to your laptop with an Ethernet port (ensure all lights are green on the switch)
 2. Open AXIS IP Utility on your laptop. Click on the camera, wait for it to load the URL (click Continue Anyway if any errors occur on UI). Finally, launch the Vaxtor URL on browser.
 3. Scan the license plate, ensure it is scanned on Vaxtor UI and it should appear on the above links - [http://XX.XX.XX.XX:5000/home/platerecognizer] and [http://XX.XX.XX.XX:5000/platerecognizer-record-latest]
