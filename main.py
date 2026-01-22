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
# ⚙️ 核心讀取與初始化
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

cfg = load_config()
JWT_TOKEN = cfg["JWT_TOKEN"]
PRIVATE_KEY_HEX = cfg["PRIVATE_KEY_HEX"]
SYMBOL = cfg["SYMBOL"]
BASE_URL = cfg["BASE_URL"]
ORDER_QTY = str(cfg["ORDER_QTY"]) # 確保為字串
TARGET_BPS = float(cfg.get("TARGET_BPS", 8))
REFRESH_RATE = float(cfg.get("REFRESH_RATE", 0.5))

class StandXBot:
    def __init__(self):
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

    def cancel_all_orders(self):
        payload_data = {"symbol": SYMBOL}
        js = json.dumps(payload_data)
        return self.session.post(f"{BASE_URL}/api/cancel_all", data=js, headers=self._get_headers(js))

    def place_order(self, side, price):
        payload = {
            "symbol": SYMBOL,
            "side": side,
            "order_type": "limit",
            "qty": ORDER_QTY,
            "price": str(price),
            "time_in_force": "gtc",
            "reduce_only": False
        }
        js = json.dumps(payload)
        resp = self.session.post(f"{BASE_URL}/api/new_order", data=js, headers=self._get_headers(js))
        try:
            return resp.json()
        except:
            return {"status": "error", "message": resp.text}

# ==========================================
# 🚀 啟動邏輯
# ==========================================
def run():
    bot = StandXBot()
    print("🚀 正在連線市場...")
    
    while True:
        if bot.mid_price == 0:
            time.sleep(1)
            continue
        
        buy_p = math.floor(bot.mid_price * (1 - TARGET_BPS/10000))
        sell_p = math.ceil(bot.mid_price * (1 + TARGET_BPS/10000))
        
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"--- StandX MM 運作中 ---")
        print(f"當前價格: {bot.mid_price}")
        print(f"計畫掛單: 買 {buy_p} | 賣 {sell_p}")
        print("-" * 30)

        try:
            # 同步執行撤單與掛單
            bot.cancel_all_orders()
            res_b = bot.place_order("buy", buy_p)
            res_s = bot.place_order("sell", sell_p)
            
            # 詳細解析狀態
            b_msg = "成功" if res_b.get("status") == "success" else res_b.get("message", "拒絕")
            s_msg = "成功" if res_s.get("status") == "success" else res_s.get("message", "拒絕")
            
            print(f"💰 買單狀態: {b_msg}")
            print(f"💰 賣單狀態: {s_msg}")
            
        except Exception as e:
            print(f"⚠️ 異常: {e}")

        time.sleep(REFRESH_RATE)

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"❌ 崩潰: {e}")
        input("按 Enter 鍵關閉...")
