import aiohttp
import asyncio
import re
import os
import subprocess
import threading
import time
from telethon import TelegramClient, events, Button
from pyrogram import Client
from pyrogram.errors import Forbidden

API_ID = 25399723
API_HASH = '49bf6c6103c8eb427911362c6d5d5bf3'
BOT_TOKEN = '7647825036:AAFkwI4DNERxHzJBFq60SYG1wSUv2Cki_ww'

VALID_URL_PATTERN = r"https?://[a-zA-Z0-9.-]*tera[a-zA-Z0-9.-]*/[^ ]+"

os.makedirs("downloads", exist_ok=True)

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
pbot = Client("pyro_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pbot.start()

progress_tracker = {}

def extract_filename(headers):
    cd = headers.get('Content-Disposition')
    if cd:
        fname_match = re.findall('filename=\"(.+?)\"', cd)
        if fname_match:
            return fname_match[0]
    return "unknown_file"

def crop_filename(name, max_len=20):
    if len(name) <= max_len:
        return name
    return name[:max_len-3] + "..."

@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    user_name = event.sender.first_name
    buttons = [
        [Button.url("JOIN CHANNEL", url="https://t.me/mrinxdildos"),
         Button.url("OWNER", url="https://t.me/M_o_Y_zZz")]
    ]
    await bot.send_message(
        event.chat_id,
        f"**👋 **𝗛𝗶𝗶𝗶....** {user_name}, **\n\n"
        f"**𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝗧𝗼 𝗠𝗥𝗶𝗡 𝘅 𝗗𝗶𝗟𝗗𝗢𝗦™ 𝗧𝗘𝗥𝗔𝗕𝗢𝗫 𝗗𝗜𝗥𝗘𝗖𝗧 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗𝗘𝗥 𝗕𝗢𝗧**\n\n"
        f"📘 𝗛𝗼𝘄 𝗜𝘁 𝗪𝗼𝗿𝗸𝘀 :\n\n"
        f"➤  **𝗣𝗮𝘀𝘁𝗲 𝘆𝗼𝘂𝗿 𝗧𝗲𝗿𝗮𝗯𝗼𝘅 𝗨𝗥𝗟 𝗯𝗲𝗹𝗼𝘄 👇 𝗧𝗵𝗲 𝗯𝗼𝘁 𝘄𝗶𝗹𝗹 𝗳𝗲𝘁𝗰𝗵 & 𝘂𝗽𝗹𝗼𝗮𝗱 𝗯𝗮𝗰𝗸 𝘁𝗵𝗲 𝗳𝗶𝗹𝗲** ⚡️\n\n"
        f"📦 **𝗦𝗶𝘇𝗘 𝗟𝗶𝗠𝗜𝗧 : 𝟭.𝟵 𝗚𝗕**\n\n"
        f"**𝗕𝗢𝗧 𝗠𝗔𝗗𝗘 𝗕𝗬 > @𝗠_o_𝗬_𝘇𝗭𝘇**\n",
        buttons=buttons,
        parse_mode='markdown'
    )
    raise events.StopPropagation


# ✅ Async downloader with resume & retry
async def fast_download_with_progress(url, output_path, chat_id, file_id, filename):
    start_time = time.time()
    downloaded = 0
    total_size = None
    chunk_size = 65536

    if os.path.exists(output_path):
        downloaded = os.path.getsize(output_path)

    try:
        while True:
            headers = {}
            if downloaded > 0:
                headers['Range'] = f'bytes={downloaded}-'

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status not in (200, 206):
                        return None, f"HTTP {resp.status}"

                    if total_size is None:
                        if 'content-range' in resp.headers:
                            match = re.search(r'/(\d+)$', resp.headers['content-range'])
                            if match:
                                total_size = int(match.group(1))
                        elif 'content-length' in resp.headers:
                            total_size = int(resp.headers['content-length'])

                    with open(output_path, 'ab') as f:
                        async for chunk in resp.content.iter_chunked(chunk_size):
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)

                            if total_size and total_size > 0:
                                percent = (downloaded / total_size) * 100
                                speed = downloaded / (time.time() - start_time + 0.1) / (1024 * 1024)
                                time_left = (total_size - downloaded) / (speed * 1024 * 1024 + 1e-5)
                                progress_tracker[(chat_id, f'download_{file_id}')] = {
                                    "percent": percent,
                                    "current": downloaded,
                                    "total": total_size,
                                    "speed": speed,
                                    "time_left": time_left,
                                    "file_name": filename,
                                    "last_update": time.time()
                                }

            break  # Download complete

    except (aiohttp.ClientPayloadError, ConnectionResetError, asyncio.TimeoutError) as e:
        print(f"[DOWNLOAD PAUSED] {e}. Retrying...")
        await asyncio.sleep(3)
        return await fast_download_with_progress(url, output_path, chat_id, file_id, filename)
    except Exception as e:
        print(f"[DOWNLOAD ERROR] {e}")
        return None, str(e)

    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        return output_path, 200
    else:
        return None, "Download failed or file empty"


