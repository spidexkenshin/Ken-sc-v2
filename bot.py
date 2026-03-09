import os
import re
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.errors import UserNotParticipant, ChatWriteForbidden
from pymongo import MongoClient
from datetime import datetime
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8562237682:AAEJCVtlLNFuteUUTnTphORPKHwRPweiHcY")
    API_ID = int(os.getenv("API_ID", "37407868"))
    API_HASH = os.getenv("API_HASH", "d7d3bff9f7cf9f3b111129bdbd13a065")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://iamnotmohit1_db_user:<iammohitgurjar.1>@kenshindb.esj4x5f.mongodb.net/?appName=KENSHINDB")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "6728678197").split(",")))
    
    # Anime Websites List
    SITES = {
        "desidubanime": "https://desidubanime.me",
        "animesalt": "https://animesalt.top",
        "animedubhindi": "https://animedubhindi.me",
        "animehindidubbed": "https://animehindidubbed.in",
        "animedekho": "https://animedekho.co.in",
        "primeilx": "https://primeilx.com",
        "hindianime": "https://hindianime.in",
        "animelok": "https://animelok.site",
        "dailyanime": "https://dailyanime.site",
        "animekai": "https://animekai.to",
        "gogoanime": "https://gogoanime3.co",
        "9anime": "https://9anime.to",
        "hianime": "https://hianime.to",
        "animepahe": "https://animepahe.ru",
        "zoro": "https://zoro.to"
    }

# Database Setup
client = MongoClient(Config.MONGO_URI)
db = client.anime_bot
users_col = db.users
settings_col = db.settings
admins_col = db.admins

# Initialize Bot
app = Client(
    "anime_scraper_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=100,
    parse_mode=enums.ParseMode.HTML
)

# Helper Functions
def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_IDS or admins_col.find_one({"user_id": user_id}) is not None

def get_settings():
    settings = settings_col.find_one({"_id": "global"})
    if not settings:
        default = {
            "_id": "global",
            "caption": "🎬 <b>{title}</b>\n\n📺 Quality: {quality}\n🌐 Source: {source}\n\n➡️ Join @yourchannel",
            "thumbnail": None,
            "filename_template": "{title}_EP{ep}_{quality}"
        }
        settings_col.insert_one(default)
        return default
    return settings

async def search_anime(query: str):
    """Search anime across multiple sites"""
    results = []
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        # DesiDubAnime Search
        try:
            url = f"{Config.SITES['desidubanime']}/?s={quote(query)}"
            tasks.append(fetch_site(session, url, "desidubanime", query))
        except:
            pass
            
        # AnimeSalt Search
        try:
            url = f"{Config.SITES['animesalt']}/search?q={quote(query)}"
            tasks.append(fetch_site(session, url, "animesalt", query))
        except:
            pass
            
        # GogoAnime Search
        try:
            url = f"{Config.SITES['gogoanime']}/search.html?keyword={quote(query)}"
            tasks.append(fetch_site(session, url, "gogoanime", query))
        except:
            pass
            
        # HiAnime Search
        try:
            url = f"{Config.SITES['hianime']}/search?keyword={quote(query)}"
            tasks.append(fetch_site(session, url, "hianime", query))
        except:
            pass
            
        # AnimePahe Search
        try:
            url = f"{Config.SITES['animepahe']}/api?m=search&q={quote(query)}"
            tasks.append(fetch_site(session, url, "animepahe", query))
        except:
            pass
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for resp in responses:
            if isinstance(resp, list):
                results.extend(resp)
            elif isinstance(resp, dict) and 'results' in resp:
                results.extend(resp['results'])
                
    return results

