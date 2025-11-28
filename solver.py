import os
import random
import asyncio
import aiohttp
import time
import uuid
import tempfile
import requests
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException
from pydub import AudioSegment
import speech_recognition as sr


class RecaptchaException(Exception):
    """Custom exception for reCAPTCHA solving errors."""
    pass


class DelayConfig:
    """Base class for delay configuration."""
    
    def delay_after_click_checkbox(self):
        """Delay after clicking the checkbox."""
        pass
    
    def delay_after_click_verify_button(self):
        """Delay after clicking the verify button."""
        pass


class StandardDelayConfig(DelayConfig):
    """Standard delay configuration with random delays."""
    
    def delay_after_click_checkbox(self):
        time.sleep(random.uniform(1.5, 3.0))
    
    def delay_after_click_verify_button(self):
        time.sleep(random.uniform(1.0, 2.0))


class RecaptchaSolver:
    """
    reCAPTCHA v2 solver using audio challenges.

    WARNING: This tool is for educational purposes, security research,
    and testing on authorized systems only. Unauthorized use may violate
    terms of service and applicable laws.
    """

    def __init__(
            self,
            driver: WebDriver,
            service_language: str = 'en-US',
            delay_config: Optional[DelayConfig] = None,
            max_retries: int = 3,
    ):
        """
        Initialize the RecaptchaSolver.

        Args:
            driver: Selenium WebDriver instance
            service_language: Language to use for speech recognition (default: en-US)
            delay_config: Optional delay configuration for human-like behavior
            max_retries: Maximum number of retry attempts for audio challenge errors
        """
        self.driver = driver
        self._language = service_language
        self._delay_config = delay_config or StandardDelayConfig()
        self._max_retries = max_retries

        # Initialize speech recognition API object
        self._recognizer = sr.Recognizer()
        # Disable dynamic energy threshold to avoid failed reCAPTCHA audio transcription
        self._recognizer.dynamic_energy_threshold = False

    def solve_recaptcha_v2_challenge(self, iframe: WebElement) -> None:
        """
        Solve a reCAPTCHA v2 challenge that has already appeared.

        Call this method directly on web pages with the "invisible reCAPTCHA" badge.

        Args:
            iframe: Web element for inline frame of reCAPTCHA challenge

        Raises:
            TimeoutException: if a timeout occurred while waiting
        """
        self.driver.switch_to.frame(iframe)

        # Try to switch to audio challenge
        try:
            audio_button = self._wait_for_element(
                by=By.XPATH,
                locator='//*[@id="recaptcha-audio-button"]',
                timeout=2,
            )
            self._js_click(audio_button)
            print("[INFO] Switched to audio challenge")
            
            # Wait for audio challenge to load
            time.sleep(random.uniform(2, 3))

        except TimeoutException:
            print("[INFO] Audio button not found, may already be in audio mode")
            pass

        # Solve the audio challenge
        self._solve_audio_challenge(self._language)

        # Locate verify button and click it
        verify_button = self._wait_for_element(
            by=By.ID,
            locator='recaptcha-verify-button',
            timeout=5,
        )

        self._js_click(verify_button)
        print("[INFO] Clicked verify button")

        if self._delay_config:
            self._delay_config.delay_after_click_verify_button()

        # Retry logic if error occurs
        for i in range(self._max_retries):
            try:
                # Check for error message
                self._wait_for_element(
                    by=By.CLASS_NAME,
                    locator='rc-audiochallenge-error-message',
                    timeout=1,
                )

                print(f"[INFO] Error detected, retrying ({i + 1}/{self._max_retries})...")

                # Solve audio challenge again
                self._solve_audio_challenge(self._language)

                # Locate verify button again to avoid stale element reference
                second_verify_button = self._wait_for_element(
                    by=By.ID,
                    locator='recaptcha-verify-button',
                    timeout=5,
                )

                self._js_click(second_verify_button)

            except TimeoutException:
                # No error message found, challenge likely solved
                break
        else:
            raise RecaptchaException('Failed to solve captcha after maximum retry attempts')

        self.driver.switch_to.parent_frame()

    def _solve_audio_challenge(self, language: str) -> None:
        """
        Download audio challenge, convert it, and recognize speech.

        Args:
            language: Language code for speech recognition

        Raises:
            RecaptchaException: if audio challenge cannot be solved
        """
        try:
            # Locate audio challenge download link
            download_link: WebElement = self._wait_for_element(
                by=By.CLASS_NAME,
                locator='rc-audiochallenge-tdownload-link',
                timeout=10,
            )

        except TimeoutException:
            raise RecaptchaException('Google has detected automated queries. Try again later.')

        # Create temporary directory and files using uuid
        tmp_dir = tempfile.gettempdir()
        id_ = uuid.uuid4().hex

        mp3_file = os.path.join(tmp_dir, f'{id_}_tmp.mp3')
        wav_file = os.path.join(tmp_dir, f'{id_}_tmp.wav')

        tmp_files = {mp3_file, wav_file}

        try:
            # Download audio file
            link = download_link.get_attribute('href')
            audio_download = requests.get(url=link, allow_redirects=True)

            with open(mp3_file, 'wb') as f:
                f.write(audio_download.content)

            print(f"[INFO] Downloaded audio to {mp3_file}")

            # Convert MP3 to WAV format for compatibility
            AudioSegment.from_mp3(mp3_file).export(wav_file, format='wav')
            print("[INFO] Converted audio to WAV format")

            # Recognize speech from audio file
            with sr.AudioFile(wav_file) as source:
                # Adjust for ambient noise
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self._recognizer.record(source)

            # Try recognition with multiple language fallbacks
            recognized_text = None
            languages = [language, 'en-US', 'en-GB', 'en']

            for lang in languages:
                try:
                    recognized_text = self._recognizer.recognize_google(
                        audio, language=lang
                    ).lower()
                    print(f"[INFO] Recognized CAPTCHA text: '{recognized_text}' (language: {lang})")
                    break
                except sr.UnknownValueError:
                    print(f"[WARN] Could not understand audio with language {lang}")
                    continue
                except sr.RequestError as e:
                    raise RecaptchaException(f'Speech recognition service error: {e}')

            if not recognized_text:
                raise RecaptchaException('Speech recognition API could not understand audio, try again')

        finally:
            # Clean up all temporary files
            for path in tmp_files:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        print(f"[WARN] Could not remove temp file {path}: {e}")

        # Write transcribed text to iframe's input box
        response_textbox = self.driver.find_element(By.ID, 'audio-response')
        response_textbox.clear()

        # Type text in human-like manner
        self._human_type(element=response_textbox, text=recognized_text)
        print("[INFO] Entered CAPTCHA text")

    def _js_click(self, element: WebElement) -> None:
        """
        Perform click on given web element using JavaScript.

        Args:
            element: web element to click
        """
        self.driver.execute_script('arguments[0].click();', element)

    def _wait_for_element(
        self,
        by: str = By.ID,
        locator: Optional[str] = None,
        timeout: float = 10,
    ) -> WebElement:
        """
        Try to locate web element within given duration.

        Args:
            by: strategy to use to locate element (see selenium.webdriver.common.by.By)
            locator: locator that identifies the element
            timeout: number of seconds to wait for element before raising TimeoutException

        Returns:
            Located web element

        Raises:
            TimeoutException: if element is not located within given duration
        """
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, locator))
        )

    @staticmethod
    def _human_type(element: WebElement, text: str) -> None:
        """
        Types in a way reminiscent of a human, with random delay between 50ms to 100ms 
        for every character.

        Args:
            element: Input element to type text to
            text: Input to be typed
        """
        for c in text:
            element.send_keys(c)
            time.sleep(random.uniform(0.05, 0.1))

    def is_solved(self) -> bool:
        """
        Check if the CAPTCHA has been solved.

        Returns:
            True if CAPTCHA is solved, False otherwise
        """
        try:
            self.driver.switch_to.default_content()

            # Switch to the reCAPTCHA checkbox iframe
            iframe_check = self.driver.find_element(
                By.XPATH, "//iframe[contains(@title, 'reCAPTCHA')]"
            )
            self.driver.switch_to.frame(iframe_check)

            # Find the checkbox element
            checkbox = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, 'recaptcha-anchor'))
            )

            aria_checked = checkbox.get_attribute("aria-checked")

            # Check if solved
            is_solved = aria_checked == "true"

            self.driver.switch_to.default_content()
            return is_solved

        except Exception as e:
            print(f"[ERROR] Failed to check CAPTCHA status: {e}")
            self.driver.switch_to.default_content()
            return False


# Backward compatibility alias
API = RecaptchaSolver