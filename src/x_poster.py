"""X (Twitter) への画像付き投稿。"""

from __future__ import annotations

import os
from pathlib import Path

import tweepy


def post_to_x(text: str, image_path: Path) -> str:
    """画像付きツイートを送信し、ツイートIDを返す。

    X API v2 はメディアアップロードに v1.1 のエンドポイントを使うため、
    OAuth1.0a で認証する API と Client の両方を作る必要がある。
    """
    api_key = os.environ["X_API_KEY"]
    api_secret = os.environ["X_API_SECRET"]
    access_token = os.environ["X_ACCESS_TOKEN"]
    access_token_secret = os.environ["X_ACCESS_TOKEN_SECRET"]

    # メディアアップロード用 (v1.1)
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
    api_v1 = tweepy.API(auth)
    media = api_v1.media_upload(filename=str(image_path))

    # ツイート投稿 (v2)
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )
    response = client.create_tweet(text=text, media_ids=[media.media_id])
    return response.data["id"]
