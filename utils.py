import requests
import os
from typing import Optional, Dict, Any

TMDB_BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"

def get_movie_data(movie_name: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Search for a movie on TMDB and retrieve its details.
    """
    if not api_key:
        return None

    # Use v4 Bearer Auth for the provided JWT token
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # 1. Search for the movie
    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {
        "query": movie_name,
        "language": "en-US",
        "page": 1,
        "include_adult": False
    }

    try:
        response = requests.get(search_url, params=params, headers=headers)
        response.raise_for_status()
        results = response.json().get("results", [])

        if not results:
            return None

        # Take the first result
        movie = results[0]
        movie_id = movie["id"]

        # 2. Get detailed movie info including videos and external_ids
        detail_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        detail_params = {
            "append_to_response": "videos,external_ids"
        }
        detail_resp = requests.get(detail_url, params=detail_params, headers=headers)
        detail_resp.raise_for_status()
        movie_details = detail_resp.json()

        # Extract relevant info
        poster_path = movie_details.get("poster_path")
        poster_url = f"{POSTER_BASE_URL}{poster_path}" if poster_path else None
        
        # Trailer link
        videos = movie_details.get("videos", {}).get("results", [])
        trailer_link = None
        for video in videos:
            if video["site"] == "YouTube" and video["type"] == "Trailer":
                trailer_link = f"https://www.youtube.com/watch?v={video['key']}"
                break
        
        # IMDb ID
        imdb_id = movie_details.get("external_ids", {}).get("imdb_id")
        
        # Result dictionary
        return {
            "title": movie_details.get("title"),
            "description": movie_details.get("overview"),
            "release_date": movie_details.get("release_date"),
            "tmdb_rating": movie_details.get("vote_average"),
            "poster_url": poster_url,
            "trailer_link": trailer_link,
            "imdb_id": imdb_id,
            "original_title": movie_details.get("original_title")
        }

    except Exception as e:
        print(f"Error fetching data from TMDB: {e}")
        return None

def search_archive_org(movie_title: str) -> Optional[str]:
    """
    Search archive.org for the movie and return a download link if available.
    """
    # URL encoded search for movie title
    search_url = "https://archive.org/advancedsearch.php"
    params = {
        "q": f'title:("{movie_title}") AND mediatype:(movies)',
        "fl[]": "identifier",
        "sort[]": "downloads desc",
        "output": "json",
        "rows": 1
    }

    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()
        docs = data.get("response", {}).get("docs", [])
        
        if docs:
            identifier = docs[0].get("identifier")
            return f"https://archive.org/details/{identifier}"
        return None
    except Exception as e:
        print(f"Error searching Archive.org: {e}")
        return None
