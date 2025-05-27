import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import os
from dotenv import load_dotenv
load_dotenv()
import random
import requests
import re
from cryptography.fernet import Fernet

# Функции для шифрования и дешифрования значений
def get_fernet():
    key = os.getenv("FERNET_KEY")
    if not key:
        # Генерируем ключ, если его нет
        key = Fernet.generate_key()
        print(f"Сгенерирован новый ключ FERNET_KEY: {key.decode()}")
        return Fernet(key)
    return Fernet(key)

def encrypt_value(value):
    if value is None:
        return None
    try:
        f = get_fernet()
        return f.encrypt(value.encode()).decode()
    except Exception as e:
        print(f"Ошибка шифрования: {e}")
        return value

def decrypt_value(value):
    if value is None:
        return None
    try:
        f = get_fernet()
        return f.decrypt(value.encode()).decode()
    except Exception as e:
        print(f"Ошибка дешифрования: {e}")
        return value

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Проверяем наличие токена бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
engine = create_engine('sqlite:///bakery.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)

# Словарь для хранения истории навигации пользователей
user_navigation_history = {}

# Модели данных
class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    price = Column(Float)
    category = Column(String)
    image_url = Column(String)
    is_special = Column(Integer, default=0)
    discount = Column(Float, default=0.0)
    rating = Column(Float, default=0.0)
    ingredients = Column(String)
    calories = Column(Integer, default=0)
    preparation_time = Column(Integer, default=60)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    _username = Column("username", String)
    _phone = Column("phone", String)
    _address = Column("address", String)
    bonus_points = Column(Integer, default=0)
    last_order_date = Column(DateTime)
    favorite_category = Column(String)
    orders = relationship("Order", back_populates="user")

    @property
    def username(self):
        return decrypt_value(self._username) if self._username else None

    @username.setter
    def username(self, value):
        self._username = encrypt_value(value) if value else None

    @property
    def phone(self):
        return decrypt_value(self._phone) if self._phone else None

    @phone.setter
    def phone(self, value):
        self._phone = encrypt_value(value) if value else None

    @property
    def address(self):
        return decrypt_value(self._address) if self._address else None

    @address.setter
    def address(self, value):
        self._address = encrypt_value(value) if value else None

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(Integer)
    quantity = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String, default='pending')
    delivery_method = Column(String)
    address = Column(String)
    delivery_date = Column(String)
    delivery_time = Column(String)
    total_price = Column(Float, default=0.0)
    review_requested = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    user = relationship("User", back_populates="orders")

class Review(Base):
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    order_id = Column(Integer, ForeignKey('orders.id'))
    rating = Column(Integer)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    is_anonymous = Column(Boolean, default=False)

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    is_active = Column(Boolean, default=True)

class LocalStorage(Base):
    __tablename__ = 'local_storage'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)

class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    message = Column(Text)
    scheduled_time = Column(DateTime)
    sent = Column(Boolean, default=False)
    notification_type = Column(String)

# Создание таблиц
Base.metadata.create_all(engine)

# Клавиатуры
def get_main_keyboard(user_id=None):
    session = Session()
    is_admin = False
    try:
        if user_id:
            admin = session.query(Admin).filter_by(user_id=user_id, is_active=True).first()
            is_admin = bool(admin)
    finally:
        session.close()

    keyboard = [
        [KeyboardButton(text="🍰 Меню"), KeyboardButton(text="🎁 Акции")],
        [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="⭐ Популярное")],
        [KeyboardButton(text="🚚 Условия доставки"), KeyboardButton(text="💳 Бонусы")],
        [KeyboardButton(text="📱 Мой профиль"), KeyboardButton(text="ℹ️ О нас")],
        [KeyboardButton(text="📝 Оставить отзыв")]
    ]

    if is_admin:
        keyboard.extend([
            [KeyboardButton(text="📋 Заказы"), KeyboardButton(text="🧺 Корзины")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="💬 Отзывы")]
        ])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_category_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🍪 Сладкие пироги", callback_data="category_sweet"))
    keyboard.add(InlineKeyboardButton(text="🥧 Сытные пироги", callback_data="category_savory"))
    keyboard.add(InlineKeyboardButton(text="🎂 Торты", callback_data="category_cakes"))
    keyboard.add(InlineKeyboardButton(text="🔥 Хиты продаж", callback_data="category_popular"))
    keyboard.add(InlineKeyboardButton(text="🌟 Новинки", callback_data="category_new"))
    return keyboard.adjust(2).as_markup()

