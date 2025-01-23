
import asyncio
import paramiko
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

API_TOKEN = '7519534898:AAEh9ipKjxTxvJ6C5mZ5cEzOKGR537kTxCI'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Данные для подключения к Raspberry Pi
RPI_HOST = '192.168.156.90'
RPI_USER = 'raspberrypi'
RPI_PASS = 'pi'
DB_PATH = '/home/pi/sqrunner.db'

# Определение состояний
class ProductState(StatesGroup):
    type = State()
    name = State()
    date = State()

# Главное меню с кнопками
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Список товаров"), KeyboardButton(text="Админ панель")]
    ],
    resize_keyboard=True
)

# Админ панель
admin_panel = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Вывести полную базу данных")],
        [KeyboardButton(text="Удалить товар по ID")],
        [KeyboardButton(text="Добавить товар")],
        [KeyboardButton(text="Выйти")]
    ],
    resize_keyboard=True
)

admin_password = "1234"
admin_users = set()

async def execute_sql_query(query):
    try:
        await asyncio.sleep(1)
        print("Подключение к Raspberry Pi...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(RPI_HOST, username=RPI_USER, password=RPI_PASS)
        print("Успешное подключение к SSH")
        command = f"sqlite3 {DB_PATH} \"{query}\""
        print(f"Выполнение запроса: {query}")
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        ssh.close()
        if error:
            print(f"Ошибка выполнения запроса: {error}")
            return f"Ошибка: {error}"
        print("Запрос выполнен успешно")
        return output.strip() if output else "Нет данных."
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return f"Ошибка подключения: {e}"

@dp.message(Command("start"))
async def send_welcome(message: Message):
    await message.answer("Привет! Выберите действие:", reply_markup=main_menu)

@dp.message(lambda message: message.text == "Список товаров")
async def show_products(message: Message):
    await message.answer("Пожалуйста, подождите... Подключение к базе данных.")
    result = await execute_sql_query("SELECT name FROM sqlite_master WHERE type='table';")
    await message.answer(f"Таблицы в базе данных:\n{result}")

@dp.message(lambda message: message.text == "Админ панель")
async def admin_access(message: Message):
    await message.answer("Введите пароль для входа в админ панель:")

@dp.message(lambda message: message.text == admin_password)
async def check_password(message: Message):
    admin_users.add(message.from_user.id)
    await message.answer("Доступ разрешен. Выберите действие:", reply_markup=admin_panel)

@dp.message(lambda message: message.text == "Выйти")
async def exit_admin_panel(message: Message):
    if message.from_user.id in admin_users:
        admin_users.remove(message.from_user.id)
    await message.answer("Вы вышли из админ панели.", reply_markup=main_menu)

@dp.message(lambda message: message.text == "Добавить товар")
async def add_product_start(message: Message, state: FSMContext):
    await message.answer("Введите тип товара:")
    await state.set_state(ProductState.type)

@dp.message(ProductState.type)
async def get_product_type(message: Message, state: FSMContext):
    await state.update_data(type=message.text)
    await message.answer("Введите имя товара:")
    await state.set_state(ProductState.name)

@dp.message(ProductState.name)
async def get_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите дату (ГГГГ-ММ-ДД):")
    await state.set_state(ProductState.date)

@dp.message(ProductState.date)
async def save_product(message: Message, state: FSMContext):
    data = await state.get_data()
    product_type = data['type']
    product_name = data['name']
    product_date = message.text
    query = f"INSERT INTO products (type, name, date) VALUES ('{product_type}', '{product_name}', '{product_date}')"
    result = await execute_sql_query(query)
    await message.answer(f"Товар добавлен:\nТип: {product_type}\nИмя: {product_name}\nДата: {product_date}\n{result}", reply_markup=admin_panel)
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
