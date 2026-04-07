import platform

# Platform-specific Chrome/Whale executable path
_platform = platform.system()

if _platform == "Windows":
    WHALE_EXECUTABLE_PATH = r"C:\Program Files\Naver\Naver Whale\whale.exe"
    CHROME_EXECUTABLE_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

elif _platform == "Darwin":  # macOS
    WHALE_EXECUTABLE_PATH = "/Applications/Naver Whale.app/Contents/MacOS/Naver Whale"
    CHROME_EXECUTABLE_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

else:  # Linux
    WHALE_EXECUTABLE_PATH = None
    CHROME_EXECUTABLE_PATH = None

# CDP connection settings (Whale/Chrome remote debugging)
CDP_PORT = 9223
CDP_HOST = "localhost"
CDP_URL = f"http://{CDP_HOST}:{CDP_PORT}"

# Whale launch command (Windows):
# "C:\Program Files\Naver\Naver Whale\whale.exe" --remote-debugging-port=9223 --user-data-dir="C:\whale-debug"

# Output settings
OUTPUT_DIR = "output"

# Scroll settings
SCROLL_PAUSE_SEC = 1.5
CAPTCHA_WAIT_SEC = 30