def get_products_keyboard(category):
    session = Session()
    try:
        if category == "popular":
            products = session.query(Product).filter(Product.rating >= 4.0).all()
        elif category == "new":
            products = session.query(Product).all()[:3]
        else:
            products = session.query(Product).filter_by(category=category).all()
        
        keyboard = InlineKeyboardBuilder()
        for product in products:
            display_price = product.price * (1 - product.discount) if product.discount > 0 else product.price
            price_text = f"{display_price:.0f} byn"
            if product.discount > 0:
                price_text += f" (-{int(product.discount * 100)}%)"
            rating_stars = "⭐" * int(product.rating) if product.rating > 0 else ""
            product_text = f"{product.name} {rating_stars} - {price_text}"
            keyboard.add(InlineKeyboardButton(
                text=product_text,
                callback_data=f"product_{product.id}"
            ))
        keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_categories"))
        return keyboard.adjust(1).as_markup()
    finally:
        session.close()

def get_payment_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="💵 Наличными", callback_data="pay_cash"))
    keyboard.add(InlineKeyboardButton(text="💳 Картой при получении", callback_data="pay_card"))
    keyboard.add(InlineKeyboardButton(text="🏦 Безналичный расчет", callback_data="pay_bank"))
    return keyboard.adjust(1).as_markup()

# Получаем или создаём пользователя
def get_or_create_user(session, telegram_id, username):
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        session.commit()
    return user

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    session = Session()
    try:
        user = get_or_create_user(session, message.from_user.id, message.from_user.username)
        is_new_user = user.last_order_date is None

        # Если телефона нет — просим ввести
        if not user.phone:
            await message.answer(
                "Добро пожаловать в нашу пекарню! 🥖\n\n"
                "Для оформления заказов нам нужен ваш номер телефона.\n"
                "Пожалуйста, введите ваш номер телефона в формате:\n<b>+375-XX-XXX-XX-XX</b>",
                parse_mode="HTML"
            )
            return

        if is_new_user:
            welcome_text = (
                "🎉 Добро пожаловать в нашу пекарню! 🥖\n\n"
                "🎁 Специально для новых клиентов - скидка 10% на первый заказ!\n"
                "Используйте промокод: НОВИЧОК\n\n"
                "Выберите интересующий вас раздел:"
            )
            user.bonus_points += 100
        else:
            welcome_text = (
                f"С возвращением, {user.username or 'друг'}! 🤗\n"
                f"💰 Ваши бонусные баллы: {user.bonus_points}\n\n"
                "Выберите интересующий вас раздел:"
            )
        session.commit()
        
        await message.answer(
            welcome_text,
            reply_markup=get_main_keyboard(message.from_user.id)
        )
    finally:
        session.close()

@dp.message(lambda message: message.text == "🍰 Меню")
async def show_menu(message: types.Message):
    await message.answer(
        "🍰 Наше меню:\n\nВыберите категорию пирогов...",
        reply_markup=get_category_keyboard()
    )

@dp.message(lambda message: message.text == "⭐ Популярное")
async def show_popular(message: types.Message):
    session = Session()
    try:
        popular_products = session.query(Product).filter(Product.rating >= 4.0).limit(5).all()
        
        if not popular_products:
            await message.answer("Пока нет популярных товаров с высокими оценками")
            return
        
        text = "⭐ Наши хиты продаж:\n\n"
        keyboard = InlineKeyboardBuilder()
        
        for product in popular_products:
            rating_stars = "⭐" * int(product.rating)
            text += f"• {product.name} {rating_stars} ({product.rating:.1f}) - {product.price:.0f} byn\n"
            keyboard.add(InlineKeyboardButton(
                text=f"Заказать {product.name}",
                callback_data=f"product_{product.id}"
            ))
        
        await message.answer(text, reply_markup=keyboard.adjust(1).as_markup())
    finally:
        session.close()

@dp.message(lambda message: message.text == "💳 Бонусы")
async def show_bonus_info(message: types.Message):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            await message.answer("Пользователь не найден")
            return
        
        # Рассчитываем историю заказов
        total_orders = session.query(Order).filter_by(user_id=user.id, status='completed').count()
        total_spent = session.query(Order).filter_by(user_id=user.id, status='completed').with_entities(
            Order.total_price).all()
        total_amount = sum([order[0] or 0 for order in total_spent])
        
        bonus_text = (
            f"💳 Ваша бонусная программа:\n\n"
            f"💰 Доступно баллов: {user.bonus_points}\n"
            f"📊 Заказов выполнено: {total_orders}\n"
            f"💸 Общая сумма заказов: {total_amount:.0f} byn\n\n"
            f"💡 Как накопить баллы:\n"
            f"• 1 byn = 1 бонусный балл\n"
            f"• Отзыв с фото = +5 баллов\n"
            f"• День рождения = +20 баллов\n\n"
            f"🎁 Как потратить:\n"
            f"• 10 баллов = 5 byn скидка\n"
            f"• 50 баллов = бесплатная доставка"
        )
        
        await message.answer(bonus_text)
    finally:
        session.close()

