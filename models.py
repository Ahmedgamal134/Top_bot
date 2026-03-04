from datetime import datetime

class User:
    """نموذج المستخدم في قاعدة البيانات"""
    def __init__(self, user_id, username=None, first_name=None, last_name=None, referred_by=None):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.balance = 0
        self.total_earned = 0
        self.referral_code = None
        self.referred_by = referred_by
        self.referrals = {"level1": [], "level2": [], "level3": []}
        self.referral_count = 0
        self.daily_checkin = {
            "last_checkin": None,
            "streak": 0,
            "total_checkins": 0
        }
        self.ads_watched = {
            "today": 0,
            "last_ad_time": None,
            "total": 0,
            "today_date": None
        }
        self.captcha_count = 0
        self.created_at = datetime.now()
        self.is_active = True
        self.is_banned = False

class AdWatch:
    """نموذج مشاهدة إعلان"""
    def __init__(self, user_id, reward):
        self.user_id = user_id
        self.date = datetime.now()
        self.day = datetime.now().date().isoformat()
        self.reward = reward

class Withdrawal:
    """نموذج طلب سحب"""
    def __init__(self, user_id, amount_coins, amount_egp, method, method_name, account_info):
        self.user_id = user_id
        self.amount_coins = amount_coins
        self.amount_egp = amount_egp
        self.method = method
        self.method_name = method_name
        self.account_info = account_info
        self.status = "pending"
        self.created_at = datetime.now()
        self.processed_at = None
        self.notes = ""

class Transaction:
    """نموذج معاملة مالية"""
    def __init__(self, user_id, amount, transaction_type, description):
        self.user_id = user_id
        self.amount = amount
        self.type = transaction_type
        self.description = description
        self.created_at = datetime.now()