from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import (
    SQLModel, Field, Session, create_engine, select, Relationship
)

# Database URL for SQLite
DATABASE_URL = "sqlite:///./data.db"

# Create the SQL engine
engine = create_engine(DATABASE_URL, echo=True)
app = FastAPI()


SQLModel.metadata.create_all(engine)
