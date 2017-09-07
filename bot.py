# -*- coding: utf-8 -*-
from datetime import datetime
from peewee import *
import telebot
import requests
import threading
import time


bot = telebot.TeleBot('')
instagram_token = ''

db = SqliteDatabase('bot.db', fields={'id': 'INTEGER AUTOINCREMENT'})
DEFAULT_RADIUS = 1000
PHOTOS_PER_MESSAGE = 10
SUBSCRIBE_CHECK = 216000


class Response:
    def __init__(self, message, user, link, timestamp, description, location=None):
        self.message = message
        self.user = user
        self.link = link
        self.timestamp = timestamp
        self.description = description
        self.location = location


class Sub(Model):
    id = IntegerField(primary_key=True)
    user_id = IntegerField()
    lat = CharField()
    long = CharField()
    radius = CharField()
    last_ig = IntegerField(default=int(datetime.today().timestamp()))
    last_vk = IntegerField(default=int(datetime.today().timestamp()))

    class Meta:
        database = db

db.connect()

if not Sub.table_exists():
    db.create_tables([Sub])


def geo(latitude, longitude, radius=DEFAULT_RADIUS):
    global instagram_token
    url_instagram = 'https://api.instagram.com/v1/media/search?lat={}&lng={}&distance={}&access_token={}'\
        .format(latitude, longitude, radius, instagram_token)
    url_vk = 'https://api.vk.com/method/photos.search?lat={}&long={}&sort=0&radius={}'\
        .format(latitude, longitude, radius)
    result_instagram = requests.get(url_instagram).json()['data']
    result_vk = requests.get(url_vk).json()['response'][1:]
    instagram = []
    for ig in result_instagram:
        username = ig['user']['username']
        link = ig['link']
        date = datetime.fromtimestamp(int(ig['created_time']))
        timestamp = int(ig['created_time'])
        description = ig['caption']['text'] if ig['caption'] else 'No description'
        location = ig['location']['name'] if ig['location']['name'] else 'Unknown place'
        message = "Username: {}\nLink: {}\nLocation: {}\nDate: {}\nDescription: {}\n\n\n" \
            .format(username, link, location, date, description)
        instagram_response = Response(message, username, link, timestamp, description, location)
        instagram.append(instagram_response)

    vk = []
    for vkcom in result_vk:
        username = vkcom['owner_id']
        link = 'https://vk.com/photo{}_{}'.format(vkcom['owner_id'], vkcom['pid'])
        img = vkcom['src_big']
        date = datetime.fromtimestamp(int(vkcom['created']))
        timestamp = int(vkcom['created'])
        description = vkcom['text'] if vkcom['text'] else 'No description'

        message = "ID: id{}\nLink: {}\nImage: {}\nDate: {}\nDescription: {}\n\n\n" \
            .format(username, link, img, date, description)
        vk_response = Response(message, username, link, timestamp, description)
        vk.append(vk_response)
    return instagram, vk


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 'Please send me your location or use command /location lat long radius (in meters)')


@bot.message_handler(commands=['sub'])
def sub(message):
    args = message.text
    if ',' in args:
        args = args.replace(',', ' ')
    args = args.split()[1:]
    if len(args) < 2:
        bot.reply_to(message, 'You must send longitude and latitude. And maybe radius (in meters)')
    else:
        latitude = args[0]
        longitude = args[1]
        if len(args) > 3:
            radius = args[2]
        else:
            radius = DEFAULT_RADIUS
        Sub(user_id=message.chat.id, lat=latitude, long=longitude, radius=radius).save()
        bot.reply_to(message, 'Got it!')


@bot.message_handler(commands=['location'])
def location(message):
    args = message.text
    if ',' in args:
        args = args.replace(',', ' ')
    args = args.split()[1:]
    if len(args) < 2:
        bot.send_message(message.chat.id, 'You must send longitude and latitude. And maybe radius (in meters)')
    else:
        try:
            safe_args = [float(arg) for arg in args]
        except ValueError:
            bot.send_message(message.chat.id, 'Unfortunately, I can not understand these coordinates')
        else:
            geo_result = geo(*safe_args)
            geo_result = geo_result[0] + geo_result[1]
            while geo_result:
                response_text = []
                response = geo_result[:PHOTOS_PER_MESSAGE]
                response_text += [resp.message for resp in response]
                response_text = ''.join(response_text)
                geo_result = geo_result[PHOTOS_PER_MESSAGE:]
                bot.send_message(message.chat.id, response_text, disable_web_page_preview=True)


@bot.message_handler(content_types=['location'])
def location(message):
    longitude = message.location.longitude
    latitude = message.location.latitude
    geo_result = geo(latitude, longitude)
    while geo_result:
        response_text = []
        response = geo_result[:PHOTOS_PER_MESSAGE]
        response_text += [resp.message for resp in response]
        response_text = ''.join(response_text)
        geo_result = geo_result[PHOTOS_PER_MESSAGE:]
        bot.send_message(message.chat.id, response_text, disable_web_page_preview=True)


def subscribe_daemon():
    while True:
        subs = Sub.select()
        for sub in subs:
            geo_result = geo(sub.lat, sub.long, sub.radius)
            for instagram in reversed(geo_result[0]):
                if instagram.timestamp > sub.last_ig:
                    Sub.update(last_ig=instagram.timestamp).where(Sub.id == sub.id).execute()
                    bot.send_message(sub.user_id, instagram.message)

            for vk in reversed(geo_result[1]):
                if vk.timestamp > sub.last_vk:
                    Sub.update(last_vk=vk.timestamp).where(Sub.id == sub.id).execute()
                    bot.send_message(sub.user_id, vk.message)

        time.sleep(SUBSCRIBE_CHECK)

threading.Thread(target=bot.polling).start()
threading.Thread(target=subscribe_daemon).start()
