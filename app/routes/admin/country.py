from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import Country
from app.schemas.admin import CountryResponse
from app.utils.response import APIResponse, success_response

router = APIRouter(prefix="/admin/countries", tags=["admin-countries"])


@router.get("/", response_model=APIResponse[List[CountryResponse]])
def get_all_countries(
    db: Session = Depends(get_db),
    # current_admin=Depends(require_superuser),
):
    countries = db.query(Country).order_by(Country.name).all()

    return success_response(data=countries, message="Countries fetched successfully")
