# PHIÊN BẢN CUỐI CÙNG - FIX SYNTAXERROR
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
                    main_bots[bot_num] = create_bot(token, bot_number=bot_num)
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
                
# --- HÀM XỬ LÝ NHẶT THẺ ĐÃ SỬA LỖI ---
def process_karuta_drop(bot, last_drop_msg_id, channel_id, karibbit_id, ktb_channel_id, heart_threshold, reaction_config, bot_name):
    """
    Hàm xử lý logic nhặt thẻ Karuta một cách ổn định.
    - bot: đối tượng bot discum.
    - last_drop_msg_id: ID của tin nhắn drop.
    - channel_id: ID kênh drop.
    - karibbit_id: ID của bot Karibbit.
    - ktb_channel_id: ID kênh để kiểm tra burn.
    - heart_threshold: Ngưỡng tim tối thiểu để nhặt.
    - reaction_config: Cấu hình reaction (emoji, delay).
    - bot_name: Tên của bot để ghi log.
    """
    # Thử lại vài lần để đảm bảo không bỏ lỡ tin nhắn của Karibbit do trễ mạng
    for i in range(4):  # Thử tối đa 4 lần
        time.sleep(0.35 + i * 0.1)  # Chờ lâu hơn một chút sau mỗi lần thử
        try:
            messages = bot.getMessages(channel_id, num=5).json()
            # Tìm tin nhắn từ Karibbit có chứa embed
            karibbit_msg = next((msg for msg in messages if msg.get("author", {}).get("id") == karibbit_id and "embeds" in msg and msg["embeds"]), None)

            if karibbit_msg:
                desc = karibbit_msg["embeds"][0].get("description", "")
                lines = desc.split('\n')

                # --- LOGIC PARSE TIM ĐÃ SỬA LỖI ---
                heart_numbers = []
                for line in lines[:3]: # Chỉ xử lý 3 dòng đầu
                    num = 0
                    try:
                        # Tách các phần trong dấu ``. Ví dụ: ['#1', '🤍55', '✨123']
                        parts = re.findall(r'`([^`]*)`', line)
                        # Giá trị tim (wishlist) thường nằm ở phần tử thứ 2 (index 1)
                        if len(parts) >= 2:
                            # Tìm số bên trong chuỗi đó. Ví dụ: tìm '55' trong '🤍55'
                            heart_match = re.search(r'\d+', parts[1])
                            if heart_match:
                                num = int(heart_match.group())
                    except (IndexError, ValueError):
                        # Bỏ qua nếu dòng không đúng định dạng hoặc không có số
                        num = 0
                    heart_numbers.append(num)
                # --- KẾT THÚC SỬA LỖI ---

                max_num = max(heart_numbers) if heart_numbers else 0
                if sum(heart_numbers) > 0 and max_num >= heart_threshold:
                    max_index = heart_numbers.index(max_num)
                    emoji, delay = reaction_config[max_index]
                    print(f"[{bot_name}] Tìm thấy! Dòng {max_index + 1} với {max_num} tim (yêu cầu >= {heart_threshold}). Nhặt với {emoji} sau {delay}s.", flush=True)

                    def grab():
                        bot.addReaction(channel_id, last_drop_msg_id, emoji)
                        time.sleep(2)
                        bot.sendMessage(ktb_channel_id, "kt b")
                    threading.Timer(delay, grab).start()
                else:
                    print(f"[{bot_name}] Bỏ qua drop, tim cao nhất là {max_num} (yêu cầu >= {heart_threshold})", flush=True)
                
                return  # Đã xử lý xong, thoát khỏi vòng lặp và hàm
        except Exception as e:
            print(f"[{bot_name}] Lỗi khi đọc tin nhắn Karibbit lần thử {i + 1}: {e}", flush=True)

    print(f"[{bot_name}] Không tìm thấy hoặc xử lý được tin nhắn Karibbit sau nhiều lần thử.", flush=True)
    
def create_bot(token, bot_number=0):
    bot = discum.Client(token=token, log=False)
    @bot.gateway.command
    def on_ready(resp):
        if resp.event.ready:
            user_data = resp.raw.get("user")
            if isinstance(user_data, dict):
                user_id = user_data.get("id")
                if user_id:
                    if bot_number == 1: bot_type = "(ALPHA)"
                    elif bot_number == 2: bot_type = "(BETA)"
                    elif bot_number == 3: bot_type = "(GAMMA)"
                    else: bot_type = ""
                    print(f"Đã đăng nhập: {user_id} {bot_type}", flush=True)

    # Hàm xử lý tin nhắn chung, NAY ĐÃ NHẬN THÊM CÁC ID CẦN THIẾT
    def on_message_handler(resp, enabled_flag_func, threshold_func, reaction_config, bot_name,
                           # Thêm các tham số mới ở đây
                           target_channel_id, target_author_id, kibbit_bot_id, burn_check_channel_id):
        if resp.event.message:
            msg = resp.parsed.auto()
            # Sử dụng các tham số mới thay vì biến global
            if (msg.get("author", {}).get("id") == target_author_id and
                msg.get("channel_id") == target_channel_id and
                "is dropping" not in msg.get("content", "") and
                not msg.get("mentions", []) and enabled_flag_func()):

                last_drop_msg_id = msg["id"]
                threading.Thread(target=process_karuta_drop, args=(
                    bot, last_drop_msg_id,
                    # Truyền các tham số đã nhận vào hàm xử lý
                    target_channel_id, kibbit_bot_id, burn_check_channel_id,
                    threshold_func(), reaction_config, bot_name
                )).start()

    # Cấu hình riêng cho từng bot chính
    main_bot_configs = {
        1: {
            "enabled_flag_func": lambda: auto_grab_enabled,
            "threshold_func": lambda: heart_threshold,
            "reaction_config": [("1️⃣", 0.5), ("2️⃣", 1.5), ("3️⃣", 2.2)],
            "bot_name": "Bot 1 (ALPHA)"
        },
        2: {
            "enabled_flag_func": lambda: auto_grab_enabled_2,
            "threshold_func": lambda: heart_threshold_2,
            "reaction_config": [("1️⃣", 0.8), ("2️⃣", 1.8), ("3️⃣", 2.5)],
            "bot_name": "Bot 2 (BETA)"
        },
        3: {
            "enabled_flag_func": lambda: auto_grab_enabled_3,
            "threshold_func": lambda: heart_threshold_3,
            "reaction_config": [("1️⃣", 0.8), ("2️⃣", 1.8), ("3️⃣", 2.5)],
            "bot_name": "Bot 3 (GAMMA)"
        }
    }

    # Nếu bot_number là của bot chính (1, 2, hoặc 3), thì gán hàm xử lý on_message
    if bot_number in main_bot_configs:
        config = main_bot_configs[bot_number]

        @bot.gateway.command
        def on_message(resp):
            # KHI GỌI, TRUYỀN CÁC BIẾN GLOBAL VÀO
            on_message_handler(resp,
                               config["enabled_flag_func"],
                               config["threshold_func"],
                               config["reaction_config"],
                               config["bot_name"],
                               # Các biến global được truyền vào đây
                               main_channel_id,
                               karuta_id,
                               karibbit_id,
                               ktb_channel_id)

    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

    if bot_number is not None:
        @bot.gateway.command
        def on_message(resp):
            is_enabled = globals().get(f'auto_grab_enabled_{bot_number}', False)
            threshold = globals().get(f'heart_threshold_{bot_number}', 50)
            channels_to_check = main_bot_configs.get(bot_number, {}).get("channels", [])
            emoji_configs = [
                [("1️⃣", 0.5), ("2️⃣", 1.5), ("3️⃣", 2.2)], [("1️⃣", 0.8), ("2️⃣", 1.8), ("3️⃣", 2.5)],
                [("1️⃣", 0.8), ("2️⃣", 1.8), ("3️⃣", 2.5)], [("1️⃣", 0.9), ("2️⃣", 1.9), ("3️⃣", 2.6)],
                [("1️⃣", 1.0), ("2️⃣", 2.0), ("3️⃣", 2.7)], [("1️⃣", 1.1), ("2️⃣", 2.1), ("3️⃣", 2.8)]
            ]
            if resp.event.message:
                msg = resp.parsed.auto()
                msg_channel_id = msg.get("channel_id")
                if (msg.get("author", {}).get("id") == karuta_id and 
                    msg_channel_id in channels_to_check and 
                    "is dropping" not in msg.get("content", "") and 
                    not msg.get("mentions", []) and is_enabled):
                    threading.Thread(target=generic_on_message, args=(
                        bot, msg_channel_id, msg["id"], threshold, bot_number, emoji_configs[bot_number-1]
                    )).start()

    threading.Thread(target=bot.gateway.run, daemon=True).start()
    return bot

