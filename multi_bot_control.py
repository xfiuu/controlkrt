# PHIÊN BẢN CUỐI CÙNG - MÔ PHỎNG LOGIC GỐC
import discum
import threading
import time
import os
import random
import re
import requests
import json
from flask import Flask, request, render_template_string, jsonify
from dotenv import load_dotenv

load_dotenv()

# --- CẤU HÌNH ---
tokens = os.getenv("TOKENS").split(",") if os.getenv("TOKENS") else []
other_channel_id = os.getenv("OTHER_CHANNEL_ID")
ktb_channel_id = os.getenv("KTB_CHANNEL_ID")
work_channel_id = os.getenv("WORK_CHANNEL_ID")
daily_channel_id = os.getenv("DAILY_CHANNEL_ID")
kvi_channel_id = os.getenv("KVI_CHANNEL_ID")
spam_channel_ids = os.getenv("SPAM_CHANNEL_ID", "").split(',') if os.getenv("SPAM_CHANNEL_ID") else []
karuta_id = "646937666251915264"
karibbit_id = "1274445226064220273"

main_bot_configs = {}
GREEK_LETTERS = {1: "ALPHA", 2: "BETA", 3: "GAMMA", 4: "DELTA", 5: "EPSILON", 6: "ZETA"}
for i in range(1, 7):
    token_env_name = f"MAIN_TOKEN_{i}" if i > 1 else "MAIN_TOKEN"
    token = os.getenv(token_env_name)
    if token:
        channels_str = os.getenv(f"MAIN_{i}_CHANNELS", "")
        channels = [c.strip() for c in channels_str.split(',') if c.strip()]
        main_bot_configs[i] = {
            "token": token,
            "channels": channels,
            "name": GREEK_LETTERS.get(i, f"MAIN_{i}")
        }

# --- BIẾN TRẠNG THÁI ---
bots, main_bots = [], {}
acc_names = [
    "Blacklist", "Khanh bang", "Dersale", "Venus", "WhyK", "Tan",
    "Ylang", "Nina", "Nathan", "Ofer", "White", "the Wicker", "Leader", "Tess", "Wyatt", "Daisy", "CantStop", "Token",
]

auto_grab_enabled_1, auto_grab_enabled_2, auto_grab_enabled_3, auto_grab_enabled_4, auto_grab_enabled_5, auto_grab_enabled_6 = False, False, False, False, False, False
heart_threshold_1, heart_threshold_2, heart_threshold_3, heart_threshold_4, heart_threshold_5, heart_threshold_6 = 50, 50, 50, 50, 50, 50

spam_enabled, auto_work_enabled, auto_reboot_enabled = False, False, False
spam_message, spam_delay, work_delay_between_acc, work_delay_after_all, auto_reboot_delay = "", 10, 10, 44100, 3600
auto_daily_enabled = False
daily_delay_after_all = 87000
daily_delay_between_acc = 3
auto_kvi_enabled = False
kvi_click_count = 10
kvi_click_delay = 3
kvi_loop_delay = 7500

last_work_cycle_time, last_daily_cycle_time, last_kvi_cycle_time, last_reboot_cycle_time, last_spam_time = 0, 0, 0, 0, 0

auto_reboot_stop_event = threading.Event()
spam_thread, auto_reboot_thread = None, None
bots_lock = threading.Lock()
server_start_time = time.time()
bot_active_states = {}

