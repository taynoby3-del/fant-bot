# bot.py - Fant Dating Bot (Полная рабочая версия)
# Замени ТВОЙ_ТОКЕН_БОТА на реальный токен

import telebot
from telebot import custom_filters
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, LabeledPrice
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from functools import wraps
import random
import emoji

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8200357741:AAHROitBBR7RSOuvnShVxPbRMekh1AE3pc0"  # ← ЗАМЕНИ ЭТО
OWNER_ID = 8392862734
OWNER_USERNAME = "@error1022"
DB_NAME = "fant_bot.db"

VIP_PRICE = 25
VIP_DAYS = 20
HIDE_PRICE = 15
HIDE_DAYS = 14

# ========== БАЗА ДАННЫХ ==========
Base = declarative_base()
engine = create_engine(f'sqlite:///{DB_NAME}')
Session = sessionmaker(bind=engine)
session = Session()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    city = Column(String, nullable=False)
    about = Column(Text, default="")
    photo_id = Column(String, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow)
    is_banned = Column(Boolean, default=False)
    ban_until = Column(DateTime, nullable=True)
    is_vip = Column(Boolean, default=False)
    vip_until = Column(DateTime, nullable=True)
    is_hidden = Column(Boolean, default=False)
    hide_until = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False)

class Complaint(Base):
    __tablename__ = 'complaints'
    id = Column(Integer, primary_key=True)
    from_user_id = Column(BigInteger, nullable=False)
    reported_username = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    screenshot_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# ========== БОТ ==========
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(BOT_TOKEN, state_storage=state_storage)

# ========== СОСТОЯНИЯ ==========
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_city = State()
    waiting_for_about = State()
    waiting_for_photo = State()
    waiting_for_username = State()

class ComplaintStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_reason = State()
    waiting_for_screenshot = State()

