#!/usr/bin/env python3
"""
Improved Test Script with Better Error Handling and Debugging

This version includes:
- More detailed logging
- Better anti-detection measures
- Overlay removal
- Enhanced iframe detection
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys
import os

# Add parent directory to path to import RecaptchaSolver
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solver import RecaptchaSolver, StandardDelayConfig


def setup_driver_enhanced():
    """
    Setup Chrome WebDriver with enhanced anti-detection measures.
    """
    options = webdriver.ChromeOptions()

    # Critical anti-detection measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)

    # Performance options
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")

    # Privacy
    options.add_argument("--incognito")

    # Realistic user agent
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    # Window size (important for element visibility)
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")

    print("[INFO] Initializing Chrome WebDriver...")
    driver = webdriver.Chrome(options=options)

    # Execute anti-detection JavaScript
    print("[INFO] Injecting anti-detection scripts...")
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            // Hide webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override chrome property
            window.chrome = {
                runtime: {}
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        '''
    })

    print("[SUCCESS] WebDriver initialized with anti-detection measures")
    return driver


def remove_overlay(driver):
    """
    Remove any overlay elements that might block clicks.
    """
    try:
        driver.execute_script("""
            // Remove all fixed position overlays with high z-index
            let overlays = document.querySelectorAll('[style*="z-index: 2000000000"]');
            overlays.forEach(el => el.remove());
            
            // Remove all elements with opacity < 0.1 that might be blocking
            let transparent = document.querySelectorAll('[style*="opacity: 0.0"]');
            transparent.forEach(el => el.remove());
            
            console.log('Removed overlay elements');
        """)
        print("[INFO] Removed potential overlay elements")
    except Exception as e:
        print(f"[WARN] Could not remove overlays: {e}")


def diagnose_page(driver):
    """
    Diagnose the current page state for debugging.
    """
    try:
        print("\n" + "="*70)
        print("PAGE DIAGNOSTICS")
        print("="*70)
        
        # Current URL
        print(f"Current URL: {driver.current_url}")
        
        # Find all iframes
        driver.switch_to.default_content()
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Total iframes found: {len(iframes)}")
        
        for i, iframe in enumerate(iframes):
            title = iframe.get_attribute("title")
            src = iframe.get_attribute("src")
            print(f"  Iframe {i+1}:")
            print(f"    Title: {title}")
            print(f"    Src: {src[:80]}..." if src and len(src) > 80 else f"    Src: {src}")
        
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"[WARN] Diagnostics failed: {e}")

def test_recaptcha_alternative():
    """
    Alternative test method using solve_recaptcha_v2_challenge directly
    (for invisible reCAPTCHA or when challenge appears automatically).
    """
    driver = None

    try:
        print("\n" + "="*70)
        print("ALTERNATIVE reCAPTCHA v2 TEST (Direct Challenge)")
        print("="*70)

        driver = setup_driver_enhanced()
        
        url = "https://www.google.com/recaptcha/api2/demo"
        print(f"\n[INFO] Navigating to {url}")
        driver.get(url)
        time.sleep(3)

        solver = RecaptchaSolver(
            driver=driver,
            service_language='en-US',
            delay_config=StandardDelayConfig(),
            max_retries=5
        )

        # Click checkbox first (manual or via JavaScript)
        driver.switch_to.default_content()
        checkbox_iframe = driver.find_element(
            By.XPATH, "//iframe[contains(@src, 'recaptcha') and contains(@src, 'anchor')]"
        )
        driver.switch_to.frame(checkbox_iframe)
        
        checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'recaptcha-anchor'))
        )
        driver.execute_script('arguments[0].click();', checkbox)
        print("[INFO] Clicked checkbox")
        
        driver.switch_to.default_content()
        time.sleep(3)

        # If challenge appears, solve it
        try:
            challenge_iframe = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//iframe[contains(@src, 'recaptcha') and contains(@src, 'bframe')]")
                )
            )
            print("[INFO] Challenge appeared, solving...")
            solver.solve_recaptcha_v2_challenge(iframe=challenge_iframe)
            
            time.sleep(2)
            success = solver.is_solved()
            print(f"[RESULT] Challenge solved: {success}")
            
        except Exception as e:
            print(f"[INFO] No challenge appeared or already solved: {e}")
            success = solver.is_solved()

        time.sleep(5)
        return success

    except Exception as e:
        print(f"[ERROR] Alternative test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    try:
        success = test_recaptcha_alternative()
        exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n[INFO] Test interrupted by user")
        exit(1)