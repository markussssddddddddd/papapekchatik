import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
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

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    product_id = Column(Integer)
    quantity = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String, default='pending')

# Создание таблиц
Base.metadata.create_all(engine)

# Клавиатуры
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍰 Меню")],
            [KeyboardButton(text="🎁 Акции")],
            [KeyboardButton(text="🛒 Корзина")],
            [KeyboardButton(text="🚚 Условия доставки")],
            [KeyboardButton(text="ℹ️ О нас")]
        ],
        resize_keyboard=True
    )
    return keyboard

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
        keyboard.add(InlineKeyboardButton(
            text=f"{product.name} - {product.price} руб.",
            callback_data=f"product_{product.id}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_categories"))
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
        reply_markup=get_main_keyboard()
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
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="➕ Добавить в корзину", callback_data=f"add_{product_id}"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_categories"))
    
    await callback.message.edit_text(
        f"{product.name}\n\n"
        f"{product.description}\n\n"
        f"Цена: {product.price} руб.",
        reply_markup=keyboard.adjust(1).as_markup()
    )
    session.close()

@dp.callback_query(lambda c: c.data.startswith('add_'))
async def add_to_cart(callback: types.CallbackQuery):
    product_id = int(callback.data.split('_')[1])
    session = Session()
    
    # Проверяем, есть ли уже такой товар в корзине
    existing_order = session.query(Order).filter_by(
        user_id=callback.from_user.id,
        product_id=product_id,
        status='pending'
    ).first()
    
    if existing_order:
        existing_order.quantity += 1
    else:
        new_order = Order(
            user_id=callback.from_user.id,
            product_id=product_id,
            quantity=1
        )
        session.add(new_order)
    
    session.commit()
    session.close()
    
    await callback.answer("Товар добавлен в корзину!")

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

@dp.callback_query(lambda c: c.data == 'back_to_main')
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите интересующий вас раздел:",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(lambda c: c.data == 'back_to_categories')
async def back_to_categories(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите категорию пирогов:",
        reply_markup=get_category_keyboard()
    )

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 