# ... (Các hàm logic phụ và vòng lặp nền không thay đổi, vì chúng đã ổn định) ...
def run_work_bot(token, acc_name):
    bot = discum.Client(token=token, log={"console": False, "file": False})
    headers = {"Authorization": token, "Content-Type": "application/json"}
    step = {"value": 0}
    def send_karuta_command(): bot.sendMessage(work_channel_id, "kc o:ef")
    def send_kn_command(): bot.sendMessage(work_channel_id, "kn")
    def send_kw_command(): bot.sendMessage(work_channel_id, "kw"); step["value"] = 2
    def click_tick(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json={"type": 3,"guild_id": guild_id,"channel_id": channel_id,"message_id": message_id,"application_id": application_id,"session_id": "a","data": {"component_type": 2,"custom_id": custom_id}})
            print(f"[Work][{acc_name}] Click tick: Status {r.status_code}", flush=True)
        except Exception as e: print(f"[Work][{acc_name}] Lỗi click tick: {e}", flush=True)
    @bot.gateway.command
    def on_message(resp):
        if not (resp.event.message or resp.event.message_update): return
        m = resp.parsed.auto()
        if str(m.get("channel_id")) != work_channel_id: return
        author_id = str(m.get("author", {}).get("id", ""))
        guild_id = m.get("guild_id")
        if step["value"] == 0 and author_id == karuta_id and "embeds" in m and len(m["embeds"]) > 0:
            desc = m["embeds"][0].get("description", "")
            card_codes = re.findall(r"\bv[a-zA-Z0-9]{6}\b", desc)
            if len(card_codes) >= 10:
                print(f"[Work][{acc_name}] Phát hiện {len(card_codes)} card, bắt đầu pick...", flush=True)
                first_5 = card_codes[:5]; last_5 = card_codes[-5:]
                for i, code in enumerate(last_5): time.sleep(2 if i == 0 else 1.5); bot.sendMessage(work_channel_id, f"kjw {code} {chr(97+i)}")
                for i, code in enumerate(first_5): time.sleep(1.5); bot.sendMessage(work_channel_id, f"kjw {code} {chr(97+i)}")
                time.sleep(1); send_kn_command(); step["value"] = 1
        elif step["value"] == 1 and author_id == karuta_id and "embeds" in m and len(m["embeds"]) > 0:
            desc = m["embeds"][0].get("description", ""); lines = desc.split("\n")
            if len(lines) >= 2:
                match = re.search(r"\d+\.\s*`([^`]+)`", lines[1])
                if match:
                    resource = match.group(1); print(f"[Work][{acc_name}] Resource: {resource}", flush=True)
                    time.sleep(2); bot.sendMessage(work_channel_id, f"kjn `{resource}` a b c d e"); time.sleep(1); send_kw_command()
        elif step["value"] == 2 and author_id == karuta_id and "components" in m:
            message_id = m["id"]; application_id = m.get("application_id", karuta_id)
            for comp in m["components"]:
                 if comp["type"] == 1 and len(comp["components"]) >= 2:	
                    btn = comp["components"][1]; print(f"[Work][{acc_name}] Click nút thứ 2: {btn['custom_id']}", flush=True); click_tick(work_channel_id, message_id, btn["custom_id"], application_id, guild_id); step["value"] = 3; bot.gateway.close(); return
    print(f"[Work][{acc_name}] Bắt đầu...", flush=True); threading.Thread(target=bot.gateway.run, daemon=True).start(); time.sleep(3); send_karuta_command()
    timeout = time.time() + 90
    while step["value"] != 3 and time.time() < timeout: time.sleep(1)
    bot.gateway.close(); print(f"[Work][{acc_name}] Đã hoàn thành.", flush=True)

def run_daily_bot(token, acc_name):
    bot = discum.Client(token=token, log={"console": False, "file": False})
    headers = {"Authorization": token, "Content-Type": "application/json"}
    state = {"step": 0, "message_id": None, "guild_id": None}
    def click_button(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json={"type": 3,"guild_id": guild_id,"channel_id": channel_id,"message_id": message_id,"application_id": application_id,"session_id": "aaa","data": {"component_type": 2, "custom_id": custom_id}})
            print(f"[Daily][{acc_name}] Click: {custom_id} - Status {r.status_code}", flush=True)
        except Exception as e: print(f"[Daily][{acc_name}] Click Error: {e}", flush=True)
    @bot.gateway.command
    def on_event(resp):
        if not (resp.event.message or resp.raw.get("t") == "MESSAGE_UPDATE"): return
        m = resp.parsed.auto()
        channel_id, author_id, message_id, guild_id, app_id = str(m.get("channel_id")), str(m.get("author", {}).get("id", "")), m.get("id", ""), m.get("guild_id", ""), m.get("application_id", karuta_id)
        if channel_id != daily_channel_id or author_id != karuta_id or "components" not in m or not m["components"]: return
        btn = next((b for comp in m["components"] if comp["type"] == 1 and comp["components"] for b in comp["components"] if b["type"] == 2), None)
        if not btn: return
        if resp.event.message and state["step"] == 0:
            print(f"[Daily][{acc_name}] Click lần 1...", flush=True); state["message_id"], state["guild_id"], state["step"] = message_id, guild_id, 1; click_button(channel_id, message_id, btn["custom_id"], app_id, guild_id)
        elif resp.raw.get("t") == "MESSAGE_UPDATE" and message_id == state["message_id"] and state["step"] == 1:
            print(f"[Daily][{acc_name}] Click lần 2...", flush=True); state["step"] = 2; click_button(channel_id, message_id, btn["custom_id"], app_id, guild_id); bot.gateway.close()
    print(f"[Daily][{acc_name}] Bắt đầu...", flush=True); threading.Thread(target=bot.gateway.run, daemon=True).start(); time.sleep(1); bot.sendMessage(daily_channel_id, "kdaily")
    timeout = time.time() + 15
    while state["step"] != 2 and time.time() < timeout: time.sleep(1)
    bot.gateway.close(); print(f"[Daily][{acc_name}] {'SUCCESS: Click xong 2 lần.' if state['step'] == 2 else 'FAIL: Không click đủ 2 lần.'}", flush=True)

def run_kvi_bot(token):
    bot = discum.Client(token=token, log={"console": False, "file": False})
    headers, state = {"Authorization": token, "Content-Type": "application/json"}, {"step": 0, "click_count": 0, "message_id": None, "guild_id": None}
    def click_button(channel_id, message_id, custom_id, application_id, guild_id):
        try:
            r = requests.post("https://discord.com/api/v9/interactions", headers=headers, json={"type": 3, "guild_id": guild_id, "channel_id": channel_id, "message_id": message_id, "application_id": application_id, "session_id": "aaa", "data": {"component_type": 2, "custom_id": custom_id}})
            print(f"[KVI] Click {state['click_count']+1}: {custom_id} - Status {r.status_code}", flush=True)
        except Exception as e: print(f"[KVI] Click Error: {e}", flush=True)
    @bot.gateway.command
    def on_event(resp):
        if not (resp.event.message or resp.raw.get("t") == "MESSAGE_UPDATE"): return
        m = resp.parsed.auto()
        channel_id, author_id, message_id, guild_id, app_id = str(m.get("channel_id")), str(m.get("author", {}).get("id", "")), m.get("id", ""), m.get("guild_id", ""), m.get("application_id", karuta_id)
        if channel_id != kvi_channel_id or author_id != karuta_id or "components" not in m or not m["components"]: return
        btn = next((b for comp in m["components"] if comp["type"] == 1 and comp["components"] for b in comp["components"] if b["type"] == 2), None)
        if not btn: return
        if resp.event.message and state["step"] == 0:
            state["message_id"], state["guild_id"], state["step"] = message_id, guild_id, 1; click_button(channel_id, message_id, btn["custom_id"], app_id, guild_id); state["click_count"] += 1
        elif resp.raw.get("t") == "MESSAGE_UPDATE" and message_id == state["message_id"] and state["click_count"] < kvi_click_count:
            time.sleep(kvi_click_delay); click_button(channel_id, message_id, btn["custom_id"], app_id, guild_id); state["click_count"] += 1
            if state["click_count"] >= kvi_click_count: print("[KVI] DONE. Đã click đủ.", flush=True); state["step"] = 2; bot.gateway.close()
    print("[KVI] Bắt đầu...", flush=True); threading.Thread(target=bot.gateway.run, daemon=True).start(); time.sleep(1); bot.sendMessage(kvi_channel_id, "kvi")
    timeout = time.time() + (kvi_click_count * kvi_click_delay) + 15
    while state["step"] != 2 and time.time() < timeout: time.sleep(0.5)
    bot.gateway.close(); print(f"[KVI] {'SUCCESS. Đã click xong.' if state['click_count'] >= kvi_click_count else f'FAIL. Chỉ click được {state['click_count']} / {kvi_click_count} lần.'}", flush=True)
    
