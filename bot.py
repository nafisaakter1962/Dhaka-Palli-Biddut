import html
import io
import os
import re
from threading import Thread
from flask import Flask
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Render Port Binding Keep-Alive Server
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is running perfectly on Render!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

keep_alive()

# Configuration
BOT_TOKEN = "8575875186:AAHlK3khfZlfEpd8BSWIZtVksX4xYC3FuwA"
DEFAULT_CRM_USERNAME = "bhedarganj"

BASE_URL = "https://reportpanel.carnival.com.bd/zonecrm/"
LOGIN_URL = BASE_URL + "index.php"
ADVANCE_AUTH_URL = BASE_URL + "advance_access.php"
DETAILS_URL = BASE_URL + "user_details.php?carnivalid="
SEARCH_PAGE_URL = BASE_URL + "search.php"
NEW_CLIENT_URL = BASE_URL + "interim.php"
PENDING_CLIENT_URL = BASE_URL + "pendingclient.php"
APPROVED_CLIENT_URL = BASE_URL + "approvedclient.php"
HOME_URL = BASE_URL + "home.php"
INVOICE_URL = BASE_URL + "invoiceclient.php"
AREA_URL = BASE_URL + "area.php"
PAYMENT_ISSUE_URL = BASE_URL + "zone_payment_issue.php"
PAYMENT_HISTORY_URL = BASE_URL + "zone_payment_issue_history.php"
CARD_ORDER_URL = BASE_URL + "cardorder.php"
PKG_MIGRATION_URL = BASE_URL + "package_migration.php"
COMPLAIN_URL = BASE_URL + "ticket.php"
WIFI_HAAT_URL = BASE_URL + "wifihaat.php"

ALL_USERS_URL = BASE_URL + "all_user_list.php"
ONLINE_USERS_URL = BASE_URL + "online_user_list.php"
REGISTERED_USERS_URL = BASE_URL + "registered_user_list.php"
EXPIRED_USERS_URL = BASE_URL + "expired_user_list.php"

AREA_LIST = [
    "narayonpur_bhedarganj",
    "akbor_bhedarganj",
    "biplob_bhedarganj",
    "shaheen_bhedarganj",
    "narayonpurpt_bhedarganj",
]

PAYMENT_ISSUES = [
    "Balance Transfer",
    "Balance Not Updated",
    "Date Extension",
    "Partial Billing Date Adjustment",
    "Other Billing Issues",
]

# Conversation States
WAITING_FOR_PASSWORD, WAITING_FOR_AUTH_PASS = range(2)
NC_NAME, NC_MOBILE, NC_ADDRESS, NC_PACKAGE, NC_NID = range(5)
ACT_INPUT_ID, ACT_DEPOSIT_AMOUNT = range(2)
AREA_UPDATE_ID = 0
PI_USER_ID, PI_DETAILS = range(2)
MIGRATE_USER_ID = 0
COMPLAIN_DETAILS = 0

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
})
is_logged_in = False

def clean(text):
    return html.escape(str(text))

def format_bd_phone(raw_phone):
    digits = re.sub(r"\D", "", str(raw_phone))
    if digits.startswith("880"):
        return digits
    elif digits.startswith("01"):
        return "88" + digits
    elif digits.startswith("1") and len(digits) == 10:
        return "880" + digits
    return None