# --- HÀM LƯU VÀ TẢI CÀI ĐẶT ---
def save_settings():
    api_key, bin_id = os.getenv("JSONBIN_API_KEY"), os.getenv("JSONBIN_BIN_ID")
    if not api_key or not bin_id: return

    settings = {
        'auto_grab_enabled_1': auto_grab_enabled_1, 'heart_threshold_1': heart_threshold_1,
        'auto_grab_enabled_2': auto_grab_enabled_2, 'heart_threshold_2': heart_threshold_2,
        'auto_grab_enabled_3': auto_grab_enabled_3, 'heart_threshold_3': heart_threshold_3,
        'auto_grab_enabled_4': auto_grab_enabled_4, 'heart_threshold_4': heart_threshold_4,
        'auto_grab_enabled_5': auto_grab_enabled_5, 'heart_threshold_5': heart_threshold_5,
        'auto_grab_enabled_6': auto_grab_enabled_6, 'heart_threshold_6': heart_threshold_6,
        'spam_enabled': spam_enabled, 'spam_message': spam_message, 'spam_delay': spam_delay,
        'auto_work_enabled': auto_work_enabled, 'work_delay_between_acc': work_delay_between_acc, 'work_delay_after_all': work_delay_after_all,
        'auto_daily_enabled': auto_daily_enabled, 'daily_delay_between_acc': daily_delay_between_acc, 'daily_delay_after_all': daily_delay_after_all,
        'auto_kvi_enabled': auto_kvi_enabled, 'kvi_click_count': kvi_click_count, 'kvi_click_delay': kvi_click_delay, 'kvi_loop_delay': kvi_loop_delay,
        'auto_reboot_enabled': auto_reboot_enabled, 'auto_reboot_delay': auto_reboot_delay,
        'bot_active_states': bot_active_states,
        'last_work_cycle_time': last_work_cycle_time,
        'last_daily_cycle_time': last_daily_cycle_time,
        'last_kvi_cycle_time': last_kvi_cycle_time,
        'last_reboot_cycle_time': last_reboot_cycle_time,
        'last_spam_time': last_spam_time,
    }

    headers = {'Content-Type': 'application/json', 'X-Master-Key': api_key}
    url = f"https://api.jsonbin.io/v3/b/{bin_id}"
    try:
        req = requests.put(url, json=settings, headers=headers, timeout=10)
        if req.status_code == 200: print("[Settings] Đã lưu cài đặt lên JSONBin.io thành công.", flush=True)
        else: print(f"[Settings] Lỗi khi lưu cài đặt: {req.status_code} - {req.text}", flush=True)
    except Exception as e: print(f"[Settings] Exception khi lưu cài đặt: {e}", flush=True)

def load_settings():
    api_key, bin_id = os.getenv("JSONBIN_API_KEY"), os.getenv("JSONBIN_BIN_ID")
    if not api_key or not bin_id:
        print("[Settings] Thiếu API Key/Bin ID, dùng cài đặt mặc định.", flush=True)
        return
    
    headers = {'X-Master-Key': api_key}
    url = f"https://api.jsonbin.io/v3/b/{bin_id}/latest"
    try:
        req = requests.get(url, headers=headers, timeout=10)
        if req.status_code == 200:
            settings = req.json().get("record", {})
            if settings:
                # Cập nhật các biến global một cách an toàn
                for key, value in settings.items():
                    if key in globals():
                        globals()[key] = value
                print("[Settings] Đã tải cài đặt từ JSONBin.io.", flush=True)
            else:
                print("[Settings] JSONBin rỗng, bắt đầu với cài đặt mặc định và lưu lại.", flush=True)
                save_settings()
        else:
            print(f"[Settings] Lỗi khi tải cài đặt: {req.status_code} - {req.text}", flush=True)
    except Exception as e: print(f"[Settings] Exception khi tải cài đặt: {e}", flush=True)