def auto_work_loop():
    global last_work_cycle_time
    while True:
        try:
            if auto_work_enabled and (time.time() - last_work_cycle_time) >= work_delay_after_all:
                print("[Work] Đã đến giờ chạy Auto Work...", flush=True)
                work_items = []
                if main_bot_configs.get(2) and bot_active_states.get('main_2', False): work_items.append({"name": "BETA NODE", "token": main_bot_configs[2]["token"]})
                if main_bot_configs.get(3) and bot_active_states.get('main_3', False): work_items.append({"name": "GAMMA NODE", "token": main_bot_configs[3]["token"]})
                with bots_lock:
                    sub_account_items = [{"name": acc_names[i] if i < len(acc_names) else f"Sub {i+1}", "token": token} for i, token in enumerate(tokens) if token.strip() and bot_active_states.get(f'sub_{i}', False)]
                    work_items.extend(sub_account_items)
                for item in work_items:
                    if not auto_work_enabled: break
                    print(f"[Work] Đang chạy acc '{item['name']}'...", flush=True)
                    run_work_bot(item['token'].strip(), item['name'])
                    print(f"[Work] Acc '{item['name']}' xong, chờ {work_delay_between_acc} giây...", flush=True); time.sleep(work_delay_between_acc)
                if auto_work_enabled:
                    print(f"[Work] Hoàn thành chu kỳ.", flush=True)
                    last_work_cycle_time = time.time();
            time.sleep(60)
        except Exception as e:
            print(f"[ERROR in auto_work_loop] {e}", flush=True); time.sleep(60)

def auto_daily_loop():
    global last_daily_cycle_time
    while True:
        try:
            if auto_daily_enabled and (time.time() - last_daily_cycle_time) >= daily_delay_after_all:
                print("[Daily] Đã đến giờ chạy Auto Daily...", flush=True)
                daily_items = []
                if main_bot_configs.get(2) and bot_active_states.get('main_2', False): daily_items.append({"name": "BETA NODE", "token": main_bot_configs[2]["token"]})
                if main_bot_configs.get(3) and bot_active_states.get('main_3', False): daily_items.append({"name": "GAMMA NODE", "token": main_bot_configs[3]["token"]})
                with bots_lock:
                    daily_items.extend([{"name": acc_names[i] if i < len(acc_names) else f"Sub {i+1}", "token": token} for i, token in enumerate(tokens) if token.strip() and bot_active_states.get(f'sub_{i}', False)])
                for item in daily_items:
                    if not auto_daily_enabled: break
                    print(f"[Daily] Đang chạy acc '{item['name']}'...", flush=True); run_daily_bot(item['token'].strip(), item['name']); print(f"[Daily] Acc '{item['name']}' xong, chờ {daily_delay_between_acc} giây...", flush=True); time.sleep(daily_delay_between_acc)
                if auto_daily_enabled:
                    print(f"[Daily] Hoàn thành chu kỳ.", flush=True)
                    last_daily_cycle_time = time.time();
            time.sleep(60)
        except Exception as e:
            print(f"[ERROR in auto_daily_loop] {e}", flush=True); time.sleep(60)

def auto_kvi_loop():
    global last_kvi_cycle_time
    while True:
        try:
            if auto_kvi_enabled and main_bot_configs.get(1) and bot_active_states.get('main_1', False) and (time.time() - last_kvi_cycle_time) >= kvi_loop_delay:
                print("[KVI] Bắt đầu chu trình KVI cho Acc Chính 1...", flush=True)
                run_kvi_bot(main_bot_configs[1]["token"])
                if auto_kvi_enabled:
                    last_kvi_cycle_time = time.time(); save_settings()
            time.sleep(60)
        except Exception as e:
            print(f"[ERROR in auto_kvi_loop] {e}", flush=True); time.sleep(60)

def auto_reboot_loop():
    global auto_reboot_enabled, last_reboot_cycle_time, auto_reboot_stop_event
    while not auto_reboot_stop_event.is_set():
        try:
            if auto_reboot_enabled and (time.time() - last_reboot_cycle_time) >= auto_reboot_delay:
                print("[Reboot] Hết thời gian chờ, tiến hành reboot các tài khoản chính.", flush=True)
                for i in range(1, 7):
                    if main_bot_configs.get(i):
                        reboot_bot(f'main_{i}'); time.sleep(5)
                last_reboot_cycle_time = time.time();
            interrupted = auto_reboot_stop_event.wait(timeout=60)
            if interrupted: break
        except Exception as e:
            print(f"[ERROR in auto_reboot_loop] {e}", flush=True); time.sleep(60)
    print("[Reboot] Luồng tự động reboot đã dừng.", flush=True)

def spam_loop():
    global last_spam_time
    while True:
        try:
            if spam_enabled and spam_message and spam_channel_ids and (time.time() - last_spam_time) >= spam_delay:
                with bots_lock:
                    bots_to_spam = [
                        (bot, acc_names[i] if i < len(acc_names) else f"Sub {i+1}")
                        for i, bot in enumerate(bots)
                        if bot and bot_active_states.get(f'sub_{i}', False)
                    ]
                for bot, acc_name in bots_to_spam:
                    if not spam_enabled: break 
                    for channel_id in spam_channel_ids:
                        if not channel_id.strip(): continue 
                        try:
                            bot.sendMessage(channel_id.strip(), spam_message)
                            print(f"[{acc_name}] đã gửi đến kênh {channel_id.strip()}: {spam_message}", flush=True)
                            time.sleep(1)
                        except Exception as e:
                            print(f"Lỗi gửi spam từ [{acc_name}] đến kênh {channel_id.strip()}: {e}", flush=True)
                    time.sleep(2)
                if spam_enabled: last_spam_time = time.time()
            time.sleep(1)
        except Exception as e:
            print(f"[ERROR in spam_loop] {e}", flush=True)
            time.sleep(1)

def periodic_save_loop():
    while True:
        time.sleep(600)
        print("[Settings] Bắt đầu lưu định kỳ...", flush=True)
        save_settings()

app = Flask(__name__)

