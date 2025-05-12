from enum import Enum
from datetime import datetime, timezone, date
from typing import List

from pydantic import BaseModel


class TRWCampus(str, Enum):
    BUSINESS_MASTERY = "BUSINESS_MASTERY"
    CRYPTO_CURRENCY_INVESTING = "CRYPTO_CURRENCY_INVESTING"
    COPYWRITING = "COPYWRITING"
    STOCKS = "STOCKS"
    CRYPTO_TRADING = "CRYPTO_TRADING"
    ECOMMERCE = "ECOMMERCE"
    SOCIAL_MEDIA_CLIENT_ACQUISITION = "SOCIAL_MEDIA_CLIENT_ACQUISITION"
    AI_AUTOMATION_AGENCY = "AI_AUTOMATION_AGENCY"
    CRYPTO_DEFI = "CRYPTO_DEFI"
    CONTENT_CREATION_AI_CAMPUS = "CONTENT_CREATION_AI_CAMPUS"
    HUSTLERS_CAMPUS = "HUSTLERS_CAMPUS"
    THE_REAL_WORLD = "THE_REAL_WORLD"
    HEALTH_FITNESS = "HEALTH_FITNESS"



class TRWStream(BaseModel):
    id: str
    name: str
    url: str
    campus: TRWCampus


class DudestreamStream(BaseModel):
    name: str
    date: date
    category: str

class TRWUpcomingStream(BaseModel):
    name: str
    start_time: datetime
    campus: TRWCampus

    def is_expired(self) -> bool:
        return self.start_time < datetime.now(timezone.utc)

class BaseChatMessage(BaseModel):
    message: str
    author: str


class TRWStreamChatMessage(BaseChatMessage):
    id: str
    time: str
    reply_to: BaseChatMessage | None
 

class HurawatchMovieSchema(BaseModel):
    id: int
    title: str
    movie_embed_url: str | None
    thumbnail_url: str
    storyline: str | None
    directors: str | None
    writers: str | None
    stars: str | None
    is_movie: bool
    genres: List[str]
    episode_embed_urls: List[str]

class HurawatchMoviesResponse(BaseModel):
    hurawatch_movies: List[HurawatchMovieSchema]
    page: int
    total_pages: int

class LibgenBookSchema(BaseModel):
    id: int
    topic_name: str
    subtopic_name: str
    authors: str
    title: str
    publisher: str
    year: str
    pages: str
    size: str
    extension: str
    language: str
    download_link: str

class LibgenBooksResponse(BaseModel):
    libgen_books: List[LibgenBookSchema]
    page: int
    total_pages: int