import httpx
from typing import Any, Dict, List, Optional
from src.config import settings


class MoodleAPIError(Exception):
    pass


class MoodleService:
    """Thin async client for Moodle REST web services.

    Expects settings to provide:
    - MOODLE_BASE_URL: base URL like https://moodle.example.com
    - MOODLE_TOKEN: service token
    - MOODLE_DEFAULT_CATEGORY_ID: int
    - MOODLE_STUDENT_ROLE_ID: int (typically 5)
    """

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None) -> None:
        self.base_url = (base_url or getattr(settings, "MOODLE_API_URL", "")).rstrip("/")
        self.token = token or getattr(settings, "MOODLE_API_TOKEN", None)
        
        print(self.base_url, self.token)
        if not self.base_url or not self.token:
            raise ValueError("MoodleService requires MOODLE_BASE_URL and MOODLE_TOKEN in settings")

    async def _call(self, wsfunction: str, params: Dict[str, Any]) -> Any:
        url = f"{self.base_url}/webservice/rest/server.php"
        query = {
            "wstoken": self.token,
            "wsfunction": wsfunction,
            "moodlewsrestformat": "json",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, params=query, data=params)
            resp.raise_for_status()
            data = resp.json()
            
            print(data)
            # Moodle errors often come as {exception, errorcode, message}
            if isinstance(data, dict) and data.get("exception"):
                raise MoodleAPIError(f"{data.get('errorcode')}: {data.get('message')}")
            return data

    # Courses
    async def get_course_by_shortname(self, shortname: str) -> Optional[Dict[str, Any]]:
        data = await self._call(
            "core_course_get_courses_by_field",
            {"field": "shortname", "value": shortname},
        )
        courses = data.get("courses", []) if isinstance(data, dict) else []
        return courses[0] if courses else None

    async def create_course(self, fullname: str, shortname: str, category_id: Optional[int] = None) -> int:
        existing = await self.get_course_by_shortname(shortname)
        if existing is not None:
            return int(existing["id"])
        category = category_id or int(getattr(settings, "MOODLE_DEFAULT_CATEGORY_ID", 1))
        payload = {
            "courses[0][fullname]": fullname,
            "courses[0][shortname]": shortname,
            "courses[0][categoryid]": category,
            "courses[0][format]": "topics",
        }
        data = await self._call("core_course_create_courses", payload)
        # Returns a list of created courses with ids
        if isinstance(data, list) and data:
            return int(data[0]["id"])
        raise MoodleAPIError("Failed to create course: unexpected response")

    # Users
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        data = await self._call(
            "core_user_get_users_by_field",
            {"field": "email", "values[0]": email},
        )
        if isinstance(data, list) and data:
            return data[0]
        return None

    async def create_user(self, *, username: str, password: str, email: str, firstname: str, lastname: str) -> int:
        payload = {
            "users[0][username]": username,
            "users[0][password]": password,
            "users[0][email]": email,
            "users[0][firstname]": firstname or "",
            "users[0][lastname]": lastname or "",
            "users[0][auth]": "manual",
        }
        data = await self._call("core_user_create_users", payload)
        if isinstance(data, list) and data:
            return int(data[0]["id"])
        raise MoodleAPIError("Failed to create user: unexpected response")

    async def ensure_user(self, *, email: str, firstname: str, lastname: str, password: Optional[str] = None) -> int:
        user = await self.get_user_by_email(email)
        if user is not None:
            return int(user["id"])
        username = email
        pwd = password or "ChangeMe123!"
        return await self.create_user(username=username, password=pwd, email=email, firstname=firstname, lastname=lastname)

    # Enrolments
    async def enrol_user_manual(self, *, user_id: int, course_id: int, role_id: Optional[int] = None) -> bool:
        role = role_id or int(getattr(settings, "MOODLE_STUDENT_ROLE_ID", 5))
        payload = {
            "enrolments[0][roleid]": role,
            "enrolments[0][userid]": user_id,
            "enrolments[0][courseid]": course_id,
        }
        data = await self._call("enrol_manual_enrol_users", payload)
        # When successful, Moodle returns an empty object
        return True

    # User update
    async def update_user_email(self, *, user_id: int, email: str) -> bool:
        payload = {
            "users[0][id]": user_id,
            "users[0][email]": email,
        }
        await self._call("core_user_update_users", payload)
        return True


# Celery tasks wrappers (optional)
try:
    from celery import shared_task
except Exception:
    shared_task = None

if shared_task:
    @shared_task
    def moodle_create_course_task(fullname: str, shortname: str) -> int:
        import asyncio
        async def _run():
            service = MoodleService()
            return await service.create_course(fullname=fullname, shortname=shortname)
        return asyncio.run(_run())

    @shared_task
    def moodle_ensure_user_task(email: str, firstname: str, lastname: str, password: str | None = None) -> int:
        import asyncio
        async def _run():
            service = MoodleService()
            return await service.ensure_user(email=email, firstname=firstname, lastname=lastname, password=password)
        return asyncio.run(_run())

    @shared_task
    def moodle_enrol_user_task(user_id: int, course_id: int, role_id: int | None = None) -> bool:
        import asyncio
        async def _run():
            service = MoodleService()
            return await service.enrol_user_manual(user_id=user_id, course_id=course_id, role_id=role_id)
        return asyncio.run(_run())

    @shared_task
    def moodle_enrol_user_by_email_task(email: str, course_id: int, role_id: int | None = None) -> bool:
        import asyncio
        async def _run():
            service = MoodleService()
            user = await service.get_user_by_email(email)
            if user is None:
                # If user not found, we cannot enrol by email without creating; ensure creates user
                uid = await service.ensure_user(email=email, firstname="", lastname="")
            else:
                uid = int(user["id"])
            return await service.enrol_user_manual(user_id=uid, course_id=course_id, role_id=role_id)
        return asyncio.run(_run())