@dp.message(lambda message: message.text == "📱 Мой профиль")
async def show_profile(message: types.Message):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            await message.answer("Профиль не найден")
            return
        
        last_order = session.query(Order).filter_by(user_id=user.id, status='completed').order_by(Order.created_at.desc()).first()
        
        profile_text = (
            f"📱 Ваш профиль:\n\n"
            f"👤 Имя: {user.username or 'Не указано'}\n"
            f"📞 Телефон: {user.phone or 'Не указан'}\n"
            f"📍 Адрес: {user.address or 'Не указан'}\n"
            f"💰 Бонусы: {user.bonus_points}\n"
            f"❤️ Любимая категория: {user.favorite_category or 'Не определена'}\n"
        )
        
        if last_order:
            profile_text += f"🕐 Последний заказ: {last_order.created_at.strftime('%d.%m.%Y')}\n"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile"))
        keyboard.add(InlineKeyboardButton(text="📋 История заказов", callback_data="order_history"))
        
        await message.answer(profile_text, reply_markup=keyboard.adjust(1).as_markup())
    finally:
        session.close()

@dp.message(lambda message: message.text == "🎁 Акции")
async def show_specials(message: types.Message):
    session = Session()
    try:
        special_products = session.query(Product).filter(Product.discount > 0).all()
        
        specials_text = "🎁 Текущие акции:\n\n"
        keyboard = InlineKeyboardBuilder()
        
        if special_products:
            for product in special_products:
                old_price = product.price
                new_price = product.price * (1 - product.discount)
                discount_percent = int(product.discount * 100)
                
                specials_text += (
                    f"🔥 {product.name}\n"
                    f"💰 {new_price:.0f} ~~{old_price:.0f} byn~~ (-{discount_percent}%)\n\n"
                )
                
                keyboard.add(InlineKeyboardButton(
                    text=f"Заказать {product.name}",
                    callback_data=f"product_{product.id}"
                ))
        else:
            specials_text += "К сожалению, специальных предложений пока нет 😔\n"
            specials_text += "Но у нас есть постоянные скидки для постоянных клиентов!"
        
        # Добавляем общие предложения
        specials_text += (
            "\n🎯 Постоянные предложения:\n"
            "• При заказе от 80 byn - бесплатная доставка\n"
            "• Скидка 5% при оплате бонусами\n"
            "• Каждый 10-й пирог в подарок!"
        )
        
        await message.answer(specials_text, reply_markup=keyboard.adjust(1).as_markup())
    finally:
        session.close()

