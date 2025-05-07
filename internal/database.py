from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from internal.models.hurawatch import Base
from internal.env import Env

# Create the SQLAlchemy engine
engine = create_engine(Env.DATABASE_URL, echo=False)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize the database
def init_db():
    Base.metadata.create_all(bind=engine)
