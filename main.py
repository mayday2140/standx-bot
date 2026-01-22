import json
import os
import sys
import time

# 讀取與 .exe 同資料夾的 config.json
def load_config():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    config_path = os.path.join(base_path, 'config.json')
    
    if not os.path.exists(config_path):
        print(f"❌ 找不到設定檔: {config_path}")
        print("請在程式旁邊建立 config.json 檔案。")
        time.sleep(10)
        sys.exit(1)
        
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- 這裡會載入你的參數 ---
try:
    cfg = load_config()
    print(f"✅ 成功載入設定！目標交易對: {cfg.get('SYMBOL')}")
    # 這裡會接你原本的交易邏輯代碼...
    # (為了演示，我們讓它印出設定值)
    for key, value in cfg.items():
        if "KEY" in key or "TOKEN" in key:
            print(f"{key}: ******** (已隱藏)")
        else:
            print(f"{key}: {value}")
except Exception as e:
    print(f"錯誤: {e}")

input("\n程式已啟動 (測試模式)，按 Enter 鍵關閉...")