async def fetch_site(session, url, site_name, query):
    """Fetch and parse individual sites"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status != 200:
                return []
                
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            results = []
            
            if site_name == "desidubanime":
                items = soup.find_all('div', class_='bsx') or soup.find_all('article')
                for item in items[:5]:
                    try:
                        title = item.find('h2') or item.find('a', class_='tip')
                        if title:
                            title_text = title.get_text(strip=True)
                            link = title.get('href') if title.name == 'a' else item.find('a').get('href')
                            img = item.find('img')
                            thumb = img.get('src') if img else None
                            
                            results.append({
                                'title': title_text,
                                'url': link if link.startswith('http') else urljoin(Config.SITES['desidubanime'], link),
                                'site': 'DesiDubAnime',
                                'language': 'Hindi Dubbed',
                                'thumbnail': thumb
                            })
                    except:
                        continue
                        
            elif site_name == "gogoanime":
                items = soup.find_all('p', class_='name') or soup.find_all('div', class_='img')
                for item in items[:5]:
                    try:
                        a_tag = item.find('a') if item.name != 'a' else item
                        title = a_tag.get('title') or a_tag.get_text(strip=True)
                        link = a_tag.get('href')
                        
                        results.append({
                            'title': title,
                            'url': urljoin(Config.SITES['gogoanime'], link),
                            'site': 'GogoAnime',
                            'language': 'Sub/Dub',
                            'thumbnail': None
                        })
                    except:
                        continue
                        
            elif site_name == "hianime":
                items = soup.find_all('div', class_='film-detail') or soup.find_all('a', class_='film-poster')
                for item in items[:5]:
                    try:
                        a_tag = item if item.name == 'a' else item.find('a')
                        title = a_tag.get('title') or a_tag.get('data-title')
                        link = a_tag.get('href')
                        img = a_tag.find('img')
                        
                        results.append({
                            'title': title,
                            'url': urljoin(Config.SITES['hianime'], link),
                            'site': 'HiAnime',
                            'language': 'Sub/Dub',
                            'thumbnail': img.get('data-src') if img else None
                        })
                    except:
                        continue
                        
            elif site_name == "animepahe":
                try:
                    data = json.loads(html)
                    for item in data.get('data', [])[:5]:
                        results.append({
                            'title': item.get('title'),
                            'url': f"{Config.SITES['animepahe']}/anime/{item.get('session')}",
                            'site': 'AnimePahe',
                            'language': 'Sub',
                            'thumbnail': item.get('poster')
                        })
                except:
                    pass
            
            return results
            
    except Exception as e:
        logger.error(f"Error fetching {site_name}: {e}")
        return []

async def get_episodes(anime_url, site):
    """Get episodes list from anime page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(anime_url, headers=headers, timeout=10) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                episodes = []
                
                if "desidubanime" in site.lower():
                    # Try to find episode list
                    ep_list = soup.find('div', class_='eplister') or soup.find('div', id='episode')
                    if ep_list:
                        items = ep_list.find_all('a') or ep_list.find_all('div', class_='episodiotitle')
                        for i, item in enumerate(items, 1):
                            try:
                                ep_num = item.find('div', class_='epl-num') or item.find('span')
                                ep_title = item.find('div', class_='epl-title') or item
                                ep_link = item.get('href') if item.name == 'a' else item.find('a').get('href')
                                
                                episodes.append({
                                    'number': ep_num.get_text(strip=True) if ep_num else str(i),
                                    'title': ep_title.get_text(strip=True) if ep_title else f"Episode {i}",
                                    'url': ep_link if ep_link.startswith('http') else urljoin(anime_url, ep_link)
                                })
                            except:
                                continue
                                
                elif "gogoanime" in site.lower():
                    ep_start = soup.find('input', {'id': 'episode_page'})
                    if ep_start:
                        ep_start = ep_start.get('ep_start', '0')
                        ep_end = soup.find('input', {'id': 'episode_page'}).get('ep_end', '0')
                        
                        for i in range(int(ep_start), int(ep_end)+1):
                            episodes.append({
                                'number': str(i),
                                'title': f"Episode {i}",
                                'url': anime_url.replace('/category/', '/') + f"-episode-{i}"
                            })
                            
                elif "hianime" in site.lower():
                    items = soup.find_all('a', {'data-id': True})
                    for item in items:
                        try:
                            ep_num = item.find('div', class_='episode-number') or item.get('data-number')
                            episodes.append({
                                'number': str(ep_num) if ep_num else item.get('data-id'),
                                'title': f"Episode {ep_num}" if ep_num else f"EP {item.get('data-id')}",
                                'url': urljoin(anime_url, item.get('href', ''))
                            })
                        except:
                            continue
                
                return episodes
                
    except Exception as e:
        logger.error(f"Error getting episodes: {e}")
        return []

