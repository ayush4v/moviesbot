import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional, Any

# List of domains (These change often, use with caution)
SITES = {
    "Moviesmod": "https://modlist.in",
    "Filmyway": "https://1filmyfly.top",
    "VegaMovies": "https://vegatm.com",
    "Filmyzilla": "https://filmyzilla.com.in",
    "9xmovies": "https://9xmovies.yt"
}

def normalize_title(text: str) -> str:
    """Normalize text to assist in loose matching."""
    return re.sub(r'[^a-z0-9]', '', text.lower())

def search_on_site(site_name: str, site_url: str, movie_title: str) -> Optional[str]:
    """
    Search for a movie on a specific site and return the link to the EXACT matching post.
    """
    search_url = f"{site_url}/?s={movie_title.replace(' ', '+')}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        # Find all posts
        posts = soup.find_all(['h1', 'h2', 'h3'], class_=re.compile(r'(entry-title|post-title|title)'))
        if not posts:
            articles = soup.find_all('article')
            for article in articles:
                title_elem = article.find(['h2', 'h3'])
                if title_elem:
                    posts.append(title_elem)

        best_link = None
        base_title_norm = normalize_title(movie_title.split(':')[0]) # First part of title

        for post in posts:
            a_tag = post.find('a')
            if not a_tag:
                continue
                
            post_text = a_tag.get_text(strip=True).lower()
            post_href = a_tag['href']
            
            # Exact Match 
            if normalize_title(movie_title) in normalize_title(post_text) or base_title_norm in normalize_title(post_text):
                return post_href
                
            # Keep first as fallback
            if not best_link:
                best_link = post_href
                
        return best_link
    except Exception as e:
        print(f"Error searching on {site_name}: {e}")
        return None

def extract_movie_info(post_url: str) -> Dict[str, Any]:
    """
    Extract download links AND poster/description from the movie page.
    """
    info = {"links": {}, "poster_url": None, "title": "Movie"}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(post_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        # Try to find a poster image
        img = soup.find('img', class_=re.compile(r'(attachment-post-thumbnail|wp-post-image|size-full)'))
        if img and img.get('src'):
            info["poster_url"] = img.get('src')
            
        # Get title
        title_tag = soup.find(['h1', 'h2'])
        if title_tag:
            info["title"] = title_tag.get_text(strip=True)

        # Find download links
        all_links = soup.find_all(['a', 'button'])
        for link in all_links:
            text = link.get_text(strip=True).lower()
            href = link.get('href') if link.name == 'a' else None
            
            if href and href.startswith('http'):
                if '480p' in text and '480p' not in info["links"]:
                    info["links"]['480p'] = href
                elif '720p' in text and '720p' not in info["links"]:
                    info["links"]['720p'] = href
                elif '1080p' in text and '1080p' not in info["links"]:
                    info["links"]['1080p'] = href
                elif '2160p' in text or '4k' in text and '2160p' not in info["links"]:
                    info["links"]['2160p'] = href

        return info
    except Exception as e:
        print(f"Error extracting links from {post_url}: {e}")
        return info

def get_all_scraped_links(movie_title: str) -> List[Dict[str, Any]]:
    """
    Get aggregated links and info from all configured sites.
    """
    results = []
    for name, url in SITES.items():
        post_link = search_on_site(name, url, movie_title)
        if post_link:
            info = extract_movie_info(post_link)
            if info["links"]:  # Only add if links were found
                results.append({
                    "site": name,
                    "post_url": post_link,
                    "title": info["title"],
                    "poster_url": info["poster_url"],
                    "download_links": info["links"]
                })
    return results

def get_torrent_links(movie_title: str) -> List[Dict[str, Any]]:
    """
    Search PirateBay API (apibay.org) for zero-click direct torrent/magnet links.
    """
    try:
        url = f"https://apibay.org/q.php?q={movie_title}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        if not data or (len(data) == 1 and data[0].get("id") == "0"):
            return results
            
        # Top 3 seeded results
        sorted_data = sorted(data, key=lambda x: int(x.get("seeders", 0)), reverse=True)
        for item in sorted_data[:3]:
            info_hash = item.get("info_hash")
            name = item.get("name")
            size_bytes = int(item.get("size", 0))
            
            # Formats size
            size_gb = round(size_bytes / (1024**3), 2)
            
            if info_hash:
                # Direct itorrents HTTP link to bypass magnet restrictions and ad layers
                torrent_link = f"https://itorrents.org/torrent/{info_hash}.torrent"
                magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={name}"
                results.append({
                    "name": name[:50] + "...",
                    "size": f"{size_gb}GB",
                    "link": torrent_link,
                    "magnet": magnet
                })
        return results
    except Exception as e:
        print(f"Error fetching Torrents: {e}")
        return []
