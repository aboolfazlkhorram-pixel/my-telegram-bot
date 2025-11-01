import os
import threading
from flask import Flask
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
import sqlite3
import random
import math
from datetime import datetime

# ====== پیکربندی ======
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise RuntimeError("❌ TOKEN environment variable not set")

ADMIN_IDS = [123456789]  # شناسه عددی ادمین

# ====== وضعیت‌های مکالمه ======
(
    WAIT_FISH, WAIT_KASR, WAIT_ADDRESS, WAIT_PHONE,
    WAIT_PDF_TITLE, WAIT_PDF_FILE,
    WAIT_TRACK_ORDER_ID, WAIT_TRACK_CODE,
    SURVEY
) = range(9)

# ====== دیتابیس ======
DB_FILE = "database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, first_name TEXT,
        book_title TEXT, order_type TEXT,
        fish_photo TEXT, kasr_photo TEXT,
        address TEXT, phone TEXT,
        order_id TEXT, status TEXT DEFAULT 'pending',
        track_code TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS surveys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, username TEXT, first_name TEXT,
        rating INTEGER, timestamp TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS pdfs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE, file_id TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# ====== توابع کمکی ======
def generate_order_id():
    return "HR" + ''.join(random.choices('0123456789', k=6))

def save_photo(file_id, filename):
    import os
    os.makedirs("photos", exist_ok=True)
    return f"photos/{filename}"

def get_pdf_file_id(title):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT file_id FROM pdfs WHERE title = ?", (title,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def format_number(n):
    return f"{n:,}"

def find_book_by_title(title):
    for b in books:
        if b["title"] == title or title in b["title"]:
            return b
    return None

def find_item_by_title(title, items):
    for i in items:
        if i["title"] == title or title in i["title"]:
            return i
    return None

def get_image_path(title):
    return "images/default.jpg"

