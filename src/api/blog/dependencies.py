from fastapi import HTTPException, Depends, status

from src.helper.schemas import BaseOutFail, ErrorMessage
from src.api.blog.service import BlogService


async def get_category(category_id: int, blog_service: BlogService = Depends()):
    category = await blog_service.get_category_by_id(category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.POST_NOT_FOUND.description,
                error_code=ErrorMessage.POST_NOT_FOUND.value,
            ).model_dump(),
        )
    return category


async def get_post(post_id: int, blog_service: BlogService = Depends()):
    post = await blog_service.get_post_by_id(post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.POST_NOT_FOUND.description,
                error_code=ErrorMessage.POST_NOT_FOUND.value,
            ).model_dump(),
        )
    return post


async def get_post_by_slug(post_slug: str, blog_service: BlogService = Depends()):
    post = await blog_service.get_post_by_slug(post_slug)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.POST_NOT_FOUND.description,
                error_code=ErrorMessage.POST_NOT_FOUND.value,
            ).model_dump(),
        )
    return post

async def get_section(section_id: int, blog_service: BlogService = Depends()):
    section = await blog_service.get_section_by_id(section_id)
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.POST_SECTION_NOT_FOUND.description,
                error_code=ErrorMessage.POST_SECTION_NOT_FOUND.value,
            ).model_dump(),
        )
    return section