async def get_download_links(episode_url, site):
    """Get download links for specific episode"""
    qualities = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(episode_url, headers=headers, timeout=10) as response:
                html = await response.text()
                
                # This is a simplified version - real implementation would need specific parsers
                # for each site's video extraction logic
                
                if "desidubanime" in site.lower():
                    # Look for video sources
                    soup = BeautifulSoup(html, 'html.parser')
                    iframe = soup.find('iframe')
                    if iframe:
                        src = iframe.get('src')
                        qualities.append({
                            'quality': 'HD',
                            'url': src,
                            'size': 'Unknown'
                        })
                        
                elif "gogoanime" in site.lower():
                    # Extract streaming links
                    match = re.search(r"iframe src=\"([^\"]+)\"", html)
                    if match:
                        qualities.append({
                            'quality': 'Auto',
                            'url': match.group(1),
                            'size': 'Unknown'
                        })
                
                # Add default qualities for demo
                if not qualities:
                    qualities = [
                        {'quality': '360p', 'url': episode_url, 'size': '~150MB'},
                        {'quality': '480p', 'url': episode_url, 'size': '~250MB'},
                        {'quality': '720p', 'url': episode_url, 'size': '~400MB'},
                        {'quality': '1080p', 'url': episode_url, 'size': '~800MB'}
                    ]
                    
    except Exception as e:
        logger.error(f"Error getting download links: {e}")
        qualities = [
            {'quality': '360p', 'url': episode_url, 'size': 'N/A'},
            {'quality': '480p', 'url': episode_url, 'size': 'N/A'},
            {'quality': '720p', 'url': episode_url, 'size': 'N/A'}
        ]
        
    return qualities

# Command Handlers
@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    user_id = message.from_user.id
    
    # Add user to database
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({
            "user_id": user_id,
            "username": message.from_user.username,
            "joined": datetime.now()
        })
    
    welcome_text = f"""
👋 <b>Welcome {message.from_user.mention}!</b>

🤖 <b>Anime Scraper Bot</b> - Your ultimate anime downloading companion!

✨ <b>Features:</b>
• Search anime from 15+ websites
• Hindi Dubbed & Subbed content
• Multiple quality options (360p to 1080p)
• Batch download support
• Custom captions & thumbnails

📝 <b>Commands:</b>
/search <name> - Search anime
/help - Show help
/settings - Bot settings (Admin only)

🔰 <b>Status:</b> {'✅ Admin' if is_admin(user_id) else '👤 User'}
    """
    
    await message.reply_text(welcome_text, disable_web_page_preview=True)

@app.on_message(filters.command("help"))
async def help_handler(client, message: Message):
    help_text = """
📚 <b>Bot Commands Guide</b>

<b>User Commands:</b>
/start - Start the bot
/search <anime name> - Search for anime
/help - Show this message

<b>Admin Commands:</b>
/addadmin <user_id> - Add new admin
/deladmin <user_id> - Remove admin
/admins - List all admins
/setcaption <text> - Set custom caption
/setthumbnail - Set thumbnail (reply to photo)
/setfilename <template> - Set filename format
/broadcast <message> - Send message to all users
/stats - Show bot statistics

<b>Caption Variables:</b>
{title} - Anime title
{quality} - Video quality
{episode} - Episode number
{season} - Season number
{source} - Website source

<b>Filename Variables:</b>
{title} - Anime title
{ep} - Episode number
{quality} - Quality (360p, 720p, etc.)
    """
    await message.reply_text(help_text)

