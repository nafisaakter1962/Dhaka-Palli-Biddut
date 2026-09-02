import os
import asyncio
import logging
import threading
import re

import requests
from bs4 import BeautifulSoup
from flask import Flask

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("8751926796:AAE_MuRxUzB3ZnjMHQ45TLs3zhyWauK_tN0")

BASE_URL = "https://certificate.comillaboard.gov.bd"

PORT = int(os.getenv("PORT", "10000"))

# Telegram user IDs allowed to perform lookups.
# Example Render variable:
# ALLOWED_USER_IDS=123456789,987654321
ALLOWED_USER_IDS = set()

raw_ids = os.getenv("ALLOWED_USER_IDS", "")

for item in raw_ids.split(","):
    item = item.strip()

    if item.isdigit():
        ALLOWED_USER_IDS.add(int(item))


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Student Information Bot is running."


@app.route("/health")
def health():
    return "OK"


def run_flask():
    app.run(
        host="0.0.0.0",
        port=PORT
    )


# =========================================================
# HTTP
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; K) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/139.0.0.0 "
        "Mobile Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,"
        "image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9"
}


# =========================================================
# BOT
# =========================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is missing."
    )

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher(
    storage=MemoryStorage()
)


# =========================================================
# STATES
# =========================================================

class StudentSearch(StatesGroup):
    waiting_exam = State()
    waiting_year = State()
    waiting_roll = State()


# =========================================================
# AUTHORIZATION
# =========================================================

def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS


# =========================================================
# EXAM BUTTONS
# =========================================================

def exam_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📗 SSC",
                    callback_data="exam_ssc"
                ),
                InlineKeyboardButton(
                    text="📕 HSC",
                    callback_data="exam_hsc"
                )
            ]
        ]
    )


# =========================================================
# YEAR BUTTONS
# =========================================================

