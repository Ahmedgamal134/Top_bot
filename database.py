from supabase import create_client
import config

class Database:
    def __init__(self):
        """الاتصال بقاعدة بيانات Supabase"""
        try:
            self.supabase = create_client(
                config.SUPABASE_URL,
                config.SUPABASE_KEY
            )
            print("✅ اتصال Supabase ناجح")
        except Exception as e:
            print(f"❌ فشل الاتصال: {e}")
            raise e
    
    def get_user(self, user_id):
        """جلب بيانات مستخدم"""
        result = self.supabase.table('users').select('*').eq('user_id', user_id).execute()
        if result.data:
            return result.data[0]
        return None
    
    def add_user(self, user_id, username=None, first_name=None, last_name=None, referred_by=None):
        """إضافة مستخدم جديد"""
        import random
        import string
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
            "referral_count": 0
        }
        
        result = self.supabase.table('users').insert(user_data).execute()
        return user_data
    
    def watch_ad(self, user_id):
        """تسجيل مشاهدة إعلان"""
        from datetime import datetime
        
        user = self.get_user(user_id)
        if not user:
            return False
        
        ad_record = {
            "user_id": user_id,
            "date": datetime.now().isoformat(),
            "reward": 10
        }
        self.supabase.table('ads').insert(ad_record).execute()
        
        new_balance = user.get('balance', 0) + 10
        self.supabase.table('users').update({"balance": new_balance}).eq('user_id', user_id).execute()
        return True
    
    def can_watch_ad(self, user_id):
        """التحقق من إمكانية مشاهدة إعلان"""
        from datetime import datetime
        
        user = self.get_user(user_id)
        if not user:
            return False, "مستخدم غير موجود"
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        result = self.supabase.table('ads').select('count', count='exact').eq('user_id', user_id).gte('date', today_start).execute()
        today_count = result.count if hasattr(result, 'count') else 0
        
        if today_count >= 300:
            return False, "وصلت للحد اليومي 300 إعلان"
        
        return True, "يمكنك المشاهدة"
