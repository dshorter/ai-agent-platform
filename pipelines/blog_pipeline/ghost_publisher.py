"""
Ghost Admin API client.

Creates drafts (not published posts) so the Director reviews and approves
inside Ghost's own admin UI. Uses the standard JWT flow against a Ghost
instance running on the same VPS.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
import jwt


@dataclass
class GhostDraft:
    """Shape we submit to Ghost's /admin/posts endpoint."""

    title: str
    slug: str
    html: str
    tags: list[str]
    meta_description: str
    custom_excerpt: str | None = None

    def to_payload(self) -> dict:
        return {
            "posts": [
                {
                    "title": self.title,
                    "slug": self.slug,
                    "html": self.html,
                    "status": "draft",
                    "tags": [{"name": tag} for tag in self.tags],
                    "meta_description": self.meta_description,
                    "custom_excerpt": self.custom_excerpt or self.meta_description,
                }
            ]
        }


@dataclass
class GhostResult:
    post_id: str
    slug: str
    url: str


class GhostClient:
    """Minimal Ghost Admin API wrapper. Idempotent on slug."""

    def __init__(
        self,
        admin_url: str,
        admin_api_key: str,
        *,
        api_version: str = "v5",
        timeout: float = 10.0,
    ) -> None:
        self.admin_url = admin_url.rstrip("/")
        self.api_version = api_version
        self._key_id, self._secret = admin_api_key.split(":", 1)
        self._client = httpx.Client(timeout=timeout)

    def _token(self) -> str:
        iat = datetime.now(tz=timezone.utc)
        payload = {
            "iat": iat,
            "exp": iat + timedelta(minutes=5),
            "aud": f"/{self.api_version}/admin/",
        }
        return jwt.encode(
            payload,
            bytes.fromhex(self._secret),
            algorithm="HS256",
            headers={"kid": self._key_id},
        )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Ghost {self._token()}",
            "Content-Type": "application/json",
            "Accept-Version": self.api_version,
        }

    def find_by_slug(self, slug: str) -> dict | None:
        """Returns the post dict if a draft/post with this slug already exists."""
        resp = self._client.get(
            f"{self.admin_url}/ghost/api/admin/posts/slug/{slug}/",
            headers=self._headers(),
            params={"fields": "id,slug,status,url"},
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        posts = resp.json().get("posts", [])
        return posts[0] if posts else None

    def create_draft(self, draft: GhostDraft) -> GhostResult:
        """Idempotent create — returns existing draft if slug already taken."""
        existing = self.find_by_slug(draft.slug)
        if existing:
            return GhostResult(
                post_id=existing["id"],
                slug=existing["slug"],
                url=existing.get("url", ""),
            )

        resp = self._client.post(
            f"{self.admin_url}/ghost/api/admin/posts/",
            headers=self._headers(),
            json=draft.to_payload(),
        )
        resp.raise_for_status()
        post = resp.json()["posts"][0]
        return GhostResult(
            post_id=post["id"], slug=post["slug"], url=post.get("url", "")
        )

    def close(self) -> None:
        self._client.close()