def year_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="2026",
                    callback_data="year_2026"
                ),
                InlineKeyboardButton(
                    text="2025",
                    callback_data="year_2025"
                )
            ],
            [
                InlineKeyboardButton(
                    text="2024",
                    callback_data="year_2024"
                ),
                InlineKeyboardButton(
                    text="2023",
                    callback_data="year_2023"
                )
            ],
            [
                InlineKeyboardButton(
                    text="2022",
                    callback_data="year_2022"
                ),
                InlineKeyboardButton(
                    text="2021",
                    callback_data="year_2021"
                )
            ],
            [
                InlineKeyboardButton(
                    text="2020",
                    callback_data="year_2020"
                )
            ]
        ]
    )


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start_command(
    message: Message,
    state: FSMContext
):

    await state.clear()

    if not is_allowed(message.from_user.id):

        await message.answer(
            "🔒 <b>Access Restricted</b>\n\n"
            "এই bot-এ lookup করার অনুমতি আপনার নেই.",
            parse_mode="HTML"
        )

        return

    await state.set_state(
        StudentSearch.waiting_exam
    )

    await message.answer(
        "🎓 <b>Student Information Bot</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📚 Exam নির্বাচন করুন:\n"
        "━━━━━━━━━━━━━━━━━━",
        reply_markup=exam_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# EXAM SELECT
# =========================================================

@dp.callback_query(
    StudentSearch.waiting_exam,
    F.data.startswith("exam_")
)
async def exam_selected(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_allowed(callback.from_user.id):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    exam = callback.data.replace(
        "exam_",
        ""
    ).upper()

    if exam not in ("SSC", "HSC"):

        await callback.answer(
            "Invalid exam.",
            show_alert=True
        )

        return

    await state.update_data(
        exam=exam
    )

    await state.set_state(
        StudentSearch.waiting_year
    )

    await callback.message.edit_text(
        "🎓 <b>Student Information Bot</b>\n\n"
        f"📚 Exam: <b>{exam}</b>\n\n"
        "📅 Passing Year নির্বাচন করুন:",
        reply_markup=year_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# YEAR SELECT
# =========================================================

@dp.callback_query(
    StudentSearch.waiting_year,
    F.data.startswith("year_")
)
async def year_selected(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_allowed(callback.from_user.id):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return

    year = callback.data.replace(
        "year_",
        ""
    )

    allowed_years = {
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
        "2025",
        "2026"
    }

    if year not in allowed_years:

        await callback.answer(
            "Invalid year.",
            show_alert=True
        )

        return

    await state.update_data(
        year=year
    )

    await state.set_state(
        StudentSearch.waiting_roll
    )

    data = await state.get_data()

    exam = data.get(
        "exam",
        "N/A"
    )

    await callback.message.edit_text(
        "🎓 <b>Student Information Bot</b>\n\n"
        f"📚 Exam: <b>{exam}</b>\n"
        f"📅 Passing Year: <b>{year}</b>\n\n"
        "🔢 এখন Roll Number লিখুন:\n\n"
        "উদাহরণ: <code>571124</code>",
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace(
        "\xa0",
        " "
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# =========================================================
# FIND FIELD FROM STUDENT SECTION
# =========================================================

def find_field_value(section, label):

    label_lower = label.lower()

    # -----------------------------------------------------
    # Method 1:
    # Find label text and its nearby input
    # -----------------------------------------------------

    for tag in section.find_all(
        ["label", "td", "th", "div", "span"]
    ):

        text = clean_text(
            tag.get_text(
                " ",
                strip=True
            )
        )

        if label_lower not in text.lower():
            continue

        # Search input inside same tag
        inp = tag.find("input")

        if inp:

            value = clean_text(
                inp.get("value", "")
            )

            if value:
                return value

        # Search input in parent
        parent = tag.parent

        if parent:

            inp = parent.find("input")

            if inp:

                value = clean_text(
                    inp.get("value", "")
                )

                if value:
                    return value

        # Search next input
        inp = tag.find_next("input")

        if inp:

            value = clean_text(
                inp.get("value", "")
            )

            if value:
                return value

    return ""


# =========================================================
# FETCH STUDENT
# =========================================================

def fetch_student(
    exam,
    roll,
    year
):

    exam_code = exam.lower()

    url = (
        f"{BASE_URL}/find/duplicate"
        f"?exam={exam_code}"
        f"&roll={roll}"
        f"&year={year}"
    )

    logging.info(
        "Request: %s",
        url
    )

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    # Establish normal session
    try:

        session.get(
            BASE_URL,
            timeout=20
        )

    except requests.RequestException:

        pass

    # Actual request
    response = session.get(
        url,
        timeout=20
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    # -----------------------------------------------------
    # Find Student Information section
    # -----------------------------------------------------

    student_section = None

    for fieldset in soup.find_all("fieldset"):

        text = clean_text(
            fieldset.get_text(
                " ",
                strip=True
            )
        )

        if "Student Information" in text:

            student_section = fieldset
            break

    if student_section is None:

        page_text = clean_text(
            soup.get_text(
                " ",
                strip=True
            )
        )

        if "Student Information" not in page_text:

            return None

        student_section = soup

    # -----------------------------------------------------
    # Get fields by labels
    # -----------------------------------------------------

    result = {

        "Exam": find_field_value(
            student_section,
            "Exam"
        ),

        "Board": find_field_value(
            student_section,
            "Board"
        ),

        "Roll": find_field_value(
            student_section,
            "Roll Number"
        ),

        "Passing Year": find_field_value(
            student_section,
            "Passing Year"
        ),

        "Registration Number": find_field_value(
            student_section,
            "Registration Number"
        ),

        "Session": find_field_value(
            student_section,
            "Session"
        ),

        "Name": find_field_value(
            student_section,
            "Name"
        ),

        "Father's Name": find_field_value(
            student_section,
            "Father's Name"
        ),

        "Mother's Name": find_field_value(
            student_section,
            "Mother's Name"
        ),

        "Sex": find_field_value(
            student_section,
            "Sex"
        ),

        "Date of Birth": find_field_value(
            student_section,
            "Date of Birth"
        ),

        "GPA": find_field_value(
            student_section,
            "GPA"
        )
    }

    # -----------------------------------------------------
    # Some pages may have empty labels.
    # Use requested values for known fields.
    # -----------------------------------------------------

    if not result["Exam"]:
        result["Exam"] = exam.upper()

    if not result["Roll"]:
        result["Roll"] = roll

    if not result["Passing Year"]:
        result["Passing Year"] = year

    # -----------------------------------------------------
    # If there is no useful student data
    # -----------------------------------------------------

    useful_fields = [
        result["Registration Number"],
        result["Session"],
        result["Name"],
        result["Father's Name"],
        result["Mother's Name"],
        result["Sex"],
        result["GPA"]
    ]

    if not any(useful_fields):

        return None

    return result


# =========================================================
# FORMAT RESULT
# =========================================================

def format_result(result):

    def val(key):
        value = result.get(key, "")
        return value if value else "N/A"

    return (
        "🎓 <b>Student Information</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"📘 <b>Exam:</b> {val('Exam')}\n"
        f"🏫 <b>Board:</b> {val('Board')}\n"
        f"🔢 <b>Roll:</b> {val('Roll')}\n"
        f"📅 <b>Passing Year:</b> {val('Passing Year')}\n"
        f"🪪 <b>Registration Number:</b> "
        f"{val('Registration Number')}\n"
        f"📚 <b>Session:</b> {val('Session')}\n"
        f"👤 <b>Name:</b> {val('Name')}\n"
        f"👨 <b>Father's Name:</b> "
        f"{val(\"Father's Name\")}\n"
        f"👩 <b>Mother's Name:</b> "
        f"{val(\"Mother's Name\")}\n"
        f"⚧ <b>Sex:</b> {val('Sex')}\n"
        f"🎂 <b>Date of Birth:</b> "
        f"{val('Date of Birth')}\n"
        f"📊 <b>GPA:</b> {val('GPA')}\n\n"

        "━━━━━━━━━━━━━━━━━━"
    )


# =========================================================
# ROLL INPUT
# =========================================================

@dp.message(
    StudentSearch.waiting_roll
)
async def receive_roll(
    message: Message,
    state: FSMContext
):

    if not is_allowed(message.from_user.id):

        await state.clear()

        await message.answer(
            "🔒 Access denied."
        )

        return

    if not message.text:

        await message.answer(
            "❌ Roll Number লিখুন।"
        )

        return

    roll = message.text.strip()

    # Numbers only
    if not re.fullmatch(
        r"\d{4,8}",
        roll
    ):

        await message.answer(
            "❌ <b>সঠিক Roll Number দিন।</b>\n\n"
            "শুধু সংখ্যা ব্যবহার করুন।\n"
            "উদাহরণ: <code>571124</code>",
            parse_mode="HTML"
        )

        return

    data = await state.get_data()

    exam = data.get("exam")
    year = data.get("year")

    if exam not in ("SSC", "HSC"):

        await state.clear()

        await message.answer(
            "⚠️ Exam নির্বাচন করা হয়নি।\n"
            "আবার /start দিন।"
        )

        return

    if year not in {
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
        "2025",
        "2026"
    }:

        await state.clear()

        await message.answer(
            "⚠️ সঠিক Passing Year নির্বাচন করা হয়নি।"
        )

        return

    # -----------------------------------------------------
    # Loading
    # -----------------------------------------------------

    loading = await message.answer(
        "🔎 <b>Searching...</b>\n\n"
        f"📘 Exam: {exam}\n"
        f"📅 Year: {year}\n"
        f"🔢 Roll: {roll}\n\n"
        "⏳ Please wait...",
        parse_mode="HTML"
    )

    try:

        result = await asyncio.to_thread(
            fetch_student,
            exam,
            roll,
            year
        )

        if not result:

            await loading.edit_text(
                "❌ <b>Student Information পাওয়া যায়নি।</b>\n\n"
                f"📘 Exam: {exam}\n"
                f"📅 Year: {year}\n"
                f"🔢 Roll: {roll}",
                parse_mode="HTML"
            )

            return

        result_text = format_result(
            result
        )

        await loading.edit_text(
            result_text,
            parse_mode="HTML"
        )

    except requests.exceptions.Timeout:

        await loading.edit_text(
            "⏱️ <b>Server Timeout</b>\n\n"
            "কিছুক্ষণ পরে আবার চেষ্টা করুন।",
            parse_mode="HTML"
        )

    except requests.exceptions.ConnectionError:

        await loading.edit_text(
            "🌐 <b>Connection Error</b>\n\n"
            "Certificate server-এর সাথে সংযোগ করা যাচ্ছে না।",
            parse_mode="HTML"
        )

    except requests.exceptions.HTTPError:

        await loading.edit_text(
            "⚠️ <b>Website Error</b>\n\n"
            "Certificate server error response দিয়েছে।",
            parse_mode="HTML"
        )

    except Exception as error:

        logging.exception(
            "Unexpected error: %s",
            error
        )

        await loading.edit_text(
            "⚠️ <b>Unexpected Error</b>\n\n"
            "তথ্য প্রসেস করতে সমস্যা হয়েছে।",
            parse_mode="HTML"
        )

    finally:

        await state.clear()


# =========================================================
# UNKNOWN MESSAGE
# =========================================================

@dp.message()
async def unknown_message(
    message: Message
):

    await message.answer(
        "🤖 নতুন করে শুরু করতে <b>/start</b> লিখুন।",
        parse_mode="HTML"
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    # Flask server
    flask_thread = threading.Thread(
        target=run_flask,
        daemon=True
    )

    flask_thread.start()

    logging.info(
        "Flask server started on port %s",
        PORT
    )

    logging.info(
        "Telegram bot starting..."
    )

    await dp.start_polling(
        bot
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logging.info(
            "Bot stopped."
        )