# ====== کتاب‌ها — توضیحات کامل و طولانی با ایموجی ======
books = [
    {
        "title": "📖 کتاب کد کیهانی",
        "pdf_price": 170000,
        "print_price": None,
        "description": "🌌📖 کتاب کد کیهانی 🌌\n\n"
        "✨ کتاب کد کیهانی سفری است از جهان بیرون به درون بیکرانه‌ی هستی. در این اثر، رازهای نهفته در نظم ریاضی و انرژی‌های کیهانی آشکار می‌شود؛ کُدهایی که هر ذره‌ی هستی بر اساس آن می‌تپد و می‌درخشد. خواننده درمی‌یابد که جهان، تنها یک تصادف بی‌هدف نیست، بلکه مجموعه‌ای هوشمند از ارتعاشات، نغمه‌ها و نورهایی است که در هماهنگی کامل با «منِ برتر» او در حرکت‌اند. این کتاب، پلی است میان آگاهی انسانی و آگاهی کیهانی، و دری است به سوی درک یگانگی با تمام هستی.\n\n"
        "🔮 این اثر شامل:\n"
        "• رمزگشایی از الگوهای کیهانی 🌠\n"
        "• درک عمیق از ارتعاشات جهان 🌍\n"
        "• تمرین‌های کاربردی برای هماهنگی با کیهان 🧘‍♂️\n"
        "• کشف رابطه‌ی بین ریاضیات و حقیقت وجود ✨\n\n"
        "📚 مناسب برای:\n"
        "• جویندگان حقیقت 🌟\n"
        "• علاقه‌مندان به رمزگشایی کیهانی 🔭\n"
        "• کسانی که به دنبال درک عمیق‌تری از وجود هستند 💫"
    },
    {
        "title": "🔢 کتاب مفاهیم ارتعاشی اعداد",
        "pdf_price": 170000,
        "print_price": None,
        "description": "🔢📖 کتاب مفاهیم ارتعاشی اعداد 🔢\n\n"
        "✨ در کتاب مفاهیم ارتعاشی اعداد، عددها دیگر فقط نمادهای ریاضی نیستند؛ آنها حامل پیام‌هایی از سطوح بالاتر آگاهی‌اند. این کتاب با زبانی عرفانی و دقیق، راز ارتعاش هر عدد را می‌گشاید و نشان می‌دهد که چگونه هر رقم می‌تواند کلیدی باشد برای هماهنگی با فرکانس‌های خاص کیهان. از عدد یک تا نه، از وحدت تا کمال، هر کدام رمز و انرژی ویژه‌ای دارند که می‌تواند مسیر زندگی را از تاریکی به روشنایی هدایت کند. این کتاب برای آنان است که می‌خواهند اعداد را نه فقط بفهمند، بلکه احساس کنند.\n\n"
        "🎯 محتوای ارزشمند کتاب:\n"
        "• رمزگشایی از ارتعاشات اعداد 1 تا 9 🔢\n"
        "• کاربرد اعداد در زندگی روزمره 📅\n"
        "• تکنیک‌های استفاده از انرژی اعداد 💫\n"
        "• تحلیل اعداد شخصی و تأثیر آنها 🌟\n\n"
        "💡 فواید مطالعه:\n"
        "• درک بهتر از روابط عددی در جهان 🌍\n"
        "• استفاده عملی از ارتعاشات اعداد ✨\n"
        "• افزایش آگاهی از الگوهای زندگی 🔮"
    },
    {
        "title": "🕌 کتاب ذکرهای خاص عارفان",
        "pdf_price": 170000,
        "print_price": None,
        "description": "🕌📖 کتاب ذکرهای خاص عارفان 🕌\n\n"
        "✨ کتاب ذکرهای خاص عارفان دریچه‌ای‌ست به دنیای خاموشی و حضور. در این اثر، ذکرهایی جمع‌آوری شده که قرن‌ها توسط عارفان و سالکان راه حقیقت برای بیداری دل و تسلیم روح به کار رفته‌اند. هر ذکر، ارتعاشی زنده است که ذهن را از آشوب به سکون، و قلب را از غفلت به حضور می‌برد. کتاب توضیح می‌دهد که چگونه هر واژه، هر نغمه و هر نفس می‌تواند پل ارتباطی میان انسان و ذات الهی باشد. این کتاب نه فقط برای خواندن، بلکه برای تجربه‌کردن است.\n\n"
        "🕯️ محتوای معنوی کتاب:\n"
        "• مجموعه‌ای از ذکرهای ناب عارفان بزرگ 🌟\n"
        "• روش‌های صحیح خوانش و تمرین ذکرها 🎵\n"
        "• تأثیرات ارتعاشی هر ذکر بر چاکراها 💫\n"
        "• تجربیات عملی عارفان از ذکرها ✨\n\n"
        "🙏 فواید معنوی:\n"
        "• رسیدن به آرامش درونی عمیق 🕊️\n"
        "• تقویت ارتباط با ذات الهی 🌈\n"
        "• پاکسازی انرژی‌های منفی 🔥"
    },
    {
        "title": "📚 کتاب حکمت – جلد اول",
        "pdf_price": 190000,
        "print_price": 1050000,
        "description": "📚🌿 کتاب حکمت – جلد اول 🌿📚\n\n"
        "✨ کتاب حکمت (جلد اول) همچون نسیمی است که از سده‌های دور، بوی معرفت و تعمق را به جان می‌رساند. در این کتاب، سخن از اصول بنیادی آفرینش، شناخت خویشتن، و مسیر تعالی روح است. نویسنده، با زبانی شاعرانه و ژرف، انسان را به مکاشفه‌ی حقیقت وجود خود دعوت می‌کند. هر فصل، چون آینه‌ای‌ست که روح را می‌تراشد تا نور آگاهی از درون آن بدرخشد. این کتاب، به‌راستی مکتب تفکر، سکوت و حضور است.\n\n"
        "🌌 سرفصل‌های درخشان:\n"
        "• مبانی هستی شناسی و معرفت نفس 🔍\n"
        "• رمزگشایی از اسرار آفرینش 🌟\n"
        "• راه‌های عملی سیر و سلوک معنوی 🛤️\n"
        "• تمرین‌های خودشناسی و مراقبه 🧘‍♂️\n\n"
        "💫 ویژگی‌های منحصر به فرد:\n"
        "• بیان شیوا و عمیق مفاهیم عرفانی ✨\n"
        "• همراه با تمرین‌های کاربردی روزانه 📅\n"
        "• مناسب برای شروع سفر معنوی 🌠"
    }
]