def get_full_dashboard_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔍 Search Info (ID / Range)", callback_data="btn_search_prompt"), InlineKeyboardButton("📊 Live Status", callback_data="btn_status_view")],
        [InlineKeyboardButton("🛠 Client Actions", callback_data="btn_client_actions"), InlineKeyboardButton("🧾 Invoices & Bills", callback_data="btn_invoice_menu")],
        [InlineKeyboardButton("📍 Area Management", callback_data="btn_area_menu"), InlineKeyboardButton("➕ New Client", callback_data="btn_new_client_menu")],
        [InlineKeyboardButton("💳 Card Order", callback_data="btn_card_order"), InlineKeyboardButton("💵 Payment Issue", callback_data="btn_payment_issue_menu")],
        [InlineKeyboardButton("🔄 Package Migration", callback_data="btn_pkg_migration"), InlineKeyboardButton("📩 Complain", callback_data="btn_complain_menu")],
        [InlineKeyboardButton("📶 WiFi Haat", callback_data="btn_wifi_haat"), InlineKeyboardButton("🔄 Relogin (/start)", callback_data="btn_relogin")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_status_sub_keyboard():
    keyboard = [
        [InlineKeyboardButton("👥 All Users", callback_data="view_list_all"), InlineKeyboardButton("🟢 Online Users", callback_data="view_list_online")],
        [InlineKeyboardButton("🔵 Registered Users", callback_data="view_list_reg"), InlineKeyboardButton("🔴 Expired / Failed", callback_data="view_list_expired")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="btn_back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_new_client_sub_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add Client Form", callback_data="nc_add_start")],
        [InlineKeyboardButton("⏳ Pending Requests", callback_data="nc_pending_list")],
        [InlineKeyboardButton("✅ Approved Requests", callback_data="nc_approved_list")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="btn_back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_actions_sub_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 Add Deposit", callback_data="act_deposit"), InlineKeyboardButton("🔄 Renew ID", callback_data="act_renew")],
        [InlineKeyboardButton("🟢 Enable Client", callback_data="act_enable"), InlineKeyboardButton("🔴 Disable Client", callback_data="act_disable")],
        [InlineKeyboardButton("🗑 Remove MAC", callback_data="act_remove_mac")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="btn_back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_invoice_sub_keyboard():
    keyboard = [
        [InlineKeyboardButton("💵 Today's Offline Payment", callback_data="inv_today_offline")],
        [InlineKeyboardButton("💳 Today's Online Payment", callback_data="inv_today_online")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="btn_back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_area_sub_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Area Wise Payment", callback_data="area_pay_menu")],
        [InlineKeyboardButton("🔄 Change Client Area", callback_data="area_change_menu")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="btn_back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_payment_issue_sub_keyboard():
    keyboard = [
        [InlineKeyboardButton("📝 Report New Issue", callback_data="pi_new_issue_menu")],
        [InlineKeyboardButton("📜 Issue History", callback_data="pi_history")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="btn_back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Dual-Login Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_logged_in
    is_logged_in = False
    
    keyboard = [[InlineKeyboardButton(f"👤 {DEFAULT_CRM_USERNAME}", callback_data="select_user")]]
    await update.message.reply_text(
        "স্বাগতম! লগইন করার জন্য নিচে আপনার ইউজার আইডিতে ক্লিক করুন:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"ইউজার আইডি: <b>{clean(DEFAULT_CRM_USERNAME)}</b> নির্বাচিত হয়েছে।\n\nঅনুগ্রহ করে আপনার <b>CRM Password</b> লিখে পাঠান:",
        parse_mode="HTML"
    )
    return WAITING_FOR_PASSWORD

async def receive_crm_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["crm_pass"] = update.message.text.strip()
    await update.message.reply_text(
        "✅ CRM পাসওয়ার্ড গ্রহণ করা হয়েছে।\n\nএখন আপনার <b>Advance Access (Auth Password)</b> লিখে পাঠান:",
        parse_mode="HTML"
    )
    return WAITING_FOR_AUTH_PASS

async def receive_auth_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_logged_in, session
    auth_pass = update.message.text.strip()
    crm_pass = context.user_data.get("crm_pass")
    
    wait_msg = await update.message.reply_text("উভয় ধাপে প্রমাণীকরণ সম্পন্ন করা হচ্ছে, দয়া করে অপেক্ষা করুন...")
    
    try:
        session.cookies.clear()
        
        crm_payload = {"username": DEFAULT_CRM_USERNAME, "password": crm_pass, "submit": "Login"}
        session.post(LOGIN_URL, data=crm_payload, timeout=15)
        
        advance_payload = {"auth_password": auth_pass, "verify": "Verify"}
        session.post(ADVANCE_AUTH_URL, data=advance_payload, timeout=15)
        
        home_check = session.get(HOME_URL, timeout=15)
        
        if "Logout" in home_check.text or "Current Status" in home_check.text:
            is_logged_in = True
            await wait_msg.edit_text(
                "🎉 <b>সিআরএম এবং অ্যাডভান্স লগইন সফল হয়েছে!</b>\n\nনিচের ড্যাশবোর্ড থেকে সেবা নির্বাচন করুন অথবা সরাসরি গ্রাহক আইডি বা রেঞ্জ লিখে পাঠান:",
                parse_mode="HTML",
                reply_markup=get_full_dashboard_keyboard()
            )
        else:
            is_logged_in = False
            await wait_msg.edit_text("❌ পাসওয়ার্ড সঠিক নয় বা লগইন ব্যর্থ হয়েছে। পুনরায় চেষ্টা করতে /start দিন।")
            
    except Exception as e:
        is_logged_in = False
        await wait_msg.edit_text(f"⚠️ লগইনে ত্রুটি: {clean(e)}")
        
    return ConversationHandler.END

# Search Logic
async def search_prompt_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "🔍 <b>গ্রাহক অনুসন্ধান (Search)</b>\n\n"
        "• সিঙ্গেল আইডি: <code>610139</code>\n"
        "• মোবাইল নম্বর: <code>01798041312</code>\n"
        "• রেঞ্জ সার্চ (সর্বোচ্চ ৫০০): <code>610100-610150</code>\n\n"
        "অনুগ্রহ করে চ্যাটে লিখে পাঠান:",
        parse_mode="HTML"
    )

def find_carnival_id_by_phone(phone_number):
    try:
        search_payload = {"mobile": phone_number, "carnival_id": "", "email": "", "search": "Search"}
        res = session.post(SEARCH_PAGE_URL, data=search_payload, timeout=15)
        match = re.search(r"user_details\.php\?carnivalid=(\d+)", res.text)
        return match.group(1) if match else None
    except Exception:
        return None

def fetch_raw_details(client_id):
    try:
        url = f"{DETAILS_URL}{client_id}"
        response = session.get(url, timeout=10)
        if "CRM Login" in response.text:
            return "EXPIRED"

        soup = BeautifulSoup(response.text, "html.parser")
        data = {}
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cols = row.find_all(["td", "th"])
                if len(cols) >= 2:
                    data[cols[0].text.strip()] = cols[1].text.strip()

        if not data or "User ID" not in data:
            return None
        return data
    except Exception:
        return None

def format_single_client_msg(data, client_id):
    raw_status = data.get("Connection Status", "Offline")
    status_display = "🟢 <b>Online</b>" if "Online" in raw_status else "🔴 <b>Offline</b>"
    raw_account = data.get("Account Status", "N/A")
    account_display = "🟢 Active" if "Active" in raw_account else f"🔴 {clean(raw_account)}"

    return (
        f"👤 <b>গ্রাহকের তথ্য (Client Details)</b>\n"
        f"──────────────────\n"
        f"🆔 <b>User ID:</b> <code>{clean(data.get('User ID', client_id))}</code>\n"
        f"👤 <b>Name:</b> {clean(data.get('Name', 'N/A'))}\n"
        f"📞 <b>Mobile:</b> <code>{clean(data.get('Mobile', 'N/A'))}</code>\n"
        f"🏠 <b>Address:</b> {clean(data.get('Address', 'N/A'))}\n"
        f"📍 <b>Area:</b> {clean(data.get('Area', 'N/A'))}\n"
        f"📦 <b>Package:</b> {clean(data.get('Package', 'N/A'))}\n"
        f"💳 <b>Balance:</b> {clean(data.get('Balance', '0.00'))} ৳\n"
        f"⏳ <b>Expire Date:</b> <code>{clean(data.get('Expired Date', 'N/A'))}</code>\n\n"
        f"🌐 <b>কানেকশন স্ট্যাটাস (Connection)</b>\n"
        f"──────────────────\n"
        f"📶 <b>Status:</b> {status_display}\n"
        f"⚙️ <b>Account:</b> {account_display}\n"
        f"🔗 <b>IP:</b> <code>{clean(data.get('Assigned IP', 'N/A'))}</code>\n"
        f"📟 <b>MAC:</b> <code>{clean(data.get('Router MAC', 'N/A'))}</code>\n"
        f"🕒 <b>Last Logoff:</b> {clean(data.get('Last Logoff', 'N/A'))}"
    )

async def execute_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_logged_in
    if not is_logged_in:
        await update.message.reply_text("⚠️ আপনি লগইন অবস্থায় নেই। প্রথমে /start দিয়ে লগইন সম্পন্ন করুন।")
        return

    raw_text = update.message.text.strip()

    range_match = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", raw_text)
    if range_match:
        start_id = int(range_match.group(1))
        end_id = int(range_match.group(2))

        if start_id > end_id:
            start_id, end_id = end_id, start_id

        total_count = (end_id - start_id) + 1

        if total_count > 500:
            await update.message.reply_text("⚠️ আপনি সর্বোচ্চ ৫০০টি আইডির রেঞ্জ সার্চ করতে পারবেন।")
            return

        progress_msg = await update.message.reply_text(
            f"🔄 <b>রেঞ্জ সার্চ শুরু হয়েছে:</b> <code>{start_id}</code> থেকে <code>{end_id}</code> (মোট {total_count} টি আইডি)\n"
            f"অনুগ্রহ করে কিছুক্ষণ অপেক্ষা করুন...",
            parse_mode="HTML"
        )

        found_users = []
        online_count = 0
        offline_count = 0

        for current_id in range(start_id, end_id + 1):
            data = fetch_raw_details(str(current_id))
            if data == "EXPIRED":
                is_logged_in = False
                await progress_msg.edit_text("⚠️ সেশনের মেয়াদ শেষ হয়ে গেছে। আবার /start দিন।")
                return
            if data:
                status = data.get("Connection Status", "Offline")
                is_on = "Online" in status
                if is_on:
                    online_count += 1
                else:
                    offline_count += 1

                found_users.append({
                    "id": current_id,
                    "name": data.get("Name", "N/A"),
                    "mobile": data.get("Mobile", "N/A"),
                    "status": "Online" if is_on else "Offline",
                    "package": data.get("Package", "N/A"),
                    "area": data.get("Area", "N/A"),
                    "balance": data.get("Balance", "0.00"),
                    "expired": data.get("Expired Date", "N/A")
                })

        if not found_users:
            await progress_msg.edit_text(f"❌ রেঞ্জ <code>{start_id}-{end_id}</code> এর মধ্যে কোনো গ্রাহক পাওয়া যায়নি।", parse_mode="HTML")
            return

        file_buffer = io.StringIO()
        file_buffer.write("Carnival Internet - Bhedarganj Range Search Result\n")
        file_buffer.write(f"Range: {start_id} to {end_id} | Total Found: {len(found_users)}\n")
        file_buffer.write("="*75 + "\n\n")

        for u in found_users:
            file_buffer.write(
                f"ID: {u['id']} | Name: {u['name']} | Mobile: {u['mobile']}\n"
                f"Status: {u['status']} | Package: {u['package']} | Area: {u['area']}\n"
                f"Balance: {u['balance']} Tk | Expire Date: {u['expired']}\n"
                f"{'-'*75}\n"
            )

        file_bytes = io.BytesIO(file_buffer.getvalue().encode("utf-8"))
        file_bytes.name = f"Range_{start_id}_{end_id}.txt"

        summary_text = (
            f"📊 <b>রেঞ্জ সার্চ ফলাফল:</b>\n"
            f"──────────────────\n"
            f"🔢 <b>রেঞ্জ:</b> <code>{start_id}</code> — <code>{end_id}</code>\n"
            f"👥 <b>মোট প্রাপ্ত গ্রাহক:</b> {len(found_users)} জন\n"
            f"🟢 <b>Online:</b> {online_count} জন\n"
            f"🔴 <b>Offline:</b> {offline_count} জন\n\n"
            f"📁 বিস্তারিত তালিকাটি ফাইলে পাঠানো হলো:"
        )

        await progress_msg.edit_text(summary_text, parse_mode="HTML")
        await update.message.reply_document(document=file_bytes, caption=f"📄 Range Search ({start_id} to {end_id})")
        return

    input_text = raw_text
    if not input_text.isdigit():
        await update.message.reply_text("সঠিক আইডি, মোবাইল নম্বর অথবা রেঞ্জ দিন।")
        return

    wait_msg = await update.message.reply_text("তথ্য অনুসন্ধান করা হচ্ছে...")

    if len(input_text) in [10, 11] and (input_text.startswith("01") or input_text.startswith("1")):
        carnival_id = find_carnival_id_by_phone(input_text)
        if not carnival_id:
            await wait_msg.edit_text(f"❌ মোবাইল নম্বর: <code>{clean(input_text)}</code> দিয়ে কোনো আইডি পাওয়া যায়নি।", parse_mode="HTML")
            return
        data = fetch_raw_details(carnival_id)
        cid = carnival_id
    else:
        data = fetch_raw_details(input_text)
        cid = input_text

    if data == "EXPIRED":
        is_logged_in = False
        await wait_msg.edit_text("⚠️ সেশনের মেয়াদ শেষ। আবার /start দিয়ে লগইন করুন।")
        return
    elif data is None:
        await wait_msg.edit_text("❌ কোনো তথ্য পাওয়া যায়নি।", parse_mode="HTML")
        return

    msg_text = format_single_client_msg(data, cid)
    mobile = data.get("Mobile")

    reply_markup = None
    if mobile:
        formatted_number = format_bd_phone(mobile)
        if formatted_number:
            reply_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("💬 WhatsApp", url=f"https://wa.me/{formatted_number}"),
                    InlineKeyboardButton("✈️ Telegram", url=f"https://t.me/+{formatted_number}")
                ]
            ])

    await wait_msg.edit_text(msg_text, parse_mode="HTML", reply_markup=reply_markup)