@dp.message(lambda message: message.text == "🛒 Корзина")
async def show_cart(message: types.Message):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user:
            await message.answer("В корзине ничего нет")
            return
        
        orders = session.query(Order).filter_by(user_id=user.id, status='pending').all()
        if not orders:
            await message.answer("🛒 Корзина пуста\n\nПосмотрите наше меню и добавьте что-нибудь вкусное!")
            return
        
        total = 0
        cart_text = "🛒 Ваша корзина:\n\n"
        
        for order in orders:
            product = session.query(Product).get(order.product_id)
            if product:
                price = product.price * (1 - product.discount) if product.discount > 0 else product.price
                item_total = price * order.quantity
                
                cart_text += f"• {product.name}\n"
                cart_text += f"  {order.quantity} шт. × {price:.0f} = {item_total:.0f} byn\n"
                if product.discount > 0:
                    cart_text += f"  💸 Скидка {int(product.discount * 100)}%\n"
                cart_text += "\n"
                total += item_total
        
        # Рассчитываем доставку
        delivery_cost = 0 if total >= 80 else 8 
        if delivery_cost > 0:
            cart_text += f"🚚 Доставка: {delivery_cost} byn\n"
            total += delivery_cost
        else:
            cart_text += "🚚 Доставка: БЕСПЛАТНО\n"
        
        cart_text += f"\n💰 Итого: {total:.0f} byn"
        
        # Показываем возможность использования бонусов
        if user.bonus_points >= 100:
            possible_discount = min(user.bonus_points // 2, total * 0.3)  # Максимум 30% от суммы
            cart_text += f"\n🎁 Доступна скидка бонусами: до {possible_discount:.0f} byn"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="✅ Оформить заказ", callback_data="start_checkout"))
        keyboard.add(InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart"))
        keyboard.add(InlineKeyboardButton(text="➕ Добавить еще", callback_data="back_to_categories"))
        
        await message.answer(cart_text, reply_markup=keyboard.adjust(1).as_markup())
    finally:
        session.close()

@dp.message(lambda message: message.text == "🚚 Условия доставки")
async def show_delivery_info(message: types.Message):
    await message.answer(
        "🚚 Условия доставки:\n\n"
        "🏠 Обычная доставка:\n"
        "• По городу: 8 byn\n"
        "• Время: 2-3 часа\n"
        "• Бесплатно при заказе от 80 byn\n\n"
        "🏪 Самовывоз:\n"
        "• Независимости 43\n"
        "• Независимости 60\n"
        "• Время: 2-3 часа\n"
        "• Скидка 5% от суммы заказа\n\n"
        "⏰ Режим работы: 10:00 - 20:00"
    )

@dp.message(lambda message: message.text == "ℹ️ О нас")
async def show_about(message: types.Message):
    await message.answer(
        "ℹ️ О нашей пекарне 🥖\n\n"
        "👨‍🍳 Семейная пекарня\n"
        "🌱 Только натуральные ингредиенты\n"
        "👑 Традиционные рецепты + современные технологии\n\n"
        "🏆 Наши достижения:\n"
        "• Лучшая пекарня города 2023\n"
        "• 5000+ довольных клиентов\n"
        "• Средний рейтинг 4.8/5\n\n"
        "📞 Контакты:\n"
        "• Телефон: +375-44-554-30-43\n"
        "• Instagram: @papapek.by\n"
        "• Адреса: Независимости 43, 60"
    )

@dp.message(lambda message: message.text == "📝 Оставить отзыв")
async def leave_review(message: types.Message):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            await message.answer("Пользователь не найден")
            return
        
        # Находим завершенные заказы без отзывов
        completed_orders = session.query(Order).filter_by(
            user_id=user.id, 
            status='completed'
        ).all()
        
        if not completed_orders:
            await message.answer("У вас пока нет завершенных заказов для оценки")
            return
        
        # Показываем заказы для выбора
        keyboard = InlineKeyboardBuilder()
        
        for order in completed_orders[-5:]:  # Последние 5 заказов
            product = session.query(Product).get(order.product_id)
            if product:
                existing_review = session.query(Review).filter_by(order_id=order.id).first()
                
                if not existing_review:
                    keyboard.add(InlineKeyboardButton(
                        text=f"Оценить: {product.name}",
                        callback_data=f"review_order_{order.id}"
                    ))
        
        if keyboard._buttons:
            await message.answer(
                "📝 Выберите заказ для оценки:",
                reply_markup=keyboard.adjust(1).as_markup()
            )
        else:
            await message.answer("Все ваши заказы уже оценены! Спасибо за обратную связь 🙏")
    finally:
        session.close()

# Обработчики callback-запросов
@dp.callback_query(lambda c: c.data.startswith('category_'))
async def process_category(callback: types.CallbackQuery):
    category = callback.data.split('_')[1]
    
    category_names = {
        'sweet': 'Сладкие пироги',
        'savory': 'Сытные пироги',
        'cakes': 'Торты',
        'popular': 'Популярные',
        'new': 'Новинки'
    }
    
    await callback.message.edit_text(
        f"🍰 {category_names.get(category, 'Пироги')}:\n\nВыберите пирог:",
        reply_markup=get_products_keyboard(category)
    )

@dp.callback_query(lambda c: c.data.startswith('product_'))
async def process_product(callback: types.CallbackQuery):
    try:
        product_id = int(callback.data.split('_')[1])
        session = Session()
        try:
            product = session.query(Product).get(product_id)
            if not product:
                await callback.message.answer("Пирог не найден.")
                return

            # Формируем подробное описание
            price = product.price * (1 - product.discount) if product.discount > 0 else product.price
            
            product_text = f"🥧 {product.name}\n\n"
            product_text += f"📝 {product.description}\n\n"
            
            if product.ingredients:
                product_text += f"🥄 Состав: {product.ingredients}\n"
            
            if product.calories > 0:
                product_text += f"🔥 Калорийность: {product.calories} ккал/100г\n"
            
            product_text += f"⏰ Время приготовления: {product.preparation_time} мин\n"
            
            if product.rating > 0:
                stars = "⭐" * int(product.rating)
                product_text += f"⭐ Рейтинг: {stars} ({product.rating:.1f})\n"
            
            product_text += f"\n💰 Цена: {price:.0f} byn"
            
            if product.discount > 0:
                product_text += f" ~~{product.price:.0f}~~ (-{int(product.discount * 100)}%)"

            keyboard = InlineKeyboardBuilder()
            keyboard.add(InlineKeyboardButton(text="➕ В корзину", callback_data=f"add_{product_id}"))
            keyboard.add(InlineKeyboardButton(text="📋 Отзывы", callback_data=f"reviews_{product_id}"))
            keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_to_products_{product.category}"))

            await callback.message.edit_text(product_text, reply_markup=keyboard.adjust(1).as_markup())
        finally:
            session.close()
    except (ValueError, IndexError):
        await callback.message.answer("Неверный ID товара")

@dp.callback_query(lambda c: c.data.startswith('add_'))
async def add_to_cart(callback: types.CallbackQuery):
    try:
        product_id = int(callback.data.split('_')[1])
        session = Session()
        try:
            user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
            if not user:
                user = get_or_create_user(session, callback.from_user.id, callback.from_user.username)
            
            product = session.query(Product).get(product_id)
            if not product:
                await callback.answer("Товар не найден")
                return
            
            # Проверяем, есть ли уже этот товар в корзине
            existing_order = session.query(Order).filter_by(
                user_id=user.id,
                product_id=product_id,
                status='pending'
            ).first()
            
            if existing_order:
                existing_order.quantity += 1
                await callback.answer(f"Добавлено еще одно {product.name} в корзину")
            else:
                new_order = Order(
                    user_id=user.id,
                    product_id=product_id,
                    quantity=1,
                    status='pending'
                )
                session.add(new_order)
                await callback.answer(f"🛒 {product.name} добавлен в корзину!")
            
            session.commit()
        finally:
            session.close()
    except (ValueError, IndexError):
        await callback.answer("Ошибка при добавлении товара")

@dp.callback_query(lambda c: c.data.startswith('reviews_'))
async def show_product_reviews(callback: types.CallbackQuery):
    try:
        product_id = int(callback.data.split('_')[1])
        session = Session()
        try:
            product = session.query(Product).get(product_id)
            if not product:
                await callback.answer("Товар не найден")
                return
            
            reviews = session.query(Review).filter_by(product_id=product_id).order_by(Review.created_at.desc()).limit(10).all()
            
            if not reviews:
                await callback.message.edit_text(
                    f"📋 Отзывы о {product.name}\n\nПока нет отзывов об этом товаре.\nСтаньте первым, кто оставит отзыв! 😊",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 Назад", callback_data=f"product_{product_id}")
                    ]])
                )
                return
            
            reviews_text = f"📋 Отзывы о {product.name}\n\n"
            
            total_rating = sum([r.rating for r in reviews])
            avg_rating = total_rating / len(reviews)
            stars = "⭐" * int(avg_rating)
            
            reviews_text += f"Средняя оценка: {stars} {avg_rating:.1f}/5 ({len(reviews)} отзывов)\n\n"
            
            for review in reviews[:5]:  # Показываем последние 5 отзывов
                user_review = session.query(User).get(review.user_id)
                username = user_review.username if user_review and not review.is_anonymous else "Анонимный покупатель"
                
                review_stars = "⭐" * review.rating
                reviews_text += f"{review_stars} {username}\n"
                if review.comment:
                    reviews_text += f'"{review.comment}"\n'
                reviews_text += f"📅 {review.created_at.strftime('%d.%m.%Y')}\n\n"
            
            keyboard = InlineKeyboardBuilder()
            keyboard.add(InlineKeyboardButton(text="🔙 Назад к товару", callback_data=f"product_{product_id}"))
            
            await callback.message.edit_text(reviews_text, reply_markup=keyboard.as_markup())
        finally:
            session.close()
    except (ValueError, IndexError):
        await callback.answer("Ошибка при загрузке отзывов")