# ====== محصولات فیزیکی — توضیحات کامل و طولانی با ایموجی ======
incense_items = [
    {
        "title": "📿 دستبند ترکیبی سنگ هفت چاکرا + رودراکشا", 
        "price": 630000, 
        "description": "📿✨ دستبند ترکیبی سنگ هفت چاکرا + رودراکشا ✨📿\n\n"
        "🌈 این دستبند، هماهنگی میان زمین و آسمان است؛ ترکیبی از انرژی‌های مقدس هفت چاکرا با نیروی باستانی رودراکشا.\n\n"
        "💎 سنگ‌های رنگین‌کمان چاکراها، هرکدام با فرکانس ویژه‌ی خود، مسیر انرژی حیات را در بدن متعادل می‌سازند — از ریشه‌ی زمین تا تاج آسمان. رودراکشا نیز چون نگهبان آگاهی، ارتعاشات منفی را می‌زداید و ارتباط با درون را عمیق‌تر می‌کند.\n\n"
        "🔄 فواید انرژی‌بخشی:\n"
        "• تعادل کامل چاکراهای هفتگانه 🌈\n"
        "• دفع انرژی‌های منفی و استرس 🔮\n"
        "• تقویت تمرکز و آرامش درونی 🧘‍♀️\n"
        "• افزایش جریان انرژی مثبت در زندگی 💫\n\n"
        "🎁 ویژگی‌های فیزیکی:\n"
        "• ساخته شده از سنگ‌های طبیعی و اصل 💎\n"
        "• طراحی ارگونومیک و زیبا ✨\n"
        "• مناسب برای استفاده روزمره 📿"
    },
    {
        "title": "📿 تسبیح ۱۰۸ دانه‌ای رودراکشا", 
        "price": 810000, 
        "description": "📿🕉️ تسبیح ۱۰۸ دانه‌ای رودراکشا 🕉️📿\n\n"
        "✨ تسبیح ۱۰۸ دانه‌ای رودراکشا، ابزاری مقدس است که از دل آیین‌های باستانی تا امروز، همچون پلی میان انسان و آگاهی الهی باقی مانده است.\n\n"
        "💎 هر دانه‌ی رودراکشا، نماد اشک خداوند شیواست — ذره‌ای از نیروی خالص آفرینش که ارتعاش دعا، مراقبه و ذکر را هزاران برابر می‌کند.\n\n"
        "🙏 فواید معنوی:\n"
        "• افزایش تمرکز در مراقبه و ذکرگویی 🧘‍♂️\n"
        "• تقویت انرژی‌های معنوی و روحانی 🌟\n"
        "• ایجاد آرامش عمیق درونی 🕊️\n"
        "• کمک به پاکسازی کرمای گذشته 🔥\n\n"
        "🔮 ویژگی‌های منحصر به فرد:\n"
        "• ۱۰۸ دانه طبیعی رودراکشا 📿\n"
        "• انرژی‌بخشی و خواص درمانی 💫\n"
        "• مناسب برای مدیتیشن طولانی مدت ✨"
    }
]

stones = [
    {
        "title": "💜 سنگ آمیتیست", 
        "price": 580000, 
        "description": "💜🔮 سنگ آمیتیست 🔮💜\n\n"
        "✨ سنگ آمیتیست: سنگی آرام‌بخش و محافظت‌کننده که ارتعاشات ذهن را متعادل می‌سازد. این سنگ بنفش زیبا، انرژی‌های منفی را دفع کرده و شهود را تقویت می‌کند. مناسب برای مراقبه، خواب آرام و تمرکز عمیق.\n\n"
        "🌙 خواص انرژی‌بخشی:\n"
        "• آرامش‌بخش ذهن و روان 🧘‍♀️\n"
        "• تقویت حس ششم و شهود 🔮\n"
        "• دفع انرژی‌های منفی محیط 🌌\n"
        "• کمک به خواب عمیق و رویاهای شفاف 💤\n\n"
        "💎 ویژگی‌های فیزیکی:\n"
        "• رنگ بنفش عمیق و درخشان 💜\n"
        "• تراش طبیعی و انرژی‌بخش ✨\n"
        "• مناسب برای استفاده شخصی و دکوراسیون 🏠"
    }
]

courses = [
    {
        "title": "👁️ دوره فعالسازی چشم سوم", 
        "price": 690000, 
        "description": "👁️🌀 دوره فعالسازی چشم سوم 🌀👁️\n\n"
        "✨ دورهٔ فعالسازی چشم سوم: تمرین‌ها و آموزش‌هایی عملی برای بیداری شهود و بینایی درونی. در این دوره، با روش‌های تنفس، مراقبه، تجسم و تمرین‌های انرژی، چشم سوم فعال شده و دسترسی به ادراک فراحسی فراهم می‌شود.\n\n"
        "🎯 سرفصل‌های آموزشی:\n"
        "• آشنایی با آناتومی انرژی چشم سوم 🔍\n"
        "• تمرین‌های تنفسی برای فعالسازی 🌬️\n"
        "• تکنیک‌های مدیتیشن پیشرفته 🧘‍♂️\n"
        "• روش‌های تقویت حس ششم و شهود 🔮\n\n"
        "💫 فواید شرکت در دوره:\n"
        "• افزایش درک فراحسی و بصیرت 👁️\n"
        "• تقویت قوهٔ تخیل و خلاقیت 🎨\n"
        "• دستیابی به آرامش عمیق درونی 🕊️\n"
        "• بهبود تصمیم‌گیری و بینش زندگی 💫"
    }
]

# ====== قیمت به حروف ======
price_words = {
    170000: "📊 صد و هفتاد هزار تومان 💰",
    190000: "📊 صد و نود هزار تومان 💰", 
    933000: "📊 نهصد و سی و سه هزار تومان 💰",
    1050000: "📊 یک میلیون و پنجاه هزار تومان 💰",
    1190000: "📊 یک میلیون و صد و نود هزار تومان 💰",
    710000: "📊 هفتصد و ده هزار تومان 💰", 
    580000: "📊 پانصد و هشتاد هزار تومان 💰",
    450000: "📊 چهارصد و پنجاه هزار تومان 💰", 
    570000: "📊 پانصد و هفتاد هزار تومان 💰",
    630000: "📊 ششصد و سی هزار تومان 💰", 
    810000: "📊 هشتصد و ده هزار تومان 💰",
    690000: "📊 ششصد و نود هزار تومان 💰", 
    590000: "📊 پانصد و نود هزار تومان 💰"
}

