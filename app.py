# -*- coding: utf-8 -*-

import feedparser
import discord
import httpx
import json
from random import randint
from bs4 import BeautifulSoup
from discord.ext import tasks
from config import settings

client = discord.Client()
cli = httpx.Client()

def rJson():
    path = './userslib/db.json'
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return False

def wJson(obj):
    path = './userslib/db.json'
    with open(path, 'w') as f:
        json.dump(obj, f)

def search(title):
    obj = {}
    words = [' - игра на стадии разработки', ' полная версия на русском - торрент', ' - полная версия', ' - торрент']
    data = {
        'do': 'search',
        'subaction': 'search',
        'story': title
    }

    res = cli.post('https://tuttop.com', data=data)
    soup = BeautifulSoup(res.text, 'html.parser')
    titles = soup.findAll('div', class_='main-news-title')

    if len(titles) == 0:
        return False

    for t in titles:
        name = t.a.string
        for i in words:
            name = name.replace(i, '')
        obj[name] = t.a.get('href')
    
    return obj

def getGame(title, link):
    res = cli.get(link)
    soup = BeautifulSoup(res.text, 'html.parser').find('div', class_='full-news-content')
    obj = {'title': title, 'link': link}
    obj['img'] = 'https://tuttop.com' + soup.div.img.get('src')
    obj['torrent'] = soup.find('div', class_='button_download').a.get('href')
    obj['size'] = soup.find('div', class_='button_download').find('div', class_='rightbt').text

    return obj

def parseRSS(url):
    try:
        feed = feedparser.parse(url)
        if feed['status'] == 200:
            feed = feed['entries'][0]
            game = {'title': '', 'link': '', 'img': '', 'desc': '', 'sys': [], 'about': []}
            sysKeys = ['Операц', 'Проц', 'Операт', 'Видео', 'Место']
            abKeys = ['Жанр', 'Разраб', 'Плат', 'Язык', 'Размер']
            sysreq = feed.turbo_content[feed.turbo_content.find('Системные'):].replace('<b><span style="color:#FF0000">', '')

            if feed.summary.find('jpg') != -1: game['img'] = feed.summary[(feed.summary.find('src') + 5):(feed.summary.find('jpg') + 3)]
            else: game['img'] = feed.summary[(feed.summary.find('src') + 5):(feed.summary.find('png') + 3)]
            game['title'] = feed.title.replace(' - торрент', '')
            game['link'] = feed.link
            game['desc'] = feed.summary[(feed.summary.rfind('/>') + 2):]
    
            for i in sysKeys:
                if sysreq.find(i) != -1:
                    game['sys'].append(sysreq[sysreq.find(i):sysreq.find('<', sysreq.find(i))])
            for i in abKeys:
                if sysreq.find(i) != -1:
                    game['about'].append(sysreq[sysreq.find(i):sysreq.find('<', sysreq.find(i))])

            return game
        else:
            print('parse_status_error: ' + feed['status'])
            return False
    except:
        print('parse_error')
        return False

@tasks.loop(seconds=15)
async def check():
    last = open('./last.txt').read()
    res = parseRSS('https://tuttop.com/rss.xml')
    if not res: return
    text = { 'desc': res['desc'], 'sys': '', 'about': ''}

    if last != res['title'].lower():
        last = res['title'].lower()
        with open('./last.txt', 'w') as f:
            f.write(last)

        resp = httpx.get(res['link']).text
        start = resp.find('https://tuttop.com/torrent')
        end = resp.find('.torrent', start)
        url = resp[start:end + 8]

        db = rJson()
        mention = []
        
        for u in db.keys():
            for t in db[u]:
                if last.find(t) != -1:
                    mention.append(f'<@{u}>')

        for i in res['sys']:
            word = i.partition(':')[0]
            i = i.replace(word, f"`{word}`")
            text['sys'] += (i + '\n')
        for i in res['about']:
            word = i.partition(':')[0]
            i = i.replace(word, f"`{word}`")
            text['about'] += (i + '\n')
        
        embed = discord.Embed(
            #random color
            color=randint(0, 0xFFFFFF),
            title=res['title'],
            description=f"{text['desc']}\n\n\n**Системные требования:**\n{text['sys']}\n**Об игре:**\n{text['about']}\n[Подробности]({res['link']})\n[Cкачать торрент]({url})"
            )
        embed.set_image(url=res['img'])

        channel = client.get_channel(settings['channel'])
        await channel.send(' '.join(mention), embed=embed)

@client.event
async def on_message(msg):
    channel = msg.channel
    if channel.id == settings['channel'] and msg.author != client.user:

        if msg.content.startswith('***'):
            db = rJson()
            title = msg.content.replace('*** ', '')

            if str(msg.author.id) in db.keys():
                if title.lower() not in db[str(msg.author.id)]:
                    db[str(msg.author.id)].append(title.lower())
                else:
                    await channel.send(f'`{title} уже существует в вашей коллекции.`')
                    return
            else: db[str(msg.author.id)] = [title.lower()]
        
            await channel.send(f'Упоминание о `{title}`, добавлено в коллекцию пользователя - `{msg.author.nick}`.')

        elif msg.content.startswith('!s'):
            def Check(m):
                return m.channel.id == channel.id and m.author.id == msg.author.id

            title = msg.content.replace('!s ', '')
            obj = search(title)
            if not obj:
                await channel.send('Совпадений не найдено.')
                return

            if len(obj) == 1:
                game = getGame(list(obj.keys())[0], obj[list(obj.keys())[0]])

                embed = discord.Embed(
                    color=randint(0, 0xFFFFFF),
                    title=game['title'],
                    description=f"\n[Подробности]({game['link']})\n[Cкачать торрент]({game['torrent']}) {game['size']}"
                )
                embed.set_image(url=game['img'])
                await channel.send(embed=embed)
            else:
                text = '\n'
                for i in range(len(obj)):
                    text += f"\n`{i + 1}` - *{list(obj.keys())[i]}*"

                m = await channel.send(f"**Найдено {len(obj)} совпадений:**{text}\n\nПришлите цифру желаемой игры.")
                try: message = await client.wait_for('message', check=Check, timeout=60)
                except: pass

                if message.content.isdigit():
                    i = int(message.content)

                    await m.delete()
                    await message.delete()
                    game = getGame(list(obj.keys())[i - 1], obj[list(obj.keys())[i - 1]])

                    embed = discord.Embed(
                        color=randint(0, 0xFFFFFF),
                        title=game['title'],
                        description=f"\n[Подробности]({game['link']})\n[Cкачать торрент]({game['torrent']})"
                    )
                    embed.set_image(url=game['img'])
                    await channel.send(embed=embed)

@client.event
async def on_ready():
    print(f"Logged in as: {client.user.name}")
    check.start()

client.run(settings['token'])
