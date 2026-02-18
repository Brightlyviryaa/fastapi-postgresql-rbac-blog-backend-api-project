from datetime import datetime
from typing import Optional
from pydantic import BaseModel

# Shared properties
class CommentBase(BaseModel):
    content: Optional[str] = None
    is_approved: Optional[bool] = False

# Properties to receive on Comment creation
class CommentCreate(CommentBase):
    content: str
    post_id: int
    user_id: int

# Properties to receive on Comment update
class CommentUpdate(CommentBase):
    pass

# Properties shared by models stored in DB
class CommentInDBBase(CommentBase):
    id: int
    content: str
    post_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Properties to return to client
class Comment(CommentInDBBase):
    pass

# Properties stored in DB
class CommentInDB(CommentInDBBase):
    pass