# ====== قالب‌های پرداخت با ایموجی ======
PAYMENT_PDF_TEMPLATE = (
"🙏✨ سپاس از انتخاب شما و خوشآمد به مسیر حکمت ✨🙏\n\n"
"📖 مبلغ مربوط به فایل PDF کتاب «{book}» برابر با:\n"
"💰 {price_num} تومان\n"
"({price_text})\n\n"
"💳 لطفاً مبلغ را به شماره کارت:\n"
"`6037 9982 0040 3342`\n"
"👤 به نام: سید جلال حقیقت\n"
"واریز نمایید.\n\n"
"📸 پس از انجام واریز، لطفاً هر دو مورد زیر را برای پشتیبانی ارسال کنید:\n\n"
"1. 📷 تصویر فیش واریزی\n"
"2. 📱 تصویر پیام کسر مبلغ از حساب\n\n"
"✅ پس از تأیید پرداخت، شناسهٔ سفارش به‌صورت خودکار برای شما ارسال خواهد شد.\n\n"
"📞 در صورت هرگونه سؤال یا نیاز به پیگیری با آیدی پشتیبانی زیر در تماس باشید:\n"
"@Poshtibani36977\n\n"
"🌺 با سپاس و تمنای آرامش و برکت برای شما 🌺"
)

PAYMENT_PRINT_TEMPLATE = (
"🙏✨ سپاس از انتخاب شما و خوشآمد به مسیر حکمت ✨🙏\n\n"
"📚 مبلغ مربوط به نسخهٔ چاپی کتاب «{book}» برابر با:\n"
"💰 {price_num} تومان\n"
"({price_text})\n\n"
"💳 لطفاً مبلغ را به شماره کارت:\n"
"`6037 9982 0040 3342`\n"
"👤 به نام: سید جلال حقیقت\n"
"واریز نمایید.\n\n"
"📸 پس از انجام واریز، لطفاً هر سه مورد زیر را برای پشتیبانی ارسال کنید:\n\n"
"1. 📷 تصویر فیش و واریزی\n"
"2. 📱 تصویر پیام کسر مبلغ از حساب\n"
"3. 🏠 آدرس کامل پستی (نام گیرنده، کدپستی، شماره تماس، آدرس دقیق)\n\n"
"✅ پس از تأیید پرداخت، شناسهٔ سفارش به‌صورت خودکار برای شما ارسال خواهد شد.\n"
"🚚 پس از صدور کد مرسوله پستی، اطلاع‌رسانی و شمارهٔ رهگیری برای شما ارسال خواهد شد.\n\n"
"📞 در صورت هرگونه سؤال یا نیاز به پیگیری با آیدی پشتیبانی زیر در تماس باشید:\n"
"@Poshtibani36977\n\n"
"🌺 با سپاس و تمنای آرامش و برکت برای شما 🌺"
)

COURSE_PAYMENT_TEMPLATE = (
"🎓✨ سپاس از علاقه‌مندی شما به {item} ✨🎓\n\n"
"💰 هزینه ثبت‌نام این دوره: {price_num} تومان\n"
"({price_text})\n\n"
"💳 لطفاً مبلغ را به شماره کارت زیر واریز نمایید:\n"
"`6037 9982 0040 3342`\n"
"👤 به نام: سید جلال حقیقت\n\n"
"📸 پس از انجام واریز، لطفاً موارد زیر را برای پشتیبانی ارسال کنید:\n"
"1. 📷 تصویر فیش واریزی\n"
"2. 📱 تصویر پیام کسر مبلغ از حساب\n\n"
"📞 پشتیبانی:\n"
"@Poshtibani36977\n\n"
"✅ پس از تأیید، لینک دسترسی به دوره و اطلاعات ورود برای شما ارسال خواهد شد.\n\n"
"🌟 با آرزوی نوری عمیق در مسیر آگاهی شما 🌟"
)

# ====== منوی اصلی با ایموجی ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name if user and user.first_name else "دوست"
    welcome = (
        f"🌷 سلام {name} عزیز 🌷\n\n"
        "✨ به مسیر آگاهی و آرامش خوش آمدی ✨\n\n"
        "📖 در این فضا، نه صرفاً خواندن که تجربه‌ای از نور و حکمت در انتظارت است.\n"
        "🌌 هر کتاب، هر محصول و هر دوره، دری‌ست به جهانی از معنا و شناخت.\n"
        "💫 از منوی زیر گزینهٔ مورد نظر را انتخاب کن و سفری به درون خود را آغاز نما\n\n"
        "🕊️ آرامش و آگاهی بی‌پایان برای تو آرزومندیم 🕊️"
    )
    keyboard = [
        [KeyboardButton("🛍️ محصولات"), KeyboardButton("📞 پشتیبانی")],
        [KeyboardButton("📦 پیگیری سفارش"), KeyboardButton("⭐ نظرسنجی کیفیت و پاسخگویی")],
        [KeyboardButton("👑 بخش مدیریت (ادمین)")]
    ]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(welcome, reply_markup=reply)

