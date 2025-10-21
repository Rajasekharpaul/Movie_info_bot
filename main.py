from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes,MessageHandler,filters
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
    print("Search Command Invoked")
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
    response = requests.get(search_url, params=params)
    data = response.json().get("results", [])

    if not data:
        await update.reply_text(f"No results found for '{movie_name}'.")
        return
    
    movie=data[0]
    movie_id = movie['id']
    title = movie['title']
    release_date = movie['release_date']
    overview = movie.get('overview', 'No description available.')
    rating = movie.get('vote_average', 'No rating available.')

    # Get Language And Details
    details=requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}").json()
    languages=",".join([lang['english_name'] for lang in details.get('spoken_languages', [])])

    # Get OTT platforms
    providers= requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers?api_key={TMDB_API_KEY}").json()
    ott=providers.get('results', {}).get('IN', {}).get('flatrate', [])
    ott_platforms = ", ".join([platform['provider_name'] for platform in ott]) if ott else "No OTT platforms available"

    #Get trailers
    videos = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TMDB_API_KEY}").json()
    trailers = [v for v in videos["results"] if v["type"] == "Trailer" and v["site"] == "YouTube"]
    trailer_url = f"https://www.youtube.com/watch?v={trailers[0]['key']}" if trailers else "Not found"

    # Get Poster Image
    poster_path = movie.get("poster_path")
    poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else None

     # Final message with caption
    caption = f"""🎬 *{title}*

📅 Release Date: {release_date}

⭐ Rating: {rating}

🌐 Languages: {languages}

📺 OTT: {ott_platforms}

▶️ [Watch Trailer]({trailer_url})


📝 _{overview}_"""

    if poster_url:
        await update.message.reply_photo(
        photo=poster_url,
        caption=caption,
        parse_mode="Markdown"
    )
    else:
        await update.message.reply_text(
        caption,
        parse_mode="Markdown",
        disable_web_page_preview=True
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

app=ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("latest", latest))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), search))
app.add_handler(CommandHandler("trending", trending))
app.add_error_handler(error_handler)

if __name__ == "__main__":
    app.run_polling()