class EditProfileStates(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_photo = State()
    waiting_for_new_about = State()
    waiting_for_new_username = State()

class AdminStates(StatesGroup):
    waiting_for_delete_username = State()
    waiting_for_ban_username = State()
    waiting_for_ban_duration = State()
    waiting_for_broadcast_text = State()
    waiting_for_broadcast_photo = State()
    waiting_for_vip_username = State()
    waiting_for_vip_days = State()
    waiting_for_remove_vip = State()
    waiting_for_remove_admin = State()

class SearchStates(StatesGroup):
    waiting_for_username_search = State()
    in_search = State()

class ChatStates(StatesGroup):
    in_ai_chat = State()

# ========== МЕНЕДЖЕР БД ==========
class DBManager:
    @staticmethod
    def add_user(telegram_id, username, name, age, city, about, photo_id):
        user = User(telegram_id=telegram_id, username=username, name=name, age=age, city=city, about=about, photo_id=photo_id)
        if telegram_id == OWNER_ID:
            user.is_admin = True
            user.is_vip = True
        session.add(user)
        session.commit()
        return user

    @staticmethod
    def get_user(telegram_id):
        return session.query(User).filter_by(telegram_id=telegram_id).first()

    @staticmethod
    def get_user_by_username(username):
        return session.query(User).filter(User.username == username.replace("@", "")).first()

    @staticmethod
    def is_registered(telegram_id):
        return session.query(User).filter_by(telegram_id=telegram_id).first() is not None

    @staticmethod
    def update_user(telegram_id, **kwargs):
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            session.commit()
            return True
        return False

    @staticmethod
    def update_user_by_username(username, **kwargs):
        user = session.query(User).filter(User.username == username.replace("@", "")).first()
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            session.commit()
            return True
        return False

    @staticmethod
    def delete_user(telegram_id):
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            session.delete(user)
            session.commit()
            return True
        return False

    @staticmethod
    def ban_user(telegram_id, duration_minutes):
        user = DBManager.get_user(telegram_id)
        if user:
            user.is_banned = True
            user.ban_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
            session.commit()
            return True
        return False

    @staticmethod
    def check_ban(telegram_id):
        user = DBManager.get_user(telegram_id)
        if not user or not user.is_banned:
            return False
        if user.ban_until and user.ban_until < datetime.utcnow():
            DBManager.update_user(telegram_id, is_banned=False, ban_until=None)
            return False
        return True

    @staticmethod
    def set_vip(telegram_id, days):
        user = DBManager.get_user(telegram_id)
        if user:
            user.is_vip = True
            user.vip_until = datetime.utcnow() + timedelta(days=days)
            session.commit()
            return True
        return False

    @staticmethod
    def remove_vip(telegram_id):
        return DBManager.update_user(telegram_id, is_vip=False, vip_until=None)

    @staticmethod
    def set_hidden(telegram_id, days):
        user = DBManager.get_user(telegram_id)
        if user:
            user.is_hidden = True
            user.hide_until = datetime.utcnow() + timedelta(days=days)
            session.commit()
            return True
        return False

    @staticmethod
    def get_random_user(exclude_id, city=None):
        query = session.query(User).filter(User.telegram_id != exclude_id, User.is_banned == False, User.is_hidden == False)
        if city:
            query = query.filter(User.city.ilike(f"%{city}%"))
        return query.order_by(func.random()).first()

    @staticmethod
    def get_all_users_ids():
        return [u[0] for u in session.query(User.telegram_id).filter(User.is_banned == False).all()]

    @staticmethod
    def get_stats():
        total = session.query(User).count()
        active_today = session.query(User).filter(User.registered_at >= datetime.utcnow() - timedelta(days=1)).count()
        vip_count = session.query(User).filter(User.is_vip == True).count()
        admin_count = session.query(User).filter(User.is_admin == True).count()
        return {"total": total, "active_today": active_today, "vip": vip_count, "admins": admin_count}

    @staticmethod
    def add_complaint(from_id, reported_username, reason, screenshot_id):
        complaint = Complaint(from_user_id=from_id, reported_username=reported_username, reason=reason, screenshot_id=screenshot_id)
        session.add(complaint)
        session.commit()
        return complaint

    @staticmethod
    def is_admin(telegram_id):
        if telegram_id == OWNER_ID:
            return True
        user = DBManager.get_user(telegram_id)
        return user and user.is_admin

    @staticmethod
    def get_all_admins():
        return session.query(User).filter(User.is_admin == True).all()

    @staticmethod
    def get_all_vips():
        return session.query(User).filter(User.is_vip == True).all()

    @staticmethod
    def get_user_status(telegram_id):
        if telegram_id == OWNER_ID:
            return "👑 Владелец"
        user = DBManager.get_user(telegram_id)
        if not user:
            return "👤 Не зарегистрирован"
        if user.is_admin:
            return "🛡️ Администратор"
        if user.is_vip:
            return "💎 VIP"
        return "👤 Пользователь"

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if not DBManager.is_registered(user_id) and user_id != OWNER_ID:
        kb.add(KeyboardButton("📝 РЕГИСТРАЦИЯ 📝"))
        return kb
    
    kb.add(KeyboardButton("👤 Моя анкета 👤"))
    kb.add(KeyboardButton("🔍 Поиск анкет 🔍"))
    kb.add(KeyboardButton("🛍️ Магазин 🛍️"))
    kb.add(KeyboardButton("⚠️ Жалоба ⚠️"))
    
    if DBManager.is_admin(user_id):
        kb.add(KeyboardButton("🛠️ Админ-панель 🛠️"))
    
    if user_id == OWNER_ID:
        kb.add(KeyboardButton("👑 Владелец 👑"))
        kb.add(KeyboardButton("📊 Статистика 📊"))
    
    return kb

def get_cancel_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Отмена ❌"))
    return kb

def get_profile_edit_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("✏️ Имя ✏️"))
    kb.add(KeyboardButton("📸 Фото 📸"))
    kb.add(KeyboardButton("📝 О себе 📝"))
    kb.add(KeyboardButton("🔤 Username 🔤"))
    kb.add(KeyboardButton("🔙 Назад 🔙"))
    return kb

def get_admin_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("👑 Выдать VIP 👑"))
    kb.add(KeyboardButton("💔 Снять VIP 💔"))
    kb.add(KeyboardButton("🛡️ Назначить админа 🛡️"))
    kb.add(KeyboardButton("🗑️ Снять админа 🗑️"))
    kb.add(KeyboardButton("💀 Снос анкеты 💀"))
    kb.add(KeyboardButton("⛔ Бан анкеты ⛔"))
    kb.add(KeyboardButton("📣 Рассылка 📣"))
    kb.add(KeyboardButton("📋 Список VIP 📋"))
    kb.add(KeyboardButton("🔙 Назад 🔙"))
    return kb

