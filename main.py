import os
import asyncio
from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import db
from scrapers import scraper

# Initialize Bot
bot = Client(
    "AnimeScraperBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# --- Start & Help ---
@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    user_id = message.from_user.id
    is_admin = await db.is_admin(user_id)
    welcome_text = f"Welcome {message.from_user.mention} to Anime Scraper Bot!\n\n"
    if is_admin:
        welcome_text += "You are an Admin. Use /search <anime name> to find content."
    else:
        welcome_text += "This bot is for Admins only."
    await message.reply_text(welcome_text)

@bot.on_message(filters.command("help"))
async def help_cmd(client, message):
    help_text = """
**Admin Commands:**
/search <anime name> - Search for anime across websites
/setcaption <text> - Set custom caption for videos
/setthumbnail - Send with a photo to set thumbnail
/setfilename <name> - Set custom filename format
/addadmin <user_id> - Add a new admin
/deladmin <user_id> - Remove an admin
/admins - List all admins
"""
    await message.reply_text(help_text)

# --- Admin Management ---
@bot.on_message(filters.command("addadmin") & filters.user(Config.ADMINS))
async def add_admin_cmd(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /addadmin <user_id>")
    try:
        user_id = int(message.command[1])
        await db.add_admin(user_id)
        await message.reply_text(f"User {user_id} added as admin.")
    except ValueError:
        await message.reply_text("Invalid User ID.")

@bot.on_message(filters.command("deladmin") & filters.user(Config.ADMINS))
async def del_admin_cmd(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /deladmin <user_id>")
    try:
        user_id = int(message.command[1])
        await db.remove_admin(user_id)
        await message.reply_text(f"User {user_id} removed from admins.")
    except ValueError:
        await message.reply_text("Invalid User ID.")

@bot.on_message(filters.command("admins") & filters.user(Config.ADMINS))
async def list_admins_cmd(client, message):
    admins = await db.get_admins()
    await message.reply_text(f"Admins: {', '.join(map(str, admins))}")

# --- Settings ---
@bot.on_message(filters.command("setcaption") & filters.create(lambda _, __, m: db.is_admin(m.from_user.id)))
async def set_caption_cmd(client, message):
    caption = message.text.split(None, 1)[1] if len(message.command) > 1 else ""
    await db.set_setting("caption", caption)
    await message.reply_text(f"Caption set to:\n{caption}")

@bot.on_message(filters.command("setfilename") & filters.create(lambda _, __, m: db.is_admin(m.from_user.id)))
async def set_filename_cmd(client, message):
    filename = message.text.split(None, 1)[1] if len(message.command) > 1 else ""
    await db.set_setting("filename", filename)
    await message.reply_text(f"Filename format set to: {filename}")

# --- Search & Scrape ---
@bot.on_message(filters.command("search") & filters.create(lambda _, __, m: db.is_admin(m.from_user.id)))
async def search_cmd(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /search <anime name>")
    
    query = message.text.split(None, 1)[1]
    msg = await message.reply_text(f"Searching for '{query}'...")
    
    results = []
    results.extend(await scraper.search_desidubanime(query))
    results.extend(await scraper.search_animedubhindi(query))
    results.extend(await scraper.search_animesalt(query))
    results.extend(await scraper.search_animehindidubbed(query))
    
    if not results:
        return await msg.edit("No results found.")
    
    buttons = []
    for i, res in enumerate(results[:20]): # Limit to 20 results
        buttons.append([InlineKeyboardButton(f"{res['title']} ({res['source']})", callback_data=f"anime_{i}")])
    
    # Store results in memory for callback (in a real bot, use a database or cache)
    # For simplicity, we'll just show the first few
    await msg.edit(f"Found {len(results)} results:", reply_markup=InlineKeyboardMarkup(buttons))

# --- Callback Handlers ---
@bot.on_callback_query(filters.regex(r"^anime_"))
async def anime_callback(client, callback_query):
    # This would normally fetch the URL from a cache/db
    await callback_query.answer("Fetching episodes...")
    # For now, just a placeholder
    await callback_query.message.edit("Fetching episodes and seasons... (Feature in progress)")

if __name__ == "__main__":
    print("Bot started...")
    bot.run()
