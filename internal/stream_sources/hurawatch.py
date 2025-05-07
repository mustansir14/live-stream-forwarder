from internal.stream_sources.base import IStreamSource
from internal.stream_sources.exceptions import UnexpectedResponse, PageNotFound
from internal.schemas import DudestreamStream
from internal.models.hurawatch import HuraWatchGenre, HuraWatchMovie, HuraWatchEpisode
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select
import requests
from bs4 import BeautifulSoup
from typing import List

MOVIES_URL = "https://hurawatch.vip/movies/page/%d"
TV_SHOWS_URL = "https://hurawatch.vip/tv-shows/page/%d"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}
class Hurawatch(IStreamSource):

    def __init__(self, db_session: sessionmaker[Session]) -> None:
        self.db_session = db_session

    def monitor_streams(self):
        self.__scrape_movies()
        self.__scrape_tv_shows()
    
    def __scrape_movies(self) -> None:
        page = 1
        total_movie_count = 0
        while True:
            print_with_hurawatch_prefix(f"Checking page {page} for movies")
            try:
                soup = make_request_and_soup(MOVIES_URL % page)
            except PageNotFound:
                break
            articles = soup.find_all("article")
            for article in articles:
                movie_id = int(article["id"].split("-")[1])
                movie_url = article.a["href"]
                soup = make_request_and_soup(movie_url)
                movie_info = extract_movie_info(soup)
                embed_url = soup.iframe["src"]
                genres = []
                with self.db_session() as session:
                    for genre_name in movie_info["genres"]:
                        genre = get_or_create_genre(session, genre_name)
                        genres.append(genre)
                    create_or_update_movie(
                        session,
                        hurawatch_id=movie_id,
                        title=movie_info["title"],
                        movie_embed_url=embed_url,
                        thumbnail_url=movie_info["thumbnail_url"],
                        storyline=movie_info["storyline"],
                        directors=movie_info["directors"],
                        writers=movie_info["writers"],
                        stars=movie_info["stars"],
                        is_movie=True,
                        genres=genres,
                    )
            page += 1
            total_movie_count += len(articles)
        print_with_hurawatch_prefix(f"Done scraping movies. Total movies found: {total_movie_count}")

    def __scrape_tv_shows(self) -> None:
        page = 1
        total_movie_count = 0
        while True:
            print_with_hurawatch_prefix(f"Checking page {page} for tv shows")
            try:
                soup = make_request_and_soup(TV_SHOWS_URL % page)
            except PageNotFound:
                break
            articles = soup.find_all("article")
            for article in articles:
                movie_id = int(article["id"].split("-")[1])
                movie_url = article.a["href"]
                soup = make_request_and_soup(movie_url)
                movie_info = extract_movie_info(soup)
                # if iframe exists, means it's a single episode, else multiple episodes inside 1 post
                if soup.iframe:
                    embed_url = soup.iframe["src"]
                    episode_embed_links = []
                else:
                    embed_url = None
                    episode_tags = soup.find_all("p", {"style": "text-align: center;"})
                    episode_embed_links = []
                    for tag in episode_tags:
                        episode_embed_links.append(tag.a["href"])

                genres = []
                with self.db_session() as session:
                    for genre_name in movie_info["genres"]:
                        genre = get_or_create_genre(session, genre_name)
                        genres.append(genre)
                    tv_show = create_or_update_movie(
                        session,
                        hurawatch_id=movie_id,
                        title=movie_info["title"],
                        movie_embed_url=embed_url,
                        thumbnail_url=movie_info["thumbnail_url"],
                        storyline=movie_info["storyline"],
                        directors=movie_info["directors"],
                        writers=movie_info["writers"],
                        stars=movie_info["stars"],
                        is_movie=False,
                        genres=genres,
                    )
                    if episode_embed_links:
                        for episode_number, episode_embed_link in enumerate(episode_embed_links, start=1):
                            create_or_update_episode(
                                session,
                                tv_show_id=tv_show.id,
                                episode_number=episode_number,
                                embed_url=episode_embed_link,
                            )
            page += 1
            total_movie_count += len(articles)
        print_with_hurawatch_prefix(f"Done scraping TV Shows. Total TV Shows found: {total_movie_count}")




