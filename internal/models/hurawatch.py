from sqlalchemy import Column, Integer, String, DateTime, Boolean, Table, ForeignKey
from sqlalchemy.orm import relationship

from internal.models.base import Base

# Association table for many-to-many relationship
movie_genre_association = Table(
    'hurawatch_movie_genre',
    Base.metadata,
    Column('movie_id', Integer, ForeignKey('hurawatch_movies.id'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('hurawatch_genres.id'), primary_key=True)
)

class HuraWatchGenre(Base):
    __tablename__ = 'hurawatch_genres'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    # Relationship to HuraWatchMovie
    movies = relationship('HuraWatchMovie', secondary=movie_genre_association, back_populates='genres')

class HuraWatchEpisode(Base):
    __tablename__ = 'hurawatch_episodes'
    
    id = Column(Integer, primary_key=True)
    tv_show_id = Column(Integer, ForeignKey('hurawatch_movies.id'), nullable=False)
    episode_number = Column(Integer, nullable=False)
    embed_url = Column(String, nullable=False)
    
    # Relationship to the TV show
    tv_show = relationship('HuraWatchMovie', back_populates='episodes')

class HuraWatchMovie(Base):
    __tablename__ = 'hurawatch_movies'
    
    id = Column(Integer, primary_key=True)
    hurawatch_id = Column(Integer, nullable=False, unique=True)
    title = Column(String, nullable=False)
    movie_embed_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=False)
    storyline = Column(String, nullable=True)
    directors = Column(String, nullable=True)
    writers = Column(String, nullable=True)
    stars = Column(String, nullable=True)
    is_movie = Column(Boolean, default=True)  # True for movies, False for TV shows
    genres = relationship('HuraWatchGenre', secondary=movie_genre_association, back_populates='movies')
    episodes = relationship('HuraWatchEpisode', back_populates='tv_show', cascade='all, delete-orphan')