async def fetch_terabox_download_link(session, link):
    api_url = f"https://free-api.mrinmoy.workers.dev/?url={link}"
    async with session.get(api_url) as resp:
        if resp.status != 200:
            return None, resp.status
        try:
            data = await resp.json()
        except:
            return None, "Failed to parse JSON"
        if not all(k in data for k in ["file_name", "link", "thumb", "sizebytes"]):
            return None, "Missing keys"
        return {
            "download_link": data["link"],
            "filename": data["file_name"],
            "thumbnail_url": data["thumb"],
            "file_size": f"{data['size']}",
            "size_bytes": data["sizebytes"]
        }, 200


async def download_and_send_file(event, link):
    chat_id = event.chat_id
    file_id = str(abs(hash(link)))[:8]

    sender = await event.get_sender()
    sender_username = sender.username if sender.username else "unknown_user"

    async with aiohttp.ClientSession() as session:
        response, status = await fetch_terabox_download_link(session, link)
        if not response:
            await bot.send_message(chat_id, f"Failed to fetch download link for {link}")
            return

        download_link = response["download_link"]
        filename = response["filename"]
        file_size = response["file_size"]
        thumbnail_url = response["thumbnail_url"]

    # ✅ Keep original button text — no filename
    download_msg = await bot.send_message(
        chat_id,
        f"📥  𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴...\n\n• 📎 𝗧𝗘𝗥𝗔𝗕𝗢𝗫 𝗟𝗜𝗡𝗞 > `{link}`\n\n• 📦 𝗙𝗶𝗟𝗘 𝗦𝗜𝗭𝗘 > `{file_size}`",
        buttons=[[Button.inline("⌛️ 𝗩𝗶𝗲𝘄 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀 ⏳", data=f"progress_download_{file_id}")]]
    )

    try:
        filepath = os.path.join("downloads", filename)
        result_path, result_status = await fast_download_with_progress(
            download_link, filepath, chat_id, file_id, filename
        )

        if not result_path or result_status != 200:
            await bot.send_message(chat_id, "❌ File download failed.")
            await download_msg.delete()
            return

        # ✅ Use thumbnail from API directly — no ffmpeg
        thumb_path = None
        if thumbnail_url:
            temp_thumb = filepath + ".jpg"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(thumbnail_url) as thumb_resp:
                        if thumb_resp.status == 200:
                            with open(temp_thumb, "wb") as f:
                                f.write(await thumb_resp.read())
                            thumb_path = temp_thumb
                        else:
                            print(f"[THUMBNAIL] Failed to download, status: {thumb_resp.status}")
            except Exception as e:
                print(f"[THUMBNAIL DOWNLOAD ERROR] {e}")

        upload_msg = await bot.send_message(
            chat_id,
            f"📤  𝗨𝗽𝗹𝗼𝗮𝗱𝗶𝗻𝗴...\n\n • 📦 𝗙𝗶𝗟𝗘 𝗡𝗔𝗠𝗘 > `{filename}`\n\n • 📦 𝗙𝗶𝗟𝗘 𝗦𝗜𝗭𝗘 > `{file_size}`",
            buttons=[[Button.inline("⌛️ 𝗩𝗶𝗲𝘄 𝗨𝗽𝗹𝗼𝗮𝗱 𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀 ⏳", data=f"progress_upload_{file_id}")]]
        )

        start_time = time.time()

        async def upload_progress(current, total):
            percent = (current / total) * 100
            elapsed = time.time() - start_time
            speed = (current / (elapsed + 0.1)) / (1024 * 1024)
            time_left = (total - current) / (speed * 1024 * 1024 + 1e-5)
            progress_tracker[(chat_id, f'upload_{file_id}')] = {
                "percent": percent,
                "current": current,
                "total": total,
                "speed": speed,
                "time_left": time_left,
                "file_name": filename,
                "last_update": time.time()
            }

        message = await pbot.send_video(
            chat_id,
            filepath,
            caption=f"**\n𝗛𝗲𝗿𝗲 𝗜𝘀 𝗬𝗼𝘂𝗿 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗲𝗱 𝗩𝗶𝗱𝗲𝗼....** \n\n•   𝗙𝗶𝗟𝗘 𝗡𝗔𝗠𝗘    📦   `{filename}` 👀\n\n •   𝗙𝗶𝗟𝗘 𝗦𝗜𝗭𝗘    📦   `{file_size}`\n\n •   𝗥𝗘𝗤𝗨𝗘𝗦𝗧𝗘𝗗 𝗕𝗬 > @{sender_username}\n\n   •   𝗕𝗢𝗧 𝗠𝗔𝗗𝗘 𝗕𝗬  >  @𝗠_o_𝗬_𝘇𝗭𝘇 ",
            thumb=thumb_path,  # Can be None — Pyrogram handles it
            progress=upload_progress,
            supports_streaming=True,
            has_spoiler=True,
            protect_content=False
        )

        # ✅ Forward to channel
        try:
            await pbot.copy_message(
                chat_id="@dumpbymxdterabot",
                from_chat_id=chat_id,
                message_id=message.id
            )
        except Forbidden:
            print("[ERROR] Bot not admin in target channel or channel ID invalid.")
        except Exception as e:
            print(f"[COPY ERROR] {e}")

        await download_msg.delete()
        await upload_msg.delete()

        if os.path.exists(filepath): os.remove(filepath)
        if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)

    except Exception as e:
        await bot.send_message(chat_id, f"Error: {str(e)}")
    finally:
        progress_tracker.pop((chat_id, f'download_{file_id}'), None)
        progress_tracker.pop((chat_id, f'upload_{file_id}'), None)


