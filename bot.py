import os
import re
import asyncio
import aiohttp
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, unquote
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config - Directly yahan se le raha hu, Railway variables bhi support karega
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8562237682:AAEJCVtlLNFuteUUTnTphORPKHwRPweiHcY")
    API_ID = int(os.getenv("API_ID", "37407868"))
    API_HASH = os.getenv("API_HASH", "d7d3bff9f7cf9f3b111129bdbd13a065")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "6728678197").split(",")))
    
    # Target Websites (Real-time scraping)
    SITES = {
        "desidubanime": {
            "url": "https://desidubanime.me",
            "search_path": "/?s={query}",
            "name": "DesiDubAnime"
        },
        "animesalt": {
            "url": "https://animesalt.top",
            "search_path": "/search?q={query}",
            "name": "AnimeSalt"
        },
        "animedubhindi": {
            "url": "https://animedubhindi.me",
            "search_path": "/?s={query}",
            "name": "AnimeDubHindi"
        },
        "animehindidubbed": {
            "url": "https://animehindidubbed.in",
            "search_path": "/?s={query}",
            "name": "AnimeHindiDubbed"
        }
    }

# Initialize Bot
app = Client(
    "anime_scraper_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    workers=100,
    parse_mode=enums.ParseMode.HTML
)

# In-memory storage (No MongoDB needed)
user_sessions = {}
search_cache = {}
settings = {
    "caption": "🎬 <b>{title}</b>\n📺 Episode: {episode}\n🌐 Source: {source}\n🔰 Quality: {quality}\n\n⚡ Join @yourchannel",
    "thumbnail": None,
    "filename": "{title}_EP{episode}_{quality}"
}

def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_IDS

# ============== REAL-TIME SCRAPING FUNCTIONS ==============

async def fetch_page(url, headers=None, timeout=15):
    """Generic page fetcher with error handling"""
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=default_headers, timeout=timeout, ssl=False) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"HTTP {response.status} for {url}")
                    return None
    except Exception as e:
        logger.error(f"Fetch error for {url}: {e}")
        return None

