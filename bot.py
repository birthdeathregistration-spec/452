import telebot
import requests
import json
import io
import threading
import time
import re
from datetime import datetime
from urllib.parse import quote
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ==========================================
# ১. কনফিগারেশন ও ফন্ট সেটআপ
# ==========================================
API_TOKEN = '8721977069:AAH2QA4mT4L57Cw9hqawOU4l1kSbND9au1Y'
bot = telebot.TeleBot(API_TOKEN)

# বাংলা ফন্ট রেজিস্টার (নিশ্চিত করুন SolaimanLipi.ttf ফাইলটি কোড ফোল্ডারে আছে)
try:
    pdfmetrics.registerFont(TTFont('BanglaFont', 'SolaimanLipi.ttf'))
except:
    print("⚠️ Bangla Font not found! PDF will show boxes.")

session = requests.Session()
vault = {
    "csrf": "",
    "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "is_alive": False,
    "current_page": "https://bdris.gov.bd/admin/",
    "app_start": 0,
    "app_length": 10, # ১০টি করে ডাটা লোড হবে
    "sharok_no": 1
}

ID_MAP = {} 

# ==========================================
# ২. PDF তৈরির ফাংশন (JSON to PDF)
# ==========================================

def create_pdf_sonod(data):
    """সার্ভারের JSON ডাটা থেকে PDF সনদ তৈরি করবে"""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(600, 800))
    
    # ডিজাইন ও ফন্ট সেটআপ
    can.setFont('BanglaFont', 20)
    can.drawCentredString(300, 750, "জন্ম নিবন্ধন সনদ")
    can.line(50, 740, 550, 740)
    
    can.setFont('BanglaFont', 14)
    # JSON থেকে ডাটা বের করা (সার্ভারের ফিল্ড নেম অনুযায়ী)
    info = [
        f"নিবন্ধন নম্বর: {data.get('ubrn', 'N/A')}",
        f"নাম: {data.get('personNameBn', 'N/A')}",
        f"পিতার নাম: {data.get('fatherNameBn', 'N/A')}",
        f"মাতার নাম: {data.get('motherNameBn', 'N/A')}",
        f"জন্ম তারিখ: {data.get('dateOfBirth', 'N/A')}",
        f"লিঙ্গ: {data.get('gender', 'N/A')}",
        f"ঠিকানা: {data.get('permanentAddressBn', 'N/A')}"
    ]
    
    y = 700
    for text in info:
        can.drawString(100, y, text)
        y -= 30
        
    can.save()
    packet.seek(0)
    return packet

# ==========================================
# ৩. রিপিন্ট ও ডাটা লজিক (Fix: Reprint Data Load)
# ==========================================

def navigate_to(url):
    headers = {'User-Agent': vault["ua"], 'Referer': vault["current_page"]}
    try:
        res = session.get(url, headers=headers, timeout=25)
        csrf_match = re.search(r'name="_csrf" content="([^"]+)"', res.text)
        if csrf_match: vault["csrf"] = csrf_match.group(1)
        vault["current_page"] = url
        return True, res.text
    except: return False, None

def call_api(url, method="GET", data=None):
    headers = {
        'authority': 'bdris.gov.bd', 'client': 'bris',
        'x-csrf-token': vault["csrf"], 'x-requested-with': 'XMLHttpRequest',
        'user-agent': vault["ua"], 'referer': vault["current_page"]
    }
    try:
        if method == "POST": 
            headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
            return session.post(url, headers=headers, data=data, timeout=30)
        return session.get(url, headers=headers, timeout=30)
    except: return None

def extract_data_id(html):
    match = re.search(r'data=([A-Za-z0-9_\-]+)', html)
    return match.group(1) if match else None

