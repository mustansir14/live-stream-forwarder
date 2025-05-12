# create a fastapi app with two endpoints list running streams and list upcoming streams

import asyncio
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from internal.database import init_db
from internal.dependencies import get_session
from internal.env import Env
from internal.models.hurawatch import HuraWatchMovie, HuraWatchGenre
from internal.models.libgen import LibgenBook, LibgenTopic
from internal.redis import RedisClient
from internal.schemas import TRWStream, TRWUpcomingStream, DudestreamStream, HurawatchMoviesResponse, HurawatchMovieSchema, LibgenBookSchema, LibgenBooksResponse
from internal.websocket import ConnectionManager

app = FastAPI()

# CORS allow all origins
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = RedisClient(host=Env.REDIS_HOST, port=Env.REDIS_PORT)
init_db()


@app.get("/trw-running-streams", response_model=List[TRWStream])
async def get_trw_running_streams():
    return redis_client.get_trw_running_streams()


@app.get("/trw-upcoming-streams", response_model=List[TRWUpcomingStream])
async def get_trw_upcoming_streams():
    upcoming_streams = redis_client.get_trw_upcoming_streams()

    upcoming_streams_to_return = []
    # remove old streams
    for upcoming_stream in upcoming_streams:
        if upcoming_stream.is_expired():
            redis_client.delete_trw_upcoming_stream(upcoming_stream)
            continue
        upcoming_streams_to_return.append(upcoming_stream)
    
    return upcoming_streams_to_return


@app.get("/dudestream-streams", response_model=List[DudestreamStream])
async def get_dudestream_streams():
    return redis_client.get_dudestream_streams()


@app.get("/hurawatch-movies", response_model=HurawatchMoviesResponse)
async def get_hurawatch_movies(page: int = None, is_movie: bool = None, genre: str = None, session: Session = Depends(get_session)):

    query = select(HuraWatchMovie)
    count_query = select(func.count(HuraWatchMovie.id))
    if is_movie is not None:
        query = query.where(HuraWatchMovie.is_movie == is_movie)
        count_query = count_query.where(HuraWatchMovie.is_movie == is_movie)
    if genre:
        query = query.join(HuraWatchGenre, HuraWatchMovie.genres).where(HuraWatchGenre.name == genre)
        count_query = count_query.join(HuraWatchGenre, HuraWatchMovie.genres).where(HuraWatchGenre.name == genre)

    if page > 0:
        page = page
    else:
        page = 1
    
    records_per_page = 12
    total_records = session.execute(count_query).scalar_one()
    total_pages = (total_records + records_per_page - 1) // records_per_page
    query = query.offset((page - 1) * records_per_page).limit(records_per_page)   
    movies = session.scalars(query).all()

    response_movies = []
    for movie in movies:
        episode_embed_urls = []
        for episode in movie.episodes:
            episode_embed_urls.append(episode.embed_url)
        response_movies.append(HurawatchMovieSchema(
            id=movie.id,
            title=movie.title,
            movie_embed_url=movie.movie_embed_url,
            thumbnail_url=movie.thumbnail_url,
            storyline=movie.storyline,
            directors=movie.directors,
            writers=movie.writers,
            stars=movie.stars,
            is_movie=movie.is_movie,
            genres=[genre.name for genre in movie.genres],
            episode_embed_urls=episode_embed_urls
        ))

    return HurawatchMoviesResponse(
        hurawatch_movies=response_movies,
        page=page,
        total_pages=total_pages
    )

@app.get("/libgen-books", response_model=LibgenBooksResponse)
async def get_libgen_movies(page: int = None, topic: str = None, subtopic: str = None, session: Session = Depends(get_session)):
    query = select(LibgenBook)
    count_query = select(func.count(LibgenBook.id))
    if topic:
        query = query.join(LibgenTopic).where(LibgenTopic.parent.has(name=topic))
        count_query = count_query.join(LibgenTopic).where(LibgenTopic.parent.has(name=topic))
    if subtopic:
        query = query.join(LibgenTopic).where(LibgenTopic.name == subtopic)
        count_query = count_query.join(LibgenTopic).where(LibgenTopic.name == subtopic)

    if page > 0:
        page = page
    else:
        page = 1
    
    records_per_page = 12
    total_records = session.execute(count_query).scalar_one()
    total_pages = (total_records + records_per_page - 1) // records_per_page
    query = query.offset((page - 1) * records_per_page).limit(records_per_page)   
    books = session.scalars(query).all()

    response_books = []
    for book in books:
        response_books.append(
            LibgenBookSchema(
                id=book.id,
                topic_name=book.topic.parent.name,
                subtopic_name=book.topic.name,
                authors=book.authors,
                title=book.title,
                publisher=book.publisher,
                year=book.year,
                pages=book.pages,
                size=book.size,
                extension=book.extension,
                language=book.language,
                download_link=book.download_link
            )
        )

    return LibgenBooksResponse(
        libgen_books=response_books,
        page=page,
        total_pages=total_pages
    )


manager = ConnectionManager()


@app.websocket("/ws/stream-messages/{stream_id}")
async def get_stream_messages(websocket: WebSocket, stream_id: str):
    await manager.connect(websocket)
    try:
        while True:
            # Dequeue message from Redis
            message = redis_client.dequeue_trw_stream_message(stream_id)
            if message:
                # Broadcast the message to all connected clients
                await manager.broadcast(message)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print(f"Client disconnected from stream {stream_id}")
    finally:
        manager.disconnect(websocket)
