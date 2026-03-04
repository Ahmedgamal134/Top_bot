#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import config
from database import Database
import sys
import os

# إعداد التسجيل لعرض الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# قاعدة البيانات
try:
    db = Database()
    logger.info("✅ اتصال قاعدة البيانات ناجح")
except Exception as e:
    logger.error(f"❌ فشل اتصال قاعدة البيانات: {e}")
    sys.exit(1)

# ========== الدوال المساعدة ==========
def get_main_keyboard(user_id):
    """لوحة المفاتيح الرئيسية"""
    keyboard = [
        [InlineKeyboardButton("💰 مشاهدة إعلان", callback_data="watch_ad")],
        [InlineKeyboardButton("📅 تسجيل يومي", callback_data="daily_checkin")],
        [InlineKeyboardButton("👥 نظام الإحالة", callback_data="referral")],
        [InlineKeyboardButton("💳 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("💸 سحب أرباح", callback_data="withdraw")]
    ]
    return InlineKeyboardMarkup(keyboard)

def format_number(num):
    """تنسيق الأرقام (1000 -> 1K, 1000000 -> 1M)"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    if num >= 1000:
        return f"{num/1000:.1f}K"
    return str(num)

def get_progress_bar(current, total, length=10):
    """شريط التقدم"""
    filled = int((current / total) * length)
    empty = length - filled
    return "█" * filled + "░" * empty

# ========== أوامر البوت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بداية البوت"""
    user = update.effective_user
    args = context.args
    
    # التحقق من وجود كود إحالة
    referred_by = None
    if args and args[0].startswith("ref_"):
        referred_by = args[0][4:]  # إزالة "ref_"
    
    # إضافة المستخدم للقاعدة
    db_user = db.get_user(user.id)
    if not db_user:
        db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            referred_by=referred_by
        )
        
        welcome_message = f"""✨ **أهلاً بك {user.first_name} في بوت Tap to Earn!** ✨

💰 **اربح نقوداً حقيقية** عن طريق:
• 📺 مشاهدة الإعلانات (حتى 300 إعلان/يوم)
• 📅 التسجيل اليومي (مكافآت متزايدة)
• 👥 دعوة الأصدقاء (نظام إحالة 3 مستويات)

⚡ **مميزات البوت:**
• سحب على فودافون كاش - PayPal - USDT
• الحد الأدنى للسحب: 500 جنيه
• 70 كوين = 0.5 جنيه

🚀 **ابدأ الآن بالضغط على الأزرار أدناه!**"""
    else:
        welcome_message = f"✨ مرحباً بعودتك {user.first_name}! اضغط على الأزرار للبدء."
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=get_main_keyboard(user.id),
        parse_mode="Markdown"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "watch_ad":
        await show_ad_menu(query, user_id)
    elif data == "watch_ad_confirm":
        await watch_ad(query, user_id)
    elif data == "daily_checkin":
        await daily_checkin(query, user_id)
    elif data == "referral":
        await show_referral(query, user_id)
    elif data == "balance":
        await show_balance(query, user_id)
    elif data == "withdraw":
        await show_withdraw_menu(query, user_id)
    elif data.startswith("withdraw_"):
        method = data.replace("withdraw_", "")
        await request_withdrawal(query, context, user_id, method)
    elif data == "back_to_main":
        await query.edit_message_text(
            "القائمة الرئيسية:",
            reply_markup=get_main_keyboard(user_id)
        )

async def show_ad_menu(query, user_id):
    """عرض قائمة الإعلانات"""
    can_watch, message = db.can_watch_ad(user_id)
    
    user = db.get_user(user_id)
    
    # التأكد من تحديث تاريخ اليوم
    today = datetime.now().date().isoformat()
    ads_data = user.get("ads_watched", {})
    ads_today_date = ads_data.get("today_date")
    
    if ads_today_date != today:
        today_count = 0
    else:
        today_count = ads_data.get("today", 0)
    
    remaining = config.ADS_PER_DAY - today_count
    progress = get_progress_bar(today_count, config.ADS_PER_DAY)
    
    # حساب الأرباح المتوقعة
    potential_earnings = remaining * config.COIN_PER_AD
    potential_egp = potential_earnings / config.COINS_PER_POUND
    
    text = f"""📺 **مشاهدة إعلانات**

📊 **إحصائيات اليوم:**
{progress} {today_count}/{config.ADS_PER_DAY} إعلان

💰 **مكافأة كل إعلان:** +{config.COIN_PER_AD} كوين
💵 **المتبقي يمكن أن تربح:** {potential_earnings} كوين = {potential_egp:.2f} جنيه

⏱️ **وقت التهدئة:** {config.AD_COOLDOWN} ثانية بين الإعلانات
"""
    
    if can_watch is True:
        text += "\n✅ **يمكنك مشاهدة إعلان الآن**"
        keyboard = [
            [InlineKeyboardButton("▶️ مشاهدة إعلان", callback_data="watch_ad_confirm")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
    else:
        text += f"\n\n❌ **{message}**"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def watch_ad(query, user_id):
    """مشاهدة إعلان"""
    can_watch, message = db.can_watch_ad(user_id)
    
    if can_watch != True:
        await query.edit_message_text(
            f"❌ {message}\n\nعد للقائمة الرئيسية",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
            ]]),
            parse_mode="Markdown"
        )
        return
    
    # رابط الإعلان - استبدل هذا برابط Adsterra الفعلي
    ad_url = "https://www.google.com"  # رابط مؤقت للتجربة
    
    # تسجيل المشاهدة
    db.watch_ad(user_id)
    
    # جلب البيانات المحدثة
    user = db.get_user(user_id)
    today_count = user.get("ads_watched", {}).get("today", 0)
    remaining = config.ADS_PER_DAY - today_count
    
    progress = get_progress_bar(today_count, config.ADS_PER_DAY)
    
    text = f"""✅ **تمت مشاهدة الإعلان بنجاح!**

➕ **أضفت +{config.COIN_PER_AD} كوين**
💰 **رصيدك الحالي:** {format_number(user['balance'])} كوين
💵 **القيمة:** {user['balance'] / config.COINS_PER_POUND:.2f} جنيه

📊 **تقدم اليوم:**
{progress} {today_count}/{config.ADS_PER_DAY}

🔗 **رابط الإعلان:** [اضغط هنا لمشاهدة إعلان آخر]({ad_url})
"""
    
    keyboard = [
        [InlineKeyboardButton("📺 إعلان آخر", callback_data="watch_ad_confirm")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def daily_checkin(query, user_id):
    """تسجيل يومي"""
    result = db.check_daily(user_id)
    
    if result is False:
        user = db.get_user(user_id)
        streak = user.get("daily_checkin", {}).get("streak", 0)
        
        text = f"""⚠️ **لقد سجلت حضورك اليوم بالفعل**

🔥 **سلسلة أيامك:** {streak} يوم
⏳ **عد غداً لمكافأة أكبر!**"""
    else:
        user = db.get_user(user_id)
        streak = user.get("daily_checkin", {}).get("streak", 0)
        
        text = f"""✅ **تم تسجيل حضورك اليومي!**

➕ **أضفت +{result} كوين**
🔥 **سلسلة أيامك:** {streak}
💰 **رصيدك الحالي:** {format_number(user['balance'])} كوين
💵 **القيمة:** {user['balance'] / config.COINS_PER_POUND:.2f} جنيه
"""
        
        if streak == 7:
            text += f"\n🎉 **تهانينا! أكملت أسبوع كامل!**\n🏆 حصلت على مكافأة إضافية {config.WEEKLY_BONUS} كوين"
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_referral(query, user_id):
    """عرض نظام الإحالة"""
    user = db.get_user(user_id)
    stats = db.get_referral_stats(user_id)
    
    # رابط الإحالة
    bot = await query.get_bot()
    bot_username = bot.username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user['referral_code']}"
    
    text = f"""👥 **نظام الإحالة**

🔗 **رابطك الخاص:**
`{referral_link}`

📊 **إحصائياتك:**
• المستوى الأول: {stats['level1']} أصدقاء
• المستوى الثاني: {stats['level2']}
• المستوى الثالث: {stats['level3']}
• الإجمالي: {stats['total']}

💰 **نظام المكافآت:**
• المستوى الأول: 20% من أرباح أصدقائك
• المستوى الثاني: 10%
• المستوى الثالث: 5%
• كل 10 أصدقاء: +500 كوين

💡 **انسخ الرابط وشاركه مع أصدقائك!**
"""
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def show_balance(query, user_id):
    """عرض الرصيد"""
    user = db.get_user(user_id)
    
    # حساب القيمة بالجنيه
    balance_egp = user['balance'] / config.COINS_PER_POUND
    total_earned_egp = user['total_earned'] / config.COINS_PER_POUND
    
    # جلب آخر المعاملات
    transactions = db.get_transactions(user_id, 5)
    
    text = f"""💳 **محفظتي**

💰 **الرصيد الحالي:** {format_number(user['balance'])} كوين
💵 **القيمة:** {balance_egp:.2f} جنيه

📊 **إحصائيات:**
• إجمالي الأرباح: {format_number(user['total_earned'])} كوين ({total_earned_egp:.2f} جنيه)
• مشاهدات الإعلانات: {user.get('ads_watched', {}).get('total', 0)}
• أيام الحضور: {user.get('daily_checkin', {}).get('total_checkins', 0)}
• الإحالات: {user.get('referral_count', 0)}

📋 **آخر المعاملات:
"""
    
    for t in transactions[:5]:
        date = t['created_at'].strftime("%m-%d %H:%M")
        sign = "➕" if t['amount'] > 0 else "➖"
        text += f"\n{sign} {date}: {abs(t['amount'])} كوين - {t['description'][:20]}"
    
    keyboard = [
        [InlineKeyboardButton("💸 سحب الأرباح", callback_data="withdraw")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_withdraw_menu(query, user_id):
    """عرض قائمة السحب"""
    user = db.get_user(user_id)
    
    # التحقق من الحد الأدنى
    balance_egp = user['balance'] / config.COINS_PER_POUND
    can_withdraw = user['balance'] >= config.MIN_WITHDRAWAL_COINS
    needed = config.MIN_WITHDRAWAL_COINS - user['balance']
    needed_egp = needed / config.COINS_PER_POUND if needed > 0 else 0
    
    progress = get_progress_bar(
        min(user['balance'], config.MIN_WITHDRAWAL_COINS),
        config.MIN_WITHDRAWAL_COINS
    )
    
    text = f"""💸 **سحب الأرباح**

💰 **رصيدك:** {format_number(user['balance'])} كوين
💵 **القيمة:** {balance_egp:.2f} جنيه

🎯 **الهدف:**
{progress} {min(user['balance'], config.MIN_WITHDRAWAL_COINS)}/{config.MIN_WITHDRAWAL_COINS} كوين

📌 **الحد الأدنى:** {config.MIN_WITHDRAWAL_COINS} كوين = 500 جنيه
⏱️ **وقت المعالجة:** {config.WITHDRAWAL_PROCESSING_TIME}
"""
    
    if can_withdraw:
        text += f"\n✅ **يمكنك سحب أرباحك الآن**\nاختر طريقة السحب:"
        
        keyboard = []
        for method_id, method_name in config.WITHDRAWAL_METHODS.items():
            keyboard.append([InlineKeyboardButton(
                method_name, 
                callback_data=f"withdraw_{method_id}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
    else:
        text += f"\n❌ **لا يمكنك السحب بعد**\nتحتاج {needed} كوين إضافية ({needed_egp:.2f} جنيه)"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def request_withdrawal(query, context, user_id, method):
    """طلب سحب"""
    user = db.get_user(user_id)
    
    if user['balance'] < config.MIN_WITHDRAWAL_COINS:
        await query.edit_message_text(
            "❌ رصيدك غير كافٍ للسحب",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")
            ]])
        )
        return
    
    amount_egp = config.MIN_WITHDRAWAL_COINS / config.COINS_PER_POUND
    method_name = config.WITHDRAWAL_METHODS.get(method, method)
    
    text = f"""📝 **طلب سحب جديد**

💰 **المبلغ:** {config.MIN_WITHDRAWAL_COINS} كوين = {amount_egp:.2f} جنيه
💳 **الطريقة:** {method_name}

📞 **يرجى إرسال بيانات الحساب:**
• لفودافون كاش: رقم المحفظة
• لـ PayPal: البريد الإلكتروني
• لـ USDT: عنوان المحفظة (TRC20)

⏱️ **سيتم المعالجة خلال {config.WITHDRAWAL_PROCESSING_TIME}**
"""
    
    # تخزين معلومات السحب في context
    context.user_data['withdrawal'] = {
        'method': method,
        'amount': config.MIN_WITHDRAWAL_COINS,
        'waiting_for': 'account_info'
    }
    context.user_data['awaiting_withdrawal_input'] = True
    
    await query.edit_message_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # التحقق من حالة انتظار إدخال معلومات السحب
    if context.user_data.get('awaiting_withdrawal_input'):
        withdrawal_data = context.user_data.get('withdrawal', {})
        
        if withdrawal_data.get('waiting_for') == 'account_info':
            method = withdrawal_data['method']
            amount = withdrawal_data['amount']
            
            # إنشاء طلب السحب
            success, result = db.create_withdrawal(
                user_id=user_id,
                amount_coins=amount,
                method=method,
                account_info=text
            )
            
            if success:
                await update.message.reply_text(
                    f"""✅ **تم تقديم طلب السحب بنجاح!**

📋 **رقم الطلب:** `{result}`
💰 **المبلغ:** {amount} كوين = {amount/config.COINS_PER_POUND:.2f} جنيه
💳 **الطريقة:** {config.WITHDRAWAL_METHODS.get(method, method)}
⏳ **وقت المعالجة:** {config.WITHDRAWAL_PROCESSING_TIME}

سيتم التواصل معك عند اكتمال السحب.""",
                    reply_markup=get_main_keyboard(user_id),
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"❌ فشل في تقديم الطلب: {result}",
                    reply_markup=get_main_keyboard(user_id)
                )
            
            # إنهاء حالة الانتظار
            context.user_data['awaiting_withdrawal_input'] = False
            context.user_data.pop('withdrawal', None)
            return
    
    # إذا كانت الرسالة عادية
    await update.message.reply_text(
        "استخدم الأزرار للتفاعل مع البوت 👇",
        reply_markup=get_main_keyboard(user_id)
    )

# ========== أوامر المشرف ==========
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات للمشرف"""
    user_id = update.effective_user.id
    
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط")
        return
    
    stats = db.get_stats()
    
    text = f"""📊 **إحصائيات البوت**

👥 **المستخدمين:**
• الإجمالي: {stats['total_users']}
• نشط اليوم: {stats['active_today']}

📺 **الإعلانات:**
• الإجمالي: {stats['total_ads']}
• اليوم: {stats['today_ads']}

💰 **الأرباح:**
• إجمالي الأرصدة: {format_number(stats['total_balance'])} كوين
• إجمالي الأرباح: {format_number(stats['total_earned'])} كوين
• إجمالي المدفوعات: {stats['total_paid']:.2f} جنيه

⏳ **طلبات سحب معلقة:** {stats['pending_withdrawals']}
"""
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض طلبات السحب للمشرف"""
    user_id = update.effective_user.id
    
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط")
        return
    
    withdrawals = db.get_withdrawals(status="pending")
    
    if not withdrawals:
        await update.message.reply_text("✅ لا توجد طلبات سحب معلقة")
        return
    
    text = f"📋 **طلبات السحب المعلقة ({len(withdrawals)})**\n\n"
    
    for w in withdrawals[:10]:  # عرض أول 10 فقط
        from bson.objectid import ObjectId
        w_id = str(w['_id'])
        text += f"🆔 `{w_id[:8]}...`\n"
        text += f"👤 المستخدم: {w['user_id']}\n"
        text += f"💰 {w['amount_coins']} كوين = {w['amount_egp']:.2f} جنيه\n"
        text += f"💳 {w['method_name']}\n"
        text += f"📞 {w['account_info'][:30]}\n"
        text += f"📅 {w['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
        text += f"━━━━━━━━━━━━━━\n"
    
    text += "\nللموافقة على طلب:\n/approve [رقم الطلب]\n\nللرفض:\n/reject [رقم الطلب] [سبب الرفض]"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموافقة على طلب سحب"""
    user_id = update.effective_user.id
    
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ استخدم: /approve [رقم الطلب]")
        return
    
    withdrawal_id = args[0]
    
    success = db.process_withdrawal(withdrawal_id, "completed", "تمت الموافقة")
    
    if success:
        await update.message.reply_text(f"✅ تمت الموافقة على الطلب {withdrawal_id}")
    else:
        await update.message.reply_text(f"❌ فشل في معالجة الطلب")

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفض طلب سحب"""
    user_id = update.effective_user.id
    
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ استخدم: /reject [رقم الطلب] [سبب الرفض]")
        return
    
    withdrawal_id = args[0]
    reason = ' '.join(args[1:])
    
    success = db.process_withdrawal(withdrawal_id, "rejected", reason)
    
    if success:
        await update.message.reply_text(f"✅ تم رفض الطلب {withdrawal_id}")
    else:
        await update.message.reply_text(f"❌ فشل في معالجة الطلب")

# ========== تشغيل البوت ==========
def main():
    """تشغيل البوت"""
    # التحقق من التوكن
    if not config.BOT_TOKEN:
        logger.error("❌ لم يتم تعيين BOT_TOKEN في ملف .env")
        return
    
    # إنشاء التطبيق
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # إضافة معالجات الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("withdrawals", admin_withdrawals))
    app.add_handler(CommandHandler("approve", admin_approve))
    app.add_handler(CommandHandler("reject", admin_reject))
    
    # معالج الأزرار
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # معالج الرسائل النصية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تشغيل البوت
    logger.info("✅ البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()