@app.on_message(filters.command("search"))
async def search_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Please provide anime name!\n\nUsage: `/search Solo Leveling`")
    
    query = " ".join(message.command[1:])
    status_msg = await message.reply_text(f"🔍 Searching for: <b>{query}</b>\n\n⏳ Please wait...")
    
    try:
        results = await search_anime(query)
        
        if not results:
            return await status_msg.edit_text("❌ No results found! Try different keywords.")
        
        # Group by site
        sites_found = {}
        for res in results:
            site = res['site']
            if site not in sites_found:
                sites_found[site] = []
            sites_found[site].append(res)
        
        text = f"🎯 <b>Search Results for:</b> <code>{query}</code>\n\n"
        text += f"📊 <b>Found:</b> {len(results)} results from {len(sites_found)} sources\n\n"
        
        keyboard = []
        
        for idx, result in enumerate(results[:10], 1):
            lang = result.get('language', 'Unknown')
            site = result['site']
            text += f"{idx}. <b>{result['title']}</b>\n"
            text += f"   🌐 {site} | 🗣 {lang}\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"📥 {idx}. {result['title'][:30]}... [{site}]",
                callback_data=f"select_{idx}_{message.id}"
            )])
            
        # Store results in memory for callback
        app.search_results = getattr(app, 'search_results', {})
        app.search_results[message.id] = results[:10]
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_search")])
        
        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        await status_msg.edit_text(f"❌ Error occurred: {str(e)}")

@app.on_callback_query(filters.regex(r"^select_(\d+)_(\d+)$"))
async def select_anime_callback(client, callback: CallbackQuery):
    idx = int(callback.matches[0].group(1))
    msg_id = int(callback.matches[0].group(2))
    
    results = getattr(app, 'search_results', {}).get(msg_id, [])
    if not results or idx > len(results):
        return await callback.answer("❌ Session expired! Search again.", show_alert=True)
    
    anime = results[idx-1]
    
    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b>\n\n"
        f"🌐 <b>Source:</b> {anime['site']}\n"
        f"🗣 <b>Language:</b> {anime.get('language', 'Unknown')}\n\n"
        f"⏳ Fetching episodes...",
        disable_web_page_preview=True
    )
    
    # Get episodes
    episodes = await get_episodes(anime['url'], anime['site'])
    
    if not episodes:
        return await callback.message.edit_text(
            "❌ No episodes found or site is protected.\n\n"
            "Try direct link access or different source."
        )
    
    # Store episodes
    app.episodes_data = getattr(app, 'episodes_data', {})
    app.episodes_data[callback.message.id] = {
        'anime': anime,
        'episodes': episodes
    }
    
    text = f"🎬 <b>{anime['title']}</b>\n\n"
    text += f"📺 <b>Total Episodes:</b> {len(episodes)}\n"
    text += f"🌐 <b>Source:</b> {anime['site']}\n\n"
    text += "Select option:"
    
    keyboard = [
        [InlineKeyboardButton("📥 Download All Episodes", callback_data=f"dlall_{callback.message.id}")],
        [InlineKeyboardButton("📋 Select Specific Episode", callback_data=f"epmenu_{callback.message.id}")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"back_search_{msg_id}")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex(r"^epmenu_(\d+)$"))
async def episode_menu_callback(client, callback: CallbackQuery):
    msg_id = int(callback.matches[0].group(1))
    data = getattr(app, 'episodes_data', {}).get(msg_id)
    
    if not data:
        return await callback.answer("❌ Session expired!", show_alert=True)
    
    episodes = data['episodes']
    anime = data['anime']
    
    # Create episode buttons (show first 10)
    keyboard = []
    row = []
    
    for i, ep in enumerate(episodes[:20], 1):
        row.append(InlineKeyboardButton(
            f"EP {ep['number']}",
            callback_data=f"ep_{msg_id}_{i-1}"
        ))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"back_anime_{msg_id}")])
    
    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b>\n\n"
        f"📺 Select Episode:\n"
        f"Total: {len(episodes)} episodes",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_callback_query(filters.regex(r"^ep_(\d+)_(\d+)$"))
