
from sqlmodel import  TIMESTAMP, Field, Relationship
from src.helper.model import CustomBaseModel
from typing import List, Optional
from  datetime import datetime
from sqlalchemy import  JSON, Column, Text


class PostCategory(CustomBaseModel,table=True):
    __tablename__ = "post_categories"
    title: str = Field( max_length=255)
    slug : str = Field( max_length=255, index=True)
    description : Optional[str] =  Field(nullable=True)

class Post(CustomBaseModel, table=True):
    __tablename__ = "posts"
    
    user_id: str = Field(foreign_key="users.id", nullable=False)
    author_name: str = Field( max_length=255)
    title: str = Field( max_length=255, index=True)
    slug : str = Field( max_length=255, index=True)
    cover_image: str = Field(default="", max_length=255)
    summary: str = Field(default=None, sa_column=Column(Text, nullable=True))
    published_at: Optional[datetime] = Field(default=None, nullable=True, sa_type=TIMESTAMP(timezone=True))
    tags: Optional[List[str]] = Field(
        sa_column=Column(JSON, nullable=False, default=[])
    )
    category_id : int = Field(foreign_key="post_categories.id", nullable=False)
    
    sections: List["PostSection"] = Relationship(sa_relationship_kwargs={"order_by": "PostSection.position"})
    

class PostSection(CustomBaseModel,table=True):
    
    __tablename__ = "post_sections"
    
    title: str = Field( max_length=255)
    cover_image: Optional[str] = Field(default="", max_length=255)
    content : str =  Field(sa_column=Column(Text, nullable=False))
    section_style : str = Field(default = "")
    position : int = Field(default=1)
    post_id : int = Field(foreign_key="posts.id", nullable=False)
    