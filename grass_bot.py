import os
import time
import requests
import json
from cryptography.fernet import Fernet
from datetime import datetime

# Configuration
AUTH_TOKEN = "YOUR_ENCRYPTED_AUTH_TOKEN"  # Encrypted token (see setup guide)
PROXY = "http://<proxy_address>:<proxy_port>"  # Replace with your proxy
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"
ENCRYPTION_KEY = b"YOUR_ENCRYPTION_KEY"  # Generate using Fernet.generate_key()

# User-Agent Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 10; SM-A505FN) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
]

# Encryption Setup
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_token(token):
    """Encrypt the authentication token."""
    return cipher_suite.encrypt(token.encode())

def decrypt_token(encrypted_token):
    """Decrypt the authentication token."""
    return cipher_suite.decrypt(encrypted_token).decode()

# Proxy Setup
def get_proxy():
    """Return a proxy or fallback to a public proxy."""
    try:
        requests.get("http://example.com", proxies={"http": PROXY, "https": PROXY}, timeout=5)
        return PROXY
    except:
        return "http://<public_proxy_address>:<public_proxy_port>"  # Replace with a public proxy

# Telegram Logger
class TelegramLogger:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def log(self, message):
        """Send a log message to the Telegram channel."""
        payload = {
            "chat_id": self.chat_id,
            "text": message
        }
        try:
            response = requests.post(self.base_url, json=payload)
            response.raise_for_status()
            print("Log sent to Telegram successfully!")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send log to Telegram: {e}")

# Grass API Client
class GrassAPI:
    def __init__(self, auth_token):
        self.base_url = "https://api.getgrass.io"
        self.auth_token = auth_token
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENTS[0]  # Rotate user agents
        }
        self.proxy = get_proxy()
        self.session = requests.Session()

    def rotate_user_agent(self):
        """Rotate the User-Agent header."""
        self.headers["User-Agent"] = USER_AGENTS[(USER_AGENTS.index(self.headers["User-Agent"]) + 1) % len(USER_AGENTS)]

    def get_balance(self):
        """Retrieve the current points balance."""
        endpoint = f"{self.base_url}/user/points"
        try:
            response = self.session.get(endpoint, headers=self.headers, proxies={"http": self.proxy, "https": self.proxy})
            if response.status_code == 200:
                return response.json().get("balance", 0)
            elif response.status_code in [401, 403]:
                print("Unauthorized or Forbidden. Check your auth token.")
                return None
            else:
                print(f"Failed to fetch balance. Status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching balance: {e}")
            return None

    def farm_points(self, source, volume, duration):
        """Farm points using the /traffic/farm endpoint."""
        endpoint = f"{self.base_url}/traffic/farm"
        payload = {
            "source": source,
            "volume": volume,
            "duration": duration
        }
        try:
            response = self.session.post(endpoint, json=payload, headers=self.headers, proxies={"http": self.proxy, "https": self.proxy})
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Farming failed. Status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error farming points: {e}")
            return None

# Main Bot
class GrassBot:
    def __init__(self):
        self.auth_token = decrypt_token(AUTH_TOKEN)
        self.grass_api = GrassAPI(self.auth_token)
        self.telegram_logger = TelegramLogger(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

    def run(self):
        """Run the bot continuously for 24 hours with automatic restarts."""
        start_time = time.time()
        while time.time() - start_time < 86400:  # 24 hours
            try:
                # Check balance
                balance = self.grass_api.get_balance()
                if balance is not None:
                    self.telegram_logger.log(f"Current balance: {balance} points")

                # Farm points
                farming_result = self.grass_api.farm_points(source="organic", volume=100, duration=60)
                if farming_result:
                    self.telegram_logger.log(f"Farming progress: {farming_result.get('progress', 0)}%")

                # Rotate User-Agent
                self.grass_api.rotate_user_agent()

                # Wait before the next iteration
                time.sleep(60)  # Adjust interval as needed

            except Exception as e:
                print(f"Error: {e}. Restarting bot...")
                time.sleep(10)  # Wait before restarting

# Entry Point
if __name__ == "__main__":
    bot = GrassBot()
    bot.run()
