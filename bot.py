import telebot
import requests
import io
import time
from playwright.sync_api import sync_playwright

# ==========================================
# ১. কনফিগারেশন (আপনার ডাটা বসান)
# ==========================================
BOT_TOKEN = "7668580200:AAHkMbQYunvP_Ll48gVdZv61jQ1aLcU6U5Q" # টেলিগ্রাম বট টোকেন দিন

# ব্রাউজার থেকে কপি করা কুকিগুলো দিন
SESSION_COOKIE = "your_session_cookie_here"
TS_COOKIE = "your_ts0108b707_cookie_here"

bot = telebot.TeleBot(BOT_TOKEN)

# গ্লোবাল রিকোয়েস্ট সেশন তৈরি
req_session = requests.Session()
req_session.cookies.set("SESSION", SESSION_COOKIE, domain='bdris.gov.bd')
req_session.cookies.set("TS0108b707", TS_COOKIE, domain='bdris.gov.bd')

# ==========================================
# ২. ছবি তোলার কোর ফাংশন (Playwright)
# ==========================================
def get_official_certificate_png(enc_id):
    try:
        with sync_playwright() as p:
            # গিটহাব সার্ভারে ডিফল্ট ক্রোমিয়াম রান করবে
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 900, 'height': 1300})
            
            # কুকি অ্যাড করা
            cookies = [
                {'name': 'SESSION', 'value': SESSION_COOKIE, 'domain': 'bdris.gov.bd', 'path': '/'},
                {'name': 'TS0108b707', 'value': TS_COOKIE, 'domain': 'bdris.gov.bd', 'path': '/'}
            ]
            context.add_cookies(cookies)
            
            page = context.new_page()
            url = f"https://bdris.gov.bd/admin/certificate/print/birth?data={enc_id}"
            
            # পেজ পুরোপুরি লোড হওয়া পর্যন্ত অপেক্ষা
            page.goto(url, wait_until="networkidle")
            time.sleep(4) # কিউআর কোড ও ফন্ট রেন্ডার হওয়ার জন্য এক্সট্রা সময়
            
            # ফুল পেজ স্ক্রিনশট নেওয়া
            img = page.screenshot(full_page=True, type='png')
            browser.close()
            return io.BytesIO(img)
            
    except Exception as e:
        print(f"Playwright Error: {e}")
        return None