def fetch_list_ui(message, cmd):
    chat_id = message.chat.id
    # রিপিন্ট এর জন্য সঠিক এপিআই পাথ (Fix: 2tar bodle sob asbe)
    config = {
        'apps': ("/admin/br/applications/search", "/api/br/applications/search"),
        'corr': ("/admin/br/correction-applications/search", "/api/br/correction-applications/search"),
        'repr': ("/admin/br/reprint/view/applications/search", "/api/br/reprint/applications/search")
    }
    admin_p, api_p = config[cmd]
    
    success, html = navigate_to(f"https://bdris.gov.bd{admin_p}")
    data_id = extract_data_id(html)
    
    if not data_id: 
        return bot.send_message(chat_id, "❌ ডাটা আইডি পাওয়া যায়নি। সেশন চেক করুন।")

    # ডাটা লেন্থ ১০ করা হয়েছে যাতে আরও বেশি ডাটা আসে
    params = f"data={data_id}&status=ALL&draw=1&start={vault['app_start']}&length={vault['app_length']}&search[value]=&search[regex]=false&order[0][column]=1&order[0][dir]=desc"
    
    res = call_api(f"https://bdris.gov.bd{api_p}?{params}")
    if res and res.status_code == 200:
        data = res.json()
        items = data.get('data', [])
        if not items: return bot.send_message(chat_id, "📭 কোনো ডাটা নেই।")

        markup = telebot.types.InlineKeyboardMarkup()
        msg_text = f"📋 **{cmd.upper()} Results:**\n\n"
        for item in items:
            app_id, enc_id = item.get('id') or item.get('applicationId'), item.get('encryptedId')
            status = str(item.get('status', '')).upper()
            short_id = str(hash(enc_id))[-8:] 
            ID_MAP[short_id] = enc_id
            
            msg_text += f"🆔 `{app_id}` | {item.get('personNameBn', 'N/A')}\n🚩 অবস্থা: `{status}`\n"
            
            # পিডিএফ তৈরি এবং পেমেন্ট বাটন
            if any(word in status for word in ["APPLIED", "PENDING"]):
                markup.add(telebot.types.InlineKeyboardButton(f"💳 Pay: {app_id}", callback_data=f"pay_{short_id}"))
            else:
                markup.row(
                    telebot.types.InlineKeyboardButton(f"📄 Create PDF: {app_id}", callback_data=f"pdf_{short_id}"),
                    telebot.types.InlineKeyboardButton(f"✅ Paid", callback_data="none")
                )
            msg_text += "━━━━━━━━━━━━━━\n"
        
        bot.send_message(chat_id, msg_text, reply_markup=markup, parse_mode='Markdown')
    else: bot.send_message(chat_id, "❌ ডাটা লোড হয়নি।")

# ==========================================
# ৪. কলব্যাক হ্যান্ডলার (PDF Generation Fix)
# ==========================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "none": return
    
    if call.data.startswith("pdf_"):
        enc_id = ID_MAP.get(call.data.replace("pdf_", ""))
        bot.answer_callback_query(call.id, "⏳ সনদ তৈরি হচ্ছে...")
        
        # ১. আগে সার্ভার থেকে ওই আইডির বিস্তারিত ডাটা (JSON) নিতে হবে
        # আপনার সিস্টেমে আইডি দিয়ে ডিটেইলস ডাটা আনার এপিআই কল করুন
        res = call_api(f"https://bdris.gov.bd/api/br/info/encrypted/{enc_id}")
        
        if res and res.status_code == 200:
            json_data = res.json()
            # ২. JSON থেকে PDF তৈরি
            pdf_file = create_pdf_sonod(json_data)
            
            # ৩. ফাইল হিসেবে সেন্ড করা
            pdf_file.name = f"Sonod_{json_data.get('ubrn', 'info')}.pdf"
            bot.send_document(call.message.chat.id, pdf_file, caption="📄 আপনার তৈরি করা সনদ।")
        else:
            bot.send_message(call.message.chat.id, "❌ সার্ভার থেকে ডাটা পাওয়া যায়নি।")

    elif call.data.startswith("pay_"):
        # পেমেন্ট লজিক আগের মতোই থাকবে
        pass

# ==========================================
# ৫. রাউটার ও স্টার্ট
# ==========================================

@bot.message_handler(func=lambda m: True)
def router(m):
    txt = m.text
    if "/start" in txt:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("📋 Applications", "🔄 Reprint")
        return bot.send_message(m.chat.id, "🚀 BDRIS Master Bot Active!", reply_markup=markup)

    if txt == "📋 Applications": fetch_list_ui(m, 'apps')
    elif txt == "🔄 Reprint": fetch_list_ui(m, 'repr')
    # ... (অন্যান্য কমান্ড)

bot.polling(none_stop=True)