def get_owner_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("👑 Выдать VIP 👑"))
    kb.add(KeyboardButton("💔 Снять VIP 💔"))
    kb.add(KeyboardButton("🛡️ Назначить админа 🛡️"))
    kb.add(KeyboardButton("🗑️ Снять админа 🗑️"))
    kb.add(KeyboardButton("💀 Снос анкеты 💀"))
    kb.add(KeyboardButton("⛔ Бан анкеты ⛔"))
    kb.add(KeyboardButton("📣 Рассылка 📣"))
    kb.add(KeyboardButton("📋 Список админов 📋"))
    kb.add(KeyboardButton("📋 Список VIP 📋"))
    kb.add(KeyboardButton("🔙 Назад 🔙"))
    return kb

def get_shop_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(KeyboardButton("💎 VIP статус - 25⭐ (20 дней) 💎"))
    kb.add(KeyboardButton("🙈 Скрыть анкету - 15⭐ (14 дней) 🙈"))
    kb.add(KeyboardButton("🔎 Поиск по username 🔎"))
    kb.add(KeyboardButton("🔙 Назад 🔙"))
    return kb

def get_search_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add(KeyboardButton("❤️ Лайк ❤️"))
    kb.add(KeyboardButton("➡️ Скип ➡️"))
    kb.add(KeyboardButton("💬 Написать 💬"))
    kb.add(KeyboardButton("⏹️ Стоп ⏹️"))
    return kb

# ========== ДЕКОРАТОР ==========
def require_registration(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        if user_id == OWNER_ID:
            return func(message, *args, **kwargs)
        if not DBManager.is_registered(user_id):
            bot.send_message(message.chat.id, "🌸 Пройдите регистрацию! 🌸\nНажмите кнопку ниже 👇", reply_markup=get_main_keyboard(user_id))
            return
        if DBManager.check_ban(user_id):
            bot.send_message(message.chat.id, "😔 Ваша анкета заблокирована!")
            return
        return func(message, *args, **kwargs)
    return wrapper

# ========== /START ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    welcome = f"✨ *ДОБРО ПОЖАЛОВАТЬ В FANT!* ✨\n\n🌸 Уютный дейтинг-бот\n\nТвой статус: {DBManager.get_user_status(user_id)}"
    bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))

# ========== /INFO ==========
@bot.message_handler(commands=['info'])
def info_command(message):
    bot.set_state(message.from_user.id, ChatStates.in_ai_chat, message.chat.id)
    bot.send_message(message.chat.id, "🤖 *ИИ-ЧАТ FANT* 🤖\n\nПривет! Я твой собеседник! Пиши что угодно! 💕\n\nДля выхода — /start", parse_mode="Markdown")

@bot.message_handler(state=ChatStates.in_ai_chat)
def ai_chat(message):
    if message.text == '/start':
        bot.delete_state(message.from_user.id, message.chat.id)
        start_command(message)
        return
    answers = ["✨ Очень интересно! Расскажи ещё! ✨", "💕 Я тебя понимаю! 💕", "🌸 Продолжай, я слушаю! 🌸", "🦋 Ты такой классный собеседник! 🦋"]
    bot.send_message(message.chat.id, random.choice(answers))

# ========== РЕГИСТРАЦИЯ ==========
@bot.message_handler(func=lambda m: m.text and "РЕГИСТРАЦИЯ" in m.text)
def reg_start(message):
    if DBManager.is_registered(message.from_user.id):
        bot.send_message(message.chat.id, "✅ Вы уже зарегистрированы!")
        return
    bot.set_state(message.from_user.id, RegistrationStates.waiting_for_name, message.chat.id)
    bot.send_message(message.chat.id, "🌸 Как тебя зовут?", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=RegistrationStates.waiting_for_name)
def reg_name(message):
    if "Отмена" in message.text:
        bot.delete_state(message.from_user.id, message.chat.id)
        start_command(message)
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = message.text
    bot.set_state(message.from_user.id, RegistrationStates.waiting_for_age, message.chat.id)
    bot.send_message(message.chat.id, "🎂 Сколько тебе лет?", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=RegistrationStates.waiting_for_age)
def reg_age(message):
    if "Отмена" in message.text:
        bot.delete_state(message.from_user.id, message.chat.id)
        start_command(message)
        return
    if not message.text.isdigit() or int(message.text) < 14:
        bot.send_message(message.chat.id, "⚠️ Введи реальный возраст (от 14)!")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['age'] = int(message.text)
    bot.set_state(message.from_user.id, RegistrationStates.waiting_for_city, message.chat.id)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📍 Отправить геопозицию", request_location=True))
    kb.add(KeyboardButton("❌ Отмена ❌"))
    bot.send_message(message.chat.id, "🏙️ Из какого ты города?", reply_markup=kb)