# --- CÁC HÀM LOGIC BOT ---
def reboot_bot(target_id):
    global main_bots, bots
    with bots_lock:
        print(f"[Reboot] Yêu cầu reboot cho target: {target_id}", flush=True)
        if target_id.startswith('main_'):
            try:
                bot_num = int(target_id.split('_')[1])
                if bot_num in main_bots and bot_num in main_bot_configs:
                    try: main_bots[bot_num].gateway.close()
                    except Exception as e: print(f"[Reboot] Lỗi khi đóng Main Bot {bot_num}: {e}", flush=True)
                    token = main_bot_configs[bot_num]["token"]
                    # Gọi lại create_bot với cờ tương ứng
                    args = {'token': token, f'is_main_{bot_num}': True}
                    main_bots[bot_num] = create_bot(**args)
                    print(f"[Reboot] Main Bot {bot_num} ({main_bot_configs[bot_num]['name']}) đã khởi động lại.", flush=True)
            except (ValueError, IndexError) as e: print(f"[Reboot] Lỗi xử lý target Main Bot: {e}", flush=True)
        elif target_id.startswith('sub_'):
            try:
                index = int(target_id.split('_')[1])
                if 0 <= index < len(bots):
                    try: bots[index].gateway.close()
                    except Exception as e: print(f"[Reboot] Lỗi khi đóng Sub Bot {index}: {e}", flush=True)
                    token_to_reboot = tokens[index]
                    bots[index] = create_bot(token_to_reboot.strip())
                    print(f"[Reboot] Sub Bot {index} đã được khởi động lại.", flush=True)
            except (ValueError, IndexError) as e: print(f"[Reboot] Lỗi xử lý target Sub Bot: {e}", flush=True)

