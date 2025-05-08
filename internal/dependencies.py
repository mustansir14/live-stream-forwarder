from internal.database import SessionLocal

def get_session():
    with SessionLocal() as session:
        yield session