@bot.message_handler(state=RegistrationStates.waiting_for_city, content_types=['text', 'location'])
def reg_city(message):
    if message.text and "Отмена" in message.text:
        bot.delete_state(message.from_user.id, message.chat.id)
        start_command(message)
        return
    city = f"📍 {message.location.latitude}, {message.location.longitude}" if message.location else message.text
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['city'] = city
    bot.set_state(message.from_user.id, RegistrationStates.waiting_for_about, message.chat.id)
    bot.send_message(message.chat.id, "📝 Расскажи о себе (или напиши '-')", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=RegistrationStates.waiting_for_about)
def reg_about(message):
    if "Отмена" in message.text:
        bot.delete_state(message.from_user.id, message.chat.id)
        start_command(message)
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['about'] = "" if message.text == "-" else message.text
    bot.set_state(message.from_user.id, RegistrationStates.waiting_for_photo, message.chat.id)
    bot.send_message(message.chat.id, "📸 Отправь своё фото", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=RegistrationStates.waiting_for_photo, content_types=['photo'])
def reg_photo(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['photo_id'] = message.photo[-1].file_id
    bot.set_state(message.from_user.id, RegistrationStates.waiting_for_username, message.chat.id)
    bot.send_message(message.chat.id, "🔤 Твой username (без @)", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=RegistrationStates.waiting_for_username)
def reg_username(message):
    if "Отмена" in message.text:
        bot.delete_state(message.from_user.id, message.chat.id)
        start_command(message)
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        DBManager.add_user(message.from_user.id, message.text.replace("@", ""), data['name'], data['age'], data['city'], data['about'], data['photo_id'])
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, "🎉 *РЕГИСТРАЦИЯ ЗАВЕРШЕНА!* 🎉\n\nДобро пожаловать в Fant! 💕", parse_mode="Markdown")
    start_command(message)

# ========== МОЯ АНКЕТА ==========
@bot.message_handler(func=lambda m: m.text and "Моя анкета" in m.text)
@require_registration
def my_profile(message):
    user = DBManager.get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "❌ Анкета не найдена!")
        return
    
    status = DBManager.get_user_status(message.from_user.id)
    vip_status = "✅ Активен" if user.is_vip else "❌ Не активен"
    if user.is_vip and user.vip_until:
        days = (user.vip_until - datetime.utcnow()).days
        vip_status += f" (ещё {days} дн.)"
    
    hidden_status = "👁️ Видна всем" if not user.is_hidden else "🙈 Скрыта"
    
    text = f"""👤 *МОЯ АНКЕТА* 👤

✨ *Статус:* {status}
📛 *Имя:* {user.name}
🎂 *Возраст:* {user.age}
🏙️ *Город:* {user.city}
📝 *О себе:* {user.about or 'Не указано'}
🔤 *Username:* @{user.username}

💎 *VIP:* {vip_status}
👀 *Видимость:* {hidden_status}"""
    
    bot.send_photo(message.chat.id, user.photo_id, caption=text, parse_mode="Markdown", reply_markup=get_profile_edit_keyboard())

