# app/schemas.py
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, validator
import pytz


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, example="Senthoorbalan")
    phone: str = Field(..., example="+917373077820")  # E.164 format preferred
    language_pref: str = Field(default="en", example="en")
    time_zone: str = Field(..., example="Asia/Kolkata")

    @validator("phone")
    def normalize_phone(cls, v: str) -> str:
        """
        Normalize phone to valid E.164 format.
        Supports:
          - Indian numbers (+91 + 10 digits or 10 digits local)
          - US numbers (+1 + 10 digits)
          - Strips spaces, dashes, parentheses
        """
        # Clean input: remove non-digits
        digits = "".join(filter(str.isdigit, v))

        if not digits:
            raise ValueError("Phone number must contain digits")

        # Handle common Indian input patterns
        if len(digits) == 10:
            # Typical Indian mobile prefix (6-9)
            if digits[0] in "6789":
                digits = "91" + digits
            # If starts with 0 (old landline style), remove 0 and add 91
            elif digits[0] == "0":
                digits = "91" + digits[1:]

        # If no country code at all, assume India
        if not v.startswith("+"):
            digits = "91" + digits

        # Add + if missing (final E.164 format)
        if not digits.startswith("+"):
            digits = "+" + digits

        # Final validation: must be + followed by 11-15 digits (country code + number)
        if not (digits.startswith("+") and 11 <= len(digits) <= 16):
            raise ValueError(
                "Phone must be valid E.164 format "
                "(e.g. +919876543210 for India or +15551234567 for US)"
            )

        return digits

    @validator("time_zone")
    def validate_timezone(cls, v: str) -> str:
        if v not in pytz.all_timezones:
            raise ValueError(
                f"Invalid IANA time zone: {v}. "
                "Use valid tz name (e.g. Asia/Kolkata, America/New_York)"
            )
        return v


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer."""
    pass


class CustomerResponse(CustomerBase):
    """Response schema with ID."""
    id: int

    class Config:
        from_attributes = True  # Enables ORM mode


class PolicyBase(BaseModel):
    premium_amount: float = Field(..., gt=0, example=2499.00)
    due_date: date = Field(..., example="2025-12-15")
    status: str = Field(
        default="active",
        example="overdue",
        description="One of: active, overdue, paid, canceled"
    )


class PolicyCreate(PolicyBase):
    """Schema for creating a new policy."""
    customer_id: int = Field(..., example=1)


class PolicyResponse(PolicyBase):
    """Response schema with ID."""
    id: int
    customer_id: int

    class Config:
        from_attributes = True