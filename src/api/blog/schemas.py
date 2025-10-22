from datetime import datetime
from typing import List, Optional, Literal
from fastapi import UploadFile
from pydantic import BaseModel, Field
from src.helper.schemas import BaseOutPage, BaseOutSuccess


class PostCategoryCreateInput(BaseModel):
    title: str
    description: str


class PostCategoryUpdateInput(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class PostCategoryOut(BaseModel):
    id: int
    title: str
    slug: str
    description: str
    created_at: datetime
    updated_at: datetime


class PostCreateInput(BaseModel):

    author_name: str
    title: str
    cover_image: UploadFile
    section_style : Optional[str] = ""
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    category_id: int


class PostUpdateInput(BaseModel):
    author_name: Optional[str] = None
    title: Optional[str] = None
    cover_image: Optional[UploadFile] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    category_id: Optional[int] = None


class PostOut(BaseModel):
    id: int
    user_id: str
    author_name: str
    title: str
    slug: str
    cover_image: str
    summary: Optional[str]
    published_at: Optional[datetime]
    tags: Optional[List[str]]
    category_id: int
    created_at: datetime
    updated_at: datetime


class PostFilter(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)
    search: Optional[str] = None
    category_id: Optional[int] = None
    is_published: Optional[bool] = None
    tag: Optional[str] = None
    order_by: Literal["created_at", "published_at", "title"] = "created_at"
    asc: Literal["asc", "desc"] = "asc"


class PostSectionCreateInput(BaseModel):
    title: str
    cover_image: Optional[UploadFile] = None
    content: str
    position: int = 1
    post_id: int


class PostSectionUpdateInput(BaseModel):
    title: Optional[str] = None
    cover_image: Optional[UploadFile] = None
    content: Optional[str] = None
    position: Optional[int] = None
    post_id: Optional[int] = None


class PostSectionOut(BaseModel):
    id: int
    title: str
    cover_image: Optional[str]
    content: str
    position: int
    post_id: int
    created_at: datetime
    updated_at: datetime


class PostOutSuccess(BaseOutSuccess):
    data: PostOut


class PostsPageOutSuccess(BaseOutPage):
    data: List[PostOut]


class PostCategoryOutSuccess(BaseOutSuccess):
    data: PostCategoryOut


class PostCategoryListOutSuccess(BaseOutSuccess):
    data: List[PostCategoryOut]


class PostSectionOutSuccess(BaseOutSuccess):
    data: PostSectionOut


class PostSectionListOutSuccess(BaseOutSuccess):
    data: List[PostSectionOut]