@dp.callback_query(lambda c: c.data == "back_to_categories")
async def back_to_categories(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🍰 Наше меню:\n\nВыберите категорию пирогов...",
        reply_markup=get_category_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith('back_to_products_'))
async def back_to_products(callback: types.CallbackQuery):
    category = callback.data.split('_')[-1]
    
    category_names = {
        'sweet': 'Сладкие пироги',
        'savory': 'Сытные пироги', 
        'cakes': 'Торты',
        'popular': 'Популярные',
        'new': 'Новинки'
    }
    
    await callback.message.edit_text(
        f"🍰 {category_names.get(category, 'Пироги')}:\n\nВыберите пирог:",
        reply_markup=get_products_keyboard(category)
    )

@dp.callback_query(lambda c: c.data == "start_checkout")
async def start_checkout(callback: types.CallbackQuery):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        
        if not user or not user.phone:
            await callback.message.edit_text(
                "❌ Для оформления заказа необходимо указать номер телефона.\n"
                "Пожалуйста, введите ваш номер телефона в формате: +375-XX-XXX-XX-XX"
            )
            return
        
        orders = session.query(Order).filter_by(user_id=user.id, status='pending').all()
        if not orders:
            await callback.answer("Корзина пуста")
            return
        
        # Рассчитываем общую стоимость
        total = 0
        for order in orders:
            product = session.query(Product).get(order.product_id)
            if product:
                price = product.price * (1 - product.discount) if product.discount > 0 else product.price
                total += price * order.quantity
        
        delivery_cost = 0 if total >= 80 else 8
        total += delivery_cost
        
        checkout_text = (
            "📋 Оформление заказа\n\n"
            f"💰 Сумма заказа: {total:.0f} byn\n"
            f"📞 Телефон: {user.phone}\n"
            f"📍 Адрес: {user.address or 'Не указан'}\n\n"
            "Выберите способ доставки:"
        )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🚚 Доставка", callback_data="delivery_home"))
        keyboard.add(InlineKeyboardButton(text="🏪 Самовывоз", callback_data="delivery_pickup"))
        keyboard.add(InlineKeyboardButton(text="🔙 Назад к корзине", callback_data="back_to_cart"))
        
        await callback.message.edit_text(checkout_text, reply_markup=keyboard.adjust(1).as_markup())
    finally:
        session.close()

