"""Instagram Graph API への投稿。

フロー:
  1. POST /{ig-user-id}/media       (image_url + caption を渡してコンテナID取得)
  2. ステータスが FINISHED になるまで待つ
  3. POST /{ig-user-id}/media_publish (creation_id を渡して公開)

image_url は公開アクセス可能なURLである必要がある。
このプロジェクトでは GitHub の raw URL を利用する。
"""

from __future__ import annotations

import os
import time

import requests

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def post_to_instagram(image_url: str, caption: str) -> str:
    """Instagram に画像投稿し、メディアIDを返す。"""
    access_token = os.environ["IG_ACCESS_TOKEN"]
    ig_user_id = os.environ["IG_USER_ID"]

    creation_id = _create_container(ig_user_id, access_token, image_url, caption)
    _wait_until_ready(creation_id, access_token)
    return _publish(ig_user_id, access_token, creation_id)


def _create_container(ig_user_id: str, token: str, image_url: str, caption: str) -> str:
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _wait_until_ready(creation_id: str, token: str, timeout_sec: int = 120) -> None:
    """Instagram側の処理が終わる（FINISHED）まで待つ。"""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resp = requests.get(
            f"{GRAPH_API_BASE}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        )
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram media container failed: {resp.json()}")
        time.sleep(3)
    raise TimeoutError("Instagram media container did not become ready in time")


def _publish(ig_user_id: str, token: str, creation_id: str) -> str:
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]
