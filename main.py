import os
import logging
import asyncio
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    Session as DBSession,
    relationship,
)
from dotenv import load_dotenv
import requests
from cryptography.fernet import Fernet

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Конфигурация
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")  # Исправлено: используем переменную окружения
    FERNET_KEY = os.getenv("FERNET_KEY")  # Исправлено: используем переменную окружения
    RETAIL_CRM_URL = os.getenv("RETAIL_CRM_URL")  # Исправлено: используем переменную окружения
    RETAIL_CRM_API_KEY = os.getenv("RETAIL_CRM_API_KEY")  # Исправлено: используем переменную окружения
    FREE_DELIVERY_THRESHOLD = 80  # Бесплатная доставка от этой суммы
    DELIVERY_COST = 8  # Стоимость доставки

    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в переменных окружения")
        if not cls.RETAIL_CRM_URL or not cls.RETAIL_CRM_API_KEY:
            logger.warning("RetailCRM не настроен - заказы не будут синхронизироваться")

Config.validate()

# Инициализация бота
bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
engine = create_engine("sqlite:///bakery.db", echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# Шифрование данных
class DataEncryptor:
    _fernet = None

    @classmethod
    def get_fernet(cls):
        if cls._fernet is None:
            if Config.FERNET_KEY:
                cls._fernet = Fernet(Config.FERNET_KEY.encode())
            else:
                key = Fernet.generate_key()
                logger.warning(f"Сгенерирован новый ключ шифрования: {key.decode()}")
                cls._fernet = Fernet(key)
        return cls._fernet

    @classmethod
    def encrypt(cls, value: str) -> Optional[str]:
        if value is None:
            return None
        try:
            return cls.get_fernet().encrypt(value.encode()).decode()
        except Exception as e:
            logger.error(f"Ошибка шифрования: {e}")
            return value

    @classmethod
    def decrypt(cls, value: str) -> Optional[str]:
        if value is None:
            return None
        try:
            return cls.get_fernet().decrypt(value.encode()).decode()
        except Exception as e:
            logger.error(f"Ошибка дешифрования: {e}")
            return value

# Модели данных
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    category = Column(String(50))
    image_url = Column(String(255))
    is_special = Column(Boolean, default=False)
    discount = Column(Float, default=0.0)
    rating = Column(Float, default=0.0)
    ingredients = Column(Text)
    calories = Column(Integer)
    preparation_time = Column(Integer, default=60)

    @property
    def final_price(self) -> float:
        return self.price * (1 - self.discount)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    _username = Column("username", String(100))
    _phone = Column("phone", String(20))
    _address = Column("address", Text)
    bonus_points = Column(Integer, default=0)
    last_order_date = Column(DateTime)
    orders = relationship("Order", back_populates="user")

    @property
    def username(self) -> Optional[str]:
        return DataEncryptor.decrypt(self._username)

    @username.setter
    def username(self, value: str):
        self._username = DataEncryptor.encrypt(value)

    @property
    def phone(self) -> Optional[str]:
        return DataEncryptor.decrypt(self._phone)

    @phone.setter
    def phone(self, value: str):
        self._phone = DataEncryptor.encrypt(value)

    @property
    def address(self) -> Optional[str]:
        return DataEncryptor.decrypt(self._address)

    @address.setter
    def address(self, value: str):
        self._address = DataEncryptor.encrypt(value)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    retailcrm_id = Column(String(50))
    status = Column(String(20), default="new")
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    delivery_method = Column(String(20))
    delivery_time = Column(String(20))
    total_price = Column(Float)
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    price_per_unit = Column(Float)
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)

# Создание таблиц
Base.metadata.create_all(engine)