# --- GIAO DIỆN WEB VÀ API ---
# ... (Phần này được giữ nguyên như phiên bản trước) ...
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Karuta Deep - Shadow Network Control</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Creepster&family=Orbitron:wght@400;700;900&family=Courier+Prime:wght@400;700&family=Nosifer&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-bg: #0a0a0a; --secondary-bg: #1a1a1a; --panel-bg: #111111; --border-color: #333333;
            --shadow-color: #660000; --blood-red: #8b0000; --dark-red: #550000; --bone-white: #f8f8ff;
            --ghost-gray: #666666; --void-black: #000000; --deep-purple: #2d1b69; --necro-green: #228b22;
            --shadow-cyan: #008b8b; --text-primary: #f0f0f0; --text-secondary: #cccccc; --text-muted: #888888;
            --neon-yellow: #fff000;
            --shadow-red: 0 0 20px rgba(139, 0, 0, 0.5); --shadow-purple: 0 0 20px rgba(45, 27, 105, 0.5);
            --shadow-green: 0 0 20px rgba(34, 139, 34, 0.5); --shadow-cyan: 0 0 20px rgba(0, 139, 139, 0.5);
        }
        body { font-family: 'Courier Prime', monospace; background: var(--primary-bg); color: var(--text-primary); margin: 0; padding: 0;}
        .container { max-width: 1600px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; padding: 30px; background: linear-gradient(135deg, var(--void-black), rgba(139, 0, 0, 0.3)); border: 2px solid var(--blood-red); border-radius: 15px; box-shadow: var(--shadow-red), inset 0 0 20px rgba(139, 0, 0, 0.1); }
        .skull-icon { font-size: 4rem; color: var(--blood-red); margin-bottom: 15px; }
        .title { font-family: 'Nosifer', cursive; font-size: 3.5rem; letter-spacing: 4px; }
        .title-main { color: var(--blood-red); text-shadow: 0 0 30px var(--blood-red); }
        .title-sub { color: var(--deep-purple); text-shadow: 0 0 30px var(--deep-purple); }
        .subtitle { font-size: 1.3rem; color: var(--text-secondary); letter-spacing: 2px; margin-bottom: 15px; font-family: 'Orbitron', monospace; }
        .main-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .panel { background: linear-gradient(135deg, var(--panel-bg), rgba(26, 26, 26, 0.9)); border: 1px solid var(--border-color); border-radius: 10px; padding: 25px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5); }
        .panel h2 { font-family: 'Nosifer', cursive; font-size: 1.4rem; margin-bottom: 20px; text-transform: uppercase; border-bottom: 2px solid; padding-bottom: 10px; position: relative; animation: glitch-skew 1s infinite linear alternate-reverse; }
        .panel h2 i { margin-right: 10px; }
        .blood-panel { border-color: var(--blood-red); box-shadow: var(--shadow-red); grid-column: span 2; }
        .blood-panel h2 { color: var(--blood-red); border-color: var(--blood-red); }
        .dark-panel { border-color: var(--deep-purple); box-shadow: var(--shadow-purple); }
        .dark-panel h2 { color: var(--deep-purple); border-color: var(--deep-purple); }
        .void-panel { border-color: var(--ghost-gray); box-shadow: 0 0 20px rgba(102, 102, 102, 0.3); }
        .void-panel h2 { color: var(--ghost-gray); border-color: var(--ghost-gray); }
        .necro-panel { border-color: var(--necro-green); box-shadow: var(--shadow-green); }
        .necro-panel h2 { color: var(--necro-green); border-color: var(--necro-green); }
        .status-panel { border-color: var(--bone-white); box-shadow: 0 0 20px rgba(248, 248, 255, 0.2); grid-column: 1 / -1; }
        .status-panel h2 { color: var(--bone-white); border-color: var(--bone-white); }
        .code-panel { border-color: var(--shadow-cyan); box-shadow: var(--shadow-cyan); }
        .code-panel h2 { color: var(--shadow-cyan); border-color: var(--shadow-cyan); }
        .ops-panel { border-color: var(--neon-yellow, #fff000); box-shadow: 0 0 20px rgba(255, 240, 0, 0.4); }
        .ops-panel h2 { color: var(--neon-yellow, #fff000); border-color: var(--neon-yellow, #fff000); }
        .btn { background: linear-gradient(135deg, var(--secondary-bg), #333); border: 1px solid var(--border-color); color: var(--text-primary); padding: 10px 15px; border-radius: 4px; cursor: pointer; font-family: 'Orbitron', monospace; font-weight: 700; text-transform: uppercase; }
        .btn-blood { border-color: var(--blood-red); color: var(--blood-red); } .btn-blood:hover { background: var(--blood-red); color: var(--primary-bg); box-shadow: var(--shadow-red); }
        .btn-necro { border-color: var(--necro-green); color: var(--necro-green); } .btn-necro:hover { background: var(--necro-green); color: var(--primary-bg); box-shadow: var(--shadow-green); }
        .btn-primary { border-color: var(--shadow-cyan); color: var(--shadow-cyan); } .btn-primary:hover { background: var(--shadow-cyan); color: var(--primary-bg); box-shadow: var(--shadow-cyan); }
        .btn-sm { padding: 8px 12px; font-size: 0.8rem; }
        .input-group { display: flex; align-items: stretch; gap: 10px; margin-bottom: 15px; }
        .input-group label { color: var(--text-secondary); font-weight: 600; font-family: 'Orbitron', monospace; padding: 10px; background: rgba(0,0,0,0.4); border: 1px solid var(--border-color); border-right: none; border-radius: 5px 0 0 5px;}
        .input-group input, .input-group textarea, .input-group select { flex-grow: 1; background: rgba(0, 0, 0, 0.8); border: 1px solid var(--border-color); color: var(--text-primary); padding: 10px 15px; border-radius: 0 5px 5px 0; font-family: 'Courier Prime', monospace; }
        .harvest-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
        .grab-section { padding: 15px; background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: 8px;}
        .grab-section h3 { color: var(--text-secondary); margin-top:0; margin-bottom: 15px; font-family: 'Orbitron', monospace; text-shadow: 0 0 10px var(--text-secondary); display: flex; justify-content: space-between; align-items: center;}
        .reboot-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; }
        .msg-status { text-align: center; color: var(--shadow-cyan); font-family: 'Courier Prime', monospace; padding: 12px; border: 1px dashed var(--border-color); border-radius: 4px; margin-bottom: 20px; background: rgba(0, 139, 139, 0.1); display: none; }
        .status-grid { display: flex; flex-direction: column; gap: 15px; }
        .status-row { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(0,0,0,0.6); border: 1px solid var(--border-color); border-radius: 8px; }
        .status-label { font-weight: 600; font-family: 'Orbitron'; }
        .timer-display { font-family: 'Courier Prime', monospace; font-size: 1.2em; font-weight: 700; }
        .status-badge { padding: 4px 10px; border-radius: 15px; text-transform: uppercase; font-size: 0.8em; }
        .status-badge.active { background: var(--necro-green); color: var(--primary-bg); box-shadow: var(--shadow-green); }
        .status-badge.inactive { background: var(--dark-red); color: var(--text-secondary); }
        .quick-cmd-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 10px; }
        .bot-status-container { display: grid; grid-template-columns: 1fr 2fr; gap: 20px; margin-top: 15px; border-top: 1px solid var(--border-color); padding-top: 15px; }
        .bot-status-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .bot-status-item { display: flex; justify-content: space-between; align-items: center; padding: 5px 8px; background: rgba(0,0,0,0.3); border-radius: 4px; font-family: 'Courier Prime', monospace; border: 1px solid var(--blood-red); }
        .status-indicator { font-weight: 700; text-transform: uppercase; font-size: 0.9em; }
        .status-indicator.online { color: var(--necro-green); } .status-indicator.offline { color: var(--blood-red); }
        .btn-toggle-state { padding: 3px 5px; font-size: 0.9em; font-family: 'Courier Prime', monospace; border-radius: 4px; cursor: pointer; text-transform: uppercase; background: transparent; font-weight: 700; border: none; }
        .btn-rise { color: var(--necro-green); }
        .btn-rest { color: var(--blood-red); }
        .panel h2::before, .panel h2::after { content: attr(data-text); position: absolute; top: 0; left: 0; width: 100%; height: 100%; overflow: hidden; }
        .panel h2::before { left: 2px; text-shadow: -2px 0 red; clip: rect(44px, 450px, 56px, 0); animation: glitch-anim 2s infinite linear alternate-reverse; }
        .panel h2::after { left: -2px; text-shadow: -2px 0 blue; clip: rect(85px, 450px, 140px, 0); animation: glitch-anim2 3s infinite linear alternate-reverse; }
        @keyframes glitch-skew { 0% { transform: skew(0deg); } 100% { transform: skew(1.5deg); } }
        @keyframes glitch-anim{0%{clip:rect(42px,9999px,44px,0);transform:skew(.3deg)}5%{clip:rect(17px,9999px,94px,0);transform:skew(.5deg)}10%{clip:rect(40px,9999px,90px,0);transform:skew(.2deg)}15%{clip:rect(37px,9999px,20px,0);transform:skew(.8deg)}20%{clip:rect(67px,9999px,80px,0);transform:skew(.1deg)}25%{clip:rect(30px,9999px,50px,0);transform:skew(.6deg)}30%{clip:rect(50px,9999px,75px,0);transform:skew(.4deg)}35%{clip:rect(22px,9999px,69px,0);transform:skew(.2deg)}40%{clip:rect(80px,9999px,100px,0);transform:skew(.7deg)}45%{clip:rect(10px,9999px,95px,0);transform:skew(.1deg)}50%{clip:rect(85px,9999px,40px,0);transform:skew(.3deg)}55%{clip:rect(5px,9999px,80px,0);transform:skew(.9deg)}60%{clip:rect(30px,9999px,90px,0);transform:skew(.2deg)}65%{clip:rect(90px,9999px,10px,0);transform:skew(.5deg)}70%{clip:rect(10px,9999px,55px,0);transform:skew(.3deg)}75%{clip:rect(55px,9999px,25px,0);transform:skew(.6deg)}80%{clip:rect(25px,9999px,75px,0);transform:skew(.4deg)}85%{clip:rect(75px,9999px,50px,0);transform:skew(.2deg)}90%{clip:rect(50px,9999px,30px,0);transform:skew(.7deg)}95%{clip:rect(30px,9999px,10px,0);transform:skew(.1deg)}100%{clip:rect(10px,9999px,90px,0);transform:skew(.4deg)}}
        @keyframes glitch-anim2{0%{clip:rect(85px,9999px,140px,0);transform:skew(.8deg)}5%{clip:rect(20px,9999px,70px,0);transform:skew(.1deg)}10%{clip:rect(70px,9999px,10px,0);transform:skew(.4deg)}15%{clip:rect(30px,9999px,90px,0);transform:skew(.7deg)}20%{clip:rect(90px,9999px,20px,0);transform:skew(.2deg)}25%{clip:rect(40px,9999px,80px,0);transform:skew(.5deg)}30%{clip-path:inset(50% 0 30% 0);transform:skew(.3deg)}35%{clip:rect(80px,9999px,40px,0);transform:skew(.1deg)}40%{clip:rect(10px,9999px,70px,0);transform:skew(.9deg)}45%{clip:rect(70px,9999px,30px,0);transform:skew(.2deg)}50%{clip:rect(30px,9999px,90px,0);transform:skew(.6deg)}55%{clip:rect(90px,9999px,10px,0);transform:skew(.4deg)}60%{clip:rect(10px,9999px,60px,0);transform:skew(.1deg)}65%{clip:rect(60px,9999px,20px,0);transform:skew(.8deg)}70%{clip:rect(20px,9999px,80px,0);transform:skew(.2deg)}75%{clip:rect(80px,9999px,40px,0);transform:skew(.5deg)}80%{clip:rect(40px,9999px,60px,0);transform:skew(.3deg)}85%{clip:rect(60px,9999px,30px,0);transform:skew(.7deg)}90%{clip:rect(30px,9999px,70px,0);transform:skew(.1deg)}95%{clip:rect(70px,9999px,10px,0);transform:skew(.4deg)}100%{clip:rect(10px,9999px,80px,0);transform:skew(.9deg)}}
        .bot-main { border-color: var(--blood-red) !important; box-shadow: var(--shadow-red); }
        .bot-main span:first-child { color: #FF4500; text-shadow: 0 0 8px #FF4500; font-weight: 700; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="skull-icon">💀</div>
            <h1 class="title"><span class="title-main">KARUTA</span> <span class="title-sub">DEEP</span></h1>
            <p class="subtitle">Shadow Network Control Interface</p>
        </div>
        
        <div id="msg-status-container" class="msg-status"><i class="fas fa-info-circle"></i> <span id="msg-status-text"></span></div>

        <div class="main-grid">
            <div class="panel status-panel">
                <h2 data-text="System Status"><i class="fas fa-heartbeat"></i> System Status</h2>
                <div class="bot-status-container">
                    <div class="status-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="status-row"><span class="status-label"><i class="fas fa-cogs"></i> Auto Work</span><div><span id="work-timer" class="timer-display">--:--:--</span> <span id="work-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-calendar-check"></i> Auto Daily</span><div><span id="daily-timer" class="timer-display">--:--:--</span> <span id="daily-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-gem"></i> Auto KVI</span><div><span id="kvi-timer" class="timer-display">--:--:--</span> <span id="kvi-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-broadcast-tower"></i> Auto Spam</span><div><span id="spam-timer" class="timer-display">--:--:--</span><span id="spam-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-redo"></i> Auto Reboot</span><div><span id="reboot-timer" class="timer-display">--:--:--</span> <span id="reboot-status-badge" class="status-badge inactive">OFF</span></div></div>
                        <div class="status-row"><span class="status-label"><i class="fas fa-server"></i> Deep Uptime</span><div><span id="uptime-timer" class="timer-display">--:--:--</span></div></div> 
                    </div>
                    <div id="bot-status-list" class="bot-status-grid"></div>
                </div>
            </div>

            <div class="panel blood-panel">
                <h2 data-text="Soul Harvest"><i class="fas fa-crosshairs"></i> Soul Harvest</h2>
                <div class="harvest-grid">
                    {% if main_bot_configs.get(1) %}
                    <div class="grab-section">
                        <h3>ALPHA NODE <span id="harvest-status-1" class="status-badge {{ grab_status_1 }}">{{ grab_text_1 }}</span></h3>
                        <div class="input-group">
                            <input type="number" id="heart-threshold-1" value="{{ heart_threshold_1 }}" min="0">
                            <button type="button" id="harvest-toggle-1" class="btn {{ grab_button_class_1 }}">{{ grab_action_1 }}</button>
                        </div>
                    </div>
                    {% endif %}
                    {% if main_bot_configs.get(2) %}
                    <div class="grab-section">
                        <h3>BETA NODE <span id="harvest-status-2" class="status-badge {{ grab_status_2 }}">{{ grab_text_2 }}</span></h3>
                        <div class="input-group">
                            <input type="number" id="heart-threshold-2" value="{{ heart_threshold_2 }}" min="0">
                            <button type="button" id="harvest-toggle-2" class="btn {{ grab_button_class_2 }}">{{ grab_action_2 }}</button>
                        </div>
                    </div>
                    {% endif %}
                    {% if main_bot_configs.get(3) %}
                    <div class="grab-section">
                        <h3>GAMMA NODE <span id="harvest-status-3" class="status-badge {{ grab_status_3 }}">{{ grab_text_3 }}</span></h3>
                        <div class="input-group">
                            <input type="number" id="heart-threshold-3" value="{{ heart_threshold_3 }}" min="0">
                            <button type="button" id="harvest-toggle-3" class="btn {{ grab_button_class_3 }}">{{ grab_action_3 }}</button>
                        </div>
                    </div>
                    {% endif %}
                    {% if main_bot_configs.get(4) %}
                    <div class="grab-section">
                        <h3>DELTA NODE <span id="harvest-status-4" class="status-badge {{ grab_status_4 }}">{{ grab_text_4 }}</span></h3>
                        <div class="input-group">
                            <input type="number" id="heart-threshold-4" value="{{ heart_threshold_4 }}" min="0">
                            <button type="button" id="harvest-toggle-4" class="btn {{ grab_button_class_4 }}">{{ grab_action_4 }}</button>
                        </div>
                    </div>
                    {% endif %}
                    {% if main_bot_configs.get(5) %}
                    <div class="grab-section">
                        <h3>EPSILON NODE <span id="harvest-status-5" class="status-badge {{ grab_status_5 }}">{{ grab_text_5 }}</span></h3>
                        <div class="input-group">
                            <input type="number" id="heart-threshold-5" value="{{ heart_threshold_5 }}" min="0">
                            <button type="button" id="harvest-toggle-5" class="btn {{ grab_button_class_5 }}">{{ grab_action_5 }}</button>
                        </div>
                    </div>
                    {% endif %}
                    {% if main_bot_configs.get(6) %}
                    <div class="grab-section">
                        <h3>ZETA NODE <span id="harvest-status-6" class="status-badge {{ grab_status_6 }}">{{ grab_text_6 }}</span></h3>
                        <div class="input-group">
                            <input type="number" id="heart-threshold-6" value="{{ heart_threshold_6 }}" min="0">
                            <button type="button" id="harvest-toggle-6" class="btn {{ grab_button_class_6 }}">{{ grab_action_6 }}</button>
                        </div>
                    </div>
                    {% endif %}
                </div>
            </div>

            <div class="panel ops-panel">
                <h2 data-text="Manual Operations"><i class="fas fa-keyboard"></i> Manual Operations</h2>
                <div style="display: flex; flex-direction: column; gap: 15px;">
                    <div class="input-group"><input type="text" id="manual-message-input" placeholder="Enter manual message for slaves..." style="border-radius: 5px;"><button type="button" id="send-manual-message-btn" class="btn" style="flex-shrink: 0; border-color: var(--neon-yellow, #fff000); color: var(--neon-yellow, #fff000);">SEND</button></div>
                    <div id="quick-cmd-container" class="quick-cmd-grid">
                        <button type="button" data-cmd="kc o:w" class="btn">KC O:W</button><button type="button" data-cmd="kc o:ef" class="btn">KC O:EF</button><button type="button" data-cmd="kc o:p" class="btn">KC O:P</button>
                        <button type="button" data-cmd="kc e:1" class="btn">KC E:1</button><button type="button" data-cmd="kc e:2" class="btn">KC E:2</button><button type="button" data-cmd="kc e:3" class="btn">KC E:3</button>
                        <button type="button" data-cmd="kc e:4" class="btn">KC E:4</button><button type="button" data-cmd="kc e:5" class="btn">KC E:5</button><button type="button" data-cmd="kc e:6" class="btn">KC E:6</button>
                        <button type="button" data-cmd="kc e:7" class="btn">KC E:7</button>
                    </div>
                </div>
            </div>
            
            <div class="panel code-panel">
                <h2 data-text="Code Injection"><i class="fas fa-code"></i> Code Injection</h2>
                <div class="input-group"><label>Target</label><select id="inject-acc-index">{{ acc_options|safe }}</select></div>
                <div class="input-group"><label>Prefix</label><input type="text" id="inject-prefix" placeholder="e.g. kt n"></div>
                <div class="input-group"><label>Delay</label><input type="number" id="inject-delay" value="1.0" step="0.1"></div>
                <div class="input-group" style="flex-direction: column; align-items: stretch;"><label style="border-radius: 5px 5px 0 0; border-bottom: none;">Code List (comma-separated)</label><textarea id="inject-codes" placeholder="paste codes here, separated by commas" rows="3" style="border-radius: 0 0 5px 5px;"></textarea></div>
                <button type="button" id="inject-codes-btn" class="btn btn-primary" style="width: 100%; margin-top:10px;">Inject Codes</button>
            </div>

            <div class="panel void-panel">
                <h2 data-text="Shadow Labor"><i class="fas fa-cogs"></i> Shadow Labor</h2>
                <h3 style="text-align:center; font-family: 'Orbitron'; margin-bottom: 10px; color: var(--text-secondary);">AUTO WORK</h3>
                <div class="input-group"><label>Node Delay</label><input type="number" id="work-delay-between-acc" value="{{ work_delay_between_acc }}"></div>
                <div class="input-group"><label>Cycle Delay</label><input type="number" id="work-delay-after-all" value="{{ work_delay_after_all }}"></div>
                <button type="button" id="auto-work-toggle-btn" class="btn {{ work_button_class }}" style="width:100%;">{{ work_action }} WORK</button>
                <hr style="border-color: var(--border-color); margin: 25px 0;">
                <h3 style="text-align:center; font-family: 'Orbitron'; margin-bottom: 10px; color: var(--text-secondary);">DAILY RITUAL</h3>
                <div class="input-group"><label>Node Delay</label><input type="number" id="daily-delay-between-acc" value="{{ daily_delay_between_acc }}"></div>
                <div class="input-group"><label>Cycle Delay</label><input type="number" id="daily-delay-after-all" value="{{ daily_delay_after_all }}"></div>
                <button type="button" id="auto-daily-toggle-btn" class="btn {{ daily_button_class }}" style="width:100%;">{{ daily_action }} DAILY</button>
            </div>

            <div class="panel necro-panel">
                 <h2 data-text="Shadow Resurrection"><i class="fas fa-skull"></i> Shadow Resurrection</h2>
                <div class="input-group"><label>Interval (s)</label><input type="number" id="auto-reboot-delay" value="{{ auto_reboot_delay }}"></div>
                <button type="button" id="auto-reboot-toggle-btn" class="btn {{ reboot_button_class }}" style="width:100%;">{{ reboot_action }} AUTO REBOOT</button>
                <hr style="border-color: var(--border-color); margin: 20px 0;">
                <h3 style="text-align:center; font-family: 'Orbitron';">MANUAL OVERRIDE</h3>
                <div id="reboot-grid-container" class="reboot-grid" style="margin-top: 15px;">
                    {% for i, config in main_bot_configs.items() %}
                    <button type="button" data-reboot-target="main_{{ i }}" class="btn btn-necro btn-sm">{{ config.name }}</button>
                    {% endfor %}
                    {{ sub_account_buttons|safe }}
                </div>
                 <button type="button" id="reboot-all-btn" class="btn btn-blood" style="width:100%; margin-top: 15px;">REBOOT ALL SYSTEMS</button>
            </div>
            
             <div class="panel dark-panel">
                <h2 data-text="Shadow Broadcast"><i class="fas fa-broadcast-tower"></i> Shadow Broadcast</h2>
                <h3 style="text-align:center; font-family: 'Orbitron'; margin-bottom: 10px; color: var(--text-secondary);">AUTO SPAM</h3>
                <div class="input-group"><label>Message</label><textarea id="spam-message" rows="2">{{ spam_message }}</textarea></div>
                <div class="input-group"><label>Delay (s)</label><input type="number" id="spam-delay" value="{{ spam_delay }}"></div>
                <button type="button" id="spam-toggle-btn" class="btn {{ spam_button_class }}" style="width:100%;">{{ spam_action }} SPAM</button>
                <hr style="border-color: var(--border-color); margin: 25px 0;">
                <h3 style="text-align:center; font-family: 'Orbitron'; margin-bottom: 10px; color: var(--text-secondary);">AUTO KVI (MAIN ACC 1)</h3>
                <div class="input-group"><label>Clicks</label><input type="number" id="kvi-click-count" value="{{ kvi_click_count }}"></div>
                <div class="input-group"><label>Click Delay</label><input type="number" id="kvi-click-delay" value="{{ kvi_click_delay }}"></div>
                <div class="input-group"><label>Cycle Delay</label><input type="number" id="kvi-loop-delay" value="{{ kvi_loop_delay }}"></div>
                <button type="button" id="auto-kvi-toggle-btn" class="btn {{ kvi_button_class }}" style="width:100%;">{{ kvi_action }} KVI</button>
            </div>
        </div>
    </div>
<script>
    document.addEventListener('DOMContentLoaded', function () {
        function initGlitches() {
            document.querySelectorAll('.panel h2').forEach(header => {
                const textContent = header.childNodes[header.childNodes.length - 1].textContent.trim();
                header.setAttribute('data-text', textContent);
            });
        }
        initGlitches();

        const msgStatusContainer = document.getElementById('msg-status-container');
        const msgStatusText = document.getElementById('msg-status-text');

        function showStatusMessage(message) {
            if (!message) return;
            msgStatusText.textContent = message;
            msgStatusContainer.style.display = 'block';
            setTimeout(() => { msgStatusContainer.style.display = 'none'; }, 4000);
        }

        async function postData(url = '', data = {}) {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                showStatusMessage(result.message);
                setTimeout(fetchStatus, 500);
                return result;
            } catch (error) {
                console.error('Error posting data:', error);
                showStatusMessage('Error communicating with server.');
            }
        }

        function formatTime(seconds) {
            if (isNaN(seconds) || seconds < 0) return "--:--:--";
            seconds = Math.floor(seconds);
            const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
            const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
            const s = (seconds % 60).toString().padStart(2, '0');
            return `${h}:${m}:${s}`;
        }

        function updateElement(id, { textContent, className, value, innerHTML }) {
            const el = document.getElementById(id);
            if (!el) return;
            if (textContent !== undefined) el.textContent = textContent;
            if (className !== undefined) el.className = className;
            if (value !== undefined) el.value = value;
            if (innerHTML !== undefined) el.innerHTML = innerHTML;
        }

        async function fetchStatus() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                
                updateElement('work-timer', { textContent: formatTime(data.work_countdown) });
                updateElement('work-status-badge', { textContent: data.work_enabled ? 'ON' : 'OFF', className: `status-badge ${data.work_enabled ? 'active' : 'inactive'}` });
                updateElement('daily-timer', { textContent: formatTime(data.daily_countdown) });
                updateElement('daily-status-badge', { textContent: data.daily_enabled ? 'ON' : 'OFF', className: `status-badge ${data.daily_enabled ? 'active' : 'inactive'}` });
                updateElement('kvi-timer', { textContent: formatTime(data.kvi_countdown) });
                updateElement('kvi-status-badge', { textContent: data.kvi_enabled ? 'ON' : 'OFF', className: `status-badge ${data.kvi_enabled ? 'active' : 'inactive'}` });
                updateElement('reboot-timer', { textContent: formatTime(data.reboot_countdown) });
                updateElement('reboot-status-badge', { textContent: data.reboot_enabled ? 'ON' : 'OFF', className: `status-badge ${data.reboot_enabled ? 'active' : 'inactive'}` });
                updateElement('spam-timer', { textContent: formatTime(data.spam_countdown) });
                updateElement('spam-status-badge', { textContent: data.spam_enabled ? 'ON' : 'OFF', className: `status-badge ${data.spam_enabled ? 'active' : 'inactive'}` });
                const serverUptimeSeconds = (Date.now() / 1000) - data.server_start_time;
                updateElement('uptime-timer', { textContent: formatTime(serverUptimeSeconds) });

                // Logic to update UI from flat ui_states dictionary
                for(let i=1; i<=6; i++) {
                    updateElement(`harvest-toggle-${i}`, { textContent: data.ui_states[`grab_action_${i}`], className: `btn ${data.ui_states[`grab_button_class_${i}`]}` });
                    updateElement(`harvest-status-${i}`, { textContent: data.ui_states[`grab_text_${i}`], className: `status-badge ${data.ui_states[`grab_status_${i}`]}` });
                }

                updateElement('auto-work-toggle-btn', { textContent: `${data.ui_states.work_action} WORK`, className: `btn ${data.ui_states.work_button_class}` });
                updateElement('auto-daily-toggle-btn', { textContent: `${data.ui_states.daily_action} DAILY`, className: `btn ${data.ui_states.daily_button_class}` });
                updateElement('auto-reboot-toggle-btn', { textContent: `${data.ui_states.reboot_action} AUTO REBOOT`, className: `btn ${data.ui_states.reboot_button_class}` });
                updateElement('spam-toggle-btn', { textContent: `${data.ui_states.spam_action} SPAM`, className: `btn ${data.ui_states.spam_button_class}` });
                updateElement('auto-kvi-toggle-btn', { textContent: `${data.ui_states.kvi_action} KVI`, className: `btn ${data.ui_states.kvi_button_class}` });

                const listContainer = document.getElementById('bot-status-list');
                listContainer.innerHTML = ''; 
                const allBots = [...data.bot_statuses.main_bots, ...data.bot_statuses.sub_accounts];
                allBots.forEach(bot => {
                    const item = document.createElement('div');
                    item.className = 'bot-status-item';
                    if (bot.type === 'main') item.classList.add('bot-main');
                    const buttonText = bot.is_active ? 'ONLINE' : 'OFFLINE';
                    const buttonClass = bot.is_active ? 'btn-rise' : 'btn-rest';
                    item.innerHTML = `<span>${bot.name}</span><button type="button" data-target="${bot.reboot_id}" class="btn-toggle-state ${buttonClass}">${buttonText}</button>`;
                    listContainer.appendChild(item);
                });

            } catch (error) { console.error('Error fetching status:', error); }
        }
        setInterval(fetchStatus, 1000);

        // --- Event Listeners ---
        for(let i=1; i<=6; i++) {
            const btn = document.getElementById(`harvest-toggle-${i}`);
            if (btn) {
                 btn.addEventListener('click', () => postData('/api/harvest_toggle', { node: i, threshold: document.getElementById(`heart-threshold-${i}`).value }));
            }
        }
        
        document.getElementById('send-manual-message-btn').addEventListener('click', () => {
            postData('/api/manual_ops', { message: document.getElementById('manual-message-input').value })
                .then(() => { document.getElementById('manual-message-input').value = ''; });
        });
        document.getElementById('quick-cmd-container').addEventListener('click', (e) => {
            if (e.target.matches('button[data-cmd]')) {
                postData('/api/manual_ops', { quickmsg: e.target.dataset.cmd });
            }
        });

        document.getElementById('inject-codes-btn').addEventListener('click', () => {
            postData('/api/inject_codes', {
                acc_index: document.getElementById('inject-acc-index').value,
                prefix: document.getElementById('inject-prefix').value,
                delay: document.getElementById('inject-delay').value,
                codes: document.getElementById('inject-codes').value,
            }).then(() => {
                 document.getElementById('inject-prefix').value = '';
                 document.getElementById('inject-codes').value = '';
            });
        });

        document.getElementById('auto-work-toggle-btn').addEventListener('click', () => {
            postData('/api/labor_toggle', { type: 'work', delay_between: document.getElementById('work-delay-between-acc').value, delay_after: document.getElementById('work-delay-after-all').value });
        });
        document.getElementById('auto-daily-toggle-btn').addEventListener('click', () => {
            postData('/api/labor_toggle', { type: 'daily', delay_between: document.getElementById('daily-delay-between-acc').value, delay_after: document.getElementById('daily-delay-after-all').value });
        });

        document.getElementById('auto-reboot-toggle-btn').addEventListener('click', () => {
            postData('/api/reboot_toggle_auto', { delay: document.getElementById('auto-reboot-delay').value });
        });
        document.getElementById('reboot-all-btn').addEventListener('click', () => {
            postData('/api/reboot_manual', { target: 'all' });
        });
        document.getElementById('reboot-grid-container').addEventListener('click', e => {
            if(e.target.matches('button[data-reboot-target]')) {
                postData('/api/reboot_manual', { target: e.target.dataset.reboot_target });
            }
        });
        
        document.getElementById('spam-toggle-btn').addEventListener('click', () => {
            postData('/api/broadcast_toggle', { type: 'spam', message: document.getElementById('spam-message').value, delay: document.getElementById('spam-delay').value });
        });
        document.getElementById('auto-kvi-toggle-btn').addEventListener('click', () => {
             postData('/api/broadcast_toggle', { type: 'kvi', clicks: document.getElementById('kvi-click-count').value, click_delay: document.getElementById('kvi-click-delay').value, loop_delay: document.getElementById('kvi-loop-delay').value });
        });
        
        document.getElementById('bot-status-list').addEventListener('click', e => {
            if(e.target.matches('button[data-target]')) {
                postData('/api/toggle_bot_state', { target: e.target.dataset.target });
            }
        });
    });
</script>
</body>
</html>
"""

# ... (Các hàm Flask routes và main execution không thay đổi) ...

@app.route("/")
def index():
    def get_ui_state(enabled):
        return ("active", "ON", "DISABLE", "btn-blood") if enabled else ("inactive", "OFF", "ENABLE", "btn-necro")

    grab_status_1, grab_text_1, grab_action_1, grab_button_class_1 = get_ui_state(auto_grab_enabled_1)
    grab_status_2, grab_text_2, grab_action_2, grab_button_class_2 = get_ui_state(auto_grab_enabled_2)
    grab_status_3, grab_text_3, grab_action_3, grab_button_class_3 = get_ui_state(auto_grab_enabled_3)
    grab_status_4, grab_text_4, grab_action_4, grab_button_class_4 = get_ui_state(auto_grab_enabled_4)
    grab_status_5, grab_text_5, grab_action_5, grab_button_class_5 = get_ui_state(auto_grab_enabled_5)
    grab_status_6, grab_text_6, grab_action_6, grab_button_class_6 = get_ui_state(auto_grab_enabled_6)
    
    _, _, spam_action, spam_button_class = get_ui_state(spam_enabled)
    _, _, work_action, work_button_class = get_ui_state(auto_work_enabled)
    _, _, daily_action, daily_button_class = get_ui_state(auto_daily_enabled)
    _, _, kvi_action, kvi_button_class = get_ui_state(auto_kvi_enabled)
    _, _, reboot_action, reboot_button_class = get_ui_state(auto_reboot_enabled)
    
    acc_options = "".join(f'<option value="sub_{i}">{name}</option>' for i, name in enumerate(acc_names[:len(bots)]))
    for i, config in main_bot_configs.items():
        acc_options += f'<option value="main_{i}">{config["name"]} NODE (Main)</option>'

    sub_account_buttons = "".join(f'<button type="button" data-reboot-target="sub_{i}" class="btn btn-necro btn-sm">{name}</button>' for i, name in enumerate(acc_names[:len(bots)]))
    
    return render_template_string(HTML_TEMPLATE, 
        main_bot_configs=main_bot_configs,
        grab_status_1=grab_status_1, grab_text_1=grab_text_1, grab_action_1=grab_action_1, grab_button_class_1=grab_button_class_1, heart_threshold_1=heart_threshold_1,
        grab_status_2=grab_status_2, grab_text_2=grab_text_2, grab_action_2=grab_action_2, grab_button_class_2=grab_button_class_2, heart_threshold_2=heart_threshold_2,
        grab_status_3=grab_status_3, grab_text_3=grab_text_3, grab_action_3=grab_action_3, grab_button_class_3=grab_button_class_3, heart_threshold_3=heart_threshold_3,
        grab_status_4=grab_status_4, grab_text_4=grab_text_4, grab_action_4=grab_action_4, grab_button_class_4=grab_button_class_4, heart_threshold_4=heart_threshold_4,
        grab_status_5=grab_status_5, grab_text_5=grab_text_5, grab_action_5=grab_action_5, grab_button_class_5=grab_button_class_5, heart_threshold_5=heart_threshold_5,
        grab_status_6=grab_status_6, grab_text_6=grab_text_6, grab_action_6=grab_action_6, grab_button_class_6=grab_button_class_6, heart_threshold_6=heart_threshold_6,
        spam_message=spam_message, spam_delay=spam_delay, spam_action=spam_action, spam_button_class=spam_button_class,
        work_delay_between_acc=work_delay_between_acc, work_delay_after_all=work_delay_after_all, work_action=work_action, work_button_class=work_button_class,
        daily_delay_between_acc=daily_delay_between_acc, daily_delay_after_all=daily_delay_after_all, daily_action=daily_action, daily_button_class=daily_button_class,
        kvi_click_count=kvi_click_count, kvi_click_delay=kvi_click_delay, kvi_loop_delay=kvi_loop_delay, kvi_action=kvi_action, kvi_button_class=kvi_button_class,
        auto_reboot_delay=auto_reboot_delay, reboot_action=reboot_action, reboot_button_class=reboot_button_class,
        acc_options=acc_options, sub_account_buttons=sub_account_buttons
    )

@app.route("/api/harvest_toggle", methods=['POST'])
def api_harvest_toggle():
    data = request.get_json()
    node = data.get('node')
    threshold = int(data.get('threshold', 50))
    msg = f"Node {node} không hợp lệ."
    
    enabled_var = f'auto_grab_enabled_{node}'
    threshold_var = f'heart_threshold_{node}'
    
    if enabled_var in globals():
        globals()[enabled_var] = not globals()[enabled_var]
        globals()[threshold_var] = threshold
        state = "BẬT" if globals()[enabled_var] else "TẮT"
        msg = f"Auto Grab cho Node {node} đã được {state}"
        
    return jsonify({'status': 'success', 'message': msg})
@app.route("/api/inject_codes", methods=['POST'])
def api_inject_codes():
    data = request.get_json()
    target_id_str = data.get("acc_index", "")
    delay_val = float(data.get("delay", 1.0))
    prefix = data.get("prefix", "")
    codes_list = [c.strip() for c in data.get("codes", "").split(',') if c.strip()]
    target_bot, target_name = None, "Không xác định"
    
    if target_id_str.startswith('main_'):
        bot_num = int(target_id_str.split('_')[1])
        if bot_num in main_bots:
            target_bot, target_name = main_bots[bot_num], main_bot_configs[bot_num]["name"]
    elif target_id_str.startswith('sub_'):
        acc_idx = int(target_id_str.split('_')[1])
        if acc_idx < len(bots):
            target_bot, target_name = bots[acc_idx], acc_names[acc_idx]
            
    if target_bot and codes_list:
        for i, code in enumerate(codes_list): threading.Timer(delay_val * i, target_bot.sendMessage, args=(other_channel_id, f"{prefix} {code}" if prefix else code)).start()
        msg = f"Đang inject {len(codes_list)} mã vào '{target_name}'."
    else: msg = "Lỗi: Vui lòng chọn tài khoản và điền mã."
    return jsonify({'status': 'success', 'message': msg})
@app.route("/api/manual_ops", methods=['POST'])
def api_manual_ops():
    data = request.get_json()
    msg = ""
    msg_to_send = data.get('message') or data.get('quickmsg')
    if msg_to_send:
        msg = f"Sent to slaves: {msg_to_send}"
        with bots_lock:
            for idx, bot in enumerate(bots): 
                if bot and bot_active_states.get(f'sub_{idx}', False):
                    threading.Timer(2 * idx, bot.sendMessage, args=(other_channel_id, msg_to_send)).start()
    else: msg = "No message provided."
    return jsonify({'status': 'success', 'message': msg})
@app.route("/api/labor_toggle", methods=['POST'])
def api_labor_toggle():
    global auto_work_enabled, work_delay_between_acc, work_delay_after_all, last_work_cycle_time, auto_daily_enabled, daily_delay_between_acc, daily_delay_after_all, last_daily_cycle_time
    data = request.get_json()
    msg = ""
    if data.get('type') == 'work':
        auto_work_enabled = not auto_work_enabled
        if auto_work_enabled and last_work_cycle_time == 0: last_work_cycle_time = time.time() - work_delay_after_all - 1
        work_delay_between_acc = int(data.get('delay_between', 10)); work_delay_after_all = int(data.get('delay_after', 44100))
        msg = f"Auto Work {'ENABLED' if auto_work_enabled else 'DISABLED'}."
    elif data.get('type') == 'daily':
        auto_daily_enabled = not auto_daily_enabled
        if auto_daily_enabled and last_daily_cycle_time == 0: last_daily_cycle_time = time.time() - daily_delay_after_all - 1
        daily_delay_between_acc = int(data.get('delay_between', 3)); daily_delay_after_all = int(data.get('delay_after', 87000))
        msg = f"Auto Daily {'ENABLED' if auto_daily_enabled else 'DISABLED'}."
    return jsonify({'status': 'success', 'message': msg})
@app.route("/api/reboot_manual", methods=['POST'])
def api_reboot_manual():
    data = request.get_json()
    target = data.get('target')
    msg = "Không có target."
    if target:
        if target == "all":
            msg = "Rebooting all systems..."
            for i in range(1, 7):
                if main_bot_configs.get(i): reboot_bot(f'main_{i}'); time.sleep(5)
            with bots_lock:
                for i in range(len(bots)): reboot_bot(f'sub_{i}'); time.sleep(5)
        else:
            bot_name = target.upper()
            try:
                if target.startswith('main_'): bot_name = main_bot_configs[int(target.split('_')[1])]['name']
                elif target.startswith('sub_'): bot_name = acc_names[int(target.split('_')[1])]
            except: pass
            msg = f"Rebooting target: {bot_name}"
            reboot_bot(target)
    return jsonify({'status': 'success', 'message': msg})
@app.route("/api/reboot_toggle_auto", methods=['POST'])
def api_reboot_toggle_auto():
    global auto_reboot_enabled, auto_reboot_delay, auto_reboot_thread, auto_reboot_stop_event
    data = request.get_json()
    auto_reboot_enabled = not auto_reboot_enabled
    auto_reboot_delay = int(data.get("delay", 3600))
    msg = ""
    if auto_reboot_enabled:
        if auto_reboot_thread is None or not auto_reboot_thread.is_alive():
            auto_reboot_stop_event = threading.Event()
            auto_reboot_thread = threading.Thread(target=auto_reboot_loop, daemon=True)
            auto_reboot_thread.start()
        msg = "Auto Reboot ENABLED."
    else:
        if auto_reboot_stop_event: auto_reboot_stop_event.set()
        auto_reboot_thread = None
        msg = "Auto Reboot DISABLED."
    return jsonify({'status': 'success', 'message': msg})
@app.route("/api/broadcast_toggle", methods=['POST'])
def api_broadcast_toggle():
    global spam_enabled, spam_message, spam_delay, spam_thread, last_spam_time, auto_kvi_enabled, kvi_click_count, kvi_click_delay, kvi_loop_delay, last_kvi_cycle_time
    data = request.get_json()
    msg = ""
    if data.get('type') == 'spam':
        spam_message, spam_delay = data.get("message", "").strip(), int(data.get("delay", 10))
        if not spam_enabled and spam_message:
            spam_enabled = True; last_spam_time = time.time(); msg = "Spam ENABLED."
            if spam_thread is None or not spam_thread.is_alive():
                spam_thread = threading.Thread(target=spam_loop, daemon=True); spam_thread.start()
        else: spam_enabled = False; msg = "Spam DISABLED."
    elif data.get('type') == 'kvi':
        auto_kvi_enabled = not auto_kvi_enabled
        if auto_kvi_enabled and last_kvi_cycle_time == 0: last_kvi_cycle_time = time.time() - kvi_loop_delay - 1
        kvi_click_count = int(data.get('clicks', 10)); kvi_click_delay = int(data.get('click_delay', 3)); kvi_loop_delay = int(data.get('loop_delay', 7500))
        msg = f"Auto KVI {'ENABLED' if auto_kvi_enabled else 'DISABLED'}."
    return jsonify({'status': 'success', 'message': msg})
@app.route("/api/toggle_bot_state", methods=['POST'])
def api_toggle_bot_state():
    data = request.get_json()
    target = data.get('target')
    msg = ""
    if target in bot_active_states:
        bot_active_states[target] = not bot_active_states[target]
        state_text = "AWAKENED" if bot_active_states[target] else "DORMANT"
        msg = f"Target {target.upper()} has been set to {state_text}."
    return jsonify({'status': 'success', 'message': msg})

@app.route("/status")
def status():
    now = time.time()
    work_countdown = (last_work_cycle_time + work_delay_after_all - now) if auto_work_enabled else 0
    daily_countdown = (last_daily_cycle_time + daily_delay_after_all - now) if auto_daily_enabled else 0
    kvi_countdown = (last_kvi_cycle_time + kvi_loop_delay - now) if auto_kvi_enabled else 0
    reboot_countdown = (last_reboot_cycle_time + auto_reboot_delay - now) if auto_reboot_enabled else 0
    spam_countdown = (last_spam_time + spam_delay - now) if spam_enabled else 0

    bot_statuses = {"main_bots": [], "sub_accounts": []}
    for i, config in main_bot_configs.items():
        bot_statuses["main_bots"].append({
            "name": config["name"], "status": i in main_bots,
            "reboot_id": f"main_{i}", "is_active": bot_active_states.get(f'main_{i}', False), "type": "main"
        })
    with bots_lock:
        bot_statuses["sub_accounts"] = [
            {"name": acc_names[i] if i < len(acc_names) else f"Sub {i+1}", "status": bot is not None, "reboot_id": f"sub_{i}", "is_active": bot_active_states.get(f'sub_{i}', False), "type": "sub"}
            for i, bot in enumerate(bots)
        ]
    
    def get_ui_state_dict(enabled):
        return ("active", "ON", "DISABLE", "btn-blood") if enabled else ("inactive", "OFF", "ENABLE", "btn-necro")

    ui_states = {}
    states_map = {
        '1': get_ui_state_dict(auto_grab_enabled_1), '2': get_ui_state_dict(auto_grab_enabled_2),
        '3': get_ui_state_dict(auto_grab_enabled_3), '4': get_ui_state_dict(auto_grab_enabled_4),
        '5': get_ui_state_dict(auto_grab_enabled_5), '6': get_ui_state_dict(auto_grab_enabled_6),
    }

    for i in range(1, 7):
        status_val, text_val, action_val, btn_class_val = states_map[str(i)]
        ui_states[f'grab_status_{i}'] = status_val; ui_states[f'grab_text_{i}'] = text_val; ui_states[f'grab_action_{i}'] = action_val; ui_states[f'grab_button_class_{i}'] = btn_class_val

    _, _, ui_states['spam_action'], ui_states['spam_button_class'] = get_ui_state_dict(spam_enabled)
    _, _, ui_states['work_action'], ui_states['work_button_class'] = get_ui_state_dict(auto_work_enabled)
    _, _, ui_states['daily_action'], ui_states['daily_button_class'] = get_ui_state_dict(auto_daily_enabled)
    _, _, ui_states['kvi_action'], ui_states['kvi_button_class'] = get_ui_state_dict(auto_kvi_enabled)
    _, _, ui_states['reboot_action'], ui_states['reboot_button_class'] = get_ui_state_dict(auto_reboot_enabled)
    
    return jsonify({
        'work_enabled': auto_work_enabled, 'work_countdown': work_countdown,
        'daily_enabled': auto_daily_enabled, 'daily_countdown': daily_countdown,
        'kvi_enabled': auto_kvi_enabled, 'kvi_countdown': kvi_countdown,
        'reboot_enabled': auto_reboot_enabled, 'reboot_countdown': reboot_countdown,
        'spam_enabled': spam_enabled, 'spam_countdown': spam_countdown,
        'bot_statuses': bot_statuses,
        'server_start_time': server_start_time,
        'ui_states': ui_states
    })

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    load_settings()
    print("Đang khởi tạo các bot...", flush=True)
    with bots_lock:
        for bot_num, config in main_bot_configs.items():
            print(f"Khởi tạo Main Bot {bot_num} ({config['name']})...", flush=True)
            main_bots[bot_num] = create_bot(config["token"], bot_number=bot_num)
            if f'main_{bot_num}' not in bot_active_states:
                bot_active_states[f'main_{bot_num}'] = True
        for i, token in enumerate(tokens):
            if token.strip():
                bots.append(create_bot(token.strip()))
                if f'sub_{i}' not in bot_active_states:
                    bot_active_states[f'sub_{i}'] = True

    print("Đang khởi tạo các luồng nền...", flush=True)
    if spam_thread is None or not spam_thread.is_alive():
        spam_thread = threading.Thread(target=spam_loop, daemon=True)
        spam_thread.start()

    threading.Thread(target=periodic_save_loop, daemon=True).start()
    threading.Thread(target=auto_work_loop, daemon=True).start()
    threading.Thread(target=auto_daily_loop, daemon=True).start()
    threading.Thread(target=auto_kvi_loop, daemon=True).start()

    if auto_reboot_enabled and (auto_reboot_thread is None or not auto_reboot_thread.is_alive()):
        auto_reboot_stop_event = threading.Event()
        auto_reboot_thread = threading.Thread(target=auto_reboot_loop, daemon=True)
        auto_reboot_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    print(f"Khởi động Web Server tại http://0.0.0.0:{port}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
