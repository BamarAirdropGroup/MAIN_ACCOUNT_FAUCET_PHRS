import requests
import json
import time
from colorama import init, Fore, Style
from eth_account import Account
import os
import random
from web3 import Web3
from requests.exceptions import ProxyError

class FaucetClaimer:
    def __init__(self):
        init(autoreset=True)  
        self.capmonster_api_key = self._read_api_key()
        self.capmonster_url = "https://api.capmonster.cloud"
        self.site_key = "6LcFofArAAAAAMUs2mWr4nxx0OMk6VygxXYeYKuO"
        self.site_url = "https://faroswap.xyz"
        self.faucet_url = "https://api.dodoex.io/gas-faucet-server/faucet/claim"
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://faroswap.xyz',
            'priority': 'u=1, i',
            'referer': 'https://faroswap.xyz/',
            'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
        }
        self.wallets = []
        self.proxies = self._load_proxies()
        self.max_proxy_retries = 3  # Maximum number of proxy retries

    def _read_api_key(self):
        try:
            with open('key.txt', 'r') as f:
                api_key = f.read().strip()
            if not api_key:
                print(Fore.RED + "Error: API key is empty in key.txt")
                exit(1)
            return api_key
        except FileNotFoundError:
            print(Fore.RED + "Error: key.txt not found")
            exit(1)
        except Exception as e:
            print(Fore.RED + f"Error reading API key: {e}")
            exit(1)

    def _load_proxies(self):
        proxies = []
        try:
            with open('proxy.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            user_pass, ip_port = line.split('@')
                            proxy = {
                                'http': f'http://{user_pass}@{ip_port}',
                                'https': f'http://{user_pass}@{ip_port}'
                            }
                            proxies.append(proxy)
                        except ValueError:
                            print(Fore.RED + f"Invalid proxy format: {line}")
            if proxies:
                print(Fore.GREEN + f"Loaded {len(proxies)} proxies from proxy.txt")
            else:
                print(Fore.YELLOW + "No proxies found in proxy.txt, using direct connection")
            return proxies
        except FileNotFoundError:
            print(Fore.YELLOW + "proxy.txt not found, using direct connection")
            return []
        except Exception as e:
            print(Fore.RED + f"Error reading proxy.txt: {e}")
            return []

    def _load_wallets(self):
        try:
            with open('privatekey.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            private_key = line
                            account = Account.from_key(private_key)
                            self.wallets.append({
                                'address': account.address,
                                'private_key': private_key
                            })
                            print(Fore.CYAN + f"Loaded wallet address: {account.address}")
                        except ValueError:
                            print(Fore.RED + f"Invalid private key: {line}")
            if not self.wallets:
                print(Fore.RED + "No valid private keys found in privatekey.txt")
                exit(1)
        except FileNotFoundError:
            print(Fore.RED + "Error: privatekey.txt not found")
            exit(1)
        except Exception as e:
            print(Fore.RED + f"Error reading privatekey.txt: {e}")
            exit(1)

    def _solve_captcha(self, proxy=None):
        payload = {
            "clientKey": self.capmonster_api_key,
            "task": {
                "type": "RecaptchaV2TaskProxyless",
                "websiteURL": self.site_url,
                "websiteKey": self.site_key
            }
        }
        try:
            response = requests.post(f"{self.capmonster_url}/createTask", json=payload, proxies=proxy)
            response.raise_for_status()
            result = response.json()
            task_id = result.get("taskId")
            if not task_id:
                print(Fore.RED + f"Error: Failed to create CAPTCHA task: {result}")
                return None

            print(Fore.YELLOW + "Solving CAPTCHA...")
            for _ in range(30):
                time.sleep(5)
                result = requests.post(f"{self.capmonster_url}/getTaskResult", json={"clientKey": self.capmonster_api_key, "taskId": task_id}, proxies=proxy)
                result.raise_for_status()
                result_data = result.json()
                if result_data.get("status") == "ready":
                    token = result_data.get("solution", {}).get("gRecaptchaResponse")
                    print(Fore.GREEN + "CAPTCHA solved successfully")
                    return token
                elif result_data.get("errorId") != 0:
                    print(Fore.RED + f"CAPTCHA error: {result_data.get('errorDescription')}")
                    return None
            print(Fore.RED + "CAPTCHA solving timeout")
            return None
        except ProxyError as e:
            print(Fore.RED + f"Proxy error solving CAPTCHA: {e}")
            return None
        except requests.RequestException as e:
            print(Fore.RED + f"Error solving CAPTCHA: {e} - Response: {e.response.text if e.response else 'No response'}")
            return None
        except Exception as e:
            print(Fore.RED + f"Unexpected error solving CAPTCHA: {e}")
            return None

    def _claim_faucet(self, wallet, captcha_token, proxy=None):
        payload = {
            "address": wallet['address'],
            "chainId": 688689,
            "recaptchaToken": captcha_token
        }
        try:
            response = requests.post(self.faucet_url, headers=self.headers, json=payload, proxies=proxy)
            response.raise_for_status()
            result = response.json()
            (Fore.YELLOW + f"Faucet response: {json.dumps(result, indent=2)}")
            
            if result.get("code") == 0:
                tx_hash = result.get("data", {}).get("txHash")
                if tx_hash:
                    print(Fore.GREEN + f"Faucet request successful!!")
                    print(Fore.CYAN + f"TX Hash: {tx_hash}")
                    print(Fore.CYAN + f"Explorer link: https://atlantic.pharosscan.xyz/tx/{tx_hash}")
                else:
                    print(Fore.GREEN + "Faucet request successful, but TX hash not found.")
                return True
            else:
                print(Fore.RED + f"Faucet claim failed for address {wallet['address']}: {result.get('msg', 'Unknown error')}")
                return False
        except ProxyError as e:
            print(Fore.RED + f"Proxy error claiming faucet for address {wallet['address']}: {e}")
            return None
        except requests.RequestException as e:
            print(Fore.RED + f"Error claiming faucet for address {wallet['address']}: {e} - Response: {e.response.text if e.response else 'No response'}")
            return False
        except Exception as e:
            print(Fore.RED + f"Unexpected error claiming faucet for address {wallet['address']}: {e}")
            return False

    def _process_wallet(self, wallet):
        retry_count = 0
        while retry_count < self.max_proxy_retries:
            proxy = random.choice(self.proxies) if self.proxies else None
            if proxy:
                print(Fore.YELLOW + f"Using proxy: {proxy['http']}")
            
            captcha_token = self._solve_captcha(proxy)
            if captcha_token is None and proxy is not None:
                print(Fore.RED + f"Proxy failed for {wallet['address']}, retrying with a different proxy...")
                retry_count += 1
                continue
            if not captcha_token:
                print(Fore.RED + f"Failed to solve CAPTCHA for {wallet['address']}. Skipping.")
                return
            
            result = self._claim_faucet(wallet, captcha_token, proxy)
            if result is None and proxy is not None:  # Proxy error
                print(Fore.RED + f"Proxy failed for {wallet['address']}, retrying with a different proxy...")
                retry_count += 1
                continue
            elif result:
                print(Fore.GREEN + f"Faucet claim successful for {wallet['address']}.")
                return
            else:
                print(Fore.RED + f"Faucet claim failed for {wallet['address']}.")
                return
        
        print(Fore.RED + f"Max proxy retries reached for {wallet['address']}. Skipping.")

    def run(self):
        while True:
            self.wallets = []  # Clear wallets for each run
            self._load_wallets()
            
            for wallet in self.wallets:
                print(Fore.CYAN + f"\nProcessing wallet: {wallet['address']}")
                self._process_wallet(wallet)
            
            print(Fore.YELLOW + f"\nWaiting for 24 hours before next run...")
            time.sleep(24 * 60 * 60)  # Sleep for 24 hours

if __name__ == "__main__":
    claimer = FaucetClaimer()
    claimer.run()
