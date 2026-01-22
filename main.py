import requests
import time
import json
import uuid
import base64
import os
import sys
import threading
import websocket
import math
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# ==========================================
# 🛠️ 讀取設定檔 (支援 .exe 執行環境)
# ==========================================
def load_config():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_path, 'config.json')
    if not os.path.exists(config_path):
        print(f"❌ 找不到設定檔: {config_path}")
        time.sleep(5)
        sys.exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 載入參數
cfg = load_config()
JWT_TOKEN = cfg["JWT_TOKEN"]
PRIVATE_KEY_HEX = cfg["PRIVATE_KEY_HEX"]
SYMBOL = cfg["SYMBOL"]
BASE_URL = cfg["BASE_URL"]
ORDER_QTY = cfg["ORDER_QTY"]
TARGET_BPS = float(cfg.get("TARGET_BPS", 8))
REFRESH_RATE = float(cfg.get("REFRESH_RATE", 0.5))

# ==========================================
# 📡 核心交易類別
# ==========================================
class StandXBot:
    def __init__(self):
        # 處理私鑰格式
        key_hex = PRIVATE_KEY_HEX.replace("0x", "")
        self.signing_key = SigningKey(key_hex, encoder=HexEncoder)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {JWT_TOKEN}",
            "Content-Type": "application/json"
        })
        self.mid_price = 0.0
        self.ws_url = "wss://perps.standx.com/ws-stream/v1"
        threading.Thread(target=self._run_ws, daemon=True).start()

    def _on_message(self, ws, message):
        data = json.loads(message)
        if data.get("channel") == "price" and "data" in data:
            self.mid_price = float(data["data"].get("mid_price", 0))

    def _run_ws(self):
        while True:
            try:
                ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_open=lambda ws: ws.send(json.dumps({"subscribe":{"channel":"price","symbol":SYMBOL}})),
                    on_message=self._on_message
                )
                ws.run_forever()
            except: time.sleep(5)

    def _get_headers(self, payload):
        rid, ts = str(uuid.uuid4()), int(time.time() * 1000)
        msg = f"v1,{rid},{ts},{payload}"
        sig = base64.b64encode(self.signing_key.sign(msg.encode()).signature).decode()
        return {
            "x-request-sign-version": "v1",
            "x-request-id": rid,
            "x-request-timestamp": str(ts),
            "x-request-signature": sig
        }

    def place_order(self, side, price):
        payload = {
            "symbol": SYMBOL,
            "side": side,
            "order_type": "limit",
            "qty": ORDER_QTY,
            "price": str(price),
            "time_in_force": "gtc"
        }
        js = json.dumps(payload)
        return self.session.post(f"{BASE_URL}/api/new_order", data=js, headers=self._get_headers(js)).json()

# ==========================================
# 🚀 執行主循環
# ==========================================
def run():
    bot = StandXBot()
    print(f"✅ 機器人正式啟動 | 標的: {SYMBOL}")
    
    while True:
        if bot.mid_price == 0:
            print("⏳ 等待市場價格中...")
            time.sleep(2)
            continue
        
        # 計算買賣價格 (簡易 Market Making 邏輯)
        buy_p = math.floor(bot.mid_price * (1 - TARGET_BPS/10000))
        sell_p = math.ceil(bot.mid_price * (1 + TARGET_BPS/10000))
        
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"--- StandX 運行中 ---")
        print(f"當前市價: {bot.mid_price}")
        print(f"預計掛單: 買入 {buy_p} | 賣出 {sell_p}")
        
        # 這裡會根據你的策略發送訂單，建議先確認價格無誤
        # bot.place_order("buy", buy_p)
        
        time.sleep(REFRESH_RATE)

if __name__ == "__main__":
   try:
        run()
    except Exception as e:
        print(f"\n❌ 程式發生嚴重錯誤: {e}")
        print("\n請檢查 config.json 設定是否正確。")
        input("\n按 Enter 鍵退出...") # 這行會防止視窗直接關閉
