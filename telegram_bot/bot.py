import json
import os
import random
from datetime import datetime
from pathlib import Path

from environs import Env
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

THING, PHOTO, TITLE, CHOOSING = range(4)


def start(update, context):
    reply_keyboard = [['Добавить вещь']]
    update.message.reply_text(
        text="Привет! Я помогу тебе обменять что-то ненужное на очень нужное."
             " Чтобы разместить вещь к обмену напиши - Добавить вещь",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
        ),
    )
    return THING


def cancel(update, context):
    user = update.message.from_user
    update.message.reply_text(
        'Bye! I hope we can talk again some day.',
        reply_markup=ReplyKeyboardRemove()
    )


def add_thing(update, context):
    user = update.message.from_user
    if update.message.text == 'Добавить вещь':
        update.message.reply_text(
            text='Пришли фото вещи',
            reply_markup=ReplyKeyboardRemove(),
        )
        return PHOTO

    # Сейчас работает так, что можно написать 'Найти вещь' даже до загрузки своей вещи
    if update.message.text == 'Найти вещь':
        reply_keyboard = [['Обменяться', 'Следующая вещь']]
        stuff = random.choice(os.listdir('media/descriptions'))

        with open(Path('media/descriptions', stuff), mode='r') as file:
            stuff_desc = json.load(file)
        with open(stuff_desc['img_path'], mode='rb') as file:
            img = file.read()

        update.message.reply_text(
            text=stuff_desc['title'],
            reply_markup=ReplyKeyboardRemove(),
        )
        update.message.reply_photo(
            photo=img,
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True,
            ),
        )
        return PHOTO


def get_photo(update, context):

    img = update.message.photo[-1].get_file()
    Path('media/images/').mkdir(parents=True, exist_ok=True)
    extension = Path(img['file_path']).suffix
    basename = datetime.now().strftime('%y%m%d_%H%M%S')
    img_name = ''.join([basename, extension])
    img_path = img.download(Path('media/images', img_name))
    description_name = '.'.join([basename, 'json'])

    context.user_data['username'] = update.message.from_user['username']
    context.user_data['img_path'] = str(img_path)
    context.user_data['json_name'] = description_name

    update.message.reply_text(
        'Пришли название вещи'
    )
    return TITLE


def thing_title(update, context):
    context.user_data['title'] = update.message.text

    reply_keyboard = [['Добавить вещь', 'Найти вещь']]
    update.message.reply_text(
        text='Вы можете найти вещь или добавить еще одну вещь',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
        ),
    )

    Path('media/descriptions/').mkdir(parents=True, exist_ok=True)
    with open(Path('media/descriptions', context.user_data['json_name']), mode='w') as file:
        json.dump(context.user_data, file, ensure_ascii=False, indent=4)

    return CHOOSING


def main():
    env = Env()
    env.read_env()
    updater = Updater(token=env.str('BOT_TOKEN'), use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [
                MessageHandler(
                    Filters.regex('^(Добавить вещь|Найти вещь)$'), add_thing
                )
            ],
            THING: [MessageHandler(Filters.text, add_thing)],
            PHOTO: [MessageHandler(Filters.photo, get_photo)],
            TITLE: [MessageHandler(Filters.text, thing_title)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()


if __name__ == '__main__':
    main()