# Функция для создания тестовых продуктов
def create_sample_products():
    """Создает тестовые продукты в базе данных"""
    session = Session()
    try:
        # Проверяем, есть ли уже продукты
        if session.query(Product).count() > 0:
            return
        
        sample_products = [
            # Сладкие
            Product(
                name="Круассан с шоколадом",
                description="Свежий круассан с бельгийским шоколадом",
                price=4.50,
                category="Сладкие",
                is_special=False,
                rating=4.5,
                ingredients="Мука, масло, шоколад, яйца",
                calories=320,
                preparation_time=45
            ),
            Product(
                name="Эклер ванильный",
                description="Классический эклер с ванильным кремом",
                price=3.80,
                category="Сладкие",
                is_special=True,
                rating=4.7,
                ingredients="Заварное тесто, ванильный крем",
                calories=280,
                preparation_time=60
            ),
            Product(
                name="Штрудель яблочный",
                description="Традиционный штрудель с яблоками и корицей",
                price=5.20,
                category="Сладкие",
                rating=4.3,
                ingredients="Слоеное тесто, яблоки, корица",
                calories=250,
                preparation_time=90
            ),
            
            # Сытные
            Product(
                name="Пирог с мясом",
                description="Сытный пирог с говяжьим фаршем",
                price=6.80,
                category="Сытные",
                rating=4.6,
                ingredients="Тесто, говядина, лук, специи",
                calories=450,
                preparation_time=120
            ),
            Product(
                name="Киш с грибами",
                description="Французский пирог с грибами и сыром",
                price=7.50,
                category="Сытные",
                is_special=True,
                rating=4.8,
                ingredients="Песочное тесто, грибы, сыр, яйца",
                calories=380,
                preparation_time=75
            ),
            Product(
                name="Пирожок с капустой",
                description="Традиционный пирожок с тушеной капустой",
                price=2.90,
                category="Сытные",
                rating=4.2,
                ingredients="Дрожжевое тесто, капуста, морковь",
                calories=220,
                preparation_time=40
            ),
            
            # Торты
            Product(
                name="Торт Наполеон",
                description="Классический торт с заварным кремом",
                price=25.00,
                category="Торты",
                rating=4.9,
                ingredients="Слоеное тесто, заварной крем",
                calories=420,
                preparation_time=180
            ),
            Product(
                name="Чизкейк Нью-Йорк",
                description="Американский чизкейк с ягодами",
                price=18.50,
                category="Торты",
                is_special=True,
                rating=4.7,
                ingredients="Творожный сыр, печенье, ягоды",
                calories=380,
                preparation_time=240
            ),
            Product(
                name="Шоколадный торт",
                description="Многослойный торт с шоколадным кремом",
                price=22.00,
                category="Торты",
                rating=4.8,
                ingredients="Шоколадный бисквит, шоколадный крем",
                calories=500,
                preparation_time=200
            )
        ]
        
        for product in sample_products:
            session.add(product)
        
        session.commit()
        logger.info(f"Создано {len(sample_products)} тестовых продуктов")
        
    except Exception as e:
        logger.error(f"Ошибка при создании продуктов: {e}")
        session.rollback()
    finally:
        session.close()

# Создаем тестовые продукты при запуске
create_sample_products()

# Сервис для работы с RetailCRM
class RetailCRMService:
    @staticmethod
    def create_order(order_data: dict) -> Optional[str]:
        """Создает заказ в RetailCRM и возвращает ID заказа"""
        if not Config.RETAIL_CRM_URL or not Config.RETAIL_CRM_API_KEY:
            logger.warning("RetailCRM не настроен, пропускаем создание заказа")
            return None

        try:
            # Исправлено: убрали дублирование пути /api/v5/
            url = f"{Config.RETAIL_CRM_URL.rstrip('/')}/orders/create"
            response = requests.post(
                url,
                params={"apiKey": Config.RETAIL_CRM_API_KEY},
                json={"order": order_data},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                return data["order"]["id"]
            logger.error(f"RetailCRM error: {data.get('errorMsg')}")
        except Exception as e:
            logger.error(f"RetailCRM connection error: {str(e)}")
        return None

# Клавиатуры
class Keyboards:
    @staticmethod
    def main_menu(user_id: Optional[int] = None) -> ReplyKeyboardMarkup:
        """Главное меню с проверкой админских прав"""
        session = Session()
        is_admin = False
        try:
            if user_id:
                is_admin = session.query(Admin).filter_by(user_id=user_id, is_active=True).first() is not None
        finally:
            session.close()

        buttons = [
            [KeyboardButton(text="🍰 Меню"), KeyboardButton(text="🎁 Акции")],
            [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="⭐ Популярное")],
            [KeyboardButton(text="🚚 Доставка"), KeyboardButton(text="💳 Бонусы")],
            [KeyboardButton(text="📱 Профиль"), KeyboardButton(text="ℹ️ О нас")],
        ]

        if is_admin:
            buttons.extend([
                [KeyboardButton(text="📋 Заказы"), KeyboardButton(text="📊 Статистика")],
            ])

        return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    @staticmethod
    def categories() -> InlineKeyboardMarkup:
        """Клавиатура с категориями товаров"""
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="🍪 Сладкие", callback_data="category_sweet"),
            InlineKeyboardButton(text="🥧 Сытные", callback_data="category_savory"),
            InlineKeyboardButton(text="🎂 Торты", callback_data="category_cakes"),
            InlineKeyboardButton(text="🔥 Хиты", callback_data="category_popular"),
            InlineKeyboardButton(text="🌟 Новинки", callback_data="category_new"),
        )
        builder.adjust(2)
        return builder.as_markup()

