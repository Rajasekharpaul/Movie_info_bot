from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes,MessageHandler,filters,CallbackQueryHandler
from dotenv import load_dotenv
import os
import requests

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome Type /latest to get today`s movie releases")

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&sort_by=release_date.desc&release_date.lte=today"
    response = requests.get(url)
    data = response.json()

    message = "Top Five movies:\n\n"
    for movie in data.get("results", [])[:5]:
        title=movie['title']
        realise_date=movie['release_date']
        overview = movie.get('overview', 'No description.')
        message += f"Title: {title}\nRelease Date: {realise_date}\nOverview: {overview}\n\n"
    await update.message.reply_text(message)

async def search(update:Update,context:ContextTypes.DEFAULT_TYPE):
    # Determine the movie name from either command args or plain text
    if context.args:
        movie_name = " ".join(context.args)
    elif update.message and update.message.text:
        movie_name = update.message.text
    else:
        await update.message.reply_text("Please provide a movie name to search.")
        return

    search_url=f"https://api.themoviedb.org/3/search/movie"
    params={
        "api_key":TMDB_API_KEY,
        "query":movie_name,
    }
    
    # Set a timeout for robustness (as discussed in previous steps)
    response = requests.get(search_url, params=params, timeout=10) 
    data = response.json().get("results", [])

    if not data:
        await update.message.reply_text(f"No results found for '{movie_name}'")
        return
    
    # Prepare the inline keyboard
    keyboard = []
    # Limit results to the top 5 for a clean keyboard
    for movie in data[:5]: 
        title = movie['title']
        year = movie['release_date'][:4] if movie.get('release_date') else 'N/A'
        movie_id = movie['id']
        
        button_text = f"{title} ({year})"
        # The callback_data is the key part: it stores the movie ID
        callback_data = f"MOVIE_ID_{movie_id}" 
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎬 **Found {len(data)} results for '{movie_name}'.**\nPlease select a movie from the list:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def trending(update:Update,context:ContextTypes.DEFAULT_TYPE):
    url= f"https://api.themoviedb.org/3/trending/movie/day?api_key={TMDB_API_KEY}"
    response=requests.get(url)
    data=response.json().get("results", [])

    if not data:
        await update.message.reply_text("No trending movies found.")
        return
    message = "Trending Movies:\n\n"
    for movie in data[:5]:
        title = movie['title']
        release_date = movie['release_date']
        overview = movie.get('overview', 'No description.')
        message += f"Title: {title}\nRelease Date: {release_date}\nOverview: {overview}\n\n"
    await update.message.reply_text(message)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user."""
    # Log the full traceback for debugging purposes
    print(f"Update {update} caused error {context.error}") 

    # Determine a user-friendly message based on the error type
    if isinstance(context.error, requests.exceptions.ConnectTimeout) or \
       isinstance(context.error, requests.exceptions.ReadTimeout):
        message = "⚠️ **Connection Error:** I couldn't reach the movie database. Please check your network connection or try again in a moment."
    else:
        # Generic message for other unexpected errors
        message = "🚨 **An unexpected error occurred!** Please try your request again."

    # Reply to the user if an update object is available
    if update and hasattr(update, 'message') and update.message:
        await update.message.reply_text(message, parse_mode="Markdown")

def get_movie_details(movie_id, TMDB_API_KEY):
    """Fetches full details, languages, OTT, and trailers for a given movie ID."""
    api_key=TMDB_API_KEY
    # Get Language And Details
    details=requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}").json()
    languages=",".join([lang['english_name'] for lang in details.get('spoken_languages', [])])

    # Get OTT platforms
    providers= requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers?api_key={api_key}").json()
    # Assuming 'IN' (India) as before, change this if needed
    ott=providers.get('results', {}).get('IN', {}).get('flatrate', []) 
    ott_platforms = ", ".join([platform['provider_name'] for platform in ott]) if ott else "No OTT platforms available"

    #Get trailers
    videos = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={api_key}").json()
    trailers = [v for v in videos["results"] if v["type"] == "Trailer" and v["site"] == "YouTube"]
    trailer_url = f"https://www.youtube.com/watch?v={trailers[0]['key']}" if trailers else "Not found"
    
    return languages, ott_platforms, trailer_url, details.get('vote_average', 'N/A')

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the user selecting a movie from the inline keyboard."""
    query = update.callback_query
    await query.answer() # Acknowledge the button click

    # Check if the callback data starts with our prefix
    if query.data.startswith("MOVIE_ID_"):
        movie_id = query.data.replace("MOVIE_ID_", "")
        
        # 1. Fetch details using the new utility function
        try:
            languages, ott_platforms, trailer_url, rating = get_movie_details(movie_id, TMDB_API_KEY)
        except Exception as e:
            # Handle API errors/timeouts during details fetching
            print(f"Error fetching movie details for ID {movie_id}: {e}")
            await query.edit_message_text(f"Sorry, I ran into an error getting the details for this movie. Please try again.")
            return

        # 2. Get basic info and poster path for the selected movie
        basic_info = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}").json()
        
        title = basic_info.get('title', 'N/A')
        release_date = basic_info.get('release_date', 'N/A')
        overview = basic_info.get('overview', 'No description available.')
        poster_path = basic_info.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else None

        # 3. Final message with caption
        caption = f"""🎬 *{title}*

📅 Release Date: {release_date}

⭐ Rating: {rating}

🌐 Languages: {languages}

📺 OTT: {ott_platforms}

▶️ [Watch Trailer]({trailer_url})

📝 _{overview}_"""

        # Edit the message to show the poster/details instead of sending a new one
        try:
            if poster_url:
                # Telegram does not allow editing a message to change it from text to photo, 
                # so we must send a new photo and delete the old message.
                await query.message.delete()
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=poster_url,
                    caption=caption,
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    caption,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
        except Exception as e:
            print(f"Error sending final message: {e}")
            await query.message.reply_text(f"Successfully retrieved data, but hit an error displaying it.")


app=ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("latest", latest))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), search))
app.add_handler(CommandHandler("trending", trending))
app.add_handler(CallbackQueryHandler(button_click))
app.add_error_handler(error_handler)

if __name__ == "__main__":
    app.run_polling()