"""毎日の自動投稿エントリポイント。

  python -m src.main prepare   # 投稿文と画像を生成し posts/ に保存
  python -m src.main post      # posts/ から読み込んで X / Instagram に投稿
  python -m src.main all       # 上記2つを連続実行（ローカルテスト用）

GitHub Actions ではコミット/プッシュを挟むため prepare → post を別ステップで実行する。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from src.content_generator import GeneratedPost, generate_post
from src.image_generator import generate_image

JST = ZoneInfo("Asia/Tokyo")
POSTS_DIR = Path("posts")


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _today_iso() -> str:
    return datetime.now(JST).date().isoformat()


def _paths_for(today: str) -> tuple[Path, Path]:
    return POSTS_DIR / f"{today}.png", POSTS_DIR / f"{today}.json"


def cmd_prepare() -> int:
    today = _today_iso()
    image_path, sidecar_path = _paths_for(today)

    if sidecar_path.exists() and image_path.exists():
        print(f"[{today}] already prepared, skip generation")
        return 0

    print(f"[{today}] generate post...")
    post = generate_post()
    print(f"  image_text: {post.image_text!r}")
    print(f"  caption   : {post.caption!r}")
    print(f"  hashtags  : {post.hashtags}")

    seed = int(today.replace("-", ""))
    generate_image(post.image_text, image_path, seed=seed)
    print(f"  image     : {image_path}")

    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(
        json.dumps(asdict(post), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  sidecar   : {sidecar_path}")
    return 0


def cmd_post() -> int:
    today = _today_iso()
    image_path, sidecar_path = _paths_for(today)

    if not sidecar_path.exists():
        print(f"sidecar not found: {sidecar_path} (run `prepare` first)", file=sys.stderr)
        return 2

    data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    post = GeneratedPost(**data)

    if _bool_env("DRY_RUN", False):
        print("DRY_RUN=true のため投稿はスキップしました")
        print(f"  X用テキスト    : {post.x_text!r}")
        print(f"  IG用キャプション: {post.instagram_caption!r}")
        return 0

    failures: list[str] = []

    if _bool_env("POST_TO_X", True):
        try:
            from src.x_poster import post_to_x

            tweet_id = post_to_x(post.x_text, image_path)
            print(f"  X         : posted (id={tweet_id})")
        except Exception:
            failures.append("X")
            print("  X         : FAILED", file=sys.stderr)
            traceback.print_exc()

    if _bool_env("POST_TO_INSTAGRAM", True):
        try:
            from src.instagram_poster import post_to_instagram

            base_url = os.environ["PUBLIC_IMAGE_BASE_URL"].rstrip("/")
            image_url = f"{base_url}/{image_path.as_posix()}"
            media_id = post_to_instagram(image_url, post.instagram_caption)
            print(f"  Instagram : posted (id={media_id})")
        except Exception:
            failures.append("Instagram")
            print("  Instagram : FAILED", file=sys.stderr)
            traceback.print_exc()

    if failures:
        print(f"\n失敗: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Daily auto poster")
    parser.add_argument("phase", choices=["prepare", "post", "all"], default="all", nargs="?")
    args = parser.parse_args()

    if args.phase == "prepare":
        return cmd_prepare()
    if args.phase == "post":
        return cmd_post()
    rc = cmd_prepare()
    if rc != 0:
        return rc
    return cmd_post()


if __name__ == "__main__":
    sys.exit(main())
