from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
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
    if len(context.args)== 0:
        await update.message.reply_text("please provide a movie name to search like /search <movie_name>")
        return
    movie_name = " ".join(context.args)
    search_url=f"https://api.themoviedb.org/3/search/movie"
    params={
        "api_key":TMDB_API_KEY,
        "query":movie_name,
    }
    response = requests.get(search_url, params=params)
    data = response.json().get("results", [])

    if not data:
        await update.reply_text("No results found")
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

app=ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("latest", latest))
app.add_handler(CommandHandler("search", search))
app.add_handler(CommandHandler("trending", trending))

if __name__ == "__main__":
    app.run_polling()