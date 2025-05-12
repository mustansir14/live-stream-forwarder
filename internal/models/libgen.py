from internal.models.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class LibgenTopic(Base):  # Renamed from Topic to LibgenTopic
    __tablename__ = 'libgen_topics'  # Updated table name

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey('libgen_topics.id'), nullable=True)  # Updated foreign key
    parent = relationship('LibgenTopic', remote_side=[id])  # Updated relationship

class LibgenBook(Base):
    __tablename__ = 'libgen_books'

    id = Column(Integer, primary_key=True)
    libgen_id = Column(Integer, nullable=False, unique=True)
    topic_id = Column(Integer, ForeignKey('libgen_topics.id'), nullable=False)  # Updated foreign key
    topic = relationship('LibgenTopic')  # Updated relationship
    authors = Column(String, nullable=False)
    title = Column(String, nullable=False)
    publisher = Column(String, nullable=False)
    year = Column(String, nullable=False)
    pages = Column(String, nullable=False)
    language = Column(String, nullable=False)
    size = Column(String, nullable=False)
    extension = Column(String, nullable=False)
    download_link = Column(String, nullable=False)