PAGE_SIZE = 5

async def show_books_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    total = len(books)
    pages = math.ceil(total / PAGE_SIZE)
    if page < 1: page = 1
    if page > pages: page = pages
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total)
    keyboard = []
    for i in range(start_idx, end_idx):
        keyboard.append([KeyboardButton(f"{books[i]['title']}")])
    nav = []
    if page > 1: nav.append(KeyboardButton("◀️ صفحه قبل"))
    if page < pages: nav.append(KeyboardButton("صفحه بعد ▶️"))
    if nav: keyboard.append(nav)
    keyboard.append([KeyboardButton("🔙 بازگشت به منوی محصولات"), KeyboardButton("🏠 بازگشت به منوی اصلی")])
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(f"📄 صفحه {page} از {pages} — 📚 یکی از کتاب‌ها را انتخاب کنید:", reply_markup=reply)
    context.user_data["books_page"] = page

# ====== نمایش محصول با عکس و ایموجی ======
async def show_product_with_image(update: Update, context: ContextTypes.DEFAULT_TYPE, item):
    title = item["title"]
    image_path = get_image_path(title)

    lines = [item["description"]]
    if "pdf_price" in item and item["pdf_price"]:
        lines.append(f"\n📄 نسخه PDF: {format_number(item['pdf_price'])} تومان 💰")
    if "print_price" in item and item["print_price"]:
        lines.append(f"📚 نسخه چاپی: {format_number(item['print_price'])} تومان 💰")
    if "price" in item:
        lines.append(f"\n🏷️ قیمت: {format_number(item['price'])} تومان 💰")

    caption = "\n".join(lines)

    buttons = []
    if "pdf_price" in item and item["pdf_price"]:
        buttons.append([InlineKeyboardButton("🛒 خرید PDF", callback_data=f"buy_pdf_{title}")])
    if "print_price" in item and item["print_price"]:
        buttons.append([InlineKeyboardButton("🛒 خرید چاپی", callback_data=f"buy_print_{title}")])
    if "price" in item:
        buttons.append([InlineKeyboardButton("🛒 خرید محصول", callback_data=f"buy_item_{title}")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")])

    keyboard = InlineKeyboardMarkup(buttons)

    # در Render از عکس پیش‌فرض استفاده می‌کنیم
    try:
        with open(image_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=caption, reply_markup=keyboard)
    except:
        await update.message.reply_text(caption, reply_markup=keyboard)

# ====== هندلر متن با ایموجی ======
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "🛍️ محصولات":
        keyboard = [
            [KeyboardButton("📚 کتابها"), KeyboardButton("🕯️ عودها و ملزومات")],
            [KeyboardButton("💎 سنگهای انرژی"), KeyboardButton("🎓 دوره‌های ما")],
            [KeyboardButton("🏠 بازگشت به منوی اصلی")]
        ]
        await update.message.reply_text("🛍️ منوی محصولات — ✨ یکی از دسته‌ها را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    if text == "📞 پشتیبانی":
        await update.message.reply_text("📞 برای ارتباط و پیگیری: @Poshtibani36977\n\n🕊️ با آرزوی آرامش و روشنایی برای شما 🌟")
        return

    if text == "📦 پیگیری سفارش":
        await update.message.reply_text("🔍 این بخش در حال حاضر در دست به‌روزرسانی است. 📞 برای پیگیری سفارش خود با پشتیبانی تماس بگیرید:\n@Poshtibani36977\n\n⏳ با سپاس از صبر و شکیبایی شما 🌺")
        return

    if text == "👑 بخش مدیریت (ادمین)":
        await admin_panel(update, context)
        return

    if text == "📚 کتابها":
        await show_books_page(update, context, 1)
        return

    if text == "صفحه بعد ▶️":
        page = context.user_data.get("books_page", 1) + 1
        await show_books_page(update, context, page)
        return

    if text == "◀️ صفحه قبل":
        page = max(1, context.user_data.get("books_page", 1) - 1)
        await show_books_page(update, context, page)
        return

    if text == "🔙 بازگشت به منوی محصولات":
        keyboard = [
            [KeyboardButton("📚 کتابها"), KeyboardButton("🕯️ عودها و ملزومات")],
            [KeyboardButton("💎 سنگهای انرژی"), KeyboardButton("🎓 دوره‌های ما")],
            [KeyboardButton("🏠 بازگشت به منوی اصلی")]
        ]
        await update.message.reply_text("🛍️ منوی محصولات — ✨ یکی از دسته‌ها را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    if text == "🏠 بازگشت به منوی اصلی":
        await start(update, context)
        return

    # انتخاب کتاب
    book = find_book_by_title(text)
    if book:
        await show_product_with_image(update, context, book)
        return

    # انتخاب عود/سنگ/دوره
    item = find_item_by_title(text, incense_items + stones + courses)
    if item:
        await show_product_with_image(update, context, item)
        return

    await update.message.reply_text("❌ لطفاً از منو استفاده کنید یا /start را بزنید 🔄")

# ====== دکمه‌های خرید با ایموجی ======
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_menu":
        await query.edit_message_caption(caption="🔙 در حال بازگشت به منوی اصلی...", reply_markup=None)
        await start(update, context)
        return

    if data.startswith("buy_pdf_"):
        title = data.replace("buy_pdf_", "")
        book = find_book_by_title(title)
        context.user_data["buying"] = {"title": title, "type": "pdf", "price": book["pdf_price"]}
        msg = PAYMENT_PDF_TEMPLATE.format(book=title, price_num=format_number(book["pdf_price"]), price_text=price_words.get(book["pdf_price"], ""))
        await query.edit_message_caption(caption=msg, reply_markup=None, parse_mode='Markdown')
        await query.message.reply_text("📸 لطفاً تصویر فیش واریزی را ارسال کنید:")
        return WAIT_FISH

    if data.startswith("buy_print_"):
        title = data.replace("buy_print_", "")
        book = find_book_by_title(title)
        context.user_data["buying"] = {"title": title, "type": "print", "price": book["print_price"]}
        msg = PAYMENT_PRINT_TEMPLATE.format(book=title, price_num=format_number(book["print_price"]), price_text=price_words.get(book["print_price"], ""))
        await query.edit_message_caption(caption=msg, reply_markup=None, parse_mode='Markdown')
        await query.message.reply_text("📸 لطفاً تصویر فیش واریزی را ارسال کنید:")
        return WAIT_FISH

    if data.startswith("buy_item_"):
        title = data.replace("buy_item_", "")
        item = find_item_by_title(title, incense_items + stones + courses)
        if item and "price" in item:
            context.user_data["buying"] = {"title": title, "type": "item", "price": item["price"]}
            msg = PAYMENT_PRINT_TEMPLATE.format(book=title, price_num=format_number(item["price"]), price_text=price_words.get(item["price"], ""))
            await query.edit_message_caption(caption=msg, reply_markup=None, parse_mode='Markdown')
            await query.message.reply_text("📸 لطفاً تصویر فیش واریزی را ارسال کنید:")
            return WAIT_FISH

# ====== خرید PDF با ایموجی ======
async def receive_fish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ لطفاً یک تصویر ارسال کنید. 📸")
        return WAIT_FISH
    photo = update.message.photo[-1]
    file = await photo.get_file()
    filename = f"fish_{update.effective_user.id}_{photo.file_unique_id}.jpg"
    # در Render از ذخیره فایل صرف‌نظر می‌کنیم
    context.user_data["fish_photo"] = filename
    await update.message.reply_text("📱 حالا تصویر پیام کسر مبلغ از حساب را ارسال کنید:")
    return WAIT_KASR

async def receive_kasr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ لطفاً یک تصویر ارسال کنید. 📸")
        return WAIT_KASR
    photo = update.message.photo[-1]
    file = await photo.get_file()
    filename = f"kasr_{update.effective_user.id}_{photo.file_unique_id}.jpg"

    data = context.user_data["buying"]
    user = update.effective_user
    order_id = generate_order_id()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""INSERT INTO orders 
        (user_id, username, first_name, book_title, order_type, fish_photo, kasr_photo, order_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user.id, user.username or "", user.first_name or "", data["title"], data["type"],
         context.user_data["fish_photo"], filename, order_id, "pending"))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ سفارش شما با موفقیت ثبت شد!\n📦 شناسه سفارش: `{order_id}`\n⏳ در انتظار تأیید توسط تیم پشتیبانی...", parse_mode='Markdown')

    for admin in ADMIN_IDS:
        try:
            await context.bot.send_message(admin, f"🆕 سفارش جدید ({data['type']})\n👤 کاربر: {user.first_name} (@{user.username})\n📖 محصول: {data['title']}\n📦 شناسه: `{order_id}`", parse_mode='Markdown')
        except: pass

    context.user_data.clear()
    return ConversationHandler.END

# ====== خرید چاپی / محصول با ایموجی ======
async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["address"] = update.message.text
    await update.message.reply_text("📞 شماره تماس خود را وارد کنید:")
    return WAIT_PHONE

async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    data = context.user_data["buying"]
    user = update.effective_user
    order_id = generate_order_id()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""INSERT INTO orders 
        (user_id, username, first_name, book_title, order_type, fish_photo, kasr_photo, address, phone, order_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user.id, user.username or "", user.first_name or "", data["title"], data["type"],
         context.user_data["fish_photo"], context.user_data["kasr_photo"], context.user_data["address"], context.user_data["phone"], order_id, "pending"))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ سفارش شما با موفقیت ثبت شد!\n📦 شناسه سفارش: `{order_id}`\n⏳ در انتظار تأیید توسط تیم پشتیبانی...\n🚚 پس از تأیید، مرسوله پستی برای شما ارسال خواهد شد.", parse_mode='Markdown')

    for admin in ADMIN_IDS:
        try:
            await context.bot.send_message(admin, f"🆕 سفارش جدید (چاپی/محصول)\n👤 کاربر: {user.first_name} (@{user.username})\n📦 محصول: {data['title']}\n🏠 آدرس: {context.user_data['address']}\n📞 تلفن: {context.user_data['phone']}\n📋 شناسه: `{order_id}`", parse_mode='Markdown')
        except: pass

    context.user_data.clear()
    return ConversationHandler.END

# ====== پنل مدیریت با ایموجی ======
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 دسترسی محدود است. این بخش فقط برای ادمین‌ها قابل دسترسی می‌باشد.")
        return
    keyboard = [
        [KeyboardButton("📋 سفارشات در انتظار")],
        [KeyboardButton("📤 آپلود PDF")],
        [KeyboardButton("📊 نظرسنجی‌ها")],
        [KeyboardButton("🚚 ارسال کد رهگیری")],
        [KeyboardButton("🏠 بازگشت به منوی اصلی")]
    ]
    await update.message.reply_text("👑 پنل مدیریت — ✨ گزینه مورد نظر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE status = 'pending'")
    orders = c.fetchall()
    conn.close()

    if not orders:
        await update.message.reply_text("✅ هیچ سفارشی در انتظار تأیید وجود ندارد. 🎉")
        return

    for order in orders:
        msg = f"🆔 #{order[0]} | {order[3]} (@{order[2]})\n📦 {order[4]} — {order[5]}\n📋 شناسه: `{order[10]}`"
        keyboard = [[InlineKeyboardButton("✅ تأیید سفارش", callback_data=f"confirm_{order[0]}")]]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = int(query.data.split("_")[1])

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = c.fetchone()
    c.execute("UPDATE orders SET status = 'confirmed' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    user_id = order[1]
    book_title = order[4]
    order_code = order[10]

    if order[5] == "pdf":
        file_id = get_pdf_file_id(book_title)
        if file_id:
            await context.bot.send_message(user_id, f"🎉 سفارش شما تأیید شد!\n📦 شناسه سفارش: `{order_code}`\n📖 فایل کتاب برای شما ارسال می‌شود...", parse_mode='Markdown')
            await context.bot.send_document(user_id, file_id, caption=f"📖 {book_title}\n✨ با آرزوی مطالعه‌ای پر از آگاهی و روشنایی برای شما 🌟")
        else:
            await context.bot.send_message(user_id, "❌ متأسفانه فایل مورد نظر یافت نشد. 📞 لطفاً با پشتیبانی تماس بگیرید.\n@Poshtibani36977")
    else:
        await context.bot.send_message(user_id, f"🎉 سفارش شما تأیید شد!\n📦 شناسه سفارش: `{order_code}`\n🚚 مرسوله پستی به زودی برای شما ارسال خواهد شد. ⏳\n📞 برای پیگیری با پشتیبانی در ارتباط باشید.", parse_mode='Markdown')

    await query.edit_message_text(f"✅ سفارش #{order_id} با موفقیت تأیید شد. 🎉")

# ====== آپلود PDF با ایموجی ======
async def upload_pdf_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 عنوان دقیق کتاب را وارد کنید:")
    return WAIT_PDF_TITLE

async def upload_pdf_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pdf_title"] = update.message.text
    await update.message.reply_text("📤 فایل PDF را ارسال کنید:")
    return WAIT_PDF_FILE

async def upload_pdf_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document or update.message.document.mime_type != "application/pdf":
        await update.message.reply_text("❌ لطفاً فایل PDF ارسال کنید. 📄")
        return WAIT_PDF_FILE

    file_id = update.message.document.file_id
    title = context.user_data["pdf_title"]

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO pdfs (title, file_id) VALUES (?, ?)", (title, file_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ کتاب «{title}» با موفقیت آپلود شد. 📚🎉")
    return ConversationHandler.END

# ====== کد رهگیری با ایموجی ======
async def send_track_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 شناسه سفارش (مثل HR123456) را وارد کنید:")
    return WAIT_TRACK_ORDER_ID

async def send_track_order_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["track_order"] = update.message.text.strip()
    await update.message.reply_text("🚚 کد رهگیری پستی را وارد کنید:")
    return WAIT_TRACK_CODE

async def send_track_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track = update.message.text.strip()
    order_code = context.user_data["track_order"]

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM orders WHERE order_id = ? AND status = 'confirmed'", (order_code,))
    row = c.fetchone()
    c.execute("UPDATE orders SET track_code = ?, status = 'shipped' WHERE order_id = ?", (track, order_code))
    conn.commit()
    conn.close()

    if row:
        await context.bot.send_message(row[0], f"🚚 کد رهگیری مرسوله شما:\n`{track}`\n📞 برای پیگیری با شماره پشتیبانی تماس بگیرید.", parse_mode='Markdown')
        await update.message.reply_text("✅ کد رهگیری با موفقیت ارسال شد. 🎉")
    else:
        await update.message.reply_text("❌ سفارش مورد نظر یافت نشد. 🔍")
    return ConversationHandler.END

# ====== نظرسنجی با ایموجی ======
async def survey_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐⭐⭐⭐⭐ (عالی)", callback_data="survey_5")],
        [InlineKeyboardButton("⭐⭐⭐⭐ (خیلی خوب)", callback_data="survey_4")],
        [InlineKeyboardButton("⭐⭐⭐ (خوب)", callback_data="survey_3")],
        [InlineKeyboardButton("⭐⭐ (متوسط)", callback_data="survey_2")],
        [InlineKeyboardButton("⭐ (ضعیف)", callback_data="survey_1")]
    ])
    await update.message.reply_text("⭐ لطفاً کیفیت خدمات و پاسخگویی ما را ارزیابی کنید:", reply_markup=keyboard)
    return SURVEY

