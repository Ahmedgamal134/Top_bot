from pymongo import MongoClient
from datetime import datetime, timedelta
import random
import string
import config
import time

class Database:
    def __init__(self):
        """الاتصال بقاعدة البيانات مع إعدادات SSL متسامحة"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # ✅ إعدادات اتصال قوية جداً لمواجهة مشاكل SSL
                self.client = MongoClient(
                    config.MONGO_URI,
                    tls=True,
                    tlsAllowInvalidCertificates=True,      # تجاهل صحة الشهادة
                    tlsAllowInvalidHostnames=True,         # تجاهل صحة اسم المضيف
                    connectTimeoutMS=30000,                 # 30 ثانية مهلة الاتصال
                    socketTimeoutMS=30000,                  # 30 ثانية مهلة القراءة/الكتابة
                    serverSelectionTimeoutMS=30000,         # 30 ثانية مهلة اختيار السيرفر
                    retryWrites=True,
                    retryReads=True
                )
                # اختبار الاتصال
                self.client.admin.command('ping')
                print("✅ اتصال MongoDB ناجح")
                break
            except Exception as e:
                print(f"⚠️ محاولة اتصال {attempt + 1} فشلت: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    print("❌ فشل الاتصال بقاعدة البيانات بعد 3 محاولات")
                    raise e
        
        self.db = self.client[config.DB_NAME]
        
        # مجموعات البيانات
        self.users = self.db.users
        self.ads = self.db.ads
        self.withdrawals = self.db.withdrawals
        self.transactions = self.db.transactions
        self.captcha = self.db.captcha
        
        # إنشاء الفهارس (Indexes) عشان البحث يكون أسرع
        self.users.create_index("user_id", unique=True)
        self.users.create_index("referral_code", unique=True)
    
    # ========== إدارة المستخدمين ==========
    def add_user(self, user_id, username=None, first_name=None, last_name=None, referred_by=None):
        """إضافة مستخدم جديد"""
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "balance": 0,
            "total_earned": 0,
            "referral_code": referral_code,
            "referred_by": referred_by,
            "referrals": {"level1": [], "level2": [], "level3": []},
            "referral_count": 0,
            "daily_checkin": {
                "last_checkin": None,
                "streak": 0,
                "total_checkins": 0
            },
            "ads_watched": {
                "today": 0,
                "last_ad_time": None,
                "total": 0,
                "today_date": datetime.now().date().isoformat()
            },
            "captcha_count": 0,
            "created_at": datetime.now(),
            "is_active": True,
            "is_banned": False
        }
        
        # لو المستخدم دخل عن طريق إحالة
        if referred_by:
            referrer = self.get_user_by_referral_code(referred_by)
            if referrer:
                self.add_referral(referrer["user_id"], user_id, level=1)
                bonus = int(config.REFERRAL_BONUS_LEVEL1 * 100)
                self.add_transaction(referrer["user_id"], bonus, "referral_bonus", f"مكافأة إحالة المستخدم {user_id}")
                self.update_balance(referrer["user_id"], bonus)
        
        self.users.insert_one(user_data)
        return user_data
    
    def get_user(self, user_id):
        """جلب بيانات مستخدم"""
        return self.users.find_one({"user_id": user_id})
    
    def get_user_by_referral_code(self, code):
        """جلب مستخدم عن طريق كود الإحالة"""
        return self.users.find_one({"referral_code": code})
    
    # ========== نظام الإحالة ==========
    def add_referral(self, referrer_id, referred_id, level=1):
        """إضافة إحالة جديدة"""
        field = f"referrals.level{level}"
        self.users.update_one({"user_id": referrer_id}, {"$push": {field: referred_id}})
        self.users.update_one({"user_id": referrer_id}, {"$inc": {"referral_count": 1}})
        
        user = self.get_user(referrer_id)
        new_count = user.get("referral_count", 0)
        
        # مكافأة كل 10 أصدقاء
        if new_count % 10 == 0:
            self.add_transaction(referrer_id, config.REFERRAL_MILESTONE_BONUS, "milestone_bonus", f"مكافأة إنجاز {new_count} أصدقاء")
            self.update_balance(referrer_id, config.REFERRAL_MILESTONE_BONUS)
        return True
    
    def get_referral_stats(self, user_id):
        """إحصائيات الإحالات"""
        user = self.get_user(user_id)
        if not user:
            return None
        
        referrals = user.get("referrals", {})
        level1 = len(referrals.get("level1", []))
        level2 = len(referrals.get("level2", []))
        level3 = len(referrals.get("level3", []))
        
        return {
            "level1": level1,
            "level2": level2,
            "level3": level3,
            "total": level1 + level2 + level3
        }
    
    # ========== نظام التسجيل اليومي ==========
    def check_daily(self, user_id):
        """تسجيل حضور يومي"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        today = datetime.now().date()
        last = user.get("daily_checkin", {}).get("last_checkin")
        
        # لو سجل اليوم قبل كده
        if last and last.date() == today:
            return False
        
        # حساب السلسلة (streak)
        if last and (today - last.date()).days == 1:
            streak = user.get("daily_checkin", {}).get("streak", 0) + 1
        else:
            streak = 1
        
        # حساب المكافأة
        bonus_index = min(streak - 1, len(config.DAILY_BONUS) - 1)
        bonus = config.DAILY_BONUS[bonus_index]
        
        # مكافأة أسبوعية
        if streak == 7:
            bonus += config.WEEKLY_BONUS
        
        # تحديث قاعدة البيانات
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "daily_checkin.last_checkin": datetime.now(),
                "daily_checkin.streak": streak
            },
            "$inc": {
                "daily_checkin.total_checkins": 1,
                "balance": bonus,
                "total_earned": bonus
            }}
        )
        
        self.add_transaction(user_id, bonus, "daily_bonus", f"مكافأة اليوم {streak}")
        return bonus
    
    # ========== نظام الإعلانات ==========
    def can_watch_ad(self, user_id):
        """التحقق من إمكانية مشاهدة إعلان"""
        user = self.get_user(user_id)
        if not user:
            return False, "مستخدم غير موجود"
        
        if user.get("is_banned", False):
            return False, "حسابك محظور"
        
        today = datetime.now().date()
        today_str = today.isoformat()
        ads_data = user.get("ads_watched", {})
        today_count = ads_data.get("today", 0)
        ads_today_date = ads_data.get("today_date")
        
        # لو اليوم جديد، نعيد تعيين العداد
        if ads_today_date != today_str:
            self.users.update_one(
                {"user_id": user_id},
                {"$set": {"ads_watched.today": 0, "ads_watched.today_date": today_str}}
            )
            today_count = 0
        
        # الحد اليومي
        if today_count >= config.ADS_PER_DAY:
            return False, f"وصلت للحد اليومي {config.ADS_PER_DAY} إعلان"
        
        # وقت التهدئة
        last_time = ads_data.get("last_ad_time")
        if last_time:
            time_diff = (datetime.now() - last_time).total_seconds()
            if time_diff < config.AD_COOLDOWN:
                remaining = config.AD_COOLDOWN - time_diff
                return False, f"انتظر {int(remaining)} ثانية"
        
        # الكابتشا بعد عدد معين
        captcha_count = user.get("captcha_count", 0)
        if captcha_count >= config.CAPTCHA_AFTER_ADS:
            return "captcha", "مطلوب حل كابتشا"
        
        return True, "يمكنك المشاهدة"
    
    def watch_ad(self, user_id):
        """تسجيل مشاهدة إعلان"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        today = datetime.now().date().isoformat()
        ads_data = user.get("ads_watched", {})
        today_count = ads_data.get("today", 0)
        
        # تسجيل الإعلان
        ad_record = {
            "user_id": user_id,
            "date": datetime.now(),
            "day": today,
            "count": today_count + 1,
            "reward": config.COIN_PER_AD
        }
        self.ads.insert_one(ad_record)
        
        # تحديث بيانات المستخدم
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "ads_watched.today": today_count + 1,
                "ads_watched.last_ad_time": datetime.now(),
                "ads_watched.today_date": today
            },
            "$inc": {
                "ads_watched.total": 1,
                "balance": config.COIN_PER_AD,
                "total_earned": config.COIN_PER_AD,
                "captcha_count": 1
            }}
        )
        
        self.add_transaction(user_id, config.COIN_PER_AD, "ad_reward", f"مشاهدة إعلان #{today_count + 1}")
        return True
    
    # ========== نظام المعاملات ==========
    def add_transaction(self, user_id, amount, transaction_type, description):
        """تسجيل معاملة"""
        transaction = {
            "user_id": user_id,
            "amount": amount,
            "type": transaction_type,
            "description": description,
            "created_at": datetime.now()
        }
        self.transactions.insert_one(transaction)
    
    def get_transactions(self, user_id, limit=50):
        """جلب معاملات المستخدم"""
        cursor = self.transactions.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        return list(cursor)
    
    def update_balance(self, user_id, amount):
        """تحديث الرصيد"""
        self.users.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})
    
    # ========== نظام السحب ==========
    def create_withdrawal(self, user_id, amount_coins, method, account_info):
        """إنشاء طلب سحب"""
        user = self.get_user(user_id)
        if not user:
            return False, "مستخدم غير موجود"
        
        if user["balance"] < amount_coins:
            return False, "رصيد غير كافٍ"
        
        if amount_coins < config.MIN_WITHDRAWAL_COINS:
            return False, f"الحد الأدنى {config.MIN_WITHDRAWAL_COINS} كوين"
        
        amount_egp = amount_coins / config.COINS_PER_POUND
        
        if method not in config.WITHDRAWAL_METHODS:
            return False, "طريقة سحب غير مدعومة"
        
        withdrawal = {
            "user_id": user_id,
            "amount_coins": amount_coins,
            "amount_egp": round(amount_egp, 2),
            "method": method,
            "method_name": config.WITHDRAWAL_METHODS[method],
            "account_info": account_info,
            "status": "pending",
            "created_at": datetime.now(),
            "processed_at": None,
            "notes": ""
        }
        
        result = self.withdrawals.insert_one(withdrawal)
        self.update_balance(user_id, -amount_coins)
        self.add_transaction(user_id, -amount_coins, "withdrawal_request", f"طلب سحب {amount_egp:.2f} جنيه عبر {method}")
        
        return True, str(result.inserted_id)
    
    def get_withdrawals(self, user_id=None, status=None, limit=50):
        """جلب طلبات السحب"""
        query = {}
        if user_id:
            query["user_id"] = user_id
        if status:
            query["status"] = status
        return list(self.withdrawals.find(query).sort("created_at", -1).limit(limit))
    
    def process_withdrawal(self, withdrawal_id, status, notes=""):
        """معالجة طلب سحب (للمشرف)"""
        from bson.objectid import ObjectId
        
        result = self.withdrawals.update_one(
            {"_id": ObjectId(withdrawal_id)},
            {"$set": {"status": status, "processed_at": datetime.now(), "notes": notes}}
        )
        
        if result.modified_count > 0 and status == "rejected":
            withdrawal = self.withdrawals.find_one({"_id": ObjectId(withdrawal_id)})
            self.update_balance(withdrawal["user_id"], withdrawal["amount_coins"])
            self.add_transaction(
                withdrawal["user_id"],
                withdrawal["amount_coins"],
                "withdrawal_rejected",
                f"تم رفض طلب السحب وإعادة {withdrawal['amount_coins']} كوين"
            )
            return True
        
        return result.modified_count > 0
    
    # ========== إحصائيات ==========
    def get_stats(self):
        """إحصائيات عامة"""
        total_users = self.users.count_documents({})
        
        today = datetime.now().replace(hour=0, minute=0, second=0)
        active_today = self.users.count_documents({"daily_checkin.last_checkin": {"$gte": today}})
        
        total_ads = self.ads.count_documents({})
        today_ads = self.ads.count_documents({"date": {"$gte": today}})
        
        pipeline = [{"$group": {"_id": None, "total_balance": {"$sum": "$balance"}, "total_earned": {"$sum": "$total_earned"}}}]
        totals = list(self.users.aggregate(pipeline))
        
        pending_withdrawals = self.withdrawals.count_documents({"status": "pending"})
        
        payments_pipeline = [{"$match": {"status": "completed"}}, {"$group": {"_id": None, "total_paid": {"$sum": "$amount_egp"}}}]
        payments = list(self.withdrawals.aggregate(payments_pipeline))
        
        return {
            "total_users": total_users,
            "active_today": active_today,
            "total_ads": total_ads,
            "today_ads": today_ads,
            "total_balance": totals[0]["total_balance"] if totals else 0,
            "total_earned": totals[0]["total_earned"] if totals else 0,
            "pending_withdrawals": pending_withdrawals,
            "total_paid": payments[0]["total_paid"] if payments else 0
        }
    
    # ========== نظام الكابتشا ==========
    def create_captcha(self, user_id):
        """إنشاء كابتشا"""
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        result = num1 + num2
        
        captcha_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        captcha_data = {
            "_id": captcha_id,
            "user_id": user_id,
            "num1": num1,
            "num2": num2,
            "result": result,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=5),
            "solved": False
        }
        
        self.captcha.insert_one(captcha_data)
        
        return {"id": captcha_id, "question": f"{num1} + {num2} = ?"}
    
    def verify_captcha(self, captcha_id, answer):
        """التحقق من الكابتشا"""
        captcha = self.captcha.find_one({"_id": captcha_id})
        
        if not captcha:
            return False, "كابتشا غير صالحة"
        
        if captcha.get("solved", False):
            return False, "تم استخدام هذه الكابتشا من قبل"
        
        if datetime.now() > captcha["expires_at"]:
            return False, "انتهت صلاحية الكابتشا"
        
        if int(answer) != captcha["result"]:
            return False, "إجابة خاطئة"
        
        self.captcha.update_one({"_id": captcha_id}, {"$set": {"solved": True}})
        self.users.update_one({"user_id": captcha["user_id"]}, {"$set": {"captcha_count": 0}})
        
        return True, "✅ صحيح"
    
    def reset_daily_ads(self):
        """إعادة تعيين الإعلانات اليومية"""
        today = datetime.now().date().isoformat()
        self.users.update_many({}, {"$set": {"ads_watched.today": 0, "ads_watched.today_date": today}})