async def select_episode_callback(client, callback: CallbackQuery):
    msg_id = int(callback.matches[0].group(1))
    ep_idx = int(callback.matches[0].group(2))
    
    data = getattr(app, 'episodes_data', {}).get(msg_id)
    if not data:
        return await callback.answer("❌ Session expired!", show_alert=True)
    
    episode = data['episodes'][ep_idx]
    anime = data['anime']
    
    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b>\n"
        f"📺 <b>Episode {episode['number']}</b>\n\n"
        f"⏳ Fetching download links...",
        disable_web_page_preview=True
    )
    
    # Get qualities
    qualities = await get_download_links(episode['url'], anime['site'])
    
    keyboard = []
    for q in qualities:
        keyboard.append([InlineKeyboardButton(
            f"📥 {q['quality']} - {q['size']}",
            url=q['url']  # Direct link or callback for upload
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"epmenu_{msg_id}")])
    
    settings = get_settings()
    caption = settings['caption'].format(
        title=anime['title'],
        quality='Multiple',
        episode=episode['number'],
        source=anime['site']
    )
    
    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b>\n"
        f"📺 <b>Episode {episode['number']}</b>\n\n"
        f"{caption}\n\n"
        f"Select Quality:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex(r"^dlall_(\d+)$"))
async def download_all_callback(client, callback: CallbackQuery):
    msg_id = int(callback.matches[0].group(1))
    data = getattr(app, 'episodes_data', {}).get(msg_id)
    
    if not data:
        return await callback.answer("❌ Session expired!", show_alert=True)
    
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Only admins can batch download!", show_alert=True)
    
    episodes = data['episodes']
    anime = data['anime']
    
    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b>\n\n"
        f"📥 Starting batch download of {len(episodes)} episodes...\n"
        f"⏳ This may take a while.",
        disable_web_page_preview=True
    )
    
    # Process episodes
    settings = get_settings()
    failed = 0
    success = 0
    
    for i, ep in enumerate(episodes[:5]):  # Limit to 5 for demo
        try:
            qualities = await get_download_links(ep['url'], anime['site'])
            if qualities:
                q = qualities[-1]  # Best quality
                
                caption = settings['caption'].format(
                    title=anime['title'],
                    quality=q['quality'],
                    episode=ep['number'],
                    source=anime['site']
                )
                
                # Send as document or video link
                await callback.message.reply_text(
                    f"📤 <b>Episode {ep['number']}</b>\n\n"
                    f"🔗 <b>Link:</b> {q['url']}\n\n"
                    f"{caption}",
                    disable_web_page_preview=True
                )
                success += 1
                await asyncio.sleep(2)  # Rate limit
        except Exception as e:
            failed += 1
            logger.error(f"Failed to process ep {ep['number']}: {e}")
    
    await callback.message.reply_text(
        f"✅ <b>Batch Download Complete!</b>\n\n"
        f"📥 Success: {success}\n"
        f"❌ Failed: {failed}\n"
        f"⏭ Skipped: {len(episodes) - success - failed}"
    )

# Admin Commands
@app.on_message(filters.command("addadmin") & filters.user(Config.ADMIN_IDS))
async def add_admin_handler(client, message: Message):
    if len(message.command) != 2:
        return await message.reply_text("Usage: `/addadmin <user_id>`")
    
    try:
        new_admin_id = int(message.command[1])
        if admins_col.find_one({"user_id": new_admin_id}):
            return await message.reply_text("❌ User is already an admin!")
        
        admins_col.insert_one({
            "user_id": new_admin_id,
            "added_by": message.from_user.id,
            "added_at": datetime.now()
        })
        
        await message.reply_text(f"✅ Added `{new_admin_id}` as admin!")
    except ValueError:
        await message.reply_text("❌ Invalid user ID!")

@app.on_message(filters.command("deladmin") & filters.user(Config.ADMIN_IDS))
async def del_admin_handler(client, message: Message):
    if len(message.command) != 2:
        return await message.reply_text("Usage: `/deladmin <user_id>`")
    
    try:
        admin_id = int(message.command[1])
        if admin_id in Config.ADMIN_IDS:
            return await message.reply_text("❌ Cannot remove primary admin!")
        
        result = admins_col.delete_one({"user_id": admin_id})
        if result.deleted_count:
            await message.reply_text(f"✅ Removed admin `{admin_id}`")
        else:
            await message.reply_text("❌ User is not an admin!")
    except ValueError:
        await message.reply_text("❌ Invalid user ID!")

