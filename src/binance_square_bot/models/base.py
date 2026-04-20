from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from contextlib import contextmanager

Base = declarative_base()

class Database:
    _engine = None
    _SessionLocal = None

    @classmethod
    def init(cls, db_path: str = "data/app.db"):
        cls._engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        cls._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls._engine)
        Base.metadata.create_all(bind=cls._engine)

    @classmethod
    @contextmanager
    def get_session(cls) -> Session:
        session = cls._SessionLocal()
        try:
            yield session
        finally:
            session.close()
