# app/utils/date_filters.py

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Query
from sqlalchemy.sql.elements import ColumnElement

# ---------- STEP 1: NORMALIZATION ----------


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def normalize_date_range(
    from_date: Optional[datetime],
    to_date: Optional[datetime],
):
    from_dt = to_utc(from_date)
    to_dt = to_utc(to_date)

    if from_dt and to_dt and from_dt > to_dt:
        raise HTTPException(400, "Invalid date range")

    # inclusive end-of-day
    if to_dt:
        to_dt = to_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    return from_dt, to_dt


# ---------- STEP 2: APPLY FILTER ----------


def apply_date_range(
    query: Query,
    column: ColumnElement,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
):
    if from_date:
        query = query.filter(column >= from_date)

    if to_date:
        query = query.filter(column <= to_date)

    return query


# ---------- STEP 3: ONE-LINE WRAPPER ----------


def filter_by_date_range(
    query: Query,
    column: ColumnElement,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
):
    from_dt, to_dt = normalize_date_range(from_date, to_date)
    return apply_date_range(query, column, from_dt, to_dt)
