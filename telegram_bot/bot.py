import json
import random
from datetime import datetime
from pathlib import Path

from environs import Env
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

THING, PHOTO, TITLE, CHOOSING = range(4)


def get_priority_users(descriptions, user):
    priority_users = []
    things = descriptions[user]['things']
    for thing in things:
        priority_users.extend(thing['priority_users'])
    
    return set(priority_users)


def get_thing_attrs(descriptions):
    user = random.choice(list(descriptions.keys()))
    thing = random.choice(descriptions[user]['things'])
    with open(thing['img_path'], mode='rb') as file:
        img = file.read()
    return thing, img, user


def start(update, context):
    if not update.message.from_user.username:
        update.message.reply_text(
            text='Заполни свой username в настройках Telegram и нажми /start',
            reply_markup=ReplyKeyboardRemove()
            )
    else:
        reply_keyboard = [['Добавить вещь', 'Найти вещь']]
        update.message.reply_text(
            text="Привет! Я помогу тебе обменять что-то ненужное на очень нужное.\n"
                 "Чтобы разместить вещь к обмену нажми - Добавить вещь\n"
                 "Если ты уже размещал вещи и хочешь найти вариант для обмена нажми - Найти вещь",
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
    user = update.message.from_user['username']
    if update.message.text == 'Добавить вещь':
        update.message.reply_text(
            text='Пришли фото вещи',
            reply_markup=ReplyKeyboardRemove(),
        )
        return PHOTO

    elif update.message.text == 'Найти вещь':
        reply_keyboard = [['Обменяться', 'Добавить вещь', 'Найти вещь']]
        with open('media/descriptions.json', mode='r') as file:
            descriptions = json.load(file)
        priority_users = get_priority_users(descriptions, user)
        if priority_users: # Сейчас работает так, что показывает только вещи приоретеных пользователей, если они есть
            for priority_user in priority_users:
                descriptions = {
                    priority_user: descriptions[priority_user]
                }
                thing, img, user_of_thing = get_thing_attrs(descriptions)
                context.user_data.clear()
                context.user_data[user_of_thing] = user_of_thing
                update.message.reply_text(
                    text=thing['title'],
                    reply_markup=ReplyKeyboardRemove(),
                )
                update.message.reply_photo(
                    photo=img,
                    reply_markup=ReplyKeyboardMarkup(
                        reply_keyboard, one_time_keyboard=True,
                    ),
                )
        else:
            try:
                del descriptions[user]
            except KeyError:
                update.message.reply_text(
                    text='Для доступа к другим вещам, сначала добавь свою.',
                    reply_markup=ReplyKeyboardMarkup(
                        [['Добавить вещь']], one_time_keyboard=True,
                    ),
                )
                return THING

            thing, img, user_of_thing = get_thing_attrs(descriptions)
            context.user_data.clear()
            context.user_data[user_of_thing] = user_of_thing
            update.message.reply_text(
                text=thing['title'],
                reply_markup=ReplyKeyboardRemove(),
            )
            update.message.reply_photo(
                photo=img,
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True,
                ),
            )
            return THING
    elif update.message.text == 'Обменяться':
        reply_keyboard = [['Добавить вещь', 'Найти вещь']]
        with open('media/descriptions.json', mode='r+') as file:
            descriptions = json.load(file)
            user_wanted_to_change = list(context.user_data.keys())[0]
            user_wanted_to_change_chat_id = descriptions[user_wanted_to_change]["chat_id"]
            if user_wanted_to_change in get_priority_users(descriptions, update.effective_user.username):
                context.bot.send_message(chat_id=update.effective_chat.id, text="bingo")
                context.bot.send_message(chat_id=user_wanted_to_change_chat_id, text="bingo")
            else:
                descriptions[user_wanted_to_change]['things'][0]["priority_users"].append(update.effective_user.username)
                file.seek(0)
                json.dump(descriptions, file, ensure_ascii=False, indent=4)
                update.message.reply_text(
                    text='Вы выбрали вещь для обмена.',
                    reply_markup=ReplyKeyboardMarkup(
                        reply_keyboard, one_time_keyboard=True,
                    ),
                )
                return THING


def get_photo(update, context):
    img = update.message.photo[-1].get_file()

    extension = Path(img['file_path']).suffix
    basename = datetime.now().strftime('%y%m%d_%H%M%S')
    img_name = ''.join([basename, extension])
    img_path = img.download(Path('media/images', img_name))

    context.user_data['img_path'] = str(img_path)

    update.message.reply_text(
        'Пришли название вещи'
    )
    return TITLE


def thing_title(update, context):
    user = update.message.from_user['username']
    thing_desc = {
        'title': update.message.text,
        'img_path': context.user_data['img_path'],
        'priority_users': []
    }

    reply_keyboard = [['Добавить вещь', 'Найти вещь']]
    update.message.reply_text(
        text='Вы можете найти вещь или добавить еще одну вещь',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
        ),
    )
    with open('media/descriptions.json', mode='r+') as file:
        descriptions = json.load(file)

        if user in descriptions:
            descriptions[user]['things'].append(thing_desc)
        else:
            descriptions[user] = {
                'chat_id': update.message.from_user['id'],
                'location': '',
                'things': [thing_desc]
            }

        file.seek(0)
        json.dump(descriptions, file, ensure_ascii=False, indent=4)

    return CHOOSING


def main():
    env = Env()
    env.read_env()
    updater = Updater(token=env.str('BOT_TOKEN'), use_context=True)
    dispatcher = updater.dispatcher

    Path('media/images/').mkdir(parents=True, exist_ok=True)
    try:
        with open('media/descriptions.json', mode='x') as file:
            file.write('{}')
    except FileExistsError:
        pass

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
