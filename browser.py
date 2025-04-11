from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from config import VAXTOR_URL, BROWSER_OPTIONS

class BrowserSession:
    def __init__(self):
        self.driver = None
        self.setup_browser()
    
    def setup_browser(self):
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            
            options = Options()
            for option, value in BROWSER_OPTIONS.items():
                if isinstance(value, bool) and value:
                    options.add_argument(f"--{option.replace('_', '-')}")
                elif isinstance(value, str):
                    options.add_argument(f"--{option.replace('_', '-')}={value}")
            
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            print("✅ Browser initialized successfully")
            
            if not self.initial_login():
                raise Exception("Failed to perform initial login")
                
        except Exception as e:
            print(f"❌ Failed to initialize browser: {str(e)}")
            self.driver = None
    
    def force_recreate_session(self):
        print("🔄 Forcing complete session recreation...")
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            
            time.sleep(2)
            self.setup_browser()
            return self.driver is not None
            
        except Exception as e:
            print(f"❌ Failed to recreate session: {str(e)}")
            return False
    
    def check_session_valid(self):
        try:
            self.driver.execute_script("return document.readyState")
            return True
        except:
            return False
    
    def refresh_and_get_data(self):
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"\n🔄 Refresh attempt {attempt + 1} of {max_retries}")
                
                if not self.check_session_valid():
                    print("⚠️ Session invalid, attempting recreation...")
                    if not self.force_recreate_session():
                        raise Exception("Failed to recreate session")
                    print("✅ Session recreated successfully")
                
                self.driver.refresh()
                
                try:
                    WebDriverWait(self.driver, 30).until(
                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                    )
                    
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
                    if self.force_recreate_session():
                        continue
                    else:
                        raise Exception("Failed to recover after wait error")
                
                time.sleep(5)
                
                return self.driver.page_source
                
            except Exception as e:
                print(f"❌ Refresh attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    print(f"⏳ Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    
                    if not self.force_recreate_session():
                        print("❌ Failed to recreate session")
                        continue
        
        return None
    
    def initial_login(self):
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
                
                WebDriverWait(self.driver, 30).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                
                time.sleep(3)
                return True
                
            except Exception as e:
                print(f"❌ Login attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"⏳ Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
        return False
    
    def quit(self):
        try:
            if self.driver:
                self.driver.quit()
                print("✅ Browser closed")
        except Exception as e:
            print(f"⚠️ Error closing browser: {str(e)}")
            try:
                self.driver.quit()
            except:
                pass 