async def search_desidubanime(query):
    """Search DesiDubAnime.me"""
    try:
        search_url = f"{Config.SITES['desidubanime']['url']}/?s={quote(query)}"
        html = await fetch_page(search_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Try multiple selectors
        items = soup.find_all('div', class_='bsx') or \
                soup.find_all('article', class_='bsx') or \
                soup.find_all('div', class_='tt') or \
                soup.select('.listupd .bsx') or \
                soup.find_all('a', class_='tip')
        
        for item in items[:8]:
            try:
                # Extract link
                link_tag = item if item.name == 'a' else item.find('a', href=True)
                if not link_tag:
                    continue
                
                link = link_tag.get('href')
                if not link:
                    continue
                
                # Full URL
                if not link.startswith('http'):
                    link = urljoin(Config.SITES['desidubanime']['url'], link)
                
                # Extract title
                title_tag = item.find('h2') or item.find('div', class_='tt') or item.find('img', alt=True)
                title = ""
                if title_tag:
                    if title_tag.name == 'img':
                        title = title_tag.get('alt', '')
                    else:
                        title = title_tag.get_text(strip=True)
                
                if not title and link_tag.get('title'):
                    title = link_tag.get('title')
                
                # Extract thumbnail
                img = item.find('img')
                thumb = None
                if img:
                    thumb = img.get('data-src') or img.get('src') or img.get('data-lazy-src')
                
                # Extract type/language info
                type_tag = item.find('span', class_='type') or item.find('div', class_='type')
                lang = "Hindi Dubbed"
                if type_tag:
                    type_text = type_tag.get_text(strip=True).lower()
                    if 'sub' in type_text:
                        lang = "Subbed"
                    elif 'dub' in type_text:
                        lang = "Dubbed"
                
                if title and link:
                    results.append({
                        'title': title,
                        'url': link,
                        'site': 'DesiDubAnime',
                        'language': lang,
                        'thumbnail': thumb,
                        'type': 'TV Series'
                    })
            except Exception as e:
                continue
                
        return results
    except Exception as e:
        logger.error(f"DesiDubAnime search error: {e}")
        return []

async def search_animesalt(query):
    """Search AnimeSalt.top"""
    try:
        search_url = f"{Config.SITES['animesalt']['url']}/search?q={quote(query)}"
        html = await fetch_page(search_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # AnimeSalt specific selectors
        items = soup.find_all('div', class_='anime-item') or \
                soup.find_all('div', class_='item') or \
                soup.find_all('article') or \
                soup.select('.anime-list .item')
        
        for item in items[:8]:
            try:
                link_tag = item.find('a', href=True)
                if not link_tag:
                    continue
                
                link = link_tag.get('href')
                if not link.startswith('http'):
                    link = urljoin(Config.SITES['animesalt']['url'], link)
                
                title_tag = item.find('h3') or item.find('h4') or item.find('div', class_='title') or item.find('img', alt=True)
                title = ""
                if title_tag:
                    if title_tag.name == 'img':
                        title = title_tag.get('alt', '')
                    else:
                        title = title_tag.get_text(strip=True)
                
                img = item.find('img')
                thumb = None
                if img:
                    thumb = img.get('data-src') or img.get('src')
                
                # Check for Hindi tag
                tags = item.find_all('span', class_='badge') or item.find_all('div', class_='tag')
                lang = "Hindi Dubbed"
                for tag in tags:
                    tag_text = tag.get_text(strip=True).lower()
                    if 'hindi' in tag_text:
                        lang = "Hindi Dubbed"
                        break
                    elif 'sub' in tag_text:
                        lang = "Subbed"
                
                if title and link:
                    results.append({
                        'title': title,
                        'url': link,
                        'site': 'AnimeSalt',
                        'language': lang,
                        'thumbnail': thumb,
                        'type': 'Anime'
                    })
            except Exception as e:
                continue
                
        return results
    except Exception as e:
        logger.error(f"AnimeSalt search error: {e}")
        return []

async def search_animedubhindi(query):
    """Search AnimeDubHindi.me"""
    try:
        search_url = f"{Config.SITES['animedubhindi']['url']}/?s={quote(query)}"
        html = await fetch_page(search_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        items = soup.find_all('div', class_='bsx') or \
                soup.find_all('article') or \
                soup.select('.listupd article')
        
        for item in items[:8]:
            try:
                link_tag = item.find('a', href=True)
                if not link_tag:
                    continue
                
                link = link_tag.get('href')
                if not link.startswith('http'):
                    link = urljoin(Config.SITES['animedubhindi']['url'], link)
                
                title = ""
                title_tag = item.find('h2') or item.find('div', class_='tt') or item.find('img', alt=True)
                if title_tag:
                    if title_tag.name == 'img':
                        title = title_tag.get('alt', '')
                    else:
                        title = title_tag.get_text(strip=True)
                
                img = item.find('img')
                thumb = img.get('data-src') or img.get('src') if img else None
                
                # Language detection
                lang_tag = item.find('span', class_='sb') or item.find('div', class_='type')
                lang = "Hindi Dubbed"
                if lang_tag:
                    lang_text = lang_tag.get_text(strip=True).lower()
                    if 'hindi' in lang_text or 'dub' in lang_text:
                        lang = "Hindi Dubbed"
                
                if title and link:
                    results.append({
                        'title': title,
                        'url': link,
                        'site': 'AnimeDubHindi',
                        'language': lang,
                        'thumbnail': thumb,
                        'type': 'Series'
                    })
            except Exception as e:
                continue
                
        return results
    except Exception as e:
        logger.error(f"AnimeDubHindi search error: {e}")
        return []

async def search_animehindidubbed(query):
    """Search AnimeHindiDubbed.in"""
    try:
        search_url = f"{Config.SITES['animehindidubbed']['url']}/?s={quote(query)}"
        html = await fetch_page(search_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        items = soup.find_all('div', class_='bsx') or \
                soup.find_all('article', class_='bsx') or \
                soup.select('.listupd .bsx')
        
        for item in items[:8]:
            try:
                link_tag = item.find('a', href=True)
                if not link_tag:
                    continue
                
                link = link_tag.get('href')
                if not link.startswith('http'):
                    link = urljoin(Config.SITES['animehindidubbed']['url'], link)
                
                title_tag = item.find('h2') or item.find('div', class_='tt') or item.find('img', alt=True)
                title = ""
                if title_tag:
                    if title_tag.name == 'img':
                        title = title_tag.get('alt', '')
                    else:
                        title = title_tag.get_text(strip=True)
                
                img = item.find('img')
                thumb = img.get('data-src') or img.get('src') if img else None
                
                status_tag = item.find('div', class_='status') or item.find('span', class_='status')
                lang = "Hindi Dubbed"
                if status_tag:
                    status_text = status_tag.get_text(strip=True).lower()
                    if 'dubbed' in status_text or 'hindi' in status_text:
                        lang = "Hindi Dubbed"
                
                if title and link:
                    results.append({
                        'title': title,
                        'url': link,
                        'site': 'AnimeHindiDubbed',
                        'language': lang,
                        'thumbnail': thumb,
                        'type': 'Anime'
                    })
            except Exception as e:
                continue
                
        return results
    except Exception as e:
        logger.error(f"AnimeHindiDubbed search error: {e}")
        return []

async def search_all_sites(query):
    """Search all sites concurrently"""
    tasks = [
        search_desidubanime(query),
        search_animesalt(query),
        search_animedubhindi(query),
        search_animehindidubbed(query)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_results = []
    
    for result in results:
        if isinstance(result, list):
            all_results.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"Search task failed: {result}")
    
    return all_results

# ============== EPISODE & VIDEO EXTRACTION ==============

async def get_episodes_desidubanime(anime_url):
    """Extract episodes from DesiDubAnime"""
    try:
        html = await fetch_page(anime_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        episodes = []
        
        # Method 1: Eplister (standard WordPress anime theme)
        ep_list = soup.find('div', class_='eplister') or soup.find('div', id='episodes')
        if ep_list:
            items = ep_list.find_all('a') or ep_list.find_all('div', class_='epl-item')
            for item in items:
                try:
                    ep_num = ""
                    ep_title = ""
                    
                    num_tag = item.find('div', class_='epl-num') or item.find('span', class_='num')
                    if num_tag:
                        ep_num = num_tag.get_text(strip=True)
                    
                    title_tag = item.find('div', class_='epl-title') or item.find('span', class_='title')
                    if title_tag:
                        ep_title = title_tag.get_text(strip=True)
                    
                    link = item.get('href') if item.name == 'a' else item.find('a', href=True)
                    if link:
                        if isinstance(link, str):
                            ep_link = link
                        else:
                            ep_link = link.get('href')
                        
                        if ep_link and not ep_link.startswith('http'):
                            ep_link = urljoin(anime_url, ep_link)
                        
                        episodes.append({
                            'number': ep_num or str(len(episodes) + 1),
                            'title': ep_title or f"Episode {ep_num or len(episodes) + 1}",
                            'url': ep_link
                        })
                except:
                    continue
        
        # Method 2: Alternative selectors
        if not episodes:
            items = soup.select('.episodelist a') or soup.find_all('a', href=re.compile(r'episode-\d+'))
            for item in items:
                try:
                    href = item.get('href', '')
                    match = re.search(r'episode-(\d+)', href, re.I)
                    if match:
                        ep_num = match.group(1)
                        episodes.append({
                            'number': ep_num,
                            'title': f"Episode {ep_num}",
                            'url': href if href.startswith('http') else urljoin(anime_url, href)
                        })
                except:
                    continue
        
        return episodes[::-1]  # Reverse to get EP1 first
    except Exception as e:
        logger.error(f"Get episodes error: {e}")
        return []

async def get_episodes_animesalt(anime_url):
    """Extract episodes from AnimeSalt"""
    try:
        html = await fetch_page(anime_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        episodes = []
        
        # Common AnimeSalt structure
        items = soup.find_all('div', class_='episode-item') or \
                soup.find_all('a', class_='episode-link') or \
                soup.select('.episode-list a')
        
        for item in items:
            try:
                link = item.get('href') if item.name == 'a' else item.find('a', href=True)
                if not link:
                    continue
                
                if isinstance(link, str):
                    ep_link = link
                else:
                    ep_link = link.get('href')
                
                if not ep_link.startswith('http'):
                    ep_link = urljoin(anime_url, ep_link)
                
                # Extract episode number
                ep_num = ""
                num_tag = item.find('div', class_='ep-number') or item.find('span', class_='number')
                if num_tag:
                    ep_num = num_tag.get_text(strip=True)
                else:
                    match = re.search(r'episode[/_-]?(\d+)', ep_link, re.I)
                    if match:
                        ep_num = match.group(1)
                
                title = item.get_text(strip=True) or f"Episode {ep_num}"
                
                if ep_num:
                    episodes.append({
                        'number': ep_num,
                        'title': title,
                        'url': ep_link
                    })
            except:
                continue
        
        return episodes
    except Exception as e:
        logger.error(f"AnimeSalt episodes error: {e}")
        return []

async def get_video_links(episode_url, site_name):
    """Extract direct video/streaming links from episode page"""
    try:
        html = await fetch_page(episode_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        qualities = []
        
        # Method 1: Find iframe (embedded players)
        iframe = soup.find('iframe', src=True)
        if iframe:
            src = iframe.get('src')
            if src:
                qualities.append({
                    'quality': 'Stream',
                    'url': src if src.startswith('http') else urljoin(episode_url, src),
                    'type': 'embed'
                })
        
        # Method 2: Find video tags
        video = soup.find('video', src=True) or soup.find('video')
        if video:
            src = video.get('src')
            if src:
                qualities.append({
                    'quality': 'Direct',
                    'url': urljoin(episode_url, src),
                    'type': 'direct'
                })
            
            # Check sources
            sources = video.find_all('source')
            for source in sources:
                src = source.get('src')
                res = source.get('res', '') or source.get('label', '') or source.get('title', '')
                if src:
                    qualities.append({
                        'quality': res or 'Auto',
                        'url': urljoin(episode_url, src),
                        'type': 'direct'
                    })
        
        # Method 3: Find download links
        download_div = soup.find('div', class_='download') or soup.find('div', id='download')
        if download_div:
            links = download_div.find_all('a', href=True)
            for link in links:
                try:
                    href = link.get('href')
                    text = link.get_text(strip=True)
                    
                    # Extract quality from text
                    quality = 'Unknown'
                    if '1080' in text:
                        quality = '1080p'
                    elif '720' in text:
                        quality = '720p'
                    elif '480' in text:
                        quality = '480p'
                    elif '360' in text:
                        quality = '360p'
                    elif '240' in text:
                        quality = '240p'
                    
                    if href and not href.startswith('javascript'):
                        qualities.append({
                            'quality': quality,
                            'url': href if href.startswith('http') else urljoin(episode_url, href),
                            'type': 'download'
                        })
                except:
                    continue
        
        # Method 4: Regex patterns for common video hosts
        patterns = [
            r'(https?://[^\s"\'<>]+\.mp4)',
            r'(https?://[^\s"\'<>]*stream[^\s"\'<>]*)',
            r'(https?://[^\s"\'<>]*video[^\s"\'<>]*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches[:3]:  # Limit to avoid duplicates
                if match not in [q['url'] for q in qualities]:
                    qualities.append({
                        'quality': 'Auto',
                        'url': match,
                        'type': 'regex'
                    })
        
        # If nothing found, return placeholder for manual inspection
        if not qualities:
            qualities.append({
                'quality': 'Visit Site',
                'url': episode_url,
                'type': 'manual'
            })
        
        return qualities
    except Exception as e:
        logger.error(f"Video extraction error: {e}")
        return [{'quality': 'Error', 'url': episode_url, 'type': 'error'}]

# ============== BOT HANDLERS ==============

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    user_id = message.from_user.id
    
    welcome_text = f"""
👋 <b>Welcome {message.from_user.mention}!</b>

🤖 <b>Anime Scraper Bot Pro</b> - Real-time Hindi Anime Downloader!

✨ <b>Features:</b>
• 🔍 Search from 4+ Hindi Anime Sites
• ⚡ Real-time scraping (No Database)
• 🎬 Direct Video Links
• 📥 Multiple Quality Options
• 🇮🇳 Hindi Dubbed Focus

📝 <b>Commands:</b>
/search <name> - Search anime (e.g., /search Solo Leveling)
/help - Show help
/about - Bot info

🔰 <b>Status:</b> {'👑 Owner' if user_id in Config.ADMIN_IDS else '👤 User'}
    """
    
    await message.reply_text(welcome_text, disable_web_page_preview=True)

@app.on_message(filters.command("help"))
async def help_handler(client, message: Message):
    help_text = """
📚 <b>Bot Commands</b>

<b>User Commands:</b>
/start - Start bot
/search <anime name> - Search across all sites
/help - This message
/about - Bot information

<b>How to Use:</b>
1. Send /search followed by anime name
2. Click on desired result
3. Select Episode or Download All
4. Choose Quality
5. Get Direct Link!

<b>Supported Sites:</b>
• DesiDubAnime.me
• AnimeSalt.top  
• AnimeDubHindi.me
• AnimeHindiDubbed.in

⚠️ <b>Note:</b> Links are scraped in real-time. If site is down, search may fail.
    """
    await message.reply_text(help_text)

@app.on_message(filters.command("about"))
async def about_handler(client, message: Message):
    await message.reply_text("""
🤖 <b>Anime Scraper Bot Pro</b>

🛠 <b>Version:</b> 2.0
⚡ <b>Engine:</b> Real-time Scraping
💾 <b>Storage:</b> In-Memory (No DB)
🐍 <b>Python:</b> 3.11+ Compatible

👑 <b>Admin:</b> @yourusername
📢 <b>Channel:</b> @yourchannel

<b>Credits:</b>
• Pyrogram
• BeautifulSoup4
• aiohttp
    """)

@app.on_message(filters.command("search"))
async def search_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ <b>Usage:</b> <code>/search anime name</code>\n\n"
            "Example: <code>/search Solo Leveling</code>\n"
            "Example: <code>/search Demon Slayer</code>",
            quote=True
        )
    
    query = " ".join(message.command[1:])
    
    # Check cache first (5 min cache)
    cache_key = f"{message.from_user.id}:{query.lower()}"
    current_time = datetime.now().timestamp()
    
    if cache_key in search_cache:
        cached_data, cached_time = search_cache[cache_key]
        if current_time - cached_time < 300:  # 5 minutes
            return await display_results(message, cached_data, query, cache_key)
    
    status_msg = await message.reply_text(
        f"🔍 <b>Searching for:</b> <code>{query}</code>\n\n"
        f"⏳ Searching DesiDubAnime.me...\n"
        f"⏳ Searching AnimeSalt.top...\n"
        f"⏳ Searching AnimeDubHindi.me...\n"
        f"⏳ Searching AnimeHindiDubbed.in...\n\n"
        f"<i>Please wait 10-15 seconds...</i>",
        quote=True
    )
    
    try:
        # Search all sites
        results = await search_all_sites(query)
        
        if not results:
            return await status_msg.edit_text(
                f"❌ <b>No results found for:</b> <code>{query}</code>\n\n"
                f"💡 <b>Tips:</b>\n"
                f"• Check spelling\n"
                f"• Try shorter names (e.g., 'Demon Slayer' instead of 'Demon Slayer: Kimetsu no Yaiba')\n"
                f"• Try English names\n"
                f"• Sites might be temporarily down"
            )
        
        # Store in cache
        search_cache[cache_key] = (results, current_time)
        
        # Store in session for callbacks
        user_sessions[message.from_user.id] = {
            'results': results,
            'query': query,
            'timestamp': current_time
        }
        
        await display_results(message, results, query, cache_key, status_msg)
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        await status_msg.edit_text(f"❌ Error occurred: {str(e)}")

async def display_results(message, results, query, cache_key, status_msg=None):
    """Display search results with inline buttons"""
    
    # Group by site
    sites_count = {}
    for r in results:
        site = r['site']
        sites_count[site] = sites_count.get(site, 0) + 1
    
    text = f"🎯 <b>Search Results:</b> <code>{query}</code>\n\n"
    text += f"📊 <b>Found {len(results)} results</b>\n"
    text += "├─ " + "\n├─ ".join([f"<b>{site}:</b> {count}" for site, count in sites_count.items()])
    text += "\n\n<b>Select an anime:</b>\n\n"
    
    keyboard = []
    
    for idx, result in enumerate(results[:10], 1):
        emoji = "🎬" if "movie" in result.get('type', '').lower() else "📺"
        lang_emoji = "🇮🇳" if "hindi" in result['language'].lower() else "🇯🇵"
        
        text += f"{idx}. {emoji} <b>{result['title']}</b>\n"
        text += f"   └─ 🌐 {result['site']} | {lang_emoji} {result['language']}\n\n"
        
        keyboard.append([InlineKeyboardButton(
            f"{idx}. {result['title'][:35]}{'...' if len(result['title']) > 35 else ''}",
            callback_data=f"anime_{message.from_user.id}_{idx-1}"
        )])
    
    keyboard.append([
        InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{cache_key}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{message.from_user.id}")
    ])
    
    if status_msg:
        await status_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    else:
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )

@app.on_callback_query(filters.regex(r"^anime_(\d+)_(\d+)$"))
async def anime_selected_callback(client, callback: CallbackQuery):
    user_id = int(callback.matches[0].group(1))
    idx = int(callback.matches[0].group(2))
    
    if user_id != callback.from_user.id:
        return await callback.answer("❌ This is not your search!", show_alert=True)
    
    session = user_sessions.get(user_id)
    if not session:
        return await callback.answer("❌ Session expired! Search again.", show_alert=True)
    
    results = session.get('results', [])
    if idx >= len(results):
        return await callback.answer("❌ Invalid selection!", show_alert=True)
    
    anime = results[idx]
    
    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b>\n\n"
        f"🌐 <b>Source:</b> {anime['site']}\n"
        f"🗣 <b>Language:</b> {anime['language']}\n"
        f"📺 <b>Type:</b> {anime.get('type', 'Unknown')}\n\n"
        f"⏳ <i>Fetching episodes...</i>",
        disable_web_page_preview=True
    )
    
    # Get episodes based on site
    if anime['site'] == 'DesiDubAnime':
        episodes = await get_episodes_desidubanime(anime['url'])
    elif anime['site'] == 'AnimeSalt':
        episodes = await get_episodes_animesalt(anime['url'])
    else:
        # Generic method for other sites
        episodes = await get_episodes_desidubanime(anime['url'])
    
    if not episodes:
        return await callback.message.edit_text(
            f"❌ <b>No episodes found!</b>\n\n"
            f"🎬 <b>{anime['title']}</b>\n"
            f"🌐 <b>Source:</b> {anime['site']}\n\n"
            f"💡 <b>Possible reasons:</b>\n"
            f"• Site structure changed\n"
            f"• Cloudflare protection active\n"
            f"• Anime page has different layout\n\n"
            f"🔗 <b>Direct Link:</b> {anime['url']}",
            disable_web_page_preview=True
        )
    
    # Store episodes in session
    session['current_anime'] = anime
    session['episodes'] = episodes
    
    text = f"🎬 <b>{anime['title']}</b>\n\n"
    text += f"📺 <b>Total Episodes:</b> {len(episodes)}\n"
    text += f"🌐 <b>Source:</b> {anime['site']}\n"
    text += f"🗣 <b>Language:</b> {anime['language']}\n\n"
    text += "<b>Choose an option:</b>"
    
    keyboard = [
        [InlineKeyboardButton("📥 Download All Episodes", callback_data=f"dlall_{user_id}")],
        [InlineKeyboardButton("📋 Select Specific Episode", callback_data=f"epmenu_{user_id}")],
        [InlineKeyboardButton("🔙 Back to Results", callback_data=f"back_{user_id}")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex(r"^epmenu_(\d+)$"))
async def episode_menu_callback(client, callback: CallbackQuery):
    user_id = int(callback.matches[0].group(1))
    
    if user_id != callback.from_user.id:
        return await callback.answer("❌ Not your session!", show_alert=True)
    
    session = user_sessions.get(user_id)
    if not session or 'episodes' not in session:
        return await callback.answer("❌ Session expired!", show_alert=True)
    
    anime = session['current_anime']
    episodes = session['episodes']
    
    # Create episode buttons (5 per row)
    keyboard = []
    row = []
    
    for i, ep in enumerate(episodes[:50], 1):  # Show first 50
        btn_text = f"EP {ep['number']}"
        row.append(InlineKeyboardButton(
            btn_text,
            callback_data=f"ep_{user_id}_{i-1}"
        ))
        
        if len(row) == 5:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Add navigation if more than 50
    if len(episodes) > 50:
        keyboard.append([InlineKeyboardButton(f"📄 Page 1/{(len(episodes)//50)+1}", callback_data="noop")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"anime_back_{user_id}")])
    
    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b>\n\n"
        f"📺 <b>Select Episode:</b>\n"
        f"Total: {len(episodes)} episodes\n\n"
        f"<i>Click on episode number:</i>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_callback_query(filters.regex(r"^ep_(\d+)_(\d+)$"))
async def episode_selected_callback(client, callback: CallbackQuery):
    user_id = int(callback.matches[0].group(1))
    ep_idx = int(callback.matches[0].group(2))
    
    if user_id != callback.from_user.id:
        return await callback.answer("❌ Not your session!", show_alert=True)
    
    session = user_sessions.get(user_id)
    if not session or 'episodes' not in session:
        return await callback.answer("❌ Session expired!", show_alert=True)
    
    episodes = session['episodes']
    if ep_idx >= len(episodes):
        return await callback.answer("❌ Invalid episode!", show_alert=True)
    
    episode = episodes[ep_idx]
    anime = session['current_anime']
    
    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b>\n"
        f"📺 <b>Episode {episode['number']}</b>\n\n"
        f"⏳ <i>Extracting video links...</i>\n"
        f"<i>This may take 5-10 seconds...</i>",
        disable_web_page_preview=True
    )
    
    # Get video links
    qualities = await get_video_links(episode['url'], anime['site'])
    
    if not qualities:
        return await callback.message.edit_text(
            f"❌ <b>No video links found!</b>\n\n"
            f"🎬 <b>{anime['title']}</b> - EP {episode['number']}\n"
            f"🔗 <b>Episode Page:</b> {episode['url']}\n\n"
            f"<i>Try visiting the site directly or try another episode.</i>",
            disable_web_page_preview=True
        )
    
    # Build quality buttons
    keyboard = []
    text = f"🎬 <b>{anime['title']}</b>\n"
    text += f"📺 <b>Episode {episode['number']}</b>\n"
    text += f"🌐 <b>Source:</b> {anime['site']}\n\n"
    text += "<b>Available Qualities:</b>\n\n"
    
    for i, q in enumerate(qualities[:6], 1):
        quality_name = q['quality']
        url = q['url']
        q_type = q['type']
        
        # Shorten URL for display
        display_url = url[:50] + '...' if len(url) > 50 else url
        
        text += f"{i}. <b>{quality_name}</b> ({q_type})\n"
        text += f"   └─ <code>{display_url}</code>\n\n"
        
        keyboard.append([InlineKeyboardButton(
            f"📥 {quality_name} - {q_type.upper()}",
            url=url if url.startswith('http') else "https://" + url
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Episodes", callback_data=f"epmenu_{user_id}")])
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data=f"back_{user_id}")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex(r"^dlall_(\d+)$"))
async def download_all_callback(client, callback: CallbackQuery):
    user_id = int(callback.matches[0].group(1))
    
    if user_id != callback.from_user.id:
        return await callback.answer("❌ Not your session!", show_alert=True)
    
    session = user_sessions.get(user_id)
    if not session or 'episodes' not in session:
        return await callback.answer("❌ Session expired!", show_alert=True)
    
    anime = session['current_anime']
    episodes = session['episodes']
    
    await callback.message.edit_text(
        f"🎬 <b>{anime['title']}</b>\n\n"
        f"📥 <b>Batch Download Mode</b>\n"
        f"📺 Total Episodes: {len(episodes)}\n"
        f"⏳ <i>Processing... This will take time.</i>\n\n"
        f"<i>Bot will send first 5 episodes as samples...</i>",
        disable_web_page_preview=True
    )
    
    # Process first 5 episodes only (to avoid flood)
    count = 0
    for ep in episodes[:5]:
        try:
            qualities = await get_video_links(ep['url'], anime['site'])
            if qualities:
                best_quality = qualities[0]  # Take first available
                
                caption = settings['caption'].format(
                    title=anime['title'],
                    episode=ep['number'],
                    source=anime['site'],
                    quality=best_quality['quality']
                )
                
                await callback.message.reply_text(
                    f"📤 <b>Episode {ep['number']}</b>\n\n"
                    f"🔗 <b>Link:</b> <code>{best_quality['url']}</code>\n\n"
                    f"{caption}",
                    disable_web_page_preview=True
                )
                count += 1
                await asyncio.sleep(2)  # Anti-flood
        except Exception as e:
            logger.error(f"Batch download error for EP {ep['number']}: {e}")
    
    await callback.message.reply_text(
        f"✅ <b>Batch Complete!</b>\n\n"
        f"📥 Sent: {count}/{min(5, len(episodes))} episodes\n"
        f"📦 Remaining: {len(episodes) - count} episodes\n\n"
        f"<i>Use /search again for specific episodes.</i>"
    )

@app.on_callback_query(filters.regex(r"^back_(\d+)$"))
async def back_to_results_callback(client, callback: CallbackQuery):
    user_id = int(callback.matches[0].group(1))
    
    if user_id != callback.from_user.id:
        return await callback.answer("❌ Not your session!", show_alert=True)
    
    session = user_sessions.get(user_id)
    if not session:
        return await callback.answer("❌ Session expired!", show_alert=True)
    
    # Re-display results
    await display_results(callback.message, session['results'], session['query'], f"{user_id}:{session['query']}")

@app.on_callback_query(filters.regex(r"^anime_back_(\d+)$"))
async def back_to_anime_callback(client, callback: CallbackQuery):
    user_id = int(callback.matches[0].group(1))
    await callback.message.edit_text("⏳ Going back...")
    # Trigger anime selection again
    fake_callback = type('obj', (object,), {
        'from_user': type('obj', (object,), {'id': user_id})(),
        'message': callback.message,
        'matches': [[None, str(user_id), '0']]  # Default to first anime
    })
    await anime_selected_callback(client, fake_callback)

@app.on_callback_query(filters.regex(r"^refresh_(.+)$"))
async def refresh_callback(client, callback: CallbackQuery):
    cache_key = callback.matches[0].group(1)
    
    # Remove from cache
    if cache_key in search_cache:
        del search_cache[cache_key]
    
    await callback.answer("🔄 Cache cleared! Search again with /search", show_alert=True)
    await callback.message.delete()

@app.on_callback_query(filters.regex(r"^cancel_(\d+)$"))
async def cancel_callback(client, callback: CallbackQuery):
    user_id = int(callback.matches[0].group(1))
    if user_id == callback.from_user.id:
        await callback.message.edit_text("❌ <b>Search cancelled!</b>\n\nUse /search to start again.")
    else:
        await callback.answer("❌ Not your search!", show_alert=True)

@app.on_callback_query(filters.regex(r"^noop$"))
async def noop_callback(client, callback: CallbackQuery):
    await callback.answer("Navigation button", show_alert=False)

# Admin commands
@app.on_message(filters.command("admin") & filters.user(Config.ADMIN_IDS))
async def admin_handler(client, message: Message):
    await message.reply_text(
        "👑 <b>Admin Panel</b>\n\n"
        "Commands:\n"
        "/stats - Bot statistics\n"
        "/broadcast - Send message to all users\n"
        "/setcaption - Set default caption\n"
        "/cache - Clear search cache\n\n"
        f"Current Cache: {len(search_cache)} searches\n"
        f"Active Sessions: {len(user_sessions)} users"
    )

@app.on_message(filters.command("stats") & filters.user(Config.ADMIN_IDS))
async def stats_handler(client, message: Message):
    await message.reply_text(
        f"📊 <b>Bot Statistics</b>\n\n"
        f"🔍 Cached Searches: {len(search_cache)}\n"
        f"👥 Active Sessions: {len(user_sessions)}\n"
        f"⏱ Uptime: Running\n"
        f"🌐 Sites: {len(Config.SITES)} configured"
    )

@app.on_message(filters.command("cache") & filters.user(Config.ADMIN_IDS))
async def clear_cache_handler(client, message: Message):
    search_cache.clear()
    user_sessions.clear()
    await message.reply_text("✅ <b>Cache cleared!</b>")

if __name__ == "__main__":
    logger.info("🚀 Starting Anime Scraper Bot...")
    logger.info(f"📡 Configured Sites: {list(Config.SITES.keys())}")
    app.run()