def create_bot(token, is_main_1=False, is_main_2=False, is_main_3=False, is_main_4=False, is_main_5=False, is_main_6=False):
    bot = discum.Client(token=token, log=False)
    
    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            user_id = resp.raw.get("user", {}).get("id")
            if user_id:
                bot_num_map = {is_main_1: 1, is_main_2: 2, is_main_3: 3, is_main_4: 4, is_main_5: 5, is_main_6: 6}
                bot_num = bot_num_map.get(True)
                bot_type = f"({main_bot_configs[bot_num]['name']})" if bot_num else ""
                print(f"Đã đăng nhập: {user_id} {bot_type}", flush=True)

    if is_main_1:
        @bot.gateway.command
        def on_message(resp):
            if not resp.event.message: return
            msg = resp.parsed.auto()
            msg_channel_id = msg.get("channel_id")
            channels = main_bot_configs.get(1, {}).get('channels', [])
            if msg.get("author", {}).get("id") == karuta_id and msg_channel_id in channels and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled_1:
                def read_karibbit_1():
                    time.sleep(1.2)
                    try:
                        messages = bot.getMessages(msg_channel_id, num=5).json()
                        for msg_item in messages:
                            if msg_item.get("author", {}).get("id") == karibbit_id and len(msg_item.get("embeds", [])) > 0:
                                desc = msg_item["embeds"][0].get("description", "")
                                lines = desc.split('\n')
                                heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                max_num = max(heart_numbers)
                                if sum(heart_numbers) > 0 and max_num >= heart_threshold_1:
                                    max_index = heart_numbers.index(max_num)
                                    emoji, delay = [("1️⃣", 0.5), ("2️⃣", 1.5), ("3️⃣", 2.2)][max_index]
                                    print(f"[Bot 1][Kênh {msg_channel_id}] Chọn thẻ {max_index+1} ({max_num} tim)", flush=True)
                                    def grab():
                                        bot.addReaction(msg_channel_id, msg["id"], emoji)
                                        time.sleep(2); bot.sendMessage(ktb_channel_id, "kt b")
                                    threading.Timer(delay, grab).start()
                                break
                    except Exception as e: print(f"Lỗi khi đọc Karibbit (Bot 1): {e}", flush=True)
                threading.Thread(target=read_karibbit_1).start()
    
    if is_main_2:
        @bot.gateway.command
        def on_message(resp):
            if not resp.event.message: return
            msg = resp.parsed.auto()
            msg_channel_id = msg.get("channel_id")
            channels = main_bot_configs.get(2, {}).get('channels', [])
            if msg.get("author", {}).get("id") == karuta_id and msg_channel_id in channels and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled_2:
                def read_karibbit_2():
                    time.sleep(1.2)
                    try:
                        messages = bot.getMessages(msg_channel_id, num=5).json()
                        for msg_item in messages:
                            if msg_item.get("author", {}).get("id") == karibbit_id and len(msg_item.get("embeds", [])) > 0:
                                desc = msg_item["embeds"][0].get("description", "")
                                lines = desc.split('\n')
                                heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                max_num = max(heart_numbers)
                                if sum(heart_numbers) > 0 and max_num >= heart_threshold_2:
                                    max_index = heart_numbers.index(max_num)
                                    emoji, delay = [("1️⃣", 0.8), ("2️⃣", 1.8), ("3️⃣", 2.5)][max_index]
                                    print(f"[Bot 2][Kênh {msg_channel_id}] Chọn thẻ {max_index+1} ({max_num} tim)", flush=True)
                                    def grab():
                                        bot.addReaction(msg_channel_id, msg["id"], emoji)
                                        time.sleep(2); bot.sendMessage(ktb_channel_id, "kt b")
                                    threading.Timer(delay, grab).start()
                                break
                    except Exception as e: print(f"Lỗi khi đọc Karibbit (Bot 2): {e}", flush=True)
                threading.Thread(target=read_karibbit_2).start()

    if is_main_3:
        @bot.gateway.command
        def on_message(resp):
            if not resp.event.message: return
            msg = resp.parsed.auto()
            msg_channel_id = msg.get("channel_id")
            channels = main_bot_configs.get(3, {}).get('channels', [])
            if msg.get("author", {}).get("id") == karuta_id and msg_channel_id in channels and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled_3:
                def read_karibbit_3():
                    time.sleep(1.2)
                    try:
                        messages = bot.getMessages(msg_channel_id, num=5).json()
                        for msg_item in messages:
                            if msg_item.get("author", {}).get("id") == karibbit_id and len(msg_item.get("embeds", [])) > 0:
                                desc = msg_item["embeds"][0].get("description", "")
                                lines = desc.split('\n')
                                heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                max_num = max(heart_numbers)
                                if sum(heart_numbers) > 0 and max_num >= heart_threshold_3:
                                    max_index = heart_numbers.index(max_num)
                                    emoji, delay = [("1️⃣", 0.8), ("2️⃣", 1.8), ("3️⃣", 2.5)][max_index]
                                    print(f"[Bot 3][Kênh {msg_channel_id}] Chọn thẻ {max_index+1} ({max_num} tim)", flush=True)
                                    def grab():
                                        bot.addReaction(msg_channel_id, msg["id"], emoji)
                                        time.sleep(2); bot.sendMessage(ktb_channel_id, "kt b")
                                    threading.Timer(delay, grab).start()
                                break
                    except Exception as e: print(f"Lỗi khi đọc Karibbit (Bot 3): {e}", flush=True)
                threading.Thread(target=read_karibbit_3).start()

    if is_main_4:
        @bot.gateway.command
        def on_message(resp):
            if not resp.event.message: return
            msg = resp.parsed.auto()
            msg_channel_id = msg.get("channel_id")
            channels = main_bot_configs.get(4, {}).get('channels', [])
            if msg.get("author", {}).get("id") == karuta_id and msg_channel_id in channels and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled_4:
                def read_karibbit_4():
                    time.sleep(1.2)
                    try:
                        messages = bot.getMessages(msg_channel_id, num=5).json()
                        for msg_item in messages:
                            if msg_item.get("author", {}).get("id") == karibbit_id and len(msg_item.get("embeds", [])) > 0:
                                desc = msg_item["embeds"][0].get("description", "")
                                lines = desc.split('\n')
                                heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                max_num = max(heart_numbers)
                                if sum(heart_numbers) > 0 and max_num >= heart_threshold_4:
                                    max_index = heart_numbers.index(max_num)
                                    emoji, delay = [("1️⃣", 0.9), ("2️⃣", 1.9), ("3️⃣", 2.6)][max_index]
                                    print(f"[Bot 4][Kênh {msg_channel_id}] Chọn thẻ {max_index+1} ({max_num} tim)", flush=True)
                                    def grab():
                                        bot.addReaction(msg_channel_id, msg["id"], emoji)
                                        time.sleep(2); bot.sendMessage(ktb_channel_id, "kt b")
                                    threading.Timer(delay, grab).start()
                                break
                    except Exception as e: print(f"Lỗi khi đọc Karibbit (Bot 4): {e}", flush=True)
                threading.Thread(target=read_karibbit_4).start()
    
    if is_main_5:
        @bot.gateway.command
        def on_message(resp):
            if not resp.event.message: return
            msg = resp.parsed.auto()
            msg_channel_id = msg.get("channel_id")
            channels = main_bot_configs.get(5, {}).get('channels', [])
            if msg.get("author", {}).get("id") == karuta_id and msg_channel_id in channels and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled_5:
                def read_karibbit_5():
                    time.sleep(1.2)
                    try:
                        messages = bot.getMessages(msg_channel_id, num=5).json()
                        for msg_item in messages:
                            if msg_item.get("author", {}).get("id") == karibbit_id and len(msg_item.get("embeds", [])) > 0:
                                desc = msg_item["embeds"][0].get("description", "")
                                lines = desc.split('\n')
                                heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                max_num = max(heart_numbers)
                                if sum(heart_numbers) > 0 and max_num >= heart_threshold_5:
                                    max_index = heart_numbers.index(max_num)
                                    emoji, delay = [("1️⃣", 1.0), ("2️⃣", 2.0), ("3️⃣", 2.7)][max_index]
                                    print(f"[Bot 5][Kênh {msg_channel_id}] Chọn thẻ {max_index+1} ({max_num} tim)", flush=True)
                                    def grab():
                                        bot.addReaction(msg_channel_id, msg["id"], emoji)
                                        time.sleep(2); bot.sendMessage(ktb_channel_id, "kt b")
                                    threading.Timer(delay, grab).start()
                                break
                    except Exception as e: print(f"Lỗi khi đọc Karibbit (Bot 5): {e}", flush=True)
                threading.Thread(target=read_karibbit_5).start()

    if is_main_6:
        @bot.gateway.command
        def on_message(resp):
            if not resp.event.message: return
            msg = resp.parsed.auto()
            msg_channel_id = msg.get("channel_id")
            channels = main_bot_configs.get(6, {}).get('channels', [])
            if msg.get("author", {}).get("id") == karuta_id and msg_channel_id in channels and "is dropping" not in msg.get("content", "") and not msg.get("mentions", []) and auto_grab_enabled_6:
                def read_karibbit_6():
                    time.sleep(1.2)
                    try:
                        messages = bot.getMessages(msg_channel_id, num=5).json()
                        for msg_item in messages:
                            if msg_item.get("author", {}).get("id") == karibbit_id and len(msg_item.get("embeds", [])) > 0:
                                desc = msg_item["embeds"][0].get("description", "")
                                lines = desc.split('\n')
                                heart_numbers = [int(m[1]) if len(m := re.findall(r'`([^`]*)`', line)) >= 2 and m[1].isdigit() else 0 for line in lines[:3]]
                                max_num = max(heart_numbers)
                                if sum(heart_numbers) > 0 and max_num >= heart_threshold_6:
                                    max_index = heart_numbers.index(max_num)
                                    emoji, delay = [("1️⃣", 1.1), ("2️⃣", 2.1), ("3️⃣", 2.8)][max_index]
                                    print(f"[Bot 6][Kênh {msg_channel_id}] Chọn thẻ {max_index+1} ({max_num} tim)", flush=True)
                                    def grab():
                                        bot.addReaction(msg_channel_id, msg["id"], emoji)
                                        time.sleep(2); bot.sendMessage(ktb_channel_id, "kt b")
                                    threading.Timer(delay, grab).start()
                                break
                    except Exception as e: print(f"Lỗi khi đọc Karibbit (Bot 6): {e}", flush=True)
                threading.Thread(target=read_karibbit_6).start()
    
    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

# ... (Toàn bộ phần còn lại của script, bao gồm các vòng lặp nền và Flask, được giữ nguyên y hệt như phiên bản trước) ...
