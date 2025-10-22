from typing import Annotated
from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from slugify import slugify

from src.api.auth.utils import check_permissions
from src.api.user.models import PermissionEnum, User
from src.helper.schemas import BaseOutFail, ErrorMessage

from src.api.blog.service import BlogService
from src.api.blog.schemas import (
    PostCategoryCreateInput,
    PostCategoryUpdateInput,
    PostCategoryOutSuccess,
    PostCategoryListOutSuccess,
    PostCreateInput,
    PostUpdateInput,
    PostOutSuccess,
    PostsPageOutSuccess,
    PostFilter,
    PostSectionCreateInput,
    PostSectionUpdateInput,
    PostSectionOutSuccess,
    PostSectionListOutSuccess,
)
from src.api.blog.dependencies import get_category, get_post, get_post_by_slug, get_section


router = APIRouter(tags=["Blog"])


# Categories
@router.get("/blog/categories", response_model=PostCategoryListOutSuccess,tags=["Post Category"])
async def list_categories(
    blog_service: BlogService = Depends(),
):
    categories = await blog_service.list_categories()
    return {"message": "Categories fetched successfully", "data": categories}

@router.get("/blog/categories/{category_id}", response_model=PostCategoryOutSuccess, tags=["Post Category"])
async def get_category_route(
    category_id: int,
    blog_service: BlogService = Depends(),
):
    category = await blog_service.get_category_by_id(category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Category not found",
                error_code="category_not_found",
            ).model_dump(),
        )
    return {"message": "Category fetched successfully", "data": category}


@router.post("/blog/categories", response_model=PostCategoryOutSuccess,tags=["Post Category"])
async def create_category(
    input: PostCategoryCreateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_CREATE_BLOG]))],
    blog_service: BlogService = Depends(),
):
    slug = slugify(input.title)
    existing = await blog_service.get_category_by_slug(slug)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message="Category slug already exists",
                error_code="category_slug_taken",
            ).model_dump(),
        )
    category = await blog_service.create_category(input)
    return {"message": "Category created successfully", "data": category}


@router.put("/blog/categories/{category_id}", response_model=PostCategoryOutSuccess,tags=["Post Category"])
async def update_category(
    category_id: int,
    input: PostCategoryUpdateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_BLOG]))],
    category=Depends(get_category),
    blog_service: BlogService = Depends(),
):
    if input.title:
        slug = slugify(input.title)
        existing = await blog_service.get_category_by_slug(slug)
        if existing is not None and existing.id != category.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.CATEGORY_ALREADY_EXISTS.description,
                    error_code=ErrorMessage.CATEGORY_ALREADY_EXISTS.value,
                ).model_dump(),
            )
    category = await blog_service.update_category(category, input)
    return {"message": "Category updated successfully", "data": category}


@router.delete("/blog/categories/{category_id}", response_model=PostCategoryOutSuccess,tags=["Post Category"])
async def delete_category(
    category_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_DELETE_BLOG]))],
    category=Depends(get_category),
    blog_service: BlogService = Depends(),
):
    category = await blog_service.delete_category(category)
    return {"message": "Category deleted successfully", "data": category}


# Posts
@router.get("/blog/posts", response_model=PostsPageOutSuccess,tags=["Post"])
async def list_posts(
    filters: Annotated[PostFilter, Query(...)],
    blog_service: BlogService = Depends(),
):
    posts, total = await blog_service.list_posts(filters)
    return {"data": posts, "page": filters.page, "number": len(posts), "total_number": total}

@router.get("/blog/get-published-posts", response_model=PostsPageOutSuccess,tags=["Post"])
async def list_posts(
    filters: Annotated[PostFilter, Query(...)],
    blog_service: BlogService = Depends(),
):
    posts, total = await blog_service.list_posts(filters,True)
    return {"data": posts, "page": filters.page, "number": len(posts), "total_number": total}

@router.post("/blog/posts", response_model=PostOutSuccess,tags=["Post"])
async def create_post(
    input: Annotated[PostCreateInput, Form(...)],
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_CREATE_BLOG]))],
    blog_service: BlogService = Depends(),
):  
    slug = slugify(input.title)
    existing = await blog_service.get_post_by_slug(slug)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.POST_ALREADY_EXISTS.description,
                error_code=ErrorMessage.POST_ALREADY_EXISTS.value,
            ).model_dump(),
        )
    post = await blog_service.create_post(data=input, user_id=current_user.id)
    return {"message": "Post created successfully", "data": post}


