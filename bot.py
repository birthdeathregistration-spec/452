import telebot
import requests
import json
import io
import time
import re
import logging
from threading import Thread
from datetime import datetime
from urllib.parse import quote
from playwright.sync_api import sync_playwright

# ==========================================
# ০. লগিং সেটআপ ও টোকেন
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 👇👇👇 ঠিক এখানে তোমার বট টোকেন বসাও 👇👇👇
API_TOKEN = "7668580200:AAHkMbQYunvP_Ll48gVdZv61jQ1aLcU6U5Q"

bot = telebot.TeleBot(API_TOKEN)

# ==========================================
# ১. ইউজার সেশন ম্যানেজমেন্ট
# ==========================================
user_sessions = {}

def get_session(chat_id):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {
            "req_session": requests.Session(),
            "csrf": "",
            "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
            "is_alive": False,
            "current_page": "https://bdris.gov.bd/admin/",
            "app_start": 0,
            "app_length": 5,
            "sharok_no": 1,
            "temp_data": {},
            "id_cache": {} 
        }
    return user_sessions[chat_id]

# ==========================================
# ২. কোর ইঞ্জিন (Navigation & API)
# ==========================================
def navigate_to(chat_id, url):
    u_sess = get_session(chat_id)
    headers = {'User-Agent': u_sess["ua"], 'Referer': u_sess["current_page"]}
    try:
        res = u_sess["req_session"].get(url, headers=headers, timeout=25)
        csrf_match = re.search(r'name="_csrf" content="([^"]+)"', res.text)
        if csrf_match: 
            u_sess["csrf"] = csrf_match.group(1)
        u_sess["current_page"] = url
        return True, res.text
    except Exception as e:
        logging.error(f"[{chat_id}] Navigation Error ({url}): {e}")
        return False, None

def call_api(chat_id, url, method="GET", data=None):
    u_sess = get_session(chat_id)
    headers = {
        'x-csrf-token': u_sess["csrf"], 
        'x-requested-with': 'XMLHttpRequest',
        'user-agent': u_sess["ua"], 
        'referer': u_sess["current_page"], 
        'origin': 'https://bdris.gov.bd'
    }
    try:
        if method == "POST":
            return u_sess["req_session"].post(url, headers=headers, data=data, timeout=30)
        return u_sess["req_session"].get(url, headers=headers, timeout=30)
    except Exception as e:
        logging.error(f"[{chat_id}] API Error: {e}")
        return None

def extract_sidebar_id(html, path):
    if not html: return None
    regex = rf'href="{re.escape(path)}\?data=([A-Za-z0-9_\-]+)"'
    match = re.search(regex, html)
    return match.group(1) if match else None

def keep_sessions_alive():
    while True:
        time.sleep(300)
        for chat_id, u_sess in list(user_sessions.items()):
            if u_sess["is_alive"]:
                navigate_to(chat_id, "https://bdris.gov.bd/admin/")

def is_cancel(m):
    text = m.text.strip() if m.text else ""
    if text.startswith("/start") or "Back to Menu" in text or "Dashboard" in text:
        bot.send_message(m.chat.id, "🏠 প্রধান মেনুতে ফিরে যাওয়া হলো।", reply_markup=main_menu())
        bot.clear_step_handler_by_chat_id(m.chat.id)
        return True
    return False

# ==========================================
# ৩. লগইন সিস্টেম (Admin & Role)
# ==========================================
def admin_login(m):
    if is_cancel(m): return
    chat_id = m.chat.id
    u_sess = get_session(chat_id)
    try:
        raw = m.text.strip()
        sid = re.search(r'SESSION=([^\s;]+)', raw).group(1)
        tsid = re.search(r'TS0108b707=([^\s;]+)', raw).group(1)
        
        u_sess["req_session"].cookies.clear()
        u_sess["req_session"].cookies.set("SESSION", sid, domain='bdris.gov.bd')
        u_sess["req_session"].cookies.set("TS0108b707", tsid, domain='bdris.gov.bd')
        
        u_sess["is_alive"] = True
        bot.send_message(chat_id, "✅ Admin Login সফল!", reply_markup=main_menu())
    except Exception as e:
        msg = bot.send_message(chat_id, "❌ ফরম্যাট ভুল! দয়া করে সঠিক সেশন আবার দিন:")
        bot.register_next_step_handler(msg, admin_login)

