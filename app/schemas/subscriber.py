from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr

# Shared properties
class SubscriberBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True

# Properties to receive on Subscriber creation
class SubscriberCreate(SubscriberBase):
    email: EmailStr

# Properties to receive on Subscriber update
class SubscriberUpdate(SubscriberBase):
    pass

# Properties shared by models stored in DB
class SubscriberInDBBase(SubscriberBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: datetime

# Properties to return to client
class Subscriber(SubscriberInDBBase):
    pass

# Properties stored in DB
class SubscriberInDB(SubscriberInDBBase):
    pass