@bot.on(events.NewMessage)
async def handler(event):
    text = event.raw_text.strip()
    links = [link for link in re.split(r"[\s\n]+", text) if re.match(VALID_URL_PATTERN, link)]
    if not links:
        return
    for i, link in enumerate(links):
        await download_and_send_file(event, link)
        if i < len(links) - 1:
            await asyncio.sleep(3)


# ✅ Updated progress handler — filename cropped to 20 chars, no rate limit
@bot.on(events.CallbackQuery(data=lambda x: x.startswith(b"progress_")))
async def show_progress(event):
    try:
        _, typ, file_id = event.data.decode().split("_", 2)
        key = (event.chat_id, f"{typ}_{file_id}")
        if key not in progress_tracker:
            await event.answer("No active progress to show ✌", alert=True)
            return

        p = progress_tracker[key]

        # ✅ TRIM FILENAME TO 20 CHARACTERS MAX
        filename = p['file_name']
        if len(filename) > 20:
            filename = filename[:17] + "..."

        bar = f"[{'█' * int(p['percent'] / 10)}{'░' * (10 - int(p['percent'] / 10))}]"
        msg = (
            f"𝗠𝗮𝗗𝗘  𝗪𝗶𝗧𝗛  𝗟𝗼𝗩𝗲  ❤️ 𝗕𝗬  @𝗠𝗼𝗬_𝘇𝗭𝘇\n\n"
            f">  𝗙𝗶𝗟𝗘 𝗡𝗔𝗠𝗘   :  {filename}\n"
            f">    {bar} {p['percent']:.2f}%\n"
            f">     {p['current'] / (1024 * 1024):.2f} MB of {p['total'] / (1024 * 1024):.2f} MB\n"
            f">   𝗦𝗣𝗘𝗘𝗗  :   {p['speed']:.2f} MB/s\n"
            f">    𝗧𝗶𝗠𝗘 𝗟𝗘𝗙𝗧  :   {p['time_left']:.1f}s"
        )

        # Safety: prevent overly long messages
        if len(msg) > 400:
            msg = msg[:380] + "..."

        await event.answer(msg, alert=True)

    except Exception:
        await event.answer("Unable to show progress.", alert=True)


print("Bot running...")

def terminal_progress():
    while True:
        for key, p in progress_tracker.items():
            typ = key[1].split('_')[0]
            filename = p['file_name']
            percent = p['percent']
            speed = p['speed']
            time_left = p['time_left']
            print(f"[{typ.upper()}] {filename} | {percent:.2f}% | {speed:.2f} MB/s | {time_left:.1f}s")
        time.sleep(1)

threading.Thread(target=terminal_progress, daemon=True).start()

bot.run_until_disconnected()