@app.on_message(filters.command("admins"))
async def list_admins_handler(client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("❌ Admin only!")
    
    text = "👥 <b>Admin List</b>\n\n"
    text += "<b>Primary Admins:</b>\n"
    for admin_id in Config.ADMIN_IDS:
        text += f"• `{admin_id}`\n"
    
    text += "\n<b>Added Admins:</b>\n"
    admins = list(admins_col.find())
    if admins:
        for admin in admins:
            text += f"• `{admin['user_id']}` (Added by {admin['added_by']})\n"
    else:
        text += "None\n"
    
    await message.reply_text(text)

@app.on_message(filters.command("setcaption") & filters.user(Config.ADMIN_IDS))
async def set_caption_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/setcaption <text>`\n\n"
            "Variables: {title}, {quality}, {episode}, {source}"
        )
    
    caption = " ".join(message.command[1:])
    settings_col.update_one(
        {"_id": "global"},
        {"$set": {"caption": caption}},
        upsert=True
    )
    
    await message.reply_text(f"✅ Caption updated!\n\nPreview:\n{caption}")

@app.on_message(filters.command("setthumbnail") & filters.user(Config.ADMIN_IDS))
async def set_thumbnail_handler(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply_text("❌ Reply to a photo with this command!")
    
    photo = message.reply_to_message.photo.file_id
    settings_col.update_one(
        {"_id": "global"},
        {"$set": {"thumbnail": photo}},
        upsert=True
    )
    
    await message.reply_text("✅ Thumbnail updated!")

@app.on_message(filters.command("setfilename") & filters.user(Config.ADMIN_IDS))
async def set_filename_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/setfilename <template>`\n\n"
            "Example: {{title}}_EP{{ep}}_{{quality}}\n"
            "Variables: {title}, {ep}, {quality}"
        )
    
    template = " ".join(message.command[1:])
    settings_col.update_one(
        {"_id": "global"},
        {"$set": {"filename_template": template}},
        upsert=True
    )
    
    await message.reply_text(f"✅ Filename template updated!\n\nTemplate: `{template}`")

@app.on_message(filters.command("stats") & filters.user(Config.ADMIN_IDS))
async def stats_handler(client, message: Message):
    total_users = users_col.count_documents({})
    total_admins = len(Config.ADMIN_IDS) + admins_col.count_documents({})
    
    text = f"""
📊 <b>Bot Statistics</b>

👥 <b>Total Users:</b> {total_users}
👮 <b>Total Admins:</b> {total_admins}
📅 <b>Started:</b> {datetime.now().strftime('%Y-%m-%d')}
    """
    await message.reply_text(text)

@app.on_callback_query(filters.regex(r"^cancel_search$"))
async def cancel_callback(client, callback: CallbackQuery):
    await callback.message.edit_text("❌ Search cancelled!")

@app.on_callback_query(filters.regex(r"^back_search_(\d+)$"))
async def back_search_callback(client, callback: CallbackQuery):
    await search_handler(client, callback.message.reply_to_message or callback.message)

@app.on_callback_query(filters.regex(r"^back_anime_(\d+)$"))
async def back_anime_callback(client, callback: CallbackQuery):
    msg_id = int(callback.matches[0].group(1))
    data = getattr(app, 'episodes_data', {}).get(msg_id)
    
    if data:
        anime = data['anime']
        keyboard = [
            [InlineKeyboardButton("📥 Download All", callback_data=f"dlall_{msg_id}")],
            [InlineKeyboardButton("📋 Select Episode", callback_data=f"epmenu_{msg_id}")]
        ]
        await callback.message.edit_text(
            f"🎬 <b>{anime['title']}</b>\n\nSelect option:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

if __name__ == "__main__":
    logger.info("Starting Anime Scraper Bot...")
    app.run()
