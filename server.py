import asyncio
import logging
from datetime import datetime
import requests
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from config import TOKEN, users, CHANNEL_ID, questions, Anketa, answers, API_ID, API_HASH
from fill_db import fill_questions, db_cleanup
from pyrogram import Client
import pandas as pd

db_cleanup()
fill_questions()

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)
dp.middleware.setup(LoggingMiddleware())
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=TOKEN)


menu_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
for i in range(5, 0, -1):
    menu_keyboard.add(KeyboardButton(str(i)))


async def wait_until(dt):
    now = datetime.now()
    if dt > now:
        await asyncio.sleep((dt - now).total_seconds())
    else:
        await asyncio.sleep(1)


async def scheduler(dt, coro):
    await wait_until(dt)
    return await coro


async def on_startup(_):
    # ждем начала опроса
    asyncio.create_task(scheduler(datetime(2021, 9, 8, 17, 52), send_start_message()))


async def send_start_message():
    # присылаем сообщение в канал о том, что голосование можно пройти в нашем боте
    requests.get(f'https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHANNEL_ID}&text=Вы успешно прошли обучение! Можете оставить свой отзыв нашему боту @San_School_Test_Bot. Переходите и нажимайте /start')


@dp.message_handler(commands=["help"])
async def help(message: types.Message):
    await bot.send_message(message.chat.id, "Привет! Я - бот школы корейского языка San, создан для того, чтобы производить оценку обучения! Мои команды:\n"
                                            "/start - для начала оценки, \n"
                                            "/report - для получения отчета по оценкам (только для администраторов)")


@dp.message_handler(commands=["start"])
async def welcome(message: types.Message):
    user = users.find_one({"_id": message.chat.id})
    if not user:
        await bot.send_message(
            message.chat.id,
            f"<b>Добро пожаловать, {message.from_user.username}!</b>\n\n"
            f"К сожалению, могут принять только участники недели корейского языка",
            parse_mode=ParseMode.HTML
        )
    else:
        if not answers.find_one({'user_id': message.chat.id}):
            await bot.send_message(message.chat.id, "Пожалуйста, ответьте на вопросы по шкале от 1 до 5, где 1 - не очень хорошо, 5 - отлично.")
            await bot.send_message(message.chat.id, questions.find_one({'_id': 0})['text'], reply_markup=menu_keyboard)
            await Anketa.q1.set()
        else:
            await bot.send_message(message.chat.id, "Участие в оценке можно принять только один раз!")


@dp.message_handler(state=Anketa.q1, content_types=types.ContentTypes.TEXT)
async def ask_q2(message: types.Message, state: FSMContext):
    await state.update_data(q1=message.text)
    answers.insert_one({"user_id": message.chat.id, "question": 0, "answer": int(message.text)})
    await bot.send_message(
        message.chat.id, questions.find_one({'_id': 1})['text'], reply_markup=menu_keyboard
    )
    await Anketa.q2.set()


@dp.message_handler(state=Anketa.q2, content_types=types.ContentTypes.TEXT)
async def ask_q3(message: types.Message, state: FSMContext):
    await state.update_data(q2=message.text)
    answers.insert_one({"user_id": message.chat.id, "question": 1, "answer": int(message.text)})
    await bot.send_message(
        message.chat.id, questions.find_one({'_id': 2})['text'], reply_markup=menu_keyboard
    )
    await Anketa.q3.set()


@dp.message_handler(state=Anketa.q3, content_types=types.ContentTypes.TEXT)
async def ask_comment(message: types.Message, state: FSMContext):
    await state.update_data(q3=message.text)
    answers.insert_one({"user_id": message.chat.id, "question": 2, "answer": int(message.text)})
    await bot.send_message(
        message.chat.id, questions.find_one({'_id': "free_comment"})['text'], reply_markup=types.ReplyKeyboardRemove()
    )
    await Anketa.comment.set()


@dp.message_handler(state=Anketa.comment, content_types=types.ContentTypes.TEXT)
async def get_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    answers.insert_one({"user_id": message.chat.id, "answer": message.text, "question": "free_comment"})
    await bot.send_message(
        message.chat.id, "Спасибо за участие!", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.finish()


@dp.message_handler(commands=["report"])
async def report(message: types.Message):
    if user := users.find_one({'_id': message.chat.id}):
        if user['status'] in ['administrator', 'creator']:
            await bot.send_message(message.chat.id, "Лови отчет!")
            avg_rate = {}
            all_q = questions.find({})
            for q in all_q:
                if q["_id"] != "free_comment":
                    q_answers = [answer['answer']for answer in answers.find({"question": q["_id"]})]
                    avg_rate[q['text']] = sum(q_answers)/len(q_answers)
            pretty_rates = "\n".join([f"{key} {round(value, 2)}" for key, value in avg_rate.items()])
            await bot.send_message(message.chat.id, f"Средние баллы за вопросы:\n {pretty_rates}")
            dict_results = {'Участники': ['Насколько Вам понравились уроки?', 'Оцените качество заданий:', 'Оцените сложность выполнения заданий:', 'Комментарий']}
            for user in users.find({}):
                if user["name"] != 'SanTestBot':
                    answer_list = []
                    for q in questions.find({}):
                        if answer := answers.find_one({'question': q['_id'], "user_id": user['_id']}):
                            answer_list.append(answer['answer'])
                        else:
                            answer_list.append('')
                    name_list = []
                    for i in ['username', 'name', '_id']:
                        if user[i]:
                            name_list.append(user[i] if isinstance(user[i], str) else str(user[i]))
                    dict_results[', '.join(name_list)] = answer_list
            df = pd.DataFrame.from_dict(dict_results, orient='index')
            await bot.send_document(message.chat.id, ('report.csv', df.to_csv(header=False)))
        else:
            await bot.send_message(message.chat.id, "У вас недостаточно прав для доступа к отчету. Обратитесь к администратору канала.")


if __name__ == "__main__":
    # записываем всех пользователей канала
    with app:
        for member in app.iter_chat_members(CHANNEL_ID):
            users.insert_one({'_id': member.user.id, 'name': member.user.first_name, 'status': member.status, 'username': member.user.username})
    executor.start_polling(dp, on_startup=on_startup)