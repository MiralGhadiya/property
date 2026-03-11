# app/router/admin/system_config.py

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db, require_management
from app.models.system_config import SystemConfig
from app.schemas.admin import (
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigResponse,
)

from app.utils.response import APIResponse, success_response
from app.common import PaginatedResponse
from app.deps import pagination_params

from app.utils.logger_config import app_logger as logger

router = APIRouter(
    prefix="/admin/system-config",
    tags=["admin-system-config"],
)


@router.post("", response_model=APIResponse[SystemConfigResponse])
def create_config(
    payload: SystemConfigCreate,
    db: Session = Depends(get_db),
    admin_user=Depends(require_management),
):
    existing = (
        db.query(SystemConfig)
        .filter(SystemConfig.config_key == payload.config_key)
        .first()
    )

    if existing:
        raise HTTPException(400, "Config key already exists")

    config = SystemConfig(**payload.dict())

    db.add(config)
    db.commit()
    db.refresh(config)

    logger.info(f"Config created: {config.config_key}")

    return success_response(data=config)


@router.get("", response_model=APIResponse[PaginatedResponse[SystemConfigResponse]])
def list_configs(
    db: Session = Depends(get_db),
    admin_user=Depends(require_management),
    params: dict = Depends(pagination_params),
    search: Optional[str] = Query(None),
):
    query = db.query(SystemConfig)

    if search:
        query = query.filter(SystemConfig.config_key.ilike(f"%{search}%"))

    total = query.count()

    configs = (
        query
        .order_by(SystemConfig.config_key.asc())
        .offset((params["page"] - 1) * params["limit"])
        .limit(params["limit"])
        .all()
    )

    return success_response(
        data={
            "data": [
                SystemConfigResponse(
                    id=c.id,
                    config_key=c.config_key,
                    config_value=c.config_value,
                    description=c.description,
                )
                for c in configs
            ],
            "pagination": {
                "page": params["page"],
                "limit": params["limit"],
                "total": total,
            },
        },
        message="Configs fetched successfully",
    )
    
    
@router.get("/{config_id}", response_model=APIResponse[SystemConfigResponse])
def get_config(
    config_id: UUID,
    db: Session = Depends(get_db),
    admin_user=Depends(require_management),
):
    config = db.query(SystemConfig).get(config_id)

    if not config:
        raise HTTPException(404, "Config not found")

    return success_response(data=config)


@router.put("/{config_id}", response_model=APIResponse[SystemConfigResponse])
def update_config(
    config_id: UUID,
    payload: SystemConfigUpdate,
    db: Session = Depends(get_db),
    admin_user=Depends(require_management),
):
    config = db.query(SystemConfig).get(config_id)

    if not config:
        raise HTTPException(404, "Config not found")

    for key, value in payload.dict(exclude_unset=True).items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)

    logger.info(f"Config updated: {config.config_key}")

    return success_response(data=config)


@router.delete("/{config_id}", response_model=APIResponse[bool])
def delete_config(
    config_id: UUID,
    db: Session = Depends(get_db),
    admin_user=Depends(require_management),
):
    config = db.query(SystemConfig).get(config_id)

    if not config:
        raise HTTPException(404, "Config not found")

    db.delete(config)
    db.commit()

    logger.info(f"Config deleted: {config.config_key}")

    return success_response(data=True)