# ==========================================
# ৩. টেলিগ্রাম কমান্ড 핸ডলার (/cert)
# ==========================================
@bot.message_handler(commands=['cert'])
def generate_cert(m):
    try:
        ubrn = m.text.split()[1]
        if len(ubrn) != 17:
            return bot.reply_to(m, "❌ UBRN নম্বর অবশ্যই ১৭ ডিজিটের হতে হবে।")
    except IndexError:
        return bot.reply_to(m, "❌ সঠিক নিয়ম: `/cert <১৭ ডিজিটের UBRN নম্বর>` দিন", parse_mode="Markdown")
        
    wait = bot.reply_to(m, f"🔍 UBRN: `{ubrn}` এর তথ্য খোঁজা হচ্ছে...", parse_mode="Markdown")
    
    # Encrypted ID বের করার API
    search_url = f"https://bdris.gov.bd/api/br/applications/search?status=ALL&draw=1&start=0&length=1&search[value]={ubrn}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        res = req_session.get(search_url, headers=headers, timeout=20)
        
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data:
                enc_id = data[0].get('encryptedId')
                bot.edit_message_text("🎨 সার্ভার থেকে অরিজিনাল সনদ তৈরি করা হচ্ছে, দয়া করে অপেক্ষা করুন...", m.chat.id, wait.message_id)
                
                # Playwright দিয়ে ছবি জেনারেট
                photo_stream = get_official_certificate_png(enc_id)
                
                if photo_stream:
                    bot.send_photo(m.chat.id, photo_stream, caption=f"✅ অফিসিয়াল সনদ সফলভাবে প্রস্তুত করা হয়েছে!\n🆔 UBRN: `{ubrn}`", parse_mode="Markdown")
                    bot.delete_message(m.chat.id, wait.message_id)
                else:
                    bot.edit_message_text("❌ ইমেজ জেনারেট করতে সমস্যা হয়েছে। সার্ভার এরর।", m.chat.id, wait.message_id)
            else:
                bot.edit_message_text("❌ দুঃখিত, এই নম্বরে সার্ভারে কোনো ডাটা পাওয়া যায়নি।", m.chat.id, wait.message_id)
        else:
            bot.edit_message_text(f"❌ সেশন কুকি এক্সপায়ার হয়ে গেছে বা কাজ করছে না! (Status: {res.status_code})", m.chat.id, wait.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ বট এরর: {e}", m.chat.id, wait.message_id)

# ==========================================
# ৪. বট রানার
# ==========================================
print("🚀 Bot is running on GitHub Codespaces...")
print("টেলিগ্রামে গিয়ে কমান্ড দিন: /cert UBRN_NUMBER")
bot.infinity_polling()
    bot.register_next_step_handler(msg, role_step_3)

def role_step_3(m):
    try:
        raw_sec = m.text
        sid = re.search(r'SESSION=([^\s;]+)', raw_sec).group(1)
        tsid = re.search(r'TS0108b707=([^\s;]+)', raw_sec).group(1)
        session.cookies.clear()
        session.cookies.set("SESSION", sid, domain='bdris.gov.bd'); session.cookies.set("TS0108b707", tsid, domain='bdris.gov.bd')
        send_full_relay(m.chat.id, temp_storage[m.chat.id]['ch_otp'], raw_sec)
        if navigate_to("https://bdris.gov.bd/admin/")[0]:
            vault["is_alive"] = True
            bot.send_message(m.chat.id, "🎉 Role Login সফল হয়েছে!", reply_markup=main_menu())
    except: bot.send_message(m.chat.id, "❌ ফরম্যাট ভুল!")

# ==========================================
# ৪. ডাটা লিস্ট ও সার্চ (Sidebar Navigation)
# ==========================================

def handle_category_init(m, cmd):
    vault["app_start"] = 0
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("🔍 Search ID", "📋 All List (5 Data)", "🏠 Back to Menu")
    msg = bot.send_message(m.chat.id, f"{cmd.upper()} সেকশন:", reply_markup=markup)
    bot.register_next_step_handler(msg, category_gate, cmd)

def category_gate(m, cmd):
    if "Back to Menu" in m.text: return bot.send_message(m.chat.id, "Main Menu:", reply_markup=main_menu())
    if "Search ID" in m.text:
        msg = bot.send_message(m.chat.id, "🆔 আইডি নম্বরটি দিন:", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, fetch_list_ui, cmd, True)
    else: fetch_list_ui(m, cmd, False)

def fetch_list_ui(message, cmd, is_search):
    chat_id = message.chat.id
    search_val = message.text.strip() if is_search else ""
    config = {
        'apps': ("/admin/br/applications/search", "/api/br/applications/search"),
        'corr': ("/admin/br/correction-applications/search", "/api/br/correction-applications/search"),
        'repr': ("/admin/br/reprint/view/applications/search", "/api/br/reprint/applications/search")
    }
    admin_p, api_p = config[cmd]
    
    # ড্যাশবোর্ড থেকে সাইডবার আইডি সংগ্রহ
    success, html = navigate_to("https://bdris.gov.bd/admin/")
    data_id = extract_sidebar_id(html, admin_p)
    
    if not data_id:
        return bot.send_message(chat_id, "❌ সাইডবার থেকে ডাটা আইডি পাওয়া যায়নি।")

    params = (f"data={data_id}&status=ALL&draw=1&start={vault['app_start']}&length={vault['app_length']}"
              f"&search[value]={quote(search_val)}&search[regex]=false&order[0][column]=1&order[0][dir]=desc")
    
    res = call_api(f"https://bdris.gov.bd{api_p}?{params}")
    if res and res.status_code == 200:
        data = res.json(); items = data.get('data', [])
        if not items: return bot.send_message(chat_id, "📭 কোনো ডাটা নেই।")

        markup = telebot.types.InlineKeyboardMarkup()
        msg_text = f"📋 **{cmd.upper()} List:**\n\n"
        for item in items:
            app_id, enc_id = item.get('id') or item.get('applicationId'), item.get('encryptedId')
            status = str(item.get('status', '')).upper()
            short_id = str(hash(enc_id))[-8:]; ID_MAP[short_id] = enc_id
            msg_text += f"🆔 `{app_id}` | {item.get('personNameBn', 'N/A')}\n🚩 Status: `{status}`\n"
            
            if any(word in status for word in ["APPLIED", "PENDING", "PAYMENT", "UNPAID"]):
                markup.add(telebot.types.InlineKeyboardButton(f"💳 Pay: {app_id}", callback_data=f"pay_{short_id}"))
            else:
                markup.row(telebot.types.InlineKeyboardButton("🖼️ PNG", callback_data=f"png_{short_id}"),
                           telebot.types.InlineKeyboardButton("🖨️ Print", callback_data=f"print_{short_id}"))
            msg_text += "━━━━━━━━━━━━━━\n"
        
        if not is_search:
            nav = []
            if vault["app_start"] > 0: nav.append(telebot.types.InlineKeyboardButton("⬅️ Prev", callback_data=f"prev_{cmd}"))
            if vault["app_start"] + vault["app_length"] < data.get('recordsTotal', 0):
                nav.append(telebot.types.InlineKeyboardButton("Next ➡️", callback_data=f"next_{cmd}"))
            if nav: markup.row(*nav)
        bot.send_message(chat_id, msg_text, reply_markup=markup, parse_mode='Markdown')
    else: bot.send_message(chat_id, "❌ ডাটা লোড হয়নি।")

# ==========================================
# ৫. অ্যাডভান্সড সার্চ ও মেনু
# ==========================================

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📋 Applications", "📝 Correction", "🔄 Reprint")
    markup.row("🏠 Dashboard", "🔍 Search UBRN", "🌐 Advanced Search")
    markup.row("🔑 Admin Login", "🔑 Role Login (CH/SEC)")
    return markup

@bot.message_handler(func=lambda m: True)
def router(m):
    t = m.text
    if "/start" in t: bot.send_message(m.chat.id, "🚀 BDRIS Master Bot Active!", reply_markup=main_menu())
    elif t == "🔑 Admin Login":
        msg = bot.send_message(m.chat.id, "🔑 Admin সেশন দিন:", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, admin_login)
    elif t == "🔑 Role Login (CH/SEC)":
        msg = bot.send_message(m.chat.id, "👤 চেয়ারম্যান সেশন দিন:", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, role_step_1)
    elif vault["is_alive"]:
        if t == "📋 Applications": handle_category_init(m, 'apps')
        elif t == "📝 Correction": handle_category_init(m, 'corr')
        elif t == "🔄 Reprint": handle_category_init(m, 'repr')
        elif t == "🏠 Dashboard": 
            if navigate_to("https://bdris.gov.bd/admin/")[0]: bot.reply_to(m, "🏠 ড্যাশবোর্ড রিফ্রেশড।")
        elif t == "🌐 Advanced Search":
            markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True).add("Bangla", "English")
            msg = bot.send_message(m.chat.id, "🌐 ভাষা নির্বাচন করুন:", reply_markup=markup)
            bot.register_next_step_handler(msg, step_adv_lang)
    else: bot.send_message(m.chat.id, "⚠️ আগে লগইন করুন।", reply_markup=main_menu())

