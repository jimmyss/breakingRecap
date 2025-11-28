# Quick Start

## Get Started in 5 Minutes

### Step 1: Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install FFmpeg
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt-get install ffmpeg

# Windows: See https://www.wikihow.com/Install-FFmpeg-on-Windows
```

### Step 2: Run Tests

#### Option A: Basic Version (Simple)
```bash
python test.py
```

#### Option B: Advanced Version (Recommended)
```bash
python test_advanced.py
```

### Step 3: Integrate into Your Project

#### Basic Integration
```python
from selenium import webdriver
from RecaptchaSolver import RecaptchaSolver

options = webdriver.ChromeOptions()
options.add_argument("--incognito")
driver = webdriver.Chrome(options=options)

driver.get("YOUR_URL_WITH_RECAPTCHA")
solver = RecaptchaSolver(driver)
solver.solveCaptcha()
```

#### Advanced Integration (with Retry)
```python
from selenium import webdriver
from RecaptchaSolverAdvanced import RecaptchaSolverAdvanced

options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
driver = webdriver.Chrome(options=options)

driver.get("YOUR_URL_WITH_RECAPTCHA")
solver = RecaptchaSolverAdvanced(driver, max_retries=3)
success = solver.solveCaptcha()

if success:
    print("Success!")
```

## Common Commands

```bash
# Default run
python test_advanced.py

# Custom URL
python test_advanced.py --url https://example.com/login

# Increase retry count
python test_advanced.py --max-retries 5

# Headless mode (no browser display)
python test_advanced.py --headless

# View help
python test_advanced.py --help
```

## ⚠️ Important Notice

**Use ONLY for**:
- ✅ Educational purposes
- ✅ Security research
- ✅ Testing your own websites
- ✅ Authorized testing

**DO NOT use for**:
- ❌ Bulk registration
- ❌ Spamming
- ❌ Malicious attacks
- ❌ Unauthorized access
