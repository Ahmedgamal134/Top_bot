import os
from dotenv import load_dotenv

load_dotenv()

# توكن البوت من BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")

# معرفات المشرفين (افصل بينهم بفواصل)
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# رابط قاعدة بيانات MongoDB
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "tap_to_earn"

# ========== نظام العملة والإعلانات ==========
COIN_PER_AD = 10                     # مكافأة كل إعلان
ADS_PER_DAY = 300                     # 300 إعلان في اليوم
AD_COOLDOWN = 5                       # 5 ثواني فقط بين الإعلانات (للسرعة)

# ========== نظام التسجيل اليومي ==========
DAILY_BONUS = [10, 15, 20, 25, 30, 35, 50]   # مكافآت الأيام المتتالية
WEEKLY_BONUS = 100                            # مكافأة إكمال أسبوع كامل

# ========== سعر الصرف ==========
COINS_PER_POUND = 140                  # 140 كوين = 1 جنيه (70 كوين = 0.5 جنيه)
MIN_WITHDRAWAL_COINS = 70000            # 70,000 كوين = 500 جنيه (الحد الأدنى للسحب)

# ========== نظام الإحالة ==========
REFERRAL_BONUS_LEVEL1 = 0.20            # 20% من أرباح الصديق المباشر
REFERRAL_BONUS_LEVEL2 = 0.10            # 10% من أرباح صديق الصديق
REFERRAL_BONUS_LEVEL3 = 0.05            # 5% من أرباح المستوى الثالث
REFERRAL_MILESTONE_BONUS = 500          # مكافأة كل 10 أصدقاء (500 كوين)

# ========== طرق السحب ==========
WITHDRAWAL_METHODS = {
    "vodafone_cash": "📱 فودافون كاش",
    "paypal": "💳 PayPal",
    "usdt": "₿ USDT (TRC20)"
}
WITHDRAWAL_PROCESSING_TIME = "24-48 ساعة"

# ========== إعدادات الأمان ==========
CAPTCHA_AFTER_ADS = 50                  # طلب كابتشا بعد 50 إعلان
MAX_REFERRALS_PER_DAY = 20               # حد أقصى للإحالات اليومية