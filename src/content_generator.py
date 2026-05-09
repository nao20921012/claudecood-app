"""Claude APIで毎日の投稿コンテンツ（名言/モチベーション）を生成する。"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """あなたはSNS（XとInstagram）向けに、人の心を動かす日本語の短い投稿を生成するコピーライターです。

テーマ:「モチベーション・名言・人生訓」

要件:
- 押し付けがましくなく、共感と前向きな一歩を促すトーン
- 自分自身に語りかけるような自然な口語
- ありきたりな格言の引用ではなく、独自の視点で書く
- 曜日や日付に強く依存しない、毎日成立する内容
- 出力は必ずJSONのみ。前後に説明文やコードブロックを付けない
"""

USER_PROMPT_TEMPLATE = """今日（{today}）の投稿を1つ作ってください。

以下のJSON形式で返してください:
{{
  "image_text": "画像中央に大きく表示する1〜2文の本文（最大60文字、改行は\\nで表現）",
  "caption": "X/Instagramに添える本文。140字以内。ハッシュタグは含めない",
  "hashtags": ["#名言", "#モチベーション", "他に2〜4個"]
}}

注意:
- image_text は短く、画像にしたとき映えるよう簡潔に
- caption は image_text と同じ文章にしない（補足や問いかけにする）
- hashtags は日本語/英語混在OK、各タグの先頭に必ず # を付ける
"""


@dataclass
class GeneratedPost:
    image_text: str
    caption: str
    hashtags: list[str]

    @property
    def x_text(self) -> str:
        """X投稿用テキスト（本文 + ハッシュタグ）。280字に収める。"""
        tags = " ".join(self.hashtags)
        full = f"{self.caption}\n\n{tags}".strip()
        return full[:280]

    @property
    def instagram_caption(self) -> str:
        """Instagram用キャプション。改行2つで区切り、ハッシュタグを末尾に。"""
        tags = " ".join(self.hashtags)
        return f"{self.caption}\n\n{tags}".strip()


def generate_post(today: date | None = None) -> GeneratedPost:
    """Claude APIを呼んで本日の投稿を生成する。"""
    today = today or date.today()
    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = Anthropic(api_key=api_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(today=today.isoformat()),
            }
        ],
    )

    raw = message.content[0].text.strip()
    data = _extract_json(raw)

    return GeneratedPost(
        image_text=data["image_text"],
        caption=data["caption"],
        hashtags=[_normalize_tag(t) for t in data["hashtags"]],
    )


def _extract_json(text: str) -> dict:
    """LLMが念のためコードブロックで返してきても拾えるようにする。"""
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    return json.loads(text)


def _normalize_tag(tag: str) -> str:
    tag = tag.strip()
    if not tag.startswith("#"):
        tag = "#" + tag
    return tag


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    post = generate_post()
    print("=== image_text ===")
    print(post.image_text)
    print("\n=== caption ===")
    print(post.caption)
    print("\n=== hashtags ===")
    print(post.hashtags)
    print("\n=== x_text ===")
    print(post.x_text)
