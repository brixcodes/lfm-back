from typing import List, Optional, Tuple
from datetime import datetime, timezone
from fastapi import Depends
from jinja2.nodes import Pos
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, or_, update
from slugify import slugify
from src.database import get_session_async
from src.api.blog.models import Post, PostCategory, PostSection
from src.api.blog.schemas import PostCategoryCreateInput, PostCategoryUpdateInput, PostCreateInput, PostFilter, PostSectionCreateInput, PostSectionUpdateInput, PostUpdateInput
from src.helper.file_helper import FileHelper


class BlogService:
    def __init__(self, session: AsyncSession = Depends(get_session_async)) -> None:
        self.session = session

    # Categories
    async def create_category(self, data : PostCategoryCreateInput) -> PostCategory:
        data = data.model_dump()
        data["slug"] = slugify(data["title"] )
        category = PostCategory(**data)
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def update_category(self, category: PostCategory, data : PostCategoryUpdateInput) -> PostCategory:
        input =  data.model_dump(exclude_none=True)
        if data.title != None :

            input["slug"] = slugify(input["title"] )
        
        for key, value in input.items():
            setattr(category, key, value)
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def get_category_by_id(self, category_id: int) -> Optional[PostCategory]:
        statement = select(PostCategory).where(PostCategory.id == category_id, PostCategory.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_category_by_slug(self, slug: str) -> Optional[PostCategory]:
        statement = select(PostCategory).where(PostCategory.slug == slug, PostCategory.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list_categories(self) -> List[PostCategory]:
        try:
            statement = select(PostCategory).where(PostCategory.delete_at.is_(None)).order_by(PostCategory.title)
            result = await self.session.execute(statement)
            return result.scalars().all()
        except Exception as e:
            # If table doesn't exist, return empty list
            if "post_categories" in str(e) and "does not exist" in str(e):
                return []
            raise e

    async def delete_category(self, category: PostCategory) -> PostCategory:
        category.delete_at = datetime.now(timezone.utc)
        self.session.add(category)
        await self.session.commit()
        return category

    # Posts
    async def create_post(self, data : PostCreateInput, user_id: str) -> Post:
        slug = slugify(data.title)
        
        cover_url, _, _ = await FileHelper.upload_file(
                data.cover_image, "/posts", slug
            )
        data = data.model_dump()
        data["cover_image"] = cover_url
        
        post = Post(**data ,user_id=user_id, slug=slug)
        self.session.add(post)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    async def update_post(self, post: Post, data :PostUpdateInput) -> Post:
        if data.title :
            slug = slugify(data.title)
        else :
            slug = None
        
        if data.cover_image is not None:
            
            FileHelper.delete_file(post.cover_image)
            cover_url, _, _ = await FileHelper.upload_file(
                data.cover_image, "/posts", slug
            )
        else:
            cover_url = post.cover_image
        
        data = data.model_dump(exclude_none=True)
        data["cover_image"] = cover_url
        if slug :
            post.slug = slug
        for key, value in data.items():
            setattr(post, key, value)
        self.session.add(post)
        await self.session.commit()
        await self.session.refresh(post)
        return post
    
    async def get_post_by_id(self, post_id: int) -> Optional[Post]:
        statement = select(Post).where(Post.id == post_id, Post.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()
    
    async def get_post_by_slug(self, slug: str) -> Optional[Post]:
        statement = select(Post).where(Post.slug == slug, Post.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()
    
    async def get_full_post_by_id(self, post_id: int) -> Optional[Post]:
        statement = (select(Post).options(selectinload(Post.sections))
                        .where(Post.id == post_id, Post.delete_at.is_(None))
                        )
        
        result = await self.session.execute(statement)
        return result.scalars().first()
    
    async def get_full_post_by_slug(self, slug: str) -> Optional[Post]:
        statement = (select(Post).options(selectinload(Post.sections))
                        .where(Post.slug == slug, Post.delete_at.is_(None))
                        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_post_by_slug(self, slug: str) -> Optional[Post]:
        statement = select(Post).where(Post.slug == slug, Post.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list_posts(self, filters: PostFilter,published:bool=False) -> Tuple[List[Post], int]:
        statement = select(Post).where(Post.delete_at.is_(None))
        count_query = select(func.count(Post.id)).where(Post.delete_at.is_(None))
        
        if published :
            statement = statement.where(Post.published_at != None)

        if filters.search is not None:
            like_clause = or_(
                Post.title.contains(filters.search),
                Post.summary.contains(filters.search),
                Post.author_name.contains(filters.search),
            )
            statement = statement.where(like_clause)
            count_query = count_query.where(like_clause)

        if filters.category_id is not None:
            statement = statement.where(Post.category_id == filters.category_id)
            count_query = count_query.where(Post.category_id == filters.category_id)
            
        if filters.is_published != None and filters.is_published :
            
            statement = statement.where(Post.published_at != None)
            count_query = count_query.where(Post.published_at != None)


        if filters.tag is not None:
            # JSON contains check can vary by DB; for portability, do a simple text contains on tags json string cast
            statement = statement.where(func.cast(Post.tags, func.TEXT).contains(filters.tag))
            count_query = count_query.where(func.cast(Post.tags, func.TEXT).contains(filters.tag))

        if filters.order_by == "created_at":
            statement = statement.order_by(Post.created_at if filters.asc == "asc" else Post.created_at.desc())
        elif filters.order_by == "published_at":
            statement = statement.order_by(Post.published_at if filters.asc == "asc" else Post.published_at.desc())
        elif filters.order_by == "title":
            statement = statement.order_by(Post.title if filters.asc == "asc" else Post.title.desc())

        total_count = (await self.session.execute(count_query)).scalar_one()

        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        return result.scalars().all(), total_count

    async def delete_post(self, post: Post) -> Post:
        post.delete_at = datetime.now(timezone.utc)
        self.session.add(post)
        await self.session.commit()
        return post

    async def publish_post(self, post: Post) -> Post:
        post.published_at = datetime.now(timezone.utc)
        self.session.add(post)
        await self.session.commit()
        await self.session.refresh(post)
        return post

    # Sections
    async def create_section(self, data : PostSectionCreateInput) -> PostSection:
        
        if data.cover_image is not None:
            cover_url, _, _ = await FileHelper.upload_file(
                data.cover_image, "/posts/sections", slugify(data.title)
            )
        else:
            cover_url = None

        data = data.model_dump()
        data["cover_image"] = cover_url
        
        section = PostSection(**data)
        self.session.add(section)
        await self.session.commit()
        await self.session.refresh(section)
        return section

    async def update_section(self, section: PostSection, data : PostSectionUpdateInput) -> PostSection:
        if data.cover_image is not None:
            if section.cover_image != None:
                FileHelper.delete_file(section.cover_image)
            cover_url, _, _ = await FileHelper.upload_file(
                data.cover_image, "/posts/sections", slugify(data.title)
            )
        else:
            cover_url = section.cover_image
            
        data = data.model_dump(exclude_none=True)
        data["cover_image"] = cover_url
        
        for key, value in data.items():
            setattr(section, key, value)
        self.session.add(section)
        await self.session.commit()
        await self.session.refresh(section)
        return section

    async def get_section_by_id(self, section_id: int) -> Optional[PostSection]:
        statement = select(PostSection).where(PostSection.id == section_id, PostSection.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list_sections_by_post(self, post_id: int) -> List[PostSection]:
        statement = (
            select(PostSection)
            .where(PostSection.post_id == post_id, PostSection.delete_at.is_(None))
            .order_by(PostSection.position)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()
    
    async def get_section_by_post_slug(self, post_slug: str) -> List[PostSection]:
        statement = select(PostSection).join(Post, PostSection.post_id == Post.id).where(Post.slug == post_slug, PostSection.delete_at.is_(None))
        result = await self.session.execute(statement.order_by(PostSection.position))
        return result.scalars().all()

    async def delete_section(self, section: PostSection) -> PostSection:
        post_id = section.post_id
        deleted_position = section.position

        # Delete the section
        await self.session.delete(section)
        await self.session.commit()

        # Shift remaining sections up
        await self.session.execute(
            update(PostSection)
            .where(PostSection.post_id == post_id)
            .where(PostSection.position > deleted_position)
            .values(position=PostSection.position - 1)
        )
        
        self.session.delete(section)
        await self.session.commit()
        return section