@dp.callback_query(lambda c: c.data == "delivery_home")
async def delivery_home(callback: types.CallbackQuery):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        
        if not user.address:
            await callback.message.edit_text(
                "📍 Для доставки необходимо указать адрес.\n"
                "Пожалуйста, введите ваш адрес доставки:"
            )
            # Сохраняем состояние ожидания адреса
            session.add(LocalStorage(user_id=user.id, key="waiting_address", value="delivery"))
            session.commit()
            return
        
        # Показываем выбор времени доставки
        await show_delivery_time_selection(callback, "home")
    finally:
        session.close()

@dp.callback_query(lambda c: c.data == "delivery_pickup")
async def delivery_pickup(callback: types.CallbackQuery):
    await show_pickup_locations(callback)

async def show_pickup_locations(callback: types.CallbackQuery):
    pickup_text = (
        "🏪 Самовывоз\n\n"
        "Выберите удобный для вас магазин:\n\n"
        "📍 Независимости 43\n"
        "⏰ 10:00 - 20:00\n\n"
        "📍 Независимости 60\n"
        "⏰ 10:00 - 20:00\n\n"
        "💡 При самовывозе скидка 5%"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📍 Независимости 43", callback_data="pickup_location_43"))
    keyboard.add(InlineKeyboardButton(text="📍 Независимости 60", callback_data="pickup_location_60"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="start_checkout"))
    
    await callback.message.edit_text(pickup_text, reply_markup=keyboard.adjust(1).as_markup())

@dp.callback_query(lambda c: c.data.startswith('pickup_location_'))
async def pickup_location(callback: types.CallbackQuery):
    location = callback.data.split('_')[-1]
    await show_delivery_time_selection(callback, f"pickup_{location}")

async def show_delivery_time_selection(callback, delivery_type):
    time_text = "⏰ Выберите удобное время:\n\n"
    
    keyboard = InlineKeyboardBuilder()
    
    # Добавляем слоты времени
    time_slots = [
        ("10:00-12:00", "morning"),
        ("12:00-15:00", "afternoon"), 
        ("15:00-18:00", "evening"),
        ("18:00-20:00", "night")
    ]
    
    for slot_text, slot_code in time_slots:
        keyboard.add(InlineKeyboardButton(
            text=slot_text,
            callback_data=f"time_{delivery_type}_{slot_code}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="start_checkout"))
    
    await callback.message.edit_text(time_text, reply_markup=keyboard.adjust(2).as_markup())

@dp.callback_query(lambda c: c.data.startswith('time_'))
async def select_time(callback: types.CallbackQuery):
    parts = callback.data.split('_')
    delivery_type = '_'.join(parts[1:-1])
    time_slot = parts[-1]
    
    time_names = {
        'morning': '10:00-12:00',
        'afternoon': '12:00-15:00',
        'evening': '15:00-18:00',
        'night': '18:00-20:00'
    }
    
    selected_time = time_names.get(time_slot, '12:00-15:00')
    
    # Показываем способы оплаты
    payment_text = (
        f"💳 Способ оплаты\n\n"
        f"⏰ Время: {selected_time}\n"
        f"🚚 Доставка: {'Самовывоз' if 'pickup' in delivery_type else 'Доставка'}\n\n"
        "Выберите способ оплаты:"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="💵 Наличными", callback_data=f"pay_cash_{delivery_type}_{time_slot}"))
    keyboard.add(InlineKeyboardButton(text="💳 Картой", callback_data=f"pay_card_{delivery_type}_{time_slot}"))
    keyboard.add(InlineKeyboardButton(text="🏦 Безналичный", callback_data=f"pay_bank_{delivery_type}_{time_slot}"))
    
    await callback.message.edit_text(payment_text, reply_markup=keyboard.adjust(1).as_markup())

@dp.callback_query(lambda c: c.data.startswith('pay_'))
async def process_payment(callback: types.CallbackQuery):
    parts = callback.data.split('_')
    payment_method = parts[1]
    delivery_type = '_'.join(parts[2:-1])
    time_slot = parts[-1]
    
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        orders = session.query(Order).filter_by(user_id=user.id, status='pending').all()
        
        if not orders:
            await callback.answer("Корзина пуста")
            return
        
        # Рассчитываем финальную стоимость
        total = 0
        order_details = []
        
        for order in orders:
            product = session.query(Product).get(order.product_id)
            if product:
                price = product.price * (1 - product.discount) if product.discount > 0 else product.price
                
                # Скидка при самовывозе
                if 'pickup' in delivery_type:
                    price *= 0.95
                
                item_total = price * order.quantity
                total += item_total
                order_details.append(f"• {product.name} x{order.quantity} = {item_total:.0f} byn")
        
        # Доставка
        delivery_cost = 0
        if 'pickup' not in delivery_type and total < 80:
            delivery_cost = 8
            total += delivery_cost
        
        # Создаем финальный заказ
        order_id = random.randint(1000, 9999)
        
        # Обновляем статус заказов
        for order in orders:
            order.status = 'confirmed'
            order.delivery_method = 'pickup' if 'pickup' in delivery_type else 'delivery'
            order.delivery_time = time_slot
            order.total_price = total / len(orders)  # Разделяем общую сумму
            order.created_at = datetime.now()
        
        # Начисляем бонусы
        user.bonus_points += int(total)
        user.last_order_date = datetime.now()
        
        session.commit()
        
        # Формируем подтверждение заказа
        time_names = {
            'morning': '10:00-12:00',
            'afternoon': '12:00-15:00',
            'evening': '15:00-18:00',
            'night': '18:00-20:00'
        }
        
        payment_names = {
            'cash': 'Наличными',
            'card': 'Картой',
            'bank': 'Безналичный расчет'
        }
        
        confirmation_text = (
            f"✅ Заказ #{order_id} оформлен!\n\n"
            f"📋 Детали заказа:\n"
            + "\n".join(order_details) + "\n\n"
            f"💰 Итого: {total:.0f} byn\n"
        )
        
        if delivery_cost > 0:
            confirmation_text += f"🚚 Доставка: {delivery_cost} byn\n"
        elif 'pickup' not in delivery_type:
            confirmation_text += "🚚 Доставка: БЕСПЛАТНО\n"
        
        confirmation_text += (
            f"⏰ Время: {time_names.get(time_slot, '12:00-15:00')}\n"
            f"💳 Оплата: {payment_names.get(payment_method, 'Наличными')}\n"
            f"🚚 {'Самовывоз' if 'pickup' in delivery_type else 'Доставка'}\n\n"
            f"🎁 Начислено бонусов: +{int(total)}\n\n"
            "Мы свяжемся с вами для подтверждения!\n"
            "Спасибо за заказ! 🙏"
        )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu"))
        
        await callback.message.edit_text(
            confirmation_text,
            reply_markup=keyboard.as_markup()
        )
        
    finally:
        session.close()

@dp.callback_query(lambda c: c.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        if user:
            session.query(Order).filter_by(user_id=user.id, status='pending').delete()
            session.commit()
        
        await callback.message.edit_text(
            "🗑 Корзина очищена\n\nВыберите товары из меню для нового заказа",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🍰 Перейти к меню", callback_data="back_to_categories")
            ]])
        )
    finally:
        session.close()