# Обработчик для добавления продуктов (только для админов)
@dp.message(Command("add_products"))
async def add_products_command(message: types.Message):
    """Команда для добавления тестовых продуктов (только для админов)"""
    session = Session()
    try:
        # Проверяем, является ли пользователь админом
        admin = session.query(Admin).filter_by(
            user_id=message.from_user.id, 
            is_active=True
        ).first()
        
        if not admin:
            await message.answer("❌ У вас нет прав для выполнения этой команды")
            return
        
        # Удаляем все существующие продукты
        session.query(Product).delete()
        session.commit()
        
        # Создаем новые продукты
        create_sample_products()
        
        await message.answer("✅ Продукты успешно добавлены в базу данных!")
        
    finally:
        session.close()

# Команда для добавления админа
@dp.message(Command("make_admin"))
async def make_admin_command(message: types.Message):
    """Команда для назначения админа (временная, для первоначальной настройки)"""
    session = Session()
    try:
        # Проверяем, есть ли уже админы
        admin_count = session.query(Admin).count()
        
        # Если админов нет, делаем первого пользователя админом
        if admin_count == 0:
            new_admin = Admin(user_id=message.from_user.id, is_active=True)
            session.add(new_admin)
            session.commit()
            await message.answer("✅ Вы назначены администратором!")
        else:
            await message.answer("❌ Админы уже существуют")
            
    finally:
        session.close()

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username
            )
            session.add(user)
            session.commit()
            await message.answer(
                "Добро пожаловать! 🎉\n\n"
                "Для оформления заказов нам нужен ваш номер телефона.\n"
                "Пожалуйста, введите номер в формате: +375-XX-XXX-XX-XX",
                parse_mode="HTML"
            )
            return

        welcome_text = (
            f"Привет, {user.username or 'друг'}! 👋\n"
            f"💰 Ваши бонусы: {user.bonus_points}\n\n"
            "Выберите раздел:"
        )
        
        await message.answer(
            welcome_text,
            reply_markup=Keyboards.main_menu(message.from_user.id)
        )
    finally:
        session.close()

@dp.message(F.text == "🍰 Меню")
async def show_menu(message: types.Message):
    session = Session()
    products = session.query(Product).all()
    if not products:
        await message.answer("Меню пусто.")
    else:
        for product in products:
            await message.answer(
                f"{product.name}\n{product.description}\nЦена: {product.price} руб."
            )
    session.close()

@dp.message(F.text == "🎁 Акции")
async def show_promotions(message: types.Message):
    """Показывает акции и специальные предложения"""
    await message.answer("🎁 <b>Акции и специальные предложения:</b>\n\nСкоро будут доступны!")

@dp.message(F.text == "⭐ Популярное")
async def show_popular(message: types.Message):
    """Показывает популярные товары"""
    session = Session()
    try:
        products = session.query(Product).filter(Product.rating >= 4.0).limit(10).all()
        
        if not products:
            await message.answer("Популярные товары отсутствуют")
            return
        
        text = "⭐ <b>Популярное:</b>\n\n"
        for product in products:
            text += (
                f"🍰 <b>{product.name}</b>\n"
                f"💰 Цена: {product.final_price:.2f} BYN\n"
                f"⭐ Рейтинг: {product.rating}/5\n"
                f"⏱ Время приготовления: {product.preparation_time} мин\n\n"
            )
        
        await message.answer(text, parse_mode="HTML")
    finally:
        session.close()

