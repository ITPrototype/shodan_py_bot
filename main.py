import asyncio
import socket
import requests
from telebot.async_telebot import AsyncTeleBot
import os
import time
from collections import defaultdict

TOKEN = ""
bot = AsyncTeleBot(TOKEN)


user_last_command_time = defaultdict(float)
COMMAND_RATE_LIMIT = 8


async def shodan(ip):
    req_url = f"https://shodan.io/host/{ip}"
    filename = f"{ip}-shodan.html"

    try:
        req_data = await asyncio.get_event_loop().run_in_executor(
            None, requests.get, req_url
        )
        if req_data.status_code == 200:
            with open(filename, "w+") as f:
                f.write(req_data.text)
            return [True, filename]
        else:
            return [False, None]
    except Exception as e:
        print(f"Error retrieving data from Shodan: {e}")
        return [False, None]


@bot.message_handler(commands=["website"])
async def get_web(message):
    current_time = time.time()
    user_id = message.from_user.id

    if current_time - user_last_command_time[user_id] < 60:
        await bot.reply_to(message, "Please wait before sending another command.")
        return

    user_last_command_time[user_id] = current_time

    msg = message.text.split(" ")
    if len(msg) > 1:
        ip = socket.gethostbyname(msg[1])
        answer = await shodan(ip)
        if answer[0]:
            try:
                with open(answer[1], "rb") as f:
                    await bot.send_document(message.chat.id, f)
                os.remove(answer[1])
            except FileNotFoundError:
                await bot.reply_to(message, "File not found")
        else:
            await bot.reply_to(message, "Requested website not found!")


@bot.message_handler(commands=["help", "start"])
async def send_welcome(message):
    await bot.reply_to(
        message, "Hello! Use /website <domain> to fetch information from Shodan."
    )


if __name__ == "__main__":
    asyncio.run(bot.polling())
