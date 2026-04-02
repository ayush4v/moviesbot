# 🎬 Movie Search Telegram Bot

A Telegram bot built with `python-telegram-bot` and `requests` to find movie details, posters, trailers, and archive.org download links.

## 🚀 Features
- **Movie Details**: Poster, Description, Release Date, and TMDb Rating.
- **Auto-Scraping**: Automatically finds download links from **Moviesmod**, **Filmyway**, and **VegaMovies**.
- **Multiple Qualities**: Extracts links for **480p**, **720p**, and **1080p** (if available).
- **YouTube Trailers**: Easily accessible through inline buttons.
- **Download Links**: Backup lookup on `archive.org`.

## 🛠 Prerequisites
1. **Python 3.8+** installed on your system.
2. **Telegram Bot Token**: Get it from [@BotFather](https://t.me/BotFather).
3. **TMDB API Key**: Get it from [themoviedb.org](https://www.themoviedb.org/documentation/api).

## 📦 Installation
1. Clone or download this project.
2. Navigate to the `movie_bot` directory.
3. Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file from the `.env.example`:
   ```bash
   cp .env.example .env
   ```
5. Add your API keys to the `.env` file.

## 🏃 Running the Bot
```bash
python bot.py
```

## 📂 Project Structure
- `bot.py`: Main bot implementation.
- `utils.py`: API logic for movie search and trailer fetching.
- `requirements.txt`: Python dependencies.
- `.env.example`: Template for environment variables.
