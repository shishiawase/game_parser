# -*- coding: utf-8 -*-

import feedparser
import discord
import asyncio
import httpx
import json
from config import settings

client = discord.Client()
last = open('./last.txt').read()

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

def parseRSS(url):
    feed = feedparser.parse(url)['entries'][0]
    game = {'title': '', 'link': '', 'img': '', 'desc': '', 'sys': [], 'about': []}
    sysKeys = ['Операц', 'Проц', 'Операт', 'Видео', 'Место']
    abKeys = ['Жанр', 'Разраб', 'Плат', 'Язык', 'Размер']
    sysreq = feed.turbo_content[feed.turbo_content.find('Системные'):].replace('<b><span style="color:#FF0000">', '')
    
    game['title'] = feed.title
    game['link'] = feed.link
    game['img'] = feed.summary[(feed.summary.find('src') + 5):(feed.summary.find('jpg') + 3)]
    game['desc'] = feed.summary[(feed.summary.rfind('/>') + 2):]
    
    for i in sysKeys:
        if sysreq.find(i) != -1:
            game['sys'].append(sysreq[sysreq.find(i):sysreq.find('<', sysreq.find(i))])
    for i in abKeys:
        if sysreq.find(i) != -1:
            game['about'].append(sysreq[sysreq.find(i):sysreq.find('<', sysreq.find(i))])

    return game

async def check(last):
    await client.wait_until_ready()

    while not client.is_closed():

        res = parseRSS('https://tuttop.com/rss.xml')
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
                color=0x3498db,
                title=res['title'],
                description=f"{text['desc']}\n\n\n**Системные требования:**\n{text['sys']}\n**Об игре:**\n{text['about']}\n[Подробности]({res['link']})\n[Cкачать торрент]({url})"
                )
            embed.set_image(url=res['img'])

            channel = client.get_channel(settings['channel'])
            await channel.send(' '.join(mention), embed=embed)
            await asyncio.sleep(15)

@client.event
async def on_ready():
    print(f"Logged in as: {client.user.name}")

@client.event
async def on_message(msg):
    if msg.content.startswith('***'):
        db = rJson()
        title = msg.content.replace('*** ', '')
        if db.get(msg.author.id): db[msg.author.id].append(title.lower())
        else: db[msg.author.id] = [title.lower()]
        wJson(db)

        channel = msg.channel
        await channel.send(f'Упоминание о `{title}`, добавлено в коллекцию пользователя - `{msg.author.nick}`.')

client.loop.create_task(check(last))
client.run(settings['token'])