def role_step_1(m):
    if is_cancel(m): return
    chat_id = m.chat.id
    u_sess = get_session(chat_id)
    raw_ch = m.text.strip()
    wait_msg = bot.send_message(chat_id, "⏳ চেয়ারম্যান সেশন চেক করা হচ্ছে...")
    
    try:
        sid = re.search(r'SESSION=([^\s;]+)', raw_ch).group(1)
        tsid = re.search(r'TS0108b707=([^\s;]+)', raw_ch).group(1)
        temp_req = requests.Session()
        temp_req.cookies.set("SESSION", sid, domain='bdris.gov.bd')
        temp_req.cookies.set("TS0108b707", tsid, domain='bdris.gov.bd')
        
        res = temp_req.get("https://bdris.gov.bd/admin/", headers={'User-Agent': u_sess["ua"]}, timeout=25)
        try: bot.delete_message(chat_id, wait_msg.message_id) 
        except: pass
        
        if "Logout" in res.text:
            msg = bot.send_message(chat_id, "✅ চেয়ারম্যান সেশন ভ্যালিড! এখন OTP প্রদান করুন:")
            bot.register_next_step_handler(msg, role_step_2)
        else:
            msg = bot.send_message(chat_id, "❌ চেয়ারম্যান সেশনটি ইনভ্যালিড! আবার দিন:")
            bot.register_next_step_handler(msg, role_step_1)
    except:
        try: bot.delete_message(chat_id, wait_msg.message_id) 
        except: pass
        msg = bot.send_message(chat_id, "❌ সেশন ফরম্যাট ভুল! আবার দিন:")
        bot.register_next_step_handler(msg, role_step_1)

def role_step_2(m):
    if is_cancel(m): return
    chat_id = m.chat.id
    msg = bot.send_message(chat_id, "✅ এখন সেক্রেটারি (Secretary) সেশন দিন:")
    bot.register_next_step_handler(msg, role_step_3)

def role_step_3(m):
    if is_cancel(m): return
    chat_id = m.chat.id
    u_sess = get_session(chat_id)
    raw_sec = m.text.strip()
    wait_msg = bot.send_message(chat_id, "⏳ সেক্রেটারি সেশন চেক করা হচ্ছে...")
    
    try:
        sid = re.search(r'SESSION=([^\s;]+)', raw_sec).group(1)
        tsid = re.search(r'TS0108b707=([^\s;]+)', raw_sec).group(1)
        u_sess["req_session"].cookies.clear()
        u_sess["req_session"].cookies.set("SESSION", sid, domain='bdris.gov.bd')
        u_sess["req_session"].cookies.set("TS0108b707", tsid, domain='bdris.gov.bd')
        
        success, html = navigate_to(chat_id, "https://bdris.gov.bd/admin/")
        try: bot.delete_message(chat_id, wait_msg.message_id) 
        except: pass
        
        if success and html and "Logout" in html:
            u_sess["is_alive"] = True
            bot.send_message(chat_id, "🎉 লগইন সফল হয়েছে!", reply_markup=main_menu())
        else:
            u_sess["req_session"].cookies.clear() 
            msg = bot.send_message(chat_id, "❌ সেক্রেটারি সেশনটি ইনভ্যালিড! আবার দিন:")
            bot.register_next_step_handler(msg, role_step_3)
    except:
        try: bot.delete_message(chat_id, wait_msg.message_id) 
        except: pass
        msg = bot.send_message(chat_id, "❌ সেশন ফরম্যাট ভুল! আবার দিন:")
        bot.register_next_step_handler(msg, role_step_3)