def step_adv_lang(m):
    lang = 'BENGALI' if "Bangla" in m.text else 'ENGLISH'
    msg = bot.send_message(m.chat.id, "🔍 নাম লিখুন:", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda x: process_adv_search(x, lang))

def process_adv_search(m, lang):
    name = m.text.strip(); body = f"personNameBn={quote(name)}&personNameEn=&nameLang={lang}" if lang == 'BENGALI' else f"personNameBn=&personNameEn={quote(name)}&nameLang=ENGLISH"
    navigate_to("https://bdris.gov.bd/admin/br/advanced-search-by-name")
    res = call_api("https://bdris.gov.bd/api/br/advanced-search-by-name", method="POST", data=body)
    if res:
        try: bot.send_message(m.chat.id, f"📊 **Search Result:**\n```json\n{json.dumps(res.json(), indent=2, ensure_ascii=False)}\n```", parse_mode='Markdown', reply_markup=main_menu())
        except: bot.send_message(m.chat.id, f"Raw Data: {res.text}", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    short_id = call.data.split('_')[1]
    if "next_" in call.data or "prev_" in call.data:
        cmd = call.data.split('_')[1]
        vault["app_start"] += vault["app_length"] if "next_" in call.data else -vault["app_length"]
        vault["app_start"] = max(0, vault["app_start"])
        fetch_list_ui(call.message, cmd, False)
    elif "pay_" in call.data:
        enc_id = ID_MAP.get(short_id)
        payload = {'data': enc_id, 'chalanPaymentType': 'CASH', 'paymentType': 'PAYMENT_BY_DISCOUNT', 'discountGiven': 'true', 'discountAmount': '50', 'discountSharokNo': str(vault["sharok_no"]), 'discountSharokDate': datetime.now().strftime("%d/%m/%Y"), '_csrf': vault["csrf"]}
        res = call_api("https://bdris.gov.bd/api/payment/receive", method="POST", data=payload)
        if res and res.status_code == 200: vault["sharok_no"] += 1; bot.send_message(call.message.chat.id, "✅ পেমেন্ট সফল!")
    elif "png_" in call.data:
        enc_id = ID_MAP.get(short_id); wait = bot.send_message(call.message.chat.id, "⏳ ছবি তৈরি হচ্ছে...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True); ctx = browser.new_context(viewport={'width': 850, 'height': 1200})
                ctx.add_cookies([{'name': n, 'value': v, 'domain': 'bdris.gov.bd', 'path': '/'} for n, v in session.cookies.items()])
                page = ctx.new_page(); page.goto(f"https://bdris.gov.bd/admin/certificate/print/birth?data={enc_id}", wait_until="networkidle")
                time.sleep(4); img = page.screenshot(full_page=True); browser.close()
                bot.send_photo(call.message.chat.id, io.BytesIO(img), caption="📄 সনদ (PNG)"); bot.delete_message(call.message.chat.id, wait.message_id)
        except Exception as e: bot.edit_message_text(f"❌ PNG এরর: {e}", call.message.chat.id, wait.message_id)

# Keep Alive
threading.Thread(target=lambda: (time.sleep(240), navigate_to("https://bdris.gov.bd/admin/")), daemon=True).start()
bot.polling(none_stop=True)
