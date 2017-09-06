# -*- coding: utf-8 -*-
from datetime import datetime
import telebot
import requests


bot = telebot.TeleBot('')
instagram_token = ''

DEFAULT_RADIUS = 1000


def geo(longitude, latitude, radius=DEFAULT_RADIUS):
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
        location = ig['location']['name'] if ig['location']['name'] else 'Unknown place'
        date = datetime.fromtimestamp(int(ig['created_time']))
        description = ig['caption']['text'] if ig['caption'] else 'No description'

        instagram_response = "Username: {}\nLink: {}\nLocation: {}\nDate: {}\nDescription: {}\n\n\n" \
            .format(username, link, location, date, description)

        instagram.append(instagram_response)

    vk = []
    for vkcom in result_vk:
        id = vkcom['owner_id']
        link = 'https://vk.com/photo{}_{}'.format(vkcom['owner_id'], vkcom['pid'])
        img = vkcom['src_big']
        date = datetime.fromtimestamp(int(vkcom['created']))
        description = vkcom['text'] if vkcom['text'] else 'No description'

        vk_response = "ID: id{}\nLink: {}\nImage: {}\nDate: {}\nDescription: {}\n\n\n" \
            .format(id, link, img, date, description)

        vk.append(vk_response)
    return instagram, vk


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 'Please send me your location or use command /location')


@bot.message_handler(commands=['location'])
def start(message):
    args = message.text.split()[1:]
    if len(args) < 2:
        bot.send_message(message.chat.id, 'You must send longitude and latitude. And maybe radius')
    else:
        try:
            safe_args = [float(arg) for arg in args]
        except ValueError:
            bot.send_message(message.chat.id, 'Unfortunately, I can not understand these coordinates')
        else:
            geo_result = geo(*safe_args)
            for response in geo_result[0]:
                bot.send_message(message.chat.id, response)
            for response in geo_result[1]:
                bot.send_message(message.chat.id, response)


@bot.message_handler(content_types=['location'])
def location(message):
    longitude = message.location.longitude
    latitude = message.location.latitude
    geo_result = geo(longitude, latitude)
    for response in geo_result[0]:
        bot.send_message(message.chat.id, response)
    for response in geo_result[1]:
        bot.send_message(message.chat.id, response)

bot.polling()