@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "🏠 Главное меню",
        reply_markup=get_main_keyboard(callback.from_user.id)
    )

# Обработчик ввода телефона
@dp.message(lambda message: re.match(r'^\+375-\d{2}-\d{3}-\d{2}-\d{2}$', message.text or ""))
async def save_phone(message: types.Message):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if user:
            user.phone = message.text
            session.commit()
            
            await message.answer(
                "✅ Номер телефона сохранен!\n\n"
                "Теперь вы можете оформлять заказы. Добро пожаловать! 🎉",
                reply_markup=get_main_keyboard(message.from_user.id)
            )
        else:
            await message.answer("Пользователь не найден. Попробуйте команду /start")
    finally:
        session.close()

# Обработчик ввода адреса (когда ожидается адрес)
@dp.message(lambda message: True)
async def handle_address_input(message: types.Message):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user:
            return
        
        # Проверяем, ожидается ли адрес
        waiting_address = session.query(LocalStorage).filter_by(
            user_id=user.id, 
            key="waiting_address"
        ).first()
        
        if waiting_address and not user.address:
            user.address = message.text
            session.delete(waiting_address)
            session.commit()
            
            await message.answer(
                f"✅ Адрес сохранен: {message.text}\n\n"
                "Теперь выберите время доставки:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="⏰ Выбрать время", callback_data="delivery_home")
                ]])
            )
        else:
            # Если это не ожидаемый ввод, показываем справку
            await message.answer(
                "❓ Не понимаю команду.\n\n"
                "Используйте кнопки меню для навигации или команду /start для начала.",
                reply_markup=get_main_keyboard(message.from_user.id)
            )
    finally:
        session.close()

