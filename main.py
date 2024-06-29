import asyncio
import socket
import requests
from telebot.async_telebot import AsyncTeleBot
import os
import time
from collections import defaultdict
import sqlite3

TOKEN = "7066613548:AAHSKghmtLJHNdlbyz6Z4xLolEFX7YPK-_A"
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
    id = message.from_user.id
    name = message.from_user.first_name
    premium = message.from_user.is_premium
    username = message.from_user.username
    msg = message.text
    data = [id, name, premium, username, msg]
    if user_exists(id):
        print(data)
    else:
        insert_to_db(data)


def user_exists(tg_id):
    try:
        conn = sqlite3.connect("db.sqlite3")
        cursor = conn.cursor()

        # Execute the query to check if the user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE tg_id = ?", (tg_id,))
        count = cursor.fetchone()[0]

        # If count > 0, user exists; otherwise, user does not exist
        if count > 0:
            return True
        else:
            return False

    except sqlite3.Error as e:
        print(f"Error checking user existence: {e}")
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def insert_to_db(data):
    try:
        conn = sqlite3.connect("db.sqlite3")
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id TEXT,
                name TEXT,
                premium TEXT,
                username TEXT,
                msg TEXT
            )
            """
        )

        # Insert data
        cursor.execute(
            "INSERT INTO users (tg_id, name, premium, username, msg) VALUES (?, ?, ?, ?, ?)",
            (data[0], data[1], data[2], data[3], data[4]),
        )

        conn.commit()
        print("Data inserted successfully.")

    except sqlite3.Error as e:
        print(f"Error inserting data into SQLite: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    asyncio.run(bot.polling())
