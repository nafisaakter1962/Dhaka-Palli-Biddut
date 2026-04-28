import requests
import asyncio
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)

# ----------- KEEP ALIVE -----------
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run).start()

# ----------- CONFIG -----------
BOT_TOKEN = "8603562534:AAFVd3eohqhtrAb_SmAyvfaV0NR2nXPnbVI"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded"
}

# ----------- SCRAPER -----------
def get_dpdc_data(cust_id):
    session = requests.Session()
    url = "https://billpay.sonalibank.com.bd/DPDC/Home/PaymentHistory"

    try:
        session.get(url, headers=headers, timeout=10)
        payload = {'SrcId': cust_id, 'Btn': 'Search'}
        r = session.post(url, data=payload, headers=headers, timeout=15)

        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table")
        if not table:
            return None

        th_list = [th.text.strip().lower() for th in table.find_all("th")]

        def find_idx(keys):
            for i, head in enumerate(th_list):
                if any(k in head for k in keys):
                    return i
            return -1

        idx_name = find_idx(["name"])
        idx_cust = find_idx(["customer no"])
        idx_bill = find_idx(["bill no"])
        idx_contact = find_idx(["contact"])
        idx_total = find_idx(["total"])
        idx_date = find_idx(["date", "transaction"])

        rows = table.find_all("tr")[1:]
        results = []

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                v_link = cols[-1].find('a')['href'] if cols[-1].find('a') else ''

                results.append({
                    "pay_id": v_link.split('/')[-1] if v_link else 'N/A',
                    "bill_no": cols[idx_bill].get_text(strip=True),
                    "name": cols[idx_name].get_text(strip=True),
                    "cust_no": cols[idx_cust].get_text(strip=True),
                    "contact": cols[idx_contact].get_text(strip=True),
                    "total": cols[idx_total].get_text(strip=True),
                    "date": cols[idx_date].get_text(strip=True) if idx_date != -1 else "N/A"
                })

        return results

    except:
        return None

# ----------- MAIN SEARCH -----------
async def run_search(update_or_query, context, start_id, end_id):
    ids = [str(i) for i in range(start_id, end_id + 1)]
    context.user_data["last_end"] = end_id

    msg_source = update_or_query.message if hasattr(update_or_query, 'message') else update_or_query
    status_msg = await msg_source.reply_text("⏳ Processing...")

    found_total = 0
    final_text = ""
    unique_contacts = set()

    for cid in ids:
        data = get_dpdc_data(cid)

        if data:
            for i, d in enumerate(data, 1):
                found_total += 1

                res_content = (
                    f"Payment ID : {d['pay_id']}\n"
                    f"Bill No.   : {d['bill_no']}\n"
                    f"Cust Name  : {d['name']}\n"
                    f"Cust No.   : {d['cust_no']}\n"
                    f"Contact No.: {d['contact']}\n"
                    f"Total Bill : {d['total']}\n"
                    f"Date       : {d['date']}"
                )

                final_text += f"📄 Result {found_total}\n```\n{res_content}\n```\n\n"

                if len(d['contact']) > 5:
                    unique_contacts.add(d['contact'])

        if int(cid) % 10 == 0 or cid == ids[-1]:
            try:
                await status_msg.edit_text(
                    f"⏳ Processing...\n🔢 ID: {cid}\n📊 Found: {found_total}\n✅ {ids.index(cid)+1}/{len(ids)}"
                )
            except:
                pass

        await asyncio.sleep(0.3)

    if final_text == "":
        final_text = "❌ No Result Found"

    # ----------- BUTTONS -----------
    keyboard = []

    for ph in sorted(unique_contacts):
        keyboard.append([
            InlineKeyboardButton("📱 WhatsApp", url=f"https://wa.me/88{ph}"),
            InlineKeyboardButton("📢 Telegram", url=f"https://t.me/+88{ph}")
        ])

    keyboard.append([
        InlineKeyboardButton("👉 Next 500", callback_data="next_500")
    ])

    await status_msg.edit_text(
        final_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ----------- HANDLER -----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    try:
        if "-" in text:
            s, e = map(int, text.split("-"))
        else:
            s = e = int(text)

        await run_search(update, context, s, e)

    except:
        await update.message.reply_text("❌ Invalid Input")

# ----------- CALLBACK -----------
async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data == "next_500":
        await query.answer()

        last_end = context.user_data.get("last_end", 0)

        await run_search(query, context, last_end + 1, last_end + 500)

# ----------- RUN -----------
if __name__ == "__main__":
    keep_alive()

    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

    app_bot.add_handler(MessageHandler(filters.TEXT, handle))
    app_bot.add_handler(CallbackQueryHandler(cb_handler))

    print("🚀 Bot Running...")
    app_bot.run_polling()