@dp.message(F.text == "🚚 Доставка")
async def show_delivery_info(message: types.Message):
    """Показывает информацию о доставке"""
    await message.answer(
        "🚚 <b>Доставка:</b>\n\n"
        "Мы предлагаем быструю и удобную доставку прямо к вашей двери.\n"
        "Стоимость доставки составляет 8 BYN, бесплатная доставка при заказе от 80 BYN.\n\n"
        "Время доставки: 12:00 - 18:00\n"
        "Пожалуйста, убедитесь, что указанный адрес доставки доступен для курьера.",
        parse_mode="HTML"
    )

@dp.message(F.text == "💳 Бонусы")
async def show_bonus_info(message: types.Message):
    """Показывает информацию о бонусах"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            await message.answer("Сначала зарегистрируйтесь через /start")
            return
        
        await message.answer(
            f"💳 <b>Ваши бонусы:</b> {user.bonus_points}\n\n"
            "Бонусы можно использовать для получения скидок на заказы.\n"
            "1 бонус = 1 рубль скидки.\n\n"
            "Накопите больше бонусов, делая заказы и приглашая друзей!",
            parse_mode="HTML"
        )
    finally:
        session.close()

@dp.message(F.text == "📱 Профиль")
async def show_profile(message: types.Message):
    """Показывает информацию о пользователе и его заказы"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            await message.answer("Сначала зарегистрируйтесь через /start")
            return
        
        # Получаем последние 5 заказов пользователя
        orders = session.query(Order).filter_by(user_id=user.id).order_by(Order.created_at.desc()).limit(5).all()
        
        orders_text = ""
        for order in orders:
            orders_text += (
                f"🛒 Заказ #{order.id} - {order.status}\n"
                f"💰 Сумма: {order.total_price:.2f} BYN\n"
                f"🕒 Дата: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )
        
        if not orders_text:
            orders_text = "У вас пока нет заказов."
        
        await message.answer(
            f"👤 <b>Профиль пользователя:</b>\n\n"
            f"Имя: {user.username or 'Не указано'}\n"
            f"Телефон: {user.phone or 'Не указан'}\n"
            f"Адрес: {user.address or 'Не указан'}\n\n"
            "📋 <b>Ваши заказы:</b>\n" + orders_text,
            parse_mode="HTML"
        )
    finally:
        session.close()

@dp.message(F.text == "ℹ️ О нас")
async def show_about(message: types.Message):
    """Показывает информацию о компании"""
    await message.answer(
        "ℹ️ <b>О нас:</b>\n\n"
        "Мы - команда энтузиастов, которая любит выпечку и хочет делиться ею с вами.\n"
        "Наша пекарня предлагает широкий выбор свежей и вкусной выпечки, приготовленной с любовью.\n\n"
        "Мы используем только качественные ингредиенты и традиционные рецепты, чтобы каждая булочка, торт или пирог были настоящим произведением искусства.\n\n"
        "Спасибо, что выбираете нас! Мы ценим каждого клиента и стремимся сделать ваш день слаще.",
        parse_mode="HTML"
    )

# Обработчик для категорий товаров
@dp.callback_query(F.data.startswith("category_"))
async def show_category(callback: CallbackQuery):
    """Показывает товары выбранной категории"""
    category = callback.data.split("_")[1]
    session = Session()
    try:
        # Маппинг категорий
        category_map = {
            "sweet": "Сладкие",
            "savory": "Сытные", 
            "cakes": "Торты",
            "popular": None,  # Популярные товары
            "new": None  # Новинки
        }
        
        if category == "popular":
            products = session.query(Product).filter(Product.rating >= 4.0).limit(10).all()
        elif category == "new":
            products = session.query(Product).filter(Product.is_special == True).limit(10).all()
        else:
            products = session.query(Product).filter(Product.category == category_map[category]).all()
        
        if not products:
            await callback.message.answer("В этой категории пока нет товаров")
            return
        
        for product in products:
            text = (
                f"🍰 <b>{product.name}</b>\n"
                f"💰 Цена: {product.final_price:.2f} BYN\n"
                f"⭐ Рейтинг: {product.rating}/5\n"
                f"⏱ Время приготовления: {product.preparation_time} мин"
            )
            
            if product.description:
                text += f"\n📝 {product.description}"
            
            # Кнопки для добавления в корзину
            builder = InlineKeyboardBuilder()
            builder.add(
                InlineKeyboardButton(
                    text="➕ В корзину", 
                    callback_data=f"add_to_cart_{product.id}"
                )
            )
            
            await callback.message.answer(
                text,
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )
    finally:
        session.close()
    
    await callback.answer()

# Обработчик добавления в корзину
@dp.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart(callback: CallbackQuery):
    """Добавляет товар в корзину"""
    product_id = int(callback.data.split("_")[3])
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        product = session.query(Product).filter_by(id=product_id).first()
        
        if not user or not product:
            await callback.answer("Ошибка при добавлении товара", show_alert=True)
            return
        
        # Находим или создаем корзину (заказ со статусом cart)
        cart_order = session.query(Order).filter_by(
            user_id=user.id, 
            status="cart"
        ).first()
        
        if not cart_order:
            cart_order = Order(user_id=user.id, status="cart")
            session.add(cart_order)
            session.commit()
        
        # Проверяем, есть ли уже этот товар в корзине
        existing_item = session.query(OrderItem).filter_by(
            order_id=cart_order.id,
            product_id=product_id
        ).first()
        
        if existing_item:
            existing_item.quantity += 1
        else:
            new_item = OrderItem(
                order_id=cart_order.id,
                product_id=product_id,
                quantity=1,
                price_per_unit=product.final_price
            )
            session.add(new_item)
        
        session.commit()
        await callback.answer(f"✅ {product.name} добавлен в корзину!")
        
    finally:
        session.close()

# Обработчик показа корзины
@dp.message(F.text == "🛒 Корзина")
async def show_cart(message: types.Message):
    """Показывает содержимое корзины"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            await message.answer("Сначала зарегистрируйтесь через /start")
            return
        
        # Находим корзину
        cart_order = session.query(Order).filter_by(
            user_id=user.id,
            status="cart"
        ).first()
        
        if not cart_order:
            await message.answer("Ваша корзина пуста")
            return
        
        cart_items = session.query(OrderItem).filter_by(order_id=cart_order.id).all()
        
        if not cart_items:
            await message.answer("Ваша корзина пуста")
            return
        
        total = 0
        text = "🛒 <b>Ваша корзина:</b>\n\n"
        
        for item in cart_items:
            item_total = item.price_per_unit * item.quantity
            total += item_total
            text += (
                f"• {item.product.name}\n"
                f"  {item.quantity} шт. × {item.price_per_unit:.2f} = {item_total:.2f} BYN\n\n"
            )
        
        delivery_cost = 0 if total >= Config.FREE_DELIVERY_THRESHOLD else Config.DELIVERY_COST
        final_total = total + delivery_cost
        
        text += f"💰 <b>Сумма товаров:</b> {total:.2f} BYN\n"
        text += f"🚚 <b>Доставка:</b> {'Бесплатно' if delivery_cost == 0 else f'{delivery_cost} BYN'}\n"
        text += f"💳 <b>Итого:</b> {final_total:.2f} BYN"
        
        # Кнопки для оформления заказа
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="✅ Оформить заказ", callback_data="confirm_order"),
            InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")
        )
        builder.adjust(1)
        
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
    finally:
        session.close()

# Обработчик оформления заказа
@dp.callback_query(F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery):
    """Подтверждение и создание заказа"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        if not user or not user.phone:
            await callback.answer("Для заказа нужен номер телефона!", show_alert=True)
            return

        # Получаем корзину
        cart_order = session.query(Order).filter_by(
            user_id=user.id,
            status="cart"
        ).first()

        if not cart_order:
            await callback.answer("Корзина пуста!", show_alert=True)
            return

        cart_items = session.query(OrderItem).filter_by(order_id=cart_order.id).all()

        if not cart_items:
            await callback.answer("Корзина пуста!", show_alert=True)
            return

        # Рассчитываем стоимость
        total = sum(item.price_per_unit * item.quantity for item in cart_items)
        delivery_cost = 0 if total >= Config.FREE_DELIVERY_THRESHOLD else Config.DELIVERY_COST
        order_total = total + delivery_cost

        # Обновляем заказ
        cart_order.status = "processing"
        cart_order.total_price = order_total
        cart_order.delivery_method = "delivery"
        cart_order.delivery_time = "12:00-18:00"
        cart_order.created_at = datetime.now()
        
        session.commit()

        # Формируем данные для RetailCRM
        order_data = {
            "firstName": user.username or "Клиент",
            "phone": user.phone,
            "email": "",
            "customerComment": "Заказ из Telegram бота",
            "orderMethod": "telegram-bot",
            "status": "new",
            "items": [
                {
                    "offer": {"externalId": str(item.product_id)},
                    "productName": item.product.name,
                    "quantity": item.quantity,
                    "initialPrice": item.price_per_unit,
                }
                for item in cart_items
            ],
            "delivery": {
                "code": "courier",
                "cost": delivery_cost,
                "address": {"text": user.address or "Не указан"},
            },
            "customFields": {
                "telegram_user_id": str(user.telegram_id)
            }
        }

        # Отправляем в RetailCRM
        retailcrm_id = RetailCRMService.create_order(order_data)
        if retailcrm_id:
            cart_order.retailcrm_id = retailcrm_id
            cart_order.status = "completed"
            session.commit()
            await callback.message.answer(
                f"✅ Заказ #{cart_order.id} оформлен!\n"
                f"💰 Сумма: {order_total:.2f} BYN\n"
                f"🚚 Доставка: {'Бесплатно' if delivery_cost == 0 else f'{delivery_cost} BYN'}\n\n"
                "Мы свяжемся с вами для подтверждения!"
            )
        else:
            await callback.message.answer(
                "⚠️ Заказ создан, но не синхронизирован с CRM.\n"
                "Администратор свяжется с вами для уточнения деталей."
            )
    except Exception as e:
        logger.error(f"Order processing error: {e}")
        await callback.message.answer("Произошла ошибка при оформлении заказа")
    finally:
        session.close()
    
    await callback.answer()

# Обработчик очистки корзины
@dp.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
    """Очищает корзину"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        
        if user:
            cart_order = session.query(Order).filter_by(
                user_id=user.id,
                status="cart"
            ).first()
            
            if cart_order:
                # Удаляем все товары из корзины
                session.query(OrderItem).filter_by(order_id=cart_order.id).delete()
                # Удаляем саму корзину
                session.delete(cart_order)
                session.commit()
        
        await callback.message.answer("🗑 Корзина очищена")
        
    finally:
        session.close()
    
    await callback.answer()

# Обработчик ввода номера телефона
@dp.message(F.text.regexp(r'^\+375-\d{2}-\d{3}-\d{2}-\d{2}$'))
async def set_phone_number(message: types.Message):
    """Сохраняет номер телефона пользователя"""
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if user:
            user.phone = message.text
            session.commit()
            
            await message.answer(
                "✅ Номер телефона сохранен!\n\n"
                "Теперь вы можете оформлять заказы.",
                reply_markup=Keyboards.main_menu(message.from_user.id)
            )
        else:
            await message.answer("Сначала выполните команду /start")
            
    finally:
        session.close()

# Запуск бота
async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)
# ... (весь ваш предыдущий код: импорты, настройки, классы, обработчики)

async def main():
    """Основная асинхронная функция для запуска бота"""
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Bot stopped with error: {str(e)}")
    finally:
        await bot.session.close()

# ... (весь ваш предыдущий код: импорты, настройки, классы, обработчики)

async def main():
    """Основная асинхронная функция для запуска бота"""
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Bot stopped with error: {str(e)}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
import os