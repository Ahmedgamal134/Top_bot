import os
from dotenv import load_dotenv

load_dotenv()

# توكن البوت
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Supabase settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# إعدادات العملة والإعلانات
COIN_PER_AD = 10
ADS_PER_DAY = 300
AD_COOLDOWN = 5

# نظام التسجيل اليومي
DAILY_BONUS = [10, 15, 20, 25, 30, 35, 50]
WEEKLY_BONUS = 100

# سعر الصرف
COINS_PER_POUND = 140
MIN_WITHDRAWAL_COINS = 70000

# نظام الإحالة
REFERRAL_BONUS_LEVEL1 = 0.20
REFERRAL_BONUS_LEVEL2 = 0.10
REFERRAL_BONUS_LEVEL3 = 0.05
REFERRAL_MILESTONE_BONUS = 500

# طرق السحب
WITHDRAWAL_METHODS = {
    "vodafone_cash": "📱 فودافون كاش",
    "paypal": "💳 PayPal",
    "usdt": "₿ USDT (TRC20)"
}
WITHDRAWAL_PROCESSING_TIME = "24-48 ساعة"

# إعدادات الأمان
CAPTCHA_AFTER_ADS = 50
MAX_REFERRALS_PER_DAY = 20