async def survey_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rating = int(query.data.split("_")[1])
    user = query.from_user

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO surveys (user_id, username, first_name, rating, timestamp) VALUES (?, ?, ?, ?, ?)",
              (user.id, user.username or "", user.first_name or "", rating, now))
    conn.commit()
    conn.close()

    await query.edit_message_text("🙏 نظرسنجی شما با موفقیت ثبت شد. 🌟 سپاس از همراهی و مشارکت ارزشمند شما 🌺")
    return ConversationHandler.END

async def show_surveys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM surveys ORDER BY id DESC LIMIT 20")
    surveys = c.fetchall()
    conn.close()

    if not surveys:
        await update.message.reply_text("📊 هنوز نظرسنجی‌ای ثبت نشده است. 📝")
        return

    msg = "📊 نظرسنجی‌های اخیر:\n\n"
    for s in surveys:
        stars = "⭐" * s[4]
        msg += f"{stars} — {s[3]} (@{s[2]}) — {s[5]}\n"
    await update.message.reply_text(msg)

# ====== وب‌سرور برای پینگ =======
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "✅ ربات تلگرام آنلاین است! 🤖", 200

@flask_app.route("/health")
def health():
    return "🟢 Healthy", 200

def run_bot():
    """تابع اجرای ربات تلگرام"""
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        
        # اضافه کردن هندلرها
        # نظرسنجی
        survey_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & filters.Regex("⭐ نظرسنجی کیفیت و پاسخگویی"), survey_start)],
            states={SURVEY: [CallbackQueryHandler(survey_callback)]},
            fallbacks=[]
        )

        # خرید PDF
        pdf_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_callback, pattern="^buy_pdf_")],
            states={
                WAIT_FISH: [MessageHandler(filters.PHOTO, receive_fish)],
                WAIT_KASR: [MessageHandler(filters.PHOTO, receive_kasr)]
            },
            fallbacks=[]
        )

        # خرید چاپی / محصول
        print_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(button_callback, pattern="^(buy_print_|buy_item_)")],
            states={
                WAIT_FISH: [MessageHandler(filters.PHOTO, receive_fish)],
                WAIT_KASR: [MessageHandler(filters.PHOTO, receive_kasr)],
                WAIT_ADDRESS: [MessageHandler(filters.TEXT, receive_address)],
                WAIT_PHONE: [MessageHandler(filters.TEXT, receive_phone)]
            },
            fallbacks=[]
        )

        # آپلود PDF
        upload_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & filters.Regex("📤 آپلود PDF"), upload_pdf_start)],
            states={
                WAIT_PDF_TITLE: [MessageHandler(filters.TEXT, upload_pdf_title)],
                WAIT_PDF_FILE: [MessageHandler(filters.Document.PDF, upload_pdf_file)]
            },
            fallbacks=[]
        )

        # کد رهگیری
        track_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & filters.Regex("🚚 ارسال کد رهگیری"), send_track_start)],
            states={
                WAIT_TRACK_ORDER_ID: [MessageHandler(filters.TEXT, send_track_order_id)],
                WAIT_TRACK_CODE: [MessageHandler(filters.TEXT, send_track_code)]
            },
            fallbacks=[]
        )

        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & filters.Regex("📋 سفارشات در انتظار"), admin_orders))
        app.add_handler(MessageHandler(filters.TEXT & filters.Regex("📊 نظرسنجی‌ها"), show_surveys))
        app.add_handler(survey_conv)
        app.add_handler(pdf_conv)
        app.add_handler(print_conv)
        app.add_handler(upload_conv)
        app.add_handler(track_conv)
        app.add_handler(CallbackQueryHandler(confirm_order, pattern="^confirm_"))
        app.add_handler(CallbackQueryHandler(button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        print("🤖 ربات تلگرام در حال اجرا...")
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطا در اجرای ربات: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # اجرای ربات در یک ترد جداگانه
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # اجرای Flask برای پینگ
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 سرور Flask روی پورت {port} اجرا می‌شود...")
    flask_app.run(host="0.0.0.0", port=port, debug=False)
