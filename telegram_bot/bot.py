from pathlib import Path
from datetime import datetime

from environs import Env
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

THING, PHOTO, TITLE, CHOICE = range(4)


def start(update, context):
    reply_keyboard = [['Добавить вещь']]
    update.message.reply_text(text="Привет! Я помогу тебе обменять что-то ненужное на очень нужное."
                                   " Чтобы разместить вещь к обмену напиши - Добавить вещь",
                              reply_markup=ReplyKeyboardMarkup(
                                  reply_keyboard, one_time_keyboard=True,
                              ),
                              )
    return THING


def cancel(update, context):
    user = update.message.from_user
    update.message.reply_text(
        'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
    )


def add_thing(update, context):
    user = update.message.from_user
    update.message.reply_text(
        text='Пришли фото вещи',
        reply_markup=ReplyKeyboardRemove(),
    )
    return PHOTO


def get_photo(update, context):
    user = update.message.from_user
    img = update.message.photo[-1].get_file()
    Path('media/images/').mkdir(parents=True, exist_ok=True)
    extension = Path(img['file_path']).suffix
    basename = datetime.now().strftime('%y%m%d_%H%M%S')
    img_name = ''.join([basename, extension])
    img.download(Path('media/images', img_name))
    update.message.reply_text(
        'Пришли название вещи'
    )
    return TITLE


def thing_title(update, context):
    reply_keyboard = [['Добавить вещь', 'Найти вещь']]
    update.message.reply_text(
        text='Вы можете найти вещь или добавить еще одну вещь',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
        ),

    )
    return CHOICE


def make_choice(update, context):
    title = update.message.text
    update.message.reply_text()
    if title == 'Добавить вещь':
        return THING
    elif title == 'Найти вещь':
        return THING


def main():
    env = Env()
    env.read_env()
    updater = Updater(token=env.str('BOT_TOKEN'), use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            THING: [MessageHandler(Filters.text, add_thing)],
            PHOTO: [MessageHandler(Filters.photo, get_photo)],
            TITLE: [MessageHandler(Filters.text, thing_title)],
            CHOICE: [MessageHandler(Filters.text, make_choice)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()


if __name__ == '__main__':
    main()
