import json
import random
from datetime import datetime
from pathlib import Path

from geopy import distance
from environs import Env
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

THING, LOCATION, PHOTO, TITLE, CHOOSING = range(5)


def get_priority_users(descriptions, user):
    try:
        priority_users = set(descriptions[user]['priority_users'])
        return priority_users
    except KeyError:
        priority_users = set()
        return priority_users


def get_thing_attrs(user_desc):
    thing_place = random.randint(0, len(user_desc['things']) - 1)
    thing = user_desc['things'][thing_place]
    with open(thing['img_path'], mode='rb') as file:
        img = file.read()
    return thing, img, thing_place


def write_to_context_user_data(context, user):
    with open('media/descriptions.json', mode='r') as file:
        descriptions = json.load(file)
    context.user_data['descriptions'] = descriptions
    context.user_data['priority_users'] = get_priority_users(
        descriptions,
        user
    )


def get_distance(user_coords, user_to_show_coords):
    return distance.distance(user_coords, user_to_show_coords).km


def get_coords(context, user):
    coords = list(context.user_data['descriptions'][user]['location'].values())[1], \
             list(context.user_data['descriptions'][user]['location'].values())[0]
    return coords


def start(update, context):
    user = update.message.from_user.username
    if user:
        reply_keyboard = [['Добавить вещь', 'Найти вещь'], ['Поделиться локацией']]
        update.message.reply_text(
            text="Привет! Я помогу тебе обменять что-то ненужное на очень нужное.\n"
                 "Чтобы разместить вещь к обмену нажми - Добавить вещь\n"
                 "Если ты уже размещал вещи и хочешь найти вариант для обмена нажми - Найти вещь\n"
                 "Если ты хочешь видеть расстояние до вещи жми - Поделиться локацией\n"
                 "Чтобы перезапустить бот, набери /start",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True
            ),
        )
        write_to_context_user_data(context, user)
        return THING
    else:
        update.message.reply_text(
            text='Заполни свой username в настройках Telegram и нажми /start',
            reply_markup=ReplyKeyboardRemove()
        )


