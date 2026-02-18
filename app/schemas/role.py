from typing import Optional

from pydantic import BaseModel


# Shared properties
class RoleBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


# Properties to receive via API on creation
class RoleCreate(RoleBase):
    name: str


# Properties to return to client
class Role(RoleBase):
    id: int

    class Config:
        from_attributes = True
