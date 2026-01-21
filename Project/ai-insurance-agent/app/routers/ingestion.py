# app/routers/ingestion.py
from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Customer, Policy
from app.schemas import (
    CustomerCreate, CustomerResponse,
    PolicyCreate, PolicyResponse
)

# This line MUST be at module level – creates the router instance
router = APIRouter(prefix="/ingest", tags=["Data Ingestion"])


@router.post("/customers/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    customer_in: CustomerCreate,
    session: Session = Depends(get_session)
):
    # Prevent duplicate phone (compliance: one contact per number)
    stmt = select(Customer).where(Customer.phone == customer_in.phone)
    if session.exec(stmt).first():
        raise HTTPException(
            status_code=400,
            detail=f"Customer with phone {customer_in.phone} already exists"
        )

    customer = Customer(**customer_in.dict())
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer


@router.post("/policies/", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    policy_in: PolicyCreate,
    session: Session = Depends(get_session)
):
    # Validate customer exists
    if not session.get(Customer, policy_in.customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")

    # Optional compliance: one active/overdue policy per customer
    active_policy = session.exec(
        select(Policy).where(
            Policy.customer_id == policy_in.customer_id,
            Policy.status.in_(["active", "overdue"])
        )
    ).first()
    if active_policy:
        raise HTTPException(
            status_code=400,
            detail="Customer already has an active/overdue policy"
        )

    policy = Policy(**policy_in.dict())
    session.add(policy)
    session.commit()
    session.refresh(policy)
    return policy