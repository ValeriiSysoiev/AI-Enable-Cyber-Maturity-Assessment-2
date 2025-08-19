from sqlmodel import create_engine, SQLModel, Session
from pathlib import Path

# Ensure app directory exists for the database
db_dir = Path(__file__).parent.parent
db_dir.mkdir(exist_ok=True)

# SQLite database URL
DATABASE_URL = f"sqlite:///{db_dir}/app.db"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}  # Required for SQLite
)

def create_db_and_tables():
    """Create database tables"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dependency to get database session"""
    with Session(engine) as session:
        yield session














