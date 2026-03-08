import aiohttp
from bs4 import BeautifulSoup
import re

class AnimeScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def fetch(self, url):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                return await response.text()

    async def search_desidubanime(self, query):
        url = f"https://www.desidubanime.me/search/?s_keyword={query.replace(' ', '+')}&orderby=popular&order=DESC&action=advanced_search&page=1"
        html = await self.fetch(url)
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        for item in soup.select('.anime-item'):
            title_tag = item.select_one('.anime-title a')
            if title_tag:
                results.append({
                    "title": title_tag.text.strip(),
                    "url": title_tag['href'],
                    "source": "DesiDubAnime",
                    "lang": "Hindi/Multi"
                })
        return results

    async def search_animedubhindi(self, query):
        url = f"https://www.animedubhindi.me/?s={query.replace(' ', '+')}"
        html = await self.fetch(url)
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        for item in soup.select('.post-item, .entry-title'):
            title_tag = item.select_one('a')
            if title_tag and 'Download' in title_tag.text:
                results.append({
                    "title": title_tag.text.strip(),
                    "url": title_tag['href'],
                    "source": "AnimeDubHindi",
                    "lang": "Hindi/Multi"
                })
        return results

    async def search_animesalt(self, query):
        # AnimeSalt uses a more complex search, but let's try a simple one
        url = f"https://animesalt.ac/?s={query.replace(' ', '+')}"
        html = await self.fetch(url)
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        for item in soup.select('.anime-card, .entry-title'):
            title_tag = item.select_one('a')
            if title_tag:
                results.append({
                    "title": title_tag.text.strip(),
                    "url": title_tag['href'],
                    "source": "AnimeSalt",
                    "lang": "Hindi/Multi"
                })
        return results

    async def search_animehindidubbed(self, query):
        url = f"https://animehindidubbed.in/?s={query.replace(' ', '+')}"
        html = await self.fetch(url)
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        for item in soup.select('.post-item, .entry-title'):
            title_tag = item.select_one('a')
            if title_tag:
                results.append({
                    "title": title_tag.text.strip(),
                    "url": title_tag['href'],
                    "source": "AnimeHindiDubbed",
                    "lang": "Hindi/Multi"
                })
        return results

    async def get_episodes(self, url, source):
        html = await self.fetch(url)
        soup = BeautifulSoup(html, 'html.parser')
        episodes = []
        
        if source == "DesiDubAnime":
            for ep in soup.select('#seasonButtonsContainer ~ .episode-list a, .episode-item a'):
                episodes.append({
                    "title": ep.text.strip(),
                    "url": ep['href']
                })
        elif source == "AnimeHindiDubbed":
            for ep in soup.select('.episode-list button, .entry-content button'):
                episodes.append({
                    "title": ep.text.strip(),
                    "url": url # Usually handled via JS or internal links
                })
        # Add more logic for other sites
        return episodes

scraper = AnimeScraper()
