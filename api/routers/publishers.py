"""CRUD for user-managed publisher names (regex tier before LLM)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import KnownPublisherCreate, KnownPublisherResponse
from persistence.orm.known_publisher_orm import KnownPublisherORM

router = APIRouter(prefix="/api/publishers", tags=["publishers"])


@router.get("", response_model=list[KnownPublisherResponse])
def list_publishers(session: Session = Depends(get_db)) -> list[KnownPublisherORM]:
    stmt = select(KnownPublisherORM).order_by(KnownPublisherORM.name)
    return list(session.scalars(stmt).all())


@router.post(
    "",
    response_model=KnownPublisherResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_publisher(
    body: KnownPublisherCreate,
    session: Session = Depends(get_db),
) -> KnownPublisherORM:
    name = body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name must not be empty.",
        )
    existing = session.scalar(
        select(KnownPublisherORM).where(KnownPublisherORM.name == name)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Publisher name already exists.",
        )
    row = KnownPublisherORM(name=name)
    session.add(row)
    session.flush()
    session.refresh(row)
    return row


@router.delete("/{publisher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_publisher(
    publisher_id: uuid.UUID,
    session: Session = Depends(get_db),
) -> None:
    row = session.get(KnownPublisherORM, publisher_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found.",
        )
    session.delete(row)