# Функция для инициализации данных (примеры товаров)
async def init_sample_data():
    session = Session()
    try:
        # Проверяем, есть ли уже товары
        existing_products = session.query(Product).count()
        if existing_products > 0:
            return
        
        # Добавляем примеры товаров
        sample_products = [
            Product(
                name="Шарлотка с яблоками",
                description="Классический домашний пирог с сочными яблоками и корицей",
                price=25.0,
                category="sweet",
                ingredients="яблоки, мука, яйца, сахар, корица",
                calories=220,
                preparation_time=45,
                rating=4.8
            ),
            Product(
                name="Пирог с капустой",
                description="Сытный пирог с тушеной капустой и зеленью",
                price=20.0,
                category="savory", 
                ingredients="капуста, лук, морковь, тесто, специи",
                calories=180,
                preparation_time=60,
                rating=4.5
            ),
            Product(
                name="Торт Наполеон",
                description="Классический торт из слоеного теста с заварным кремом",
                price=45.0,
                category="cakes",
                ingredients="слоеное тесто, молоко, яйца, масло, ваниль",
                calories=350,
                preparation_time=120,
                rating=4.9,
                discount=0.1
            ),
            Product(
                name="Пирог с мясом",
                description="Сочный пирог с говяжьим фаршем и луком",
                price=30.0,
                category="savory",
                ingredients="говядина, лук, тесто, специи",
                calories=280,
                preparation_time=80,
                rating=4.7
            ),
            Product(
                name="Медовик",
                description="Нежный медовый торт со сметанным кремом",
                price=35.0,
                category="cakes",
                ingredients="мед, мука, сметана, яйца, сахар",
                calories=300,
                preparation_time=90,
                rating=4.6
            )
        ]
        
        for product in sample_products:
            session.add(product)
        
        # Добавляем администратора (замените на свой ID)
        admin = Admin(user_id=123456789, username="admin", is_active=True)
        session.add(admin)
        
        session.commit()
        print("✅ Примеры данных добавлены")
        
    except Exception as e:
        print(f"Ошибка при инициализации данных: {e}")
        session.rollback()
    finally:
        session.close()

# Функция для создания заказа в RetailCRM
def create_retailcrm_order(user, orders, total, delivery_type, time_slot):
    api_url = os.getenv("https://papapek2.retailcrm.ru/api/v5/")
    api_key = os.getenv("17NrpZpMGmE1JIwO9XqFQL3MWuDOXO2o")
    if not api_url or not api_key:
        print("RetailCRM API не настроен")
        return

    # Формируем товары
    items = []
    for order in orders:
        items.append({
            "offer": {"externalId": str(order.product_id)},
            "quantity": order.quantity,
            "productName": order.product_id  # Можно получить имя товара, если нужно
        })

    # Формируем заказ
    data = {
        "apiKey": api_key,
        "order": {
            "firstName": user.username or "Клиент",
            "phone": user.phone,
            "customerComment": f"Заказ из Telegram-бота. Время: {time_slot}",
            "orderMethod": "telegram-bot",
            "items": items,
            "totalSumm": total,
            "delivery": {
                "code": "courier" if delivery_type == "delivery" else "self-delivery",
                "address": {
                    "text": user.address if delivery_type == "delivery" else "Самовывоз"
                }
            }
        }
    }

    try:
        response = requests.post(
            f"{api_url}orders/create",
            json=data
        )
        result = response.json()
        if result.get("success"):
            print("Заказ успешно создан в RetailCRM")
        else:
            print("Ошибка RetailCRM:", result)
    except Exception as e:
        print("Ошибка при отправке заказа в RetailCRM:", e)

# Главная функция
async def main():
    print("🚀 Запуск бота пекарни...")
    
    # Инициализируем примеры данных
    await init_sample_data()
    
    print("✅ Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())