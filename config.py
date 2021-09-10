from aiogram.dispatcher.filters.state import StatesGroup, State
from environs import Env
from pymongo import MongoClient

env = Env()
env.read_env()

CLUSTER_CONF = env('CLUSTER_CONF')
TOKEN = env('TOKEN')
CHANNEL_ID = env.int('CHANNEL_ID')
API_ID = env.int('API_ID')
API_HASH = env('API_HASH')

cluster = MongoClient(CLUSTER_CONF)
db = cluster["python_bot"]
users = db["bot_users"]
questions = db["questions"]
answers = db["answers"]


class Anketa(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    comment = State()