# ==========================================
# ৪. অটো সনদ (Original Template) Playwright
# ==========================================
def get_official_certificate_png(chat_id, enc_id):
    u_sess = get_session(chat_id)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 900, 'height': 1300})
            
            cookies = [{'name': n, 'value': v, 'domain': 'bdris.gov.bd', 'path': '/'} 
                       for n, v in u_sess["req_session"].cookies.items()]
            context.add_cookies(cookies)
            
            page = context.new_page()
            url = f"https://bdris.gov.bd/admin/certificate/print/birth?data={enc_id}"
            page.goto(url, wait_until="networkidle")
            time.sleep(3) 
            
            img = page.screenshot(full_page=True, type='png')
            browser.close()
            return io.BytesIO(img)
    except Exception as e:
        logging.error(f"PNG Generation Error: {e}")
        return None

def start_auto_cert_flow(m):
    if is_cancel(m): return
    chat_id = m.chat.id
    ubrn = m.text.strip()
    
    wait = bot.send_message(chat_id, "🔍 সার্ভার থেকে ডাটা ও টেমপ্লেট সংগ্রহ করা হচ্ছে...")
    search_url = f"https://bdris.gov.bd/api/br/applications/search?status=ALL&draw=1&start=0&length=1&search[value]={ubrn}"
    res = call_api(chat_id, search_url)
    
    if res and res.status_code == 200:
        data = res.json().get('data', [])
        if data:
            enc_id = data[0].get('encryptedId')
            bot.edit_message_text("🎨 অফিসিয়াল টেমপ্লেটে সনদ তৈরি হচ্ছে, দয়া করে অপেক্ষা করুন...", chat_id, wait.message_id)
            
            photo_stream = get_official_certificate_png(chat_id, enc_id)
            
            if photo_stream:
                bot.send_photo(chat_id, photo_stream, caption=f"✅ অফিসিয়াল সনদ তৈরি সম্পন্ন!\n🆔 UBRN: `{ubrn}`", parse_mode="Markdown")
                bot.delete_message(chat_id, wait.message_id)
            else:
                bot.edit_message_text("❌ ইমেজ জেনারেট করা সম্ভব হয়নি। Playwright এরর।", chat_id, wait.message_id)
        else:
            bot.edit_message_text("❌ এই নম্বরে সার্ভারে কোনো ডাটা পাওয়া যায়নি।", chat_id, wait.message_id)
    else:
        bot.edit_message_text("❌ সেশন এরর! আবার লগইন করুন।", chat_id, wait.message_id)

# ==========================================
# ৫. ডাটা লিস্ট ও সার্চ ক্যাটাগরি (Applications)
# ==========================================
def handle_category_init(m, cmd):
    chat_id = m.chat.id
    get_session(chat_id)["app_start"] = 0
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("🔍 Search ID", "📋 All List (5 Data)", "🏠 Back to Menu")
    msg = bot.send_message(chat_id, f"{cmd.upper()} সেকশন:", reply_markup=markup)
    bot.register_next_step_handler(msg, category_gate, cmd)

def category_gate(m, cmd):
    if is_cancel(m): return
    if "Search ID" in m.text:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True).add("🏠 Back to Menu")
        msg = bot.send_message(m.chat.id, "🆔 আইডি নম্বরটি দিন:", reply_markup=markup)
        bot.register_next_step_handler(msg, search_loop_step, cmd)
    else: 
        fetch_list_ui(m, cmd, False)

def search_loop_step(m, cmd):
    if is_cancel(m): return
    fetch_list_ui(m, cmd, True)
    msg = bot.send_message(m.chat.id, "🔍 আরও খুঁজতে আইডি দিন, অথবা মেনুতে ফিরতে '🏠 Back to Menu' চাপুন:")
    bot.register_next
