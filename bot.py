import logging
import os
import aiohttp
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from scraper import get_all_scraped_links, get_torrent_links
from utils import get_movie_data

# Load environmental variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hello {user_name}!\n\n"
        "🍿 <b>Movie Bot is Ready!</b>\n"
        "Send any movie name to get exact details, posters, and 1-Click direct downloads.",
        parse_mode='HTML'
    )

async def search_archive_org_movie(title: str) -> str:
    """Search Archive.org for a direct video link of the movie."""
    search_url = f"https://archive.org/advancedsearch.php?q=title:({title}) AND mediatype:(movies)&fl[]=identifier&sort[]=downloads+desc&output=json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    docs = data.get("response", {}).get("docs", [])
                    if docs:
                        item_id = docs[0].get("identifier")
                        return f"https://archive.org/download/{item_id}/{item_id}.mp4"
    except Exception as e:
        logger.error(f"Archive.org search error: {e}")
    return None

async def movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle movie name messages."""
    movie_name = update.message.text
    if not movie_name:
        return

    status_msg = await update.message.reply_text("🚨 Validating movie and checking databases...")

    # Validate and get exact Official Name and Image from TMDB
    movie_info = get_movie_data(movie_name, TMDB_API_KEY)
    
    if movie_info:
        exact_title = movie_info.get("title", movie_name)
        poster_url = movie_info.get("poster_url")
        description = movie_info.get("description", "No description available.")
        rating = movie_info.get("tmdb_rating", "N/A")
        release = movie_info.get("release_date", "Unknown")
        orig_title = movie_info.get("original_title", exact_title)
    else:
        exact_title = movie_name
        poster_url = None
        description = "Info hidden or site specific movie."
        rating = "N/A"
        release = "Unknown"
        orig_title = movie_name

    # Scraping
    scraped_data = get_all_scraped_links(exact_title)
    torrent_data = get_torrent_links(exact_title)
    
    if not scraped_data and not movie_info and not torrent_data:
        await status_msg.edit_text("❌ Sorry, no results found anywhere for this movie.")
        return

    # Save context 
    context.user_data['last_searched_title'] = exact_title
    context.user_data['last_scraped_data'] = scraped_data
    context.user_data['last_torrent_data'] = torrent_data
    clean_title = exact_title[:30] 

    caption = (
        f"🎬 <b>{exact_title}</b>\n"
        f"🗓️ <b>Release:</b> {release} | ⭐ <b>TMDb:</b> {rating}/10\n\n"
        f"📝 <b>Storyline:</b>\n<i>{description[:300]}...</i>\n\n"
        f"✅ <b>Select your download method below:</b>\n"
        f"*(Use 1-Click Torrents for Ad-Free downloading)*"
    )

    buttons = []
    
    # Torrent Links
    if torrent_data:
        for t in torrent_data:
            # Inline button strictly taking them to the direct .torrent file
            buttons.append([InlineKeyboardButton(f"🧲 1-Click Fast | {t['size']}", url=t['link'])])

    buttons.append([
        InlineKeyboardButton("⬇️ Try Bot Upload 480p", callback_data=f"dl_480p_{clean_title}"),
        InlineKeyboardButton("⬇️ Try Bot Upload 720p", callback_data=f"dl_720p_{clean_title}")
    ])

    # Optional external site links in main menu removed to keep UI clean, we present it after they pick

    reply_markup = InlineKeyboardMarkup(buttons)
    await status_msg.delete()

    try:
        if poster_url:
            await update.message.reply_photo(
                photo=poster_url,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                text=caption,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Media error: {e}")
        await update.message.reply_text(caption, reply_markup=reply_markup, parse_mode='HTML')

import subprocess

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle resolution button clicks for direct bot download."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("dl_"):
        parts = data.split("_", 2)
        if len(parts) >= 3:
            quality = parts[1]
            title = context.user_data.get('last_searched_title', parts[2])
            
            # Retrieve the matched URL for this quality from context if available
            scraped_data = context.user_data.get('last_scraped_data', [])
            full_movie_url = "https://modlist.in/" # Default fallback
            
            for site in scraped_data:
                links = site.get('download_links', {})
                if quality in links:
                    full_movie_url = links[quality]
                    break
            
            status = await query.message.reply_text(
                f"🔄 Please Wait... Bot is preparing <b>{title}</b> in <b>{quality}</b>.\n\n⚠️ <i>Bypassing servers... This may take a minute.</i>",
                parse_mode='HTML'
            )
            
            # Download a small trailer via yt-dlp as proof-of-concept for direct delivery
            trailer_file = "trailer.mp4"
            if os.path.exists(trailer_file):
                os.remove(trailer_file)
                
            try:
                cmd = f'yt-dlp "ytsearch1:{title} official trailer" -f "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" --max-downloads 1 -o "{trailer_file}"'
                # run synchronously (blockingly) just for trailer extraction because it's fast
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                if os.path.exists(trailer_file):
                    caption = (
                        f"🎥 <b>{title}</b> - Preview/Trailer\n\n"
                        f"🛑 <b>Telegram Limitation:</b> Bots cannot upload files larger than 50MB directly! (Movies are 1GB+).\n\n"
                        f"✅ <b>YOUR FULL MOVIE LINK ({quality})</b> 👇\n"
                        f"<a href='{full_movie_url}'>🔗 CLICK HERE TO DOWNLOAD FULL MOVIE</a>"
                    )
                    
                    with open(trailer_file, 'rb') as video:
                        await query.message.reply_video(
                            video=video,
                            caption=caption,
                            parse_mode='HTML',
                            read_timeout=120,
                            write_timeout=120,
                            connect_timeout=120
                        )
                    os.remove(trailer_file)
                else:
                    raise Exception("Trailer file not found.")
            except Exception as e:
                logger.error(f"Trailer fetch error: {e}")
                # Fallback if yt-dlp fails
                caption = (
                    f"🛑 <b>Telegram Limitation:</b> Bots cannot upload files larger than 50MB directly! (Movies are usually 1GB - 3GB).\n\n"
                    f"✅ <b>YOUR DIRECT MOVIE LINK ({quality})</b> 👇\n"
                    f"<a href='{full_movie_url}'>🔗 CLICK HERE TO FAST DOWNLOAD NOW</a>"
                )
                await query.message.reply_text(caption, parse_mode='HTML')
                
            await status.delete()

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN provided. Define it in your .env file.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, movie_search))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Movie Bot is starting in DIRECT DOWNLOAD RESOLUTION mode...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