def extract_movie_info(soup: BeautifulSoup) -> dict:
    data = {
        "title": None,
        "genres": None,
        "directors": None,
        "writers": None,
        "stars": None,
        "storyline": None,
        "thumbnail_url": None
    }

    content_div = soup.find("div", class_="post-content")
    if not content_div:
        return data  # Return all None if main container isn't found

    full_text = content_div.text.strip()
    lines = full_text.split("\n")

    storyline_started = False
    storyline_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("Title:"):
            data["title"] = line.replace("Title:", "").strip()
        elif line.startswith("Genres:"):
            # Remove the year/movie label part like "2025 Movies |"
            raw_genres = line.replace("Genres:", "").strip()
            genres_str = raw_genres.replace("|", ",")
            data["genres"] = [g.strip().lower() for g in genres_str.split(",")]
        elif line.startswith("Directors:"):
            data["directors"] = line.replace("Directors:", "").strip()
        elif line.startswith("Writer:"):
            data["writers"] = line.replace("Writer:", "").strip()
        elif line.startswith("Stars:"):
            data["stars"] = line.replace("Stars:", "").strip()
        elif "Storyline:" in line:
            storyline_started = True
            continue
        elif storyline_started:
            # Keep collecting lines until end
            storyline_lines.append(line)

    if storyline_lines:
        data["storyline"] = " ".join(storyline_lines).strip()
    
    thumbnail_image = soup.article.img
    if thumbnail_image:
        data["thumbnail_url"] = thumbnail_image["src"]
        if data["thumbnail_url"].startswith("//"):
            data["thumbnail_url"] = "https:" + data["thumbnail_url"]

    return data


def make_request_and_soup(url: str) -> BeautifulSoup:
    """Make a GET request to the specified URL with the headers."""
    response = requests.get(url, headers=REQUEST_HEADERS)
    if response.status_code == 404:
        raise PageNotFound(f"Page not found: {url}")
    if response.status_code != 200:
        raise UnexpectedResponse(f"Unexpected status code {response.status_code} from {url}")
    return BeautifulSoup(response.content, "html.parser")


                
def print_with_hurawatch_prefix(message: str) -> None:
    print(f"[Hurawatch] {message}")
            

        
def get_or_create_genre(session: Session, genre_name: str) -> HuraWatchGenre:
    """Get or create a genre in the database."""
    # use sql.select
    genre = session.scalars(select(HuraWatchGenre).where(HuraWatchGenre.name == genre_name)).first()
    if not genre:
        genre = HuraWatchGenre(name=genre_name)
        session.add(genre)
        session.commit()
    return genre

def create_or_update_movie(
        session: Session,
        hurawatch_id: int,
        title: str,
        movie_embed_url: str,
        thumbnail_url: str,
        storyline: str,
        directors: str,
        writers: str,
        stars: str,
        is_movie: bool,
        genres: List[HuraWatchGenre],
) -> HuraWatchMovie:
    
    """Create or update a movie in the database."""
    movie: HuraWatchMovie = session.scalars(select(HuraWatchMovie).where(HuraWatchMovie.hurawatch_id == hurawatch_id)).first()
    if not movie:
        movie = HuraWatchMovie(
            hurawatch_id=hurawatch_id,
            title=title,
            movie_embed_url=movie_embed_url,
            thumbnail_url=thumbnail_url,
            storyline=storyline,
            directors=directors,
            writers=writers,
            stars=stars,
            is_movie=is_movie,
        )
        session.add(movie)
    else:
        movie.title = title
        movie.movie_embed_url = movie_embed_url
        movie.thumbnail_url = thumbnail_url
        movie.storyline = storyline
        movie.directors = directors
        movie.writers = writers
        movie.stars = stars
        movie.is_movie = is_movie

    # Update genres
    movie.genres.clear()
    for genre in genres:
        movie.genres.append(genre)

    session.commit()
    return movie


def create_or_update_episode(
        session: Session,
        tv_show_id: int,
        episode_number: int,
        embed_url: str,
) -> None:
    
    """Create or update an episode in the database."""
    episode = session.scalars(select(HuraWatchEpisode).where(HuraWatchEpisode.tv_show_id == tv_show_id, HuraWatchEpisode.episode_number == episode_number)).first()
    if not episode:
        episode = HuraWatchEpisode(
            tv_show_id=tv_show_id,
            episode_number=episode_number,
            embed_url=embed_url,
        )
        session.add(episode)
    else:
        episode.embed_url = embed_url

    session.commit()