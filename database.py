"""Saves and reads grades. SQLite locally; PostgreSQL when a database URL is set."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from sqlalchemy import (Column, DateTime, Float, Integer, MetaData, String, Table,
                        create_engine, func, select)
from sqlalchemy.exc import IntegrityError

import config

metadata = MetaData()
results = Table(
    "results", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("submission_id", String(64), unique=True, nullable=False),  # blocks duplicate saves
    Column("student_name", String(100), nullable=False),
    Column("class_name", String(50), nullable=False),
    Column("correct", Integer, nullable=False),
    Column("total", Integer, nullable=False),
    Column("score_percent", Float, nullable=False),
    Column("submitted_at", DateTime, nullable=False),
)


@st.cache_resource
def get_engine():
    engine = create_engine(config.get_database_url(), pool_pre_ping=True)
    metadata.create_all(engine)  # creates the table automatically if missing
    return engine


def already_submitted(name, class_name):
    with get_engine().connect() as conn:
        q = select(func.count()).select_from(results).where(
            func.lower(results.c.student_name) == name.lower(),
            func.lower(results.c.class_name) == class_name.lower())
        return conn.execute(q).scalar() > 0


def save_result(submission_id, name, class_name, correct, total):
    """Returns 'saved' or 'duplicate'."""
    now = datetime.now(ZoneInfo(config.TIMEZONE)).replace(tzinfo=None, microsecond=0)
    try:
        with get_engine().begin() as conn:
            conn.execute(results.insert().values(
                submission_id=submission_id, student_name=name, class_name=class_name,
                correct=correct, total=total,
                score_percent=round(100 * correct / total, 1), submitted_at=now))
        return "saved"
    except IntegrityError:
        return "duplicate"


def get_all_results():
    with get_engine().connect() as conn:
        df = pd.read_sql(select(results).order_by(results.c.class_name,
                                                  results.c.student_name), conn)
    return df