@router.get("/blog/posts/{post_id}", response_model=PostOutSuccess,tags=["Post"])
async def get_post_route(
    post_id: int,
    blog_service: BlogService = Depends(),
):
    post = await blog_service.get_full_post_by_id(post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.POST_NOT_FOUND.description,
                error_code=ErrorMessage.POST_NOT_FOUND.value,
            ).model_dump(),
        )
    return {"message": "Post fetched successfully", "data": post}

@router.get("/blog/posts-by-slug/{post_slug}", response_model=PostOutSuccess,tags=["Post"])
async def get_post_route(
    post_slug: str,
    blog_service: BlogService = Depends(),
):
    post = await blog_service.get_full_post_by_slug(post_slug)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.POST_NOT_FOUND.description,
                error_code=ErrorMessage.POST_NOT_FOUND.value,
            ).model_dump(),
        )
    return {"message": "Post fetched successfully", "data": post}

@router.put("/blog/posts/{post_id}", response_model=PostOutSuccess,tags=["Post"])
async def update_post_route(
    post_id: int,
    input: Annotated[PostUpdateInput, Form(...)],
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_BLOG]))],
    post=Depends(get_post),
    blog_service: BlogService = Depends(),
):  
    if input.title != None :
        slug = slugify(input.title)
        existing = await blog_service.get_post_by_slug(slug)
        if existing is not None and existing.id != post_id :
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.POST_ALREADY_EXISTS.description,
                    error_code=ErrorMessage.POST_ALREADY_EXISTS.value,
                ).model_dump(),
            )
        
    post = await blog_service.update_post(post=post, data=input)
    return {"message": "Post updated successfully", "data": post}


@router.delete("/blog/posts/{post_id}", response_model=PostOutSuccess,tags=["Post"])
async def delete_post_route(
    post_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_DELETE_BLOG]))],
    post=Depends(get_post),
    blog_service: BlogService = Depends(),
):
    post = await blog_service.delete_post(post)
    return {"message": "Post deleted successfully", "data": post}


# Sections
@router.get("/blog/posts/{post_id}/sections", response_model=PostSectionListOutSuccess,tags=["Post Section"])
async def list_sections(
    post_id: int,
    post=Depends(get_post),
    blog_service: BlogService = Depends(),
):
    sections = await blog_service.list_sections_by_post(post_id)
    return {"message": "Sections fetched successfully", "data": sections}


@router.get("/blog/posts-by-slug/{post_slug}/sections", response_model=PostSectionListOutSuccess,tags=["Post Section"])
async def list_sections(
    post_slug: str,
    post=Depends(get_post_by_slug),
    blog_service: BlogService = Depends(),
):
    sections = await blog_service.get_section_by_post_slug(post_slug)
    return {"message": "Sections fetched successfully", "data": sections}

@router.post("/blog/sections", response_model=PostSectionOutSuccess,tags=["Post Section"])
async def create_section(
    input: Annotated[PostSectionCreateInput, Form(...)],
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_BLOG]))],
    blog_service: BlogService = Depends(),
):
    section = await blog_service.create_section(input)
    return {"message": "Section created successfully", "data": section}


@router.put("/blog/sections/{section_id}", response_model=PostSectionOutSuccess,tags=["Post Section"])
async def update_section(
    section_id: int,
    input: Annotated[PostSectionUpdateInput, Form(...)],
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_BLOG]))],
    section=Depends(get_section),
    blog_service: BlogService = Depends(),
):
    section = await blog_service.update_section(section, input)
    return {"message": "Section updated successfully", "data": section}


@router.delete("/blog/sections/{section_id}", response_model=PostSectionOutSuccess,tags=["Post Section"])
async def delete_section(
    section_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_BLOG]))],
    section=Depends(get_section),
    blog_service: BlogService = Depends(),
):
    section = await blog_service.delete_section(section)
    return {"message": "Section deleted successfully", "data": section}


# Publish Post
@router.post("/blog/posts/{post_id}/publish", response_model=PostOutSuccess,tags=["Post"])
async def publish_post_route(
    post_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_PUBLISH_BLOG]))],
    post=Depends(get_post),
    blog_service: BlogService = Depends(),
):
    post = await blog_service.publish_post(post)
    post = await blog_service.get_full_post_by_id(post.id)
    return {"message": "Post published successfully", "data": post}


