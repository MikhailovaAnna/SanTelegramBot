from config import users, questions


def fill_questions():
    questions.insert_one(
        {
            "_id": 0,
            "text": "Насколько Вам понравились уроки?"
        })
    questions.insert_one(
        {
            "_id": 1,
            "text": "Оцените качество заданий:"
        }
    )
    questions.insert_one(
        {
            "_id": 2,
            "text": "Оцените сложность выполнения заданий:"
        }
    )
    questions.insert_one(
        {
            "_id": 'free_comment',
            "text": "Оставьте, пожалуйста, свободный комментарий, если хотите что-то добавить!"
        }
    )


def db_cleanup():
    users.delete_many({})
    questions.delete_many({})