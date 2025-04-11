import asyncio
import logging
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv("BOT_TOKEN"))
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
    discount = Column(Float, default=0.0)  # Добавляем поле для скидки


class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    product_id = Column(Integer)
    quantity = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String, default='pending')


class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    is_active = Column(Boolean, default=True)

# Создание таблиц
Base.metadata.create_all(engine)

# Клавиатуры
def get_main_keyboard(user_id=None):
    session = Session()
    is_admin = False
    if user_id:
        admin = session.query(Admin).filter_by(user_id=user_id, is_active=True).first()
        is_admin = bool(admin)
    session.close()

    keyboard = [
        [KeyboardButton(text="🍰 Меню")],
        [KeyboardButton(text="🎁 Акции")],
        [KeyboardButton(text="🛒 Корзина")],
        [KeyboardButton(text="🚚 Условия доставки")],
        [KeyboardButton(text="ℹ️ О нас")]
    ]

    if is_admin:
        keyboard.extend([
            [KeyboardButton(text="📋 Заказы")],
            [KeyboardButton(text="🧺 Корзины")]
        ])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_category_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🍪 Сладкие пироги", callback_data="category_sweet"))
    keyboard.add(InlineKeyboardButton(text="🥧 Сытные пироги", callback_data="category_savory"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    return keyboard.adjust(2).as_markup()

def get_products_keyboard(category):
    session = Session()
    products = session.query(Product).filter_by(category=category).all()
    keyboard = InlineKeyboardBuilder()
    
    for product in products:
        # Учитываем скидку при отображении цены
        display_price = product.price * (1 - product.discount) if product.discount > 0 else product.price
        price_text = f"{display_price:.2f} руб."
        if product.discount > 0:
            price_text += f" (-{int(product.discount * 100)}%)"
        
        keyboard.add(InlineKeyboardButton(
            text=f"{product.name} - {price_text}",
            callback_data=f"product_{product.id}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back"))
    session.close()
    return keyboard.adjust(1).as_markup()

def get_cart_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    return keyboard.adjust(1).as_markup()

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать в нашу пекарню! 🥖\n"
        "Выберите интересующий вас раздел:",
        reply_markup=get_main_keyboard(message.from_user.id)
    )

@dp.message(lambda message: message.text == "🍰 Меню")
async def show_menu(message: types.Message):
    await message.answer(
        "Выберите категорию пирогов:",
        reply_markup=get_category_keyboard()
    )

@dp.message(lambda message: message.text == "🎁 Акции")
async def show_specials(message: types.Message):
    session = Session()
    special_product = session.query(Product).filter_by(is_special=1).first()
    if special_product:
        await message.answer(
            f"🎉 Специальное предложение!\n\n"
            f"{special_product.name}\n"
            f"{special_product.description}\n"
            f"Цена: {special_product.price * 0.8:.2f} руб. (скидка 20%)"
        )
    else:
        await message.answer("К сожалению, специальных предложений нет.")
    session.close()

@dp.message(lambda message: message.text == "🛒 Корзина")
async def show_cart(message: types.Message):
    session = Session()
    orders = session.query(Order).filter_by(user_id=message.from_user.id, status='pending').all()
    
    if not orders:
        await message.answer("В корзине ничего нет")
        return
    
    total = 0
    cart_text = "Ваша корзина:\n\n"
    
    for order in orders:
        product = session.query(Product).get(order.product_id)
        cart_text += f"{product.name} - {order.quantity} шт. x {product.price} руб.\n"
        total += product.price * order.quantity
    
    cart_text += f"\nИтого: {total} руб."
    
    await message.answer(cart_text, reply_markup=get_cart_keyboard())
    session.close()

@dp.message(lambda message: message.text == "🚚 Условия доставки")
async def show_delivery_info(message: types.Message):
    await message.answer(
        "Вам нужно выбрать позиции из меню, и мы доставим вам в любую точку города в течение часа ваш заказ."
    )

@dp.message(lambda message: message.text == "ℹ️ О нас")
async def show_about(message: types.Message):
    await message.answer(
        "Добро пожаловать в нашу пекарню! 🥖\n\n"
        "Мы - семейная пекарня с многолетней историей, где каждый пирог создается с любовью и заботой. "
        "Используем только натуральные ингредиенты и традиционные рецепты. "
        "Наша миссия - радовать вас вкусной и качественной выпечкой каждый день!"
    )

# Обработчики callback-запросов
@dp.callback_query(lambda c: c.data.startswith('category_'))
async def process_category(callback: types.CallbackQuery):
    category = callback.data.split('_')[1]
    await callback.message.edit_text(
        "Выберите пирог:",
        reply_markup=get_products_keyboard(category)
    )

@dp.callback_query(lambda c: c.data.startswith('product_'))
async def process_product(callback: types.CallbackQuery):
    product_id = int(callback.data.split('_')[1])
    session = Session()
    product = session.query(Product).get(product_id)
    
    # Сохраняем текущее состояние в историю
    user_id = callback.from_user.id
    if user_id not in user_navigation_history:
        user_navigation_history[user_id] = []
    user_navigation_history[user_id].append(('category', product.category))
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="➕ Добавить в корзину", callback_data=f"add_{product_id}"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back"))
    
    # Учитываем скидку при отображении цены
    display_price = product.price * (1 - product.discount) if product.discount > 0 else product.price
    price_text = f"{display_price:.2f} руб."
    if product.discount > 0:
        price_text += f" (-{int(product.discount * 100)}%)"
    
    # Отправляем фотографию продукта
    await callback.message.answer_photo(
        photo=product.image_url,
        caption=f"{product.name}\n\n"
                f"{product.description}\n\n"
                f"Цена: {price_text}",
        reply_markup=keyboard.adjust(1).as_markup()
    )
    
    # Удаляем предыдущее сообщение
    await callback.message.delete()
    
    session.close()

@dp.callback_query(lambda c: c.data == 'checkout')
async def process_checkout(callback: types.CallbackQuery):
    session = Session()
    orders = session.query(Order).filter_by(user_id=callback.from_user.id, status='pending').all()
    
    if not orders:
        await callback.answer("Корзина пуста!")
        return
    
    # Обновляем статус заказов
    for order in orders:
        order.status = 'completed'
    
    session.commit()
    session.close()
    
    delivery_time = datetime.now() + timedelta(seconds=5)
    
    await callback.message.edit_text(
        "Ваш заказ оформлен! 🎉\n"
        f"Ожидайте доставку в {delivery_time.strftime('%H:%M:%S')}"
    )
    
    # Имитация доставки через 5 секунд
    await asyncio.sleep(5)
    await callback.message.answer("Спасибо, что выбрали нас! Ваш заказ доставлен. 🎉")

@dp.callback_query(lambda c: c.data == 'back')
async def handle_back(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Если у пользователя есть история навигации
    if user_id in user_navigation_history and user_navigation_history[user_id]:
        # Получаем последнее состояние и удаляем его из истории
        last_state = user_navigation_history[user_id].pop()
        
        if last_state[0] == 'category':
            # Возвращаемся к выбору категории
            await callback.message.edit_text(
                "Выберите категорию пирогов:",
                reply_markup=get_category_keyboard()
            )
        elif last_state[0] == 'main':
            # Возвращаемся в главное меню
            await callback.message.edit_text(
                "Выберите интересующий вас раздел:",
                reply_markup=get_main_keyboard(callback.from_user.id)
            )
    else:
        # Если истории нет, возвращаемся в главное меню
        await callback.message.edit_text(
            "Выберите интересующий вас раздел:",
            reply_markup=get_main_keyboard(callback.from_user.id)
        )

@dp.callback_query(lambda c: c.data == 'back_to_main')
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите интересующий вас раздел:",
        reply_markup=get_main_keyboard(callback.from_user.id)
    )

@dp.callback_query(lambda c: c.data == 'back_to_categories')
async def back_to_categories(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите категорию пирогов:",
        reply_markup=get_category_keyboard()
    )

# Новые обработчики для администратора
@dp.message(lambda message: message.text == "📋 Заказы")
async def show_orders(message: types.Message):
    session = Session()
    admin = session.query(Admin).filter_by(user_id=message.from_user.id, is_active=True).first()
    
    if not admin:
        await message.answer("У вас нет прав администратора")
        return
    
    orders = session.query(Order).filter_by(status='completed').all()
    
    if not orders:
        await message.answer("Нет оформленных заказов")
        return
    
    orders_text = "Список оформленных заказов:\n\n"
    for order in orders:
        product = session.query(Product).get(order.product_id)
        orders_text += (
            f"Заказ #{order.id}\n"
            f"Пользователь: {order.user_id}\n"
            f"Товар: {product.name}\n"
            f"Количество: {order.quantity}\n"
            f"Дата: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Статус: {order.status}\n\n"
        )
    
    await message.answer(orders_text)
    session.close()

@dp.message(lambda message: message.text == "🧺 Корзины")
async def show_carts(message: types.Message):
    session = Session()
    admin = session.query(Admin).filter_by(user_id=message.from_user.id, is_active=True).first()
    
    if not admin:
        await message.answer("У вас нет прав администратора")
        return
    
    # Получаем все активные корзины (заказы со статусом pending)
    carts = session.query(Order).filter_by(status='pending').all()
    
    if not carts:
        await message.answer("Нет активных корзин")
        return
    
    carts_text = "Список активных корзин:\n\n"
    for cart in carts:
        product = session.query(Product).get(cart.product_id)
        carts_text += (
            f"Корзина пользователя: {cart.user_id}\n"
            f"Товар: {product.name}\n"
            f"Количество: {cart.quantity}\n"
            f"Дата добавления: {cart.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )
    
    await message.answer(carts_text)
    session.close()

async def update_special_offers():
    """Обновляет акции каждый час"""
    while True:
        try:
            session = Session()
            
            # Сбрасываем все текущие акции
            session.query(Product).update({Product.is_special: 0, Product.discount: 0.0})
            
            # Выбираем случайный продукт для акции
            all_products = session.query(Product).all()
            if all_products:
                special_product = random.choice(all_products)
                special_product.is_special = 1
                special_product.discount = 0.2  # 20% скидка
            
            session.commit()
            session.close()
            
            # Ждем 1 час перед следующим обновлением
            await asyncio.sleep(3600)
        except Exception as e:
            logging.error(f"Ошибка при обновлении акций: {e}")
            await asyncio.sleep(60)  # В случае ошибки ждем 1 минуту перед повторной попыткой

# Запуск бота
async def main():
    # Запускаем обновление акций в фоновом режиме
    asyncio.create_task(update_special_offers())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 