# Status & Lists
async def view_live_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wait_msg = await query.message.reply_text("ড্যাশবোর্ড রিপোর্ট আনা হচ্ছে...")

    try:
        res = session.get(HOME_URL, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        
        status_box = {}
        for tr in soup.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            if len(tds) >= 2:
                status_box[tds[0].text.strip()] = tds[1].text.strip()

        msg = (
            "📊 <b>Carnival Internet - Current Status</b>\n"
            "──────────────────────────\n"
            f"👥 <b>Total User:</b> <code>{status_box.get('Total User', 'N/A')}</code>\n"
            f"🟢 <b>Online User:</b> <code>{status_box.get('Online User', 'N/A')}</code>\n"
            f"🔵 <b>Registered User:</b> <code>{status_box.get('Registered User', 'N/A')}</code>\n"
            f"🔴 <b>Renewal Failed:</b> <code>{status_box.get('Renewal Failed User', 'N/A')}</code>\n"
            f"💰 <b>Remaining Balance:</b> <code>{status_box.get('Remaining Balance', '0')} ৳</code>\n\n"
            "তালিকা দেখতে নিচের বাটন চাপুন:"
        )
        await wait_msg.edit_text(msg, parse_mode="HTML", reply_markup=get_status_sub_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ স্ট্যাটাস আনতে ত্রুটি: {clean(e)}")

async def handle_user_lists_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    target_map = {
        "view_list_all": (ALL_USERS_URL, "👥 All Users", "👥"),
        "view_list_online": (ONLINE_USERS_URL, "🟢 Online Users", "🟢"),
        "view_list_reg": (REGISTERED_USERS_URL, "🔵 Registered Users", "🔵"),
        "view_list_expired": (EXPIRED_USERS_URL, "🔴 Expired / Failed Users", "🔴")
    }

    url, title, icon = target_map[data]
    wait_msg = await query.message.reply_text(f"{title} সংগ্রহ করা হচ্ছে...")

    try:
        res = session.get(url, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table")

        if not table:
            await wait_msg.edit_text(f"📋 {title}: কোনো তথ্য পাওয়া যায়নি।")
            return

        records = []
        rows = table.find_all("tr")
        for tr in rows[1:11]:
            cols = [td.text.strip() for td in tr.find_all(["td", "th"])]
            if len(cols) >= 3:
                records.append(
                    f"{icon} <b>ID:</b> <code>{clean(cols[0])}</code>\n"
                    f"👤 <b>Name:</b> {clean(cols[1])}\n"
                    f"🏠 <b>Address:</b> {clean(cols[2])}"
                )

        if not records:
            await wait_msg.edit_text("📋 কোনো ডাটা পাওয়া যায়নি।")
            return

        final_text = f"<b>{title} (Recent 10):</b>\n\n" + "\n\n──────────────────\n\n".join(records)
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Status", callback_data="btn_status_view")]])
        await wait_msg.edit_text(final_text, parse_mode="HTML", reply_markup=back_btn)
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")

# New Client Operations
async def new_client_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_logged_in:
        await query.message.reply_text("⚠️ অনুগ্রহ করে আগে /start দিয়ে লগইন সম্পন্ন করুন।")
        return
    await query.message.reply_text(
        "📂 <b>Carnival - New Client Menu</b>\nনিচের অপশনগুলো থেকে বেছে নিন:",
        parse_mode="HTML",
        reply_markup=get_new_client_sub_keyboard()
    )

async def new_client_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📝 <b>নতুন ক্লায়েন্ট যুক্তকরণ (ধাপ ১/৫):</b>\n\nগ্রাহকের পূর্ণ নাম লিখে পাঠান:", parse_mode="HTML")
    return NC_NAME

async def nc_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nc_name"] = update.message.text.strip()
    await update.message.reply_text("📝 <b>ধাপ ২/৫:</b> গ্রাহকের মোবাইল নম্বর লিখে পাঠান:")
    return NC_MOBILE

async def nc_receive_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nc_mobile"] = update.message.text.strip()
    await update.message.reply_text("📝 <b>ধাপ ৩/৫:</b> গ্রাহকের পূর্ণ ঠিকানা লিখে পাঠান:")
    return NC_ADDRESS

async def nc_receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nc_address"] = update.message.text.strip()
    await update.message.reply_text("📝 <b>ধাপ ৪/৫:</b> প্যাকেজের নাম বা স্পিড (যেমন: 21 Mbps):")
    return NC_PACKAGE

async def nc_receive_package(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nc_package"] = update.message.text.strip()
    await update.message.reply_text("📝 <b>ধাপ ৫/৫:</b> জাতীয় পরিচয়পত্র (NID) নম্বর দিন (না থাকলে NA লিখুন):")
    return NC_NID

async def nc_submit_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nc_nid"] = update.message.text.strip()
    wait_msg = await update.message.reply_text("আবেদনটি সার্ভারে জমা দেওয়া হচ্ছে...")
    
    payload = {
        "client_name": context.user_data.get("nc_name"),
        "client_mobile": context.user_data.get("nc_mobile"),
        "client_address": context.user_data.get("nc_address"),
        "client_package": context.user_data.get("nc_package"),
        "client_nid": context.user_data.get("nc_nid"),
        "submit": "Submit"
    }
    try:
        session.post(NEW_CLIENT_URL, data=payload, timeout=15)
        summary = (
            f"✅ <b>নতুন গ্রাহকের আবেদন সফলভাবে গৃহীত হয়েছে!</b>\n\n"
            f"👤 <b>নাম:</b> {clean(context.user_data.get('nc_name'))}\n"
            f"📞 <b>মোবাইল:</b> {clean(context.user_data.get('nc_mobile'))}\n"
            f"🏠 <b>ঠিকানা:</b> {clean(context.user_data.get('nc_address'))}\n"
            f"📦 <b>প্যাকেজ:</b> {clean(context.user_data.get('nc_package'))}\n"
            f"🆔 <b>NID:</b> {clean(context.user_data.get('nc_nid'))}"
        )
        await wait_msg.edit_text(summary, parse_mode="HTML", reply_markup=get_full_dashboard_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")
    return ConversationHandler.END

async def handle_pending_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wait_msg = await query.message.reply_text("পেন্ডিং তালিকা সংগ্রহ করা হচ্ছে...")

    try:
        res = session.get(PENDING_CLIENT_URL, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table")
        rows = []
        for table in tables:
            for tr in table.find_all("tr"):
                cols = [td.text.strip() for td in tr.find_all(["td", "th"])]
                if cols:
                    rows.append(" | ".join(cols))

        msg = "📋 <b>Pending Client List:</b>\n\n" + ("\n".join(rows[:10]) if rows else "বর্তমানে কোনো পেন্ডিং আবেদন নেই।")
        await wait_msg.edit_text(clean(msg), parse_mode="HTML", reply_markup=get_new_client_sub_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")

async def handle_approved_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wait_msg = await query.message.reply_text("অনুমোদিত তালিকা সংগ্রহ করা হচ্ছে...")

    try:
        res = session.get(APPROVED_CLIENT_URL, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        blocks = re.split(r'(#\d+)', soup.get_text())
        
        results = []
        for i in range(1, len(blocks), 2):
            tag = blocks[i].strip()
            body = blocks[i+1].strip() if (i+1) < len(blocks) else ""
            lines = [l.strip() for l in body.split("\n") if l.strip()][:8]
            results.append(f"<b>{clean(tag)}</b>\n" + "\n".join([clean(l) for l in lines]))

        output = "✅ <b>সর্বশেষ অনুমোদিত গ্রাহক তালিকা (Approved):</b>\n\n" + "\n\n──────────────────\n\n".join(results[:5])
        await wait_msg.edit_text(output, parse_mode="HTML", reply_markup=get_new_client_sub_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")

# Client Management Actions
async def client_actions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("🛠 <b>Client Management Actions:</b>\nএকটি অপশন নির্বাচন করুন:", parse_mode="HTML", reply_markup=get_actions_sub_keyboard())

async def act_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["current_action"] = query.data.replace("act_", "")
    await query.message.reply_text("👉 গ্রাহকের <b>Carnival ID</b> লিখে পাঠান:", parse_mode="HTML")
    return ACT_INPUT_ID

async def act_process_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c_id = update.message.text.strip()
    if not c_id.isdigit():
        await update.message.reply_text("সঠিক আইডি দিন।")
        return ACT_INPUT_ID

    context.user_data["action_cid"] = c_id
    act = context.user_data.get("current_action")

    if act == "deposit":
        await update.message.reply_text("💰 ডিপোজিটের পরিমাণ লিখুন (প্যাকেজ রেটের জন্য 0 লিখুন):")
        return ACT_DEPOSIT_AMOUNT

    wait_msg = await update.message.reply_text(f"{act.capitalize()} সম্পন্ন করা হচ্ছে...")
    payload = {"carnival_id": c_id, act: act.capitalize()}
    try:
        session.post(HOME_URL, data=payload, timeout=15)
        await wait_msg.edit_text(f"✅ Carnival ID <code>{clean(c_id)}</code> এর জন্য <b>{clean(act.upper())}</b> কার্যকর হয়েছে!", parse_mode="HTML", reply_markup=get_full_dashboard_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")
    return ConversationHandler.END

async def act_process_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = update.message.text.strip()
    c_id = context.user_data.get("action_cid")
    wait_msg = await update.message.reply_text("ডিপোজিট প্রসেস করা হচ্ছে...")

    payload = {
        "carnival_id": c_id,
        "amount": "" if amount == "0" else amount,
        "comments": "Bot Recharge",
        "submit": "Add Deposit"
    }
    try:
        session.post(HOME_URL, data=payload, timeout=15)
        await wait_msg.edit_text(f"✅ Carnival ID <code>{clean(c_id)}</code>-এ ডিপোজিট সফল হয়েছে!", parse_mode="HTML", reply_markup=get_full_dashboard_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")
    return ConversationHandler.END

# Invoices
async def invoice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("🧾 <b>Payment Invoice & Client Bills:</b>\nএকটি অপশন বেছে নিন:", parse_mode="HTML", reply_markup=get_invoice_sub_keyboard())

async def handle_today_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pay_type = "Offline" if "offline" in query.data else "Online"
    wait_msg = await query.message.reply_text(f"আজকের {pay_type} পেমেন্ট তালিকা খোঁজা হচ্ছে...")

    try:
        payload = {"submit": f"{pay_type} List"}
        res = session.post(INVOICE_URL, data=payload, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table")
        rows = []
        for table in tables:
            for tr in table.find_all("tr"):
                cols = [td.text.strip() for td in tr.find_all(["td", "th"])]
                if cols:
                    rows.append(" | ".join(cols))

        msg = f"📋 <b>Today's {pay_type} Payments:</b>\n\n" + ("\n".join(rows[:12]) if rows else "কোনো রেকর্ড নেই।")
        await wait_msg.edit_text(clean(msg), parse_mode="HTML")
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")

# Area Management
async def area_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📍 <b>Area Management:</b>\nএকটি অপশন নির্বাচন করুন:", parse_mode="HTML", reply_markup=get_area_sub_keyboard())

async def area_pay_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    buttons = [[InlineKeyboardButton(f"📍 {area}", callback_data=f"arpay_{area}")] for area in AREA_LIST]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="btn_area_menu")])
    await query.message.reply_text("কোন এলাকার পেমেন্ট দেখতে চান?", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_area_payment_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chosen_area = query.data.replace("arpay_", "")
    wait_msg = await query.message.reply_text(f"📍 <b>{clean(chosen_area)}</b> এলাকার পেমেন্ট খোঁজা হচ্ছে...", parse_mode="HTML")

    try:
        payload = {"area": chosen_area, "submit": "Offline List"}
        res = session.post(AREA_URL, data=payload, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table")
        rows = []
        for table in tables:
            for tr in table.find_all("tr"):
                cols = [td.text.strip() for td in tr.find_all(["td", "th"])]
                if cols:
                    rows.append(" | ".join(cols))

        msg = f"📋 <b>{clean(chosen_area)} - Payments:</b>\n\n" + ("\n".join(rows[:10]) if rows else "কোনো রেকর্ড নেই।")
        await wait_msg.edit_text(clean(msg), parse_mode="HTML")
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")

async def area_change_select_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    buttons = [[InlineKeyboardButton(f"➡️ {area}", callback_data=f"setar_{area}")] for area in AREA_LIST]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="btn_area_menu")])
    await query.message.reply_text("গ্রাহককে কোন এলাকায় যুক্ত করবেন?", reply_markup=InlineKeyboardMarkup(buttons))

async def area_take_client_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["target_area"] = query.data.replace("setar_", "")
    await query.message.reply_text("গ্রাহকের **Carnival ID** লিখে পাঠান:")
    return AREA_UPDATE_ID

async def execute_area_client_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c_id = update.message.text.strip()
    target_area = context.user_data.get("target_area")
    wait_msg = await update.message.reply_text("এরিয়া আপডেট করা হচ্ছে...")

    try:
        payload = {"carnival_id": c_id, "area": target_area, "submit": "Update"}
        session.post(AREA_URL, data=payload, timeout=15)
        await wait_msg.edit_text(f"✅ Carnival ID: <code>{clean(c_id)}</code> সফলভাবে <b>{clean(target_area)}</b>-এ স্থানান্তরিত হয়েছে!", parse_mode="HTML", reply_markup=get_full_dashboard_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")
    return ConversationHandler.END

# Payment Issues
async def payment_issue_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("💵 <b>Carnival - Payment Issues:</b>\nএকটি অপশন বেছে নিন:", parse_mode="HTML", reply_markup=get_payment_issue_sub_keyboard())

async def pi_history_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wait_msg = await query.message.reply_text("পেমেন্ট হিস্ট্রি লোড করা হচ্ছে...")

    try:
        res = session.get(PAYMENT_HISTORY_URL, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table")

        if not table:
            await wait_msg.edit_text("📋 বর্তমানে কোনো হিস্ট্রি পাওয়া যায়নি।")
            return

        records = []
        rows = table.find_all("tr")
        for tr in rows[1:6]:
            cols = [td.text.strip() for td in tr.find_all(["td", "th"])]
            if len(cols) >= 5:
                comment = cols[5] if len(cols) > 5 and cols[5] else "Pending"
                status_emoji = "✅" if "Approved" in comment or "Done" in comment else "⏳"
                records.append(
                    f"🎫 <b>Ticket #{clean(cols[0])}</b> ({status_emoji} {clean(comment)})\n"
                    f"📌 <b>Type:</b> {clean(cols[1])}\n"
                    f"🆔 <b>User ID:</b> <code>{clean(cols[2])}</code>\n"
                    f"🔄 <b>Transfer ID:</b> <code>{clean(cols[3] if cols[3] else 'N/A')}</code>\n"
                    f"🕒 <b>Time:</b> <code>{clean(cols[4])}</code>"
                )

        final_msg = "📜 <b>সর্বশেষ ৫টি Payment Issue History:</b>\n\n" + "\n\n──────────────────\n\n".join(records)
        await wait_msg.edit_text(final_msg, parse_mode="HTML", reply_markup=get_payment_issue_sub_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")

async def pi_select_issue_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    buttons = [[InlineKeyboardButton(issue, callback_data=f"setpi_{issue}")] for issue in PAYMENT_ISSUES]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="btn_payment_issue_menu")])
    await query.message.reply_text("সমস্যার ধরন নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(buttons))

async def pi_take_client_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["pi_type"] = query.data.replace("setpi_", "")
    await query.message.reply_text("গ্রাহকের <b>User ID / Carnival ID</b> লিখে পাঠান:", parse_mode="HTML")
    return PI_USER_ID

async def pi_receive_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pi_uid"] = update.message.text.strip()
    await update.message.reply_text("টাকার পরিমাণ (Amount), Trnx ID বা বিবরণ লিখে পাঠান:")
    return PI_DETAILS

async def pi_submit_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details = update.message.text.strip()
    wait_msg = await update.message.reply_text("ইস্যুটি জমা দেওয়া হচ্ছে...")

    payload = {
        "issue_type": context.user_data.get("pi_type"),
        "user_id": context.user_data.get("pi_uid"),
        "amount": details,
        "description": details,
        "submit": "Submit"
    }
    try:
        session.post(PAYMENT_ISSUE_URL, data=payload, timeout=15)
        await wait_msg.edit_text("✅ <b>পেমেন্ট ইস্যু সফলভাবে রিপোর্ট করা হয়েছে!</b>", parse_mode="HTML", reply_markup=get_full_dashboard_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")

    return ConversationHandler.END

# Additional Services
async def card_order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wait_msg = await query.message.reply_text("💳 কার্ড অর্ডার তথ্য সংগ্রহ করা হচ্ছে...")

    try:
        res = session.get(CARD_ORDER_URL, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table")
        info = []
        for t in tables:
            for tr in t.find_all("tr"):
                cols = [td.text.strip() for td in tr.find_all(["td", "th"])]
                if cols:
                    info.append(" | ".join(cols))

        text = "💳 <b>Card Order History:</b>\n\n" + "\n".join(info[:10]) if info else "💳 বর্তমানে কোনো পেন্ডিং কার্ড অর্ডার নেই।"
        await wait_msg.edit_text(clean(text), parse_mode="HTML", reply_markup=get_full_dashboard_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")

async def pkg_migration_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("🔄 প্যাকেজ মাইগ্রেশন করতে গ্রাহকের <b>Carnival ID</b> লিখে পাঠান:", parse_mode="HTML")
    return MIGRATE_USER_ID

async def execute_pkg_migration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c_id = update.message.text.strip()
    wait_msg = await update.message.reply_text("মাইগ্রেশন তথ্য যাচাই করা হচ্ছে...")

    try:
        res = session.post(PKG_MIGRATION_URL, data={"carnival_id": c_id, "submit": "Search"}, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table")
        
        rep = "🔄 <b>Migration Details:</b>\n\n" + "\n".join([" : ".join([td.text.strip() for td in tr.find_all(["td", "th"])]) for tr in table.find_all("tr")]) if table else f"✅ Carnival ID <code>{clean(c_id)}</code> প্যাকেজ মাইগ্রেশনের জন্য প্রস্তুত।"
        await wait_msg.edit_text(rep, parse_mode="HTML", reply_markup=get_full_dashboard_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")
    return ConversationHandler.END

async def complain_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📜 View Active Tickets", callback_data="comp_view_tickets")],
        [InlineKeyboardButton("✍️ Submit New Complain", callback_data="comp_add_ticket")],
        [InlineKeyboardButton("⬅️ Back to Menu", callback_data="btn_back_main")]
    ]
    await query.message.reply_text("📩 <b>Complain & Support Portal:</b>\nএকটি অপশন বেছে নিন:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def comp_view_tickets_fetch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wait_msg = await query.message.reply_text("কমপ্লেইন তালিকা সংগ্রহ করা হচ্ছে...")

    try:
        res = session.get(COMPLAIN_URL, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table")
        rows = []
        for t in tables:
            for tr in t.find_all("tr"):
                cols = [td.text.strip() for td in tr.find_all(["td", "th"])]
                if cols:
                    rows.append(" | ".join(cols))

        msg = "📋 <b>Active Complain Tickets:</b>\n\n" + "\n".join(rows[:10]) if rows else "📋 বর্তমানে কোনো ওপেন কমপ্লেইন নেই।"
        await wait_msg.edit_text(clean(msg), parse_mode="HTML")
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")

async def comp_add_ticket_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("গ্রাহকের আইডি এবং সমস্যা লিখে পাঠান:\n(যেমন: `1001478 - Fiber down`)")
    return COMPLAIN_DETAILS

async def comp_submit_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    wait_msg = await update.message.reply_text("কমপ্লেইন সাবমিট করা হচ্ছে...")

    try:
        session.post(COMPLAIN_URL, data={"details": text, "submit": "Submit"}, timeout=15)
        await wait_msg.edit_text(f"✅ কমপ্লেইন গৃহীত হয়েছে!\nবিবরণ: <code>{clean(text)}</code>", parse_mode="HTML", reply_markup=get_full_dashboard_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")
    return ConversationHandler.END

async def wifi_haat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    wait_msg = await query.message.reply_text("📶 WiFi Haat তথ্য সংগ্রহ করা হচ্ছে...")

    try:
        res = session.get(WIFI_HAAT_URL, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table")
        records = []
        for t in tables:
            for tr in t.find_all("tr"):
                cols = [td.text.strip() for td in tr.find_all(["td", "th"])]
                if cols:
                    records.append(" | ".join(cols))

        info = "📶 <b>WiFi Haat Records:</b>\n\n" + "\n".join(records[:10]) if records else "📶 WiFi Haat পোর্টালে সংযুক্ত রয়েছে। কোনো সক্রিয় ভাউচার রেকর্ড নেই।"
        await wait_msg.edit_text(clean(info), parse_mode="HTML", reply_markup=get_full_dashboard_keyboard())
    except Exception as e:
        await wait_msg.edit_text(f"⚠️ ত্রুটি: {clean(e)}")

# Nav Callbacks
async def menu_buttons_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    btn = query.data

    if btn == "btn_back_main":
        await query.message.reply_text("🏠 আপনি <b>Main Dashboard</b>-এ আছেন:", parse_mode="HTML", reply_markup=get_full_dashboard_keyboard())
    elif btn == "btn_relogin":
        await start(query, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("বাতিল করা হয়েছে।")
    return ConversationHandler.END

if __name__ == "__main__":
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(60)
        .read_timeout(60)
        .write_timeout(60)
        .build()
    )

    # 1. Login Handler
    login_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_click, pattern="^select_user$")],
        states={
            WAITING_FOR_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_crm_password)],
            WAITING_FOR_AUTH_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_auth_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    # 2. New Client Form Handler
    nc_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(new_client_start, pattern="^nc_add_start$")],
        states={
            NC_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nc_receive_name)],
            NC_MOBILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nc_receive_mobile)],
            NC_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, nc_receive_address)],
            NC_PACKAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nc_receive_package)],
            NC_NID: [MessageHandler(filters.TEXT & ~filters.COMMAND, nc_submit_form)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    # 3. Actions Handler
    action_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(act_trigger, pattern="^act_")],
        states={
            ACT_INPUT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, act_process_id)],
            ACT_DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, act_process_deposit)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    # 4. Area Migration Handler
    area_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(area_take_client_id, pattern="^setar_")],
        states={
            AREA_UPDATE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_area_client_update)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    # 5. Payment Issue Handler
    pi_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(pi_take_client_id, pattern="^setpi_")],
        states={
            PI_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, pi_receive_user_id)],
            PI_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, pi_submit_final)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    # 6. Package Migration Handler
    migrate_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(pkg_migration_start, pattern="^btn_pkg_migration$")],
        states={
            MIGRATE_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_pkg_migration)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    # 7. Complain Ticket Handler
    complain_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(comp_add_ticket_start, pattern="^comp_add_ticket$")],
        states={
            COMPLAIN_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, comp_submit_final)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(login_conv)
    app.add_handler(nc_conv)
    app.add_handler(action_conv)
    app.add_handler(area_conv)
    app.add_handler(pi_conv)
    app.add_handler(migrate_conv)
    app.add_handler(complain_conv)

    app.add_handler(CallbackQueryHandler(search_prompt_btn, pattern="^btn_search_prompt$"))
    app.add_handler(CallbackQueryHandler(new_client_menu, pattern="^btn_new_client_menu$"))
    app.add_handler(CallbackQueryHandler(handle_pending_list, pattern="^nc_pending_list$"))
    app.add_handler(CallbackQueryHandler(handle_approved_list, pattern="^nc_approved_list$"))
    app.add_handler(CallbackQueryHandler(view_live_status, pattern="^btn_status_view$"))
    app.add_handler(CallbackQueryHandler(handle_user_lists_fetch, pattern="^view_list_"))
    app.add_handler(CallbackQueryHandler(client_actions_menu, pattern="^btn_client_actions$"))
    app.add_handler(CallbackQueryHandler(invoice_menu, pattern="^btn_invoice_menu$"))
    app.add_handler(CallbackQueryHandler(handle_today_payments, pattern="^inv_today_"))
    app.add_handler(CallbackQueryHandler(area_main_menu, pattern="^btn_area_menu$"))
    app.add_handler(CallbackQueryHandler(area_pay_select, pattern="^area_pay_menu$"))
    app.add_handler(CallbackQueryHandler(handle_area_payment_fetch, pattern="^arpay_"))
    app.add_handler(CallbackQueryHandler(area_change_select_area, pattern="^area_change_menu$"))
    app.add_handler(CallbackQueryHandler(payment_issue_menu, pattern="^btn_payment_issue_menu$"))
    app.add_handler(CallbackQueryHandler(pi_history_fetch, pattern="^pi_history$"))
    app.add_handler(CallbackQueryHandler(pi_select_issue_type, pattern="^pi_new_issue_menu$"))
    app.add_handler(CallbackQueryHandler(card_order_handler, pattern="^btn_card_order$"))
    app.add_handler(CallbackQueryHandler(complain_menu, pattern="^btn_complain_menu$"))
    app.add_handler(CallbackQueryHandler(comp_view_tickets_fetch, pattern="^comp_view_tickets$"))
    app.add_handler(CallbackQueryHandler(wifi_haat_handler, pattern="^btn_wifi_haat$"))
    app.add_handler(CallbackQueryHandler(menu_buttons_info))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, execute_search))

    print("bhedarganj CRM বট সফলভাবে সচল করা হয়েছে...")
    app.run_polling()