def handling_thing(update, context):
    user = update.message.from_user['username']
    if update.message.text == 'Добавить вещь':
        update.message.reply_text(
            text='Пришли фото вещи',
            reply_markup=ReplyKeyboardRemove(),
        )
        return PHOTO

    elif update.message.text == 'Найти вещь' or update.message.text == 'Посмотреть ещё раз':
        reply_keyboard = [['Добавить вещь', 'Найти вещь'], ['Обменяться']]

        with open('media/descriptions.json', mode='r') as file:
            users = json.load(file)
        try:
            user_coords = list(users[user]['location'].values())[1], list(users[user]['location'].values())[0]
            context.user_data['user_coords'] = user_coords
        except AttributeError:
            pass
        if user not in users:
            update.message.reply_text(
                text='Для доступа к другим вещам, сначала добавь свою.',
                reply_markup=ReplyKeyboardMarkup(
                    [['Добавить вещь']], one_time_keyboard=True, resize_keyboard=True
                ),
            )
            return THING

        try:
            del context.user_data['descriptions'][user]
        except KeyError:
            pass

        if context.user_data['priority_users']:
            user_to_show = list(context.user_data['priority_users'])[0]
        else:
            try:
                user_to_show = random.choice(list(context.user_data['descriptions'].keys()))
            except IndexError:
                write_to_context_user_data(context, user)
                update.message.reply_text(
                    text='Больше вещей нет. Для того, чтобы посмотреть вещи ещё раз, нажмите Посмотреть ещё раз',
                    reply_markup=ReplyKeyboardMarkup(
                        [['Добавить вещь', 'Посмотреть ещё раз']], one_time_keyboard=True, resize_keyboard=True
                    ),
                )
                return THING

        user_desc = context.user_data['descriptions'][user_to_show]
        thing, img, thing_place = get_thing_attrs(user_desc)
        context.user_data['user_of_thing'] = user_to_show
        context.user_data['thing'] = None
        context.user_data['thing'] = thing

        update.message.reply_text(
            text=thing['title'],
            reply_markup=ReplyKeyboardRemove(),
        )
        try:
            user_to_show_coords = get_coords(context, user_to_show)
            distance = get_distance(context.user_data['user_coords'], user_to_show_coords)
            update.message.reply_text(
                text=f'Расстояние до вещи {distance:.2f}км',
                reply_markup=ReplyKeyboardRemove(),
            )
        except (AttributeError, KeyError):
            pass
        update.message.reply_photo(
            photo=img,
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True
            ),
        )
        del context.user_data['descriptions'][user_to_show]['things'][thing_place]

        if not context.user_data['descriptions'][user_to_show]['things']:
            del context.user_data['descriptions'][user_to_show]
            context.user_data['priority_users'].discard(user_to_show)
        return THING

    elif update.message.text == 'Обменяться':
        reply_keyboard = [['Добавить вещь', 'Найти вещь']]
        with open('media/descriptions.json', mode='r+') as file:
            descriptions = json.load(file)
            user_to_change = context.user_data['user_of_thing']
            user_to_change_chat_id = descriptions[user_to_change]["chat_id"]
            if user_to_change in get_priority_users(descriptions, update.effective_user.username):
                liked_things = list(set([list(thing.items())[0][1] for thing in context.bot_data['things_title_for_change'] if list(thing.items())[0][0] == user]))
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text='Ура! Можете связаться с пользователем @{} для обмена его вещи - {}, которая понравилась вам,'
                         ' на одну из ваших вещей - {}, которая понравилась ему.'.format(
                            user_to_change,
                            context.user_data['thing']['title'],
                            ', '.join(liked_things)
                        )
                )
                context.bot.send_message(
                    chat_id=user_to_change_chat_id,
                    text='Ура! Можете связаться с пользователем @{} для обмена одной из его вещей - {},'
                         ' которые вам понравились, на вашу вещь - {}, которая понравилась ему.'.format(
                            update.effective_chat.username,
                            ', '.join(liked_things),
                            context.user_data['thing']['title'],
                        )
                )
            else:
                if update.effective_user.username not in descriptions[user_to_change]["priority_users"]:
                    descriptions[user_to_change]["priority_users"].append(
                        update.effective_user.username
                    )
                thing_title_for_change = context.user_data['thing']['title']
                try:
                    context.bot_data['things_title_for_change'].append({context.user_data['user_of_thing']: thing_title_for_change})
                except KeyError:
                    context.bot_data['things_title_for_change'] = [{context.user_data['user_of_thing']: thing_title_for_change}]

                file.seek(0)
                json.dump(descriptions, file, ensure_ascii=False, indent=4)
                update.message.reply_text(
                    text='Вы выбрали вещь для обмена.',
                    reply_markup=ReplyKeyboardMarkup(
                        reply_keyboard, one_time_keyboard=True, resize_keyboard=True
                    ),
                )
                return THING

    elif update.message.text == 'Поделиться локацией':
        update.message.reply_text(
            text='Отправьте свою геопозицию',
            reply_markup=ReplyKeyboardRemove()
        )
        return LOCATION


def get_location(update, context):
    user = update.message.from_user['username']
    reply_keyboard = [['Добавить вещь', 'Найти вещь']]
    with open('media/descriptions.json', mode='r+') as file:
        descriptions = json.load(file)
        location = {
            'longitude': update.message['location']['longitude'],
            'latitude': update.message['location']['latitude'],

        }
        if user in descriptions:
            descriptions[user]['location'] = location
        else:
            descriptions[user] = {
                'chat_id': update.message.from_user['id'],
                'location': location,
                'things': [],
                'priority_users': []
            }
        file.seek(0)
        json.dump(descriptions, file, ensure_ascii=False, indent=4)
    update.message.reply_text(
        text='Отлично! Теперь можешь приступить к поиску и добавлению вещей.',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
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
        'img_path': context.user_data['img_path']
    }

    reply_keyboard = [['Добавить вещь', 'Найти вещь']]
    update.message.reply_text(
        text='Вы можете найти вещь или добавить еще одну вещь',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
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
                'things': [thing_desc],
                'priority_users': []
            }

        file.seek(0)
        context.user_data['descriptions'] = descriptions
        context.user_data['priority_users'] = get_priority_users(
            descriptions,
            user
        )
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
        allow_reentry=True,
        states={
            CHOOSING: [
                MessageHandler(
                    Filters.regex('^(Добавить вещь|Найти вещь|Поделиться локацией|Посмотреть ещё раз)$'),
                    handling_thing
                )
            ],
            LOCATION: [MessageHandler(Filters.location, get_location)],
            THING: [MessageHandler(Filters.text, handling_thing)],
            PHOTO: [MessageHandler(Filters.photo, get_photo)],
            TITLE: [MessageHandler(Filters.text, thing_title)],
        },
        fallbacks=[],
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()


if __name__ == '__main__':
    main()