# ========== РЕДАКТИРОВАНИЕ АНКЕТЫ ==========
@bot.message_handler(func=lambda m: m.text and "Имя" in m.text and "✏️" in m.text)
def edit_name_start(message):
    bot.set_state(message.from_user.id, EditProfileStates.waiting_for_new_name, message.chat.id)
    bot.send_message(message.chat.id, "✏️ Введи новое имя:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=EditProfileStates.waiting_for_new_name)
def edit_name_finish(message):
    if "Отмена" not in message.text:
        DBManager.update_user(message.from_user.id, name=message.text)
        bot.send_message(message.chat.id, "✅ Имя изменено!")
    bot.delete_state(message.from_user.id, message.chat.id)
    my_profile(message)

@bot.message_handler(func=lambda m: m.text and "Фото" in m.text and "📸" in m.text)
def edit_photo_start(message):
    bot.set_state(message.from_user.id, EditProfileStates.waiting_for_new_photo, message.chat.id)
    bot.send_message(message.chat.id, "📸 Отправь новое фото:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=EditProfileStates.waiting_for_new_photo, content_types=['photo'])
def edit_photo_finish(message):
    DBManager.update_user(message.from_user.id, photo_id=message.photo[-1].file_id)
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, "✅ Фото изменено!")
    my_profile(message)

@bot.message_handler(func=lambda m: m.text and "О себе" in m.text and "📝" in m.text)
def edit_about_start(message):
    bot.set_state(message.from_user.id, EditProfileStates.waiting_for_new_about, message.chat.id)
    bot.send_message(message.chat.id, "📝 Расскажи о себе:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=EditProfileStates.waiting_for_new_about)
def edit_about_finish(message):
    if "Отмена" not in message.text:
        DBManager.update_user(message.from_user.id, about=message.text)
        bot.send_message(message.chat.id, "✅ Описание изменено!")
    bot.delete_state(message.from_user.id, message.chat.id)
    my_profile(message)

@bot.message_handler(func=lambda m: m.text and "Username" in m.text and "🔤" in m.text)
def edit_username_start(message):
    bot.set_state(message.from_user.id, EditProfileStates.waiting_for_new_username, message.chat.id)
    bot.send_message(message.chat.id, "🔤 Введи новый username (без @):", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=EditProfileStates.waiting_for_new_username)
def edit_username_finish(message):
    if "Отмена" not in message.text:
        DBManager.update_user(message.from_user.id, username=message.text.replace("@", ""))
        bot.send_message(message.chat.id, "✅ Username изменён!")
    bot.delete_state(message.from_user.id, message.chat.id)
    my_profile(message)

# ========== МАГАЗИН ==========
@bot.message_handler(func=lambda m: m.text and "Магазин" in m.text)
@require_registration
def shop(message):
    bot.send_message(message.chat.id, "🛍️ *МАГАЗИН* 🛍️\n\nВыбери товар:", parse_mode="Markdown", reply_markup=get_shop_keyboard())

@bot.message_handler(func=lambda m: m.text and "VIP статус" in m.text)
def buy_vip(message):
    prices = [LabeledPrice(label="VIP на 20 дней", amount=VIP_PRICE)]
    bot.send_invoice(message.chat.id, "VIP статус", "Премиум на 20 дней", "vip", "", "XTR", prices)

@bot.message_handler(func=lambda m: m.text and "Скрыть анкету" in m.text)
def buy_hide(message):
    prices = [LabeledPrice(label="Скрытие на 14 дней", amount=HIDE_PRICE)]
    bot.send_invoice(message.chat.id, "Скрытие анкеты", "Анкета скрыта на 14 дней", "hide", "", "XTR", prices)

@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def payment_success(message):
    payload = message.successful_payment.invoice_payload
    if payload == "vip":
        DBManager.set_vip(message.from_user.id, VIP_DAYS)
        bot.send_message(message.chat.id, "💎 VIP активирован на 20 дней!")
    elif payload == "hide":
        DBManager.set_hidden(message.from_user.id, HIDE_DAYS)
        bot.send_message(message.chat.id, "🙈 Анкета скрыта на 14 дней!")

@bot.message_handler(func=lambda m: m.text and "Поиск по username" in m.text)
def search_by_username_start(message):
    bot.set_state(message.from_user.id, SearchStates.waiting_for_username_search, message.chat.id)
    bot.send_message(message.chat.id, "🔎 Введи username (без @):", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=SearchStates.waiting_for_username_search)
def search_by_username_finish(message):
    if "Отмена" not in message.text:
        user = DBManager.get_user_by_username(message.text)
        if user:
            text = f"👤 *АНКЕТА* 👤\n\n📛 Имя: {user.name}\n🎂 Возраст: {user.age}\n🏙️ Город: {user.city}\n📝 О себе: {user.about or '—'}\n🔤 @{user.username}"
            bot.send_photo(message.chat.id, user.photo_id, caption=text, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден!")
    bot.delete_state(message.from_user.id, message.chat.id)

# ========== ПОИСК АНКЕТ ==========
@bot.message_handler(func=lambda m: m.text and "Поиск анкет" in m.text)
@require_registration
def search_start(message):
    bot.set_state(message.from_user.id, SearchStates.in_search, message.chat.id)
    show_next_profile(message)

def show_next_profile(message):
    user = DBManager.get_user(message.from_user.id)
    next_user = DBManager.get_random_user(message.from_user.id, user.city)
    if not next_user:
        bot.send_message(message.chat.id, "😔 Пока нет анкет...")
        bot.delete_state(message.from_user.id, message.chat.id)
        start_command(message)
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['current_profile'] = next_user.telegram_id
    text = f"✨ *АНКЕТА* ✨\n\n📛 {next_user.name}, {next_user.age}\n🏙️ {next_user.city}\n📝 {next_user.about or '—'}"
    bot.send_photo(message.chat.id, next_user.photo_id, caption=text, parse_mode="Markdown", reply_markup=get_search_keyboard())

@bot.message_handler(state=SearchStates.in_search, func=lambda m: m.text and "Лайк" in m.text)
def search_like(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target = data.get('current_profile')
    if target:
        try:
            bot.send_message(target, f"❤️ Вы понравились @{message.from_user.username}!")
        except:
            pass
        bot.send_message(message.chat.id, "❤️ Лайк отправлен!")
    show_next_profile(message)

@bot.message_handler(state=SearchStates.in_search, func=lambda m: m.text and "Скип" in m.text)
def search_skip(message):
    show_next_profile(message)

@bot.message_handler(state=SearchStates.in_search, func=lambda m: m.text and "Стоп" in m.text)
def search_stop(message):
    bot.delete_state(message.from_user.id, message.chat.id)
    start_command(message)

# ========== ЖАЛОБА ==========
@bot.message_handler(func=lambda m: m.text and "Жалоба" in m.text)
@require_registration
def complaint_start(message):
    bot.set_state(message.from_user.id, ComplaintStates.waiting_for_username, message.chat.id)
    bot.send_message(message.chat.id, "⚠️ Введи username нарушителя:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=ComplaintStates.waiting_for_username)
def complaint_username(message):
    if "Отмена" in message.text:
        bot.delete_state(message.from_user.id, message.chat.id)
        start_command(message)
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['reported'] = message.text.replace("@", "")
    bot.set_state(message.from_user.id, ComplaintStates.waiting_for_reason, message.chat.id)
    bot.send_message(message.chat.id, "📝 Опиши причину:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=ComplaintStates.waiting_for_reason)
def complaint_reason(message):
    if "Отмена" in message.text:
        bot.delete_state(message.from_user.id, message.chat.id)
        start_command(message)
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['reason'] = message.text
    bot.set_state(message.from_user.id, ComplaintStates.waiting_for_screenshot, message.chat.id)
    bot.send_message(message.chat.id, "📸 Отправь скриншот:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=ComplaintStates.waiting_for_screenshot, content_types=['photo'])
def complaint_screenshot(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        DBManager.add_complaint(message.from_user.id, data['reported'], data['reason'], message.photo[-1].file_id)
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(OWNER_ID, f"⚠️ *ЖАЛОБА* ⚠️\nОт: @{message.from_user.username}\nНа: @{data['reported']}\nПричина: {data['reason']}", parse_mode="Markdown")
    bot.send_photo(OWNER_ID, message.photo[-1].file_id)
    bot.send_message(message.chat.id, "✅ Жалоба отправлена!")
    start_command(message)

# ========== АДМИН-ПАНЕЛЬ ==========
@bot.message_handler(func=lambda m: m.text and "Админ-панель" in m.text)
def admin_panel(message):
    if not DBManager.is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Нет доступа!")
        return
    kb = get_owner_keyboard() if message.from_user.id == OWNER_ID else get_admin_keyboard()
    bot.send_message(message.chat.id, "🛠️ *АДМИН-ПАНЕЛЬ* 🛠️", parse_mode="Markdown", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text and "Владелец" in m.text)
def owner_panel(message):
    if message.from_user.id != OWNER_ID:
        return
    bot.send_message(message.chat.id, "👑 *ПАНЕЛЬ ВЛАДЕЛЬЦА* 👑", parse_mode="Markdown", reply_markup=get_owner_keyboard())

# ========== ВЫДАТЬ VIP ==========
@bot.message_handler(func=lambda m: m.text and "Выдать VIP" in m.text)
def admin_vip_start(message):
    if not DBManager.is_admin(message.from_user.id):
        return
    bot.set_state(message.from_user.id, AdminStates.waiting_for_vip_username, message.chat.id)
    bot.send_message(message.chat.id, "👑 Введи username:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=AdminStates.waiting_for_vip_username)
def admin_vip_days(message):
    if "Отмена" in message.text:
        bot.delete_state(message.from_user.id, message.chat.id)
        admin_panel(message)
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['vip_username'] = message.text.replace("@", "")
    bot.set_state(message.from_user.id, AdminStates.waiting_for_vip_days, message.chat.id)
    bot.send_message(message.chat.id, "📆 На сколько дней?")

@bot.message_handler(state=AdminStates.waiting_for_vip_days)
def admin_vip_finish(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Введи число!")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        username = data['vip_username']
    user = DBManager.get_user_by_username(username)
    if user and DBManager.set_vip(user.telegram_id, int(message.text)):
        bot.send_message(message.chat.id, f"✅ VIP выдан @{username} на {message.text} дней!")
        try:
            bot.send_message(user.telegram_id, f"💎 Вам выдан VIP на {message.text} дней!")
        except:
            pass
    else:
        bot.send_message(message.chat.id, "❌ Пользователь не найден!")
    bot.delete_state(message.from_user.id, message.chat.id)

# ========== СНЯТЬ VIP ==========
@bot.message_handler(func=lambda m: m.text and "Снять VIP" in m.text)
def admin_remove_vip_start(message):
    if not DBManager.is_admin(message.from_user.id):
        return
    bot.set_state(message.from_user.id, AdminStates.waiting_for_remove_vip, message.chat.id)
    bot.send_message(message.chat.id, "💔 Введи username:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=AdminStates.waiting_for_remove_vip)
def admin_remove_vip_finish(message):
    if "Отмена" not in message.text:
        user = DBManager.get_user_by_username(message.text)
        if user and DBManager.remove_vip(user.telegram_id):
            bot.send_message(message.chat.id, f"✅ VIP снят с @{message.text}")
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден!")
    bot.delete_state(message.from_user.id, message.chat.id)

# ========== НАЗНАЧИТЬ АДМИНА ==========
@bot.message_handler(func=lambda m: m.text and "Назначить админа" in m.text)
def admin_add_start(message):
    if message.from_user.id != OWNER_ID:
        bot.send_message(message.chat.id, "❌ Только владелец!")
        return
    bot.set_state(message.from_user.id, AdminStates.waiting_for_vip_username, message.chat.id)
    bot.send_message(message.chat.id, "🛡️ Введи username нового админа:", reply_markup=get_cancel_keyboard())
    # Используем то же состояние, но логика другая
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['action'] = 'add_admin'

@bot.message_handler(state=AdminStates.waiting_for_vip_username, func=lambda m: True)
def admin_add_finish(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        action = data.get('action', 'vip')
    if action == 'add_admin':
        if DBManager.update_user_by_username(message.text, is_admin=True):
            bot.send_message(message.chat.id, f"✅ @{message.text} теперь админ!")
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден!")
    bot.delete_state(message.from_user.id, message.chat.id)

# ========== СНЯТЬ АДМИНА ==========
@bot.message_handler(func=lambda m: m.text and "Снять админа" in m.text)
def admin_remove_start(message):
    if message.from_user.id != OWNER_ID:
        return
    bot.set_state(message.from_user.id, AdminStates.waiting_for_remove_admin, message.chat.id)
    bot.send_message(message.chat.id, "🗑️ Введи username:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=AdminStates.waiting_for_remove_admin)
def admin_remove_finish(message):
    if "Отмена" not in message.text:
        if DBManager.update_user_by_username(message.text, is_admin=False):
            bot.send_message(message.chat.id, f"✅ @{message.text} больше не админ!")
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден!")
    bot.delete_state(message.from_user.id, message.chat.id)

# ========== СНОС АНКЕТЫ ==========
@bot.message_handler(func=lambda m: m.text and "Снос анкеты" in m.text)
def admin_delete_start(message):
    if not DBManager.is_admin(message.from_user.id):
        return
    bot.set_state(message.from_user.id, AdminStates.waiting_for_delete_username, message.chat.id)
    bot.send_message(message.chat.id, "💀 Введи username для удаления:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=AdminStates.waiting_for_delete_username)
def admin_delete_finish(message):
    if "Отмена" not in message.text:
        user = DBManager.get_user_by_username(message.text)
        if user and DBManager.delete_user(user.telegram_id):
            bot.send_message(message.chat.id, f"✅ Анкета @{message.text} удалена!")
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден!")
    bot.delete_state(message.from_user.id, message.chat.id)

# ========== БАН ==========
@bot.message_handler(func=lambda m: m.text and "Бан анкеты" in m.text)
def admin_ban_start(message):
    if not DBManager.is_admin(message.from_user.id):
        return
    bot.set_state(message.from_user.id, AdminStates.waiting_for_ban_username, message.chat.id)
    bot.send_message(message.chat.id, "⛔ Введи username для бана:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=AdminStates.waiting_for_ban_username)
def admin_ban_days(message):
    if "Отмена" in message.text:
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['ban_username'] = message.text.replace("@", "")
    bot.set_state(message.from_user.id, AdminStates.waiting_for_ban_duration, message.chat.id)
    bot.send_message(message.chat.id, "⏱️ На сколько минут забанить?")

@bot.message_handler(state=AdminStates.waiting_for_ban_duration)
def admin_ban_finish(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Введи число!")
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        username = data['ban_username']
    user = DBManager.get_user_by_username(username)
    if user and DBManager.ban_user(user.telegram_id, int(message.text)):
        bot.send_message(message.chat.id, f"✅ @{username} забанен на {message.text} минут!")
    else:
        bot.send_message(message.chat.id, "❌ Пользователь не найден!")
    bot.delete_state(message.from_user.id, message.chat.id)

# ========== РАССЫЛКА ==========
@bot.message_handler(func=lambda m: m.text and "Рассылка" in m.text)
def admin_broadcast_start(message):
    if not DBManager.is_admin(message.from_user.id):
        return
    bot.set_state(message.from_user.id, AdminStates.waiting_for_broadcast_text, message.chat.id)
    bot.send_message(message.chat.id, "📣 Введи текст рассылки:", reply_markup=get_cancel_keyboard())

@bot.message_handler(state=AdminStates.waiting_for_broadcast_text)
def admin_broadcast_photo(message):
    if "Отмена" in message.text:
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['broadcast_text'] = message.text
    bot.set_state(message.from_user.id, AdminStates.waiting_for_broadcast_photo, message.chat.id)
    bot.send_message(message.chat.id, "🖼️ Отправь фото (или '-' пропустить):")

@bot.message_handler(state=AdminStates.waiting_for_broadcast_photo, content_types=['photo', 'text'])
def admin_broadcast_send(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        text = data['broadcast_text']
    
    photo_id = None
    if message.content_type == 'photo':
        photo_id = message.photo[-1].file_id
    
    users = DBManager.get_all_users_ids()
    success = 0
    for uid in users:
        try:
            if photo_id:
                bot.send_photo(uid, photo_id, caption=text)
            else:
                bot.send_message(uid, text)
            success += 1
        except:
            pass
    
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, f"✅ Рассылка отправлена! Получили: {success}/{len(users)}")

# ========== СПИСКИ ==========
@bot.message_handler(func=lambda m: m.text and "Список админов" in m.text)
def list_admins(message):
    if message.from_user.id != OWNER_ID:
        return
    admins = DBManager.get_all_admins()
    text = "🛡️ *АДМИНЫ:* 🛡️\n\n"
    for a in admins:
        text += f"• @{a.username}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and "Список VIP" in m.text)
def list_vips(message):
    if not DBManager.is_admin(message.from_user.id):
        return
    vips = DBManager.get_all_vips()
    text = "💎 *VIP ПОЛЬЗОВАТЕЛИ:* 💎\n\n"
    for v in vips[:20]:
        text += f"• @{v.username}\n"
    if len(vips) > 20:
        text += f"\n... и ещё {len(vips) - 20}"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ========== СТАТИСТИКА ==========
@bot.message_handler(func=lambda m: m.text and "Статистика" in m.text)
def stats(message):
    if message.from_user.id != OWNER_ID and not DBManager.is_admin(message.from_user.id):
        return
    s = DBManager.get_stats()
    text = f"""📊 *СТАТИСТИКА* 📊

👥 Всего: {s['total']}
📅 За 24ч: {s['active_today']}
💎 VIP: {s['vip']}
🛡️ Админов: {s['admins']}"""
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ========== НАЗАД ==========
@bot.message_handler(func=lambda m: m.text and "Назад" in m.text)
def back_button(message):
    bot.delete_state(message.from_user.id, message.chat.id)
    start_command(message)

@bot.message_handler(func=lambda m: m.text and "Отмена" in m.text)
def cancel_button(message):
    bot.delete_state(message.from_user.id, message.chat.id)
    start_command(message)

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("🚀 Бот Fant запущен!")
    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.infinity_polling()
