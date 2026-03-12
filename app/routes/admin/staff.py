from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.models.user import User
from app.models.staff import Staff

from app.schemas.staff import StaffCreate, StaffResponse, StaffUpdate

from app.auth import hash_password
from app.common import PaginatedResponse

from app.database.db import get_db
from app.utils.response import APIResponse, success_response
from app.deps import pagination_params, require_management

router = APIRouter(prefix="/admin/staff", tags=["admin-staff"])


def build_accesses(staff: Staff) -> dict:
    return {
        "can_access_user": staff.can_access_user,
        "can_access_staff": staff.can_access_staff,
        "can_access_dashboard": staff.can_access_dashboard,
        "can_access_reports": staff.can_access_reports,
        "can_access_subscriptions_plans": staff.can_access_subscriptions_plans,
        "can_access_config": staff.can_access_config,
    }


@router.post("/", response_model=APIResponse[StaffResponse])
def create_staff(
    staff: StaffCreate, 
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_management)
):

    existing_staff = db.query(Staff).filter(Staff.email == staff.email).first()
    if existing_staff:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(staff.password)

    if not admin_user:
        raise HTTPException(status_code=404, detail="Admin user not found")

    new_staff = Staff(
        name=staff.name,
        email=staff.email,
        phone=staff.phone,
        password=hashed_password, 
        role=staff.role,
        user_id=admin_user.id, 
        can_access_user=staff.can_access_user,
        can_access_staff=staff.can_access_staff,
        can_access_dashboard=staff.can_access_dashboard,
        can_access_reports=staff.can_access_reports,
        can_access_subscriptions_plans=staff.can_access_subscriptions_plans,
        can_access_config=staff.can_access_config,   
    )

    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    return success_response(
        data = StaffResponse(
            id=new_staff.id,
            name=new_staff.name,
            email=new_staff.email,
            phone=new_staff.phone,
            role=new_staff.role,
            accesses=build_accesses(new_staff),
    ),
        message="Staff member created successfully"
    )


@router.get("/", response_model=APIResponse[PaginatedResponse[StaffResponse]])
def list_staff(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_management),
    params: dict = Depends(pagination_params),
    
):
    
    query = db.query(Staff)

    if params["limit"] is not None:
        staff_members = query.offset((params["page"] - 1) * params["limit"]).limit(params["limit"]).all()
    else:
        staff_members = query.all()

    total = db.query(Staff).count()
    
    data = [
    StaffResponse(
            id=s.id,
            name=s.name,
            email=s.email,
            phone=s.phone,
            role=s.role,
            accesses=build_accesses(s),
        )
        for s in staff_members
    ]

    return success_response(
        data={
            "data": data,
            "pagination": {
                "page": params["page"],
                "limit": params["limit"],
                "total": total,
            }
    },
        message="Staff list fetched successfully"
    )


@router.get("/{staff_id}", response_model=APIResponse[StaffResponse])
def get_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_management),
):
    
    staff_member = db.query(Staff).filter(Staff.id == staff_id).first()

    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")

    return success_response(
        data=StaffResponse(
            id=staff_member.id,
            name=staff_member.name,
            email=staff_member.email,
            phone=staff_member.phone,
            role=staff_member.role,
        accesses=build_accesses(staff_member),
    ),
        message="Staff member fetched successfully"
    )


@router.patch("/{staff_id}", response_model=APIResponse[StaffResponse])
def update_staff(
    staff_id: UUID,
    staff_update: StaffUpdate, 
    db: Session = Depends(get_db),
    _: User = Depends(require_management),
):
    staff_member = db.query(Staff).filter(Staff.id == staff_id).first()

    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")

    if staff_update.name is not None:
        staff_member.name = staff_update.name
    if staff_update.email is not None:
        staff_member.email = staff_update.email
    if staff_update.phone is not None:
        staff_member.phone = staff_update.phone
    if staff_update.role is not None:
        staff_member.role = staff_update.role
    if staff_update.password is not None:
        staff_member.password = staff_update.password  
    if staff_update.can_access_user is not None:
        staff_member.can_access_user = staff_update.can_access_user
    if staff_update.can_access_staff is not None:
        staff_member.can_access_staff = staff_update.can_access_staff
    if staff_update.can_access_dashboard is not None:
        staff_member.can_access_dashboard = staff_update.can_access_dashboard
    if staff_update.can_access_reports is not None:
        staff_member.can_access_reports = staff_update.can_access_reports
    if staff_update.can_access_subscriptions_plans is not None:
        staff_member.can_access_subscriptions_plans = staff_update.can_access_subscriptions_plans
    if staff_update.can_access_config is not None:
        staff_member.can_access_config = staff_update.can_access_config

    db.commit()
    db.refresh(staff_member)

    return success_response(
        data=StaffResponse(
            id=staff_member.id,
            name=staff_member.name,
            email=staff_member.email,
            phone=staff_member.phone,
            role=staff_member.role,
            accesses=build_accesses(staff_member),
        ),
        message="Staff updated successfully"
    )
    
    
@router.delete("/{staff_id}", response_model=APIResponse[dict])
def delete_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_management),
):
    staff_member = db.query(Staff).filter(Staff.id == staff_id).first()

    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")

    db.delete(staff_member)
    db.commit()

    return success_response(
        message="Staff member deleted successfully",
        data={"id": str(staff_id)}
    )