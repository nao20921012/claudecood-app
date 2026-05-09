"""Pillowで投稿用の正方形画像（1080x1080）を生成する。"""

from __future__ import annotations

import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CANVAS_SIZE = 1080
PADDING = 100

# OS別の日本語フォント候補。最初に見つかったものを使う。
FONT_CANDIDATES = [
    # GitHub Actions Ubuntu (apt install fonts-noto-cjk)
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    # Windows
    "C:/Windows/Fonts/YuGothB.ttc",
    "C:/Windows/Fonts/yugothib.ttf",
    "C:/Windows/Fonts/meiryob.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
    # macOS
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
]

# 落ち着いたグラデーション背景のパターン（上端→下端）
GRADIENTS = [
    ((30, 60, 114), (43, 88, 118)),    # 深いブルー
    ((44, 62, 80), (52, 152, 219)),    # 紺→水色
    ((26, 41, 128), (38, 208, 206)),   # 紫紺→ターコイズ
    ((65, 88, 208), (200, 80, 192)),   # 青紫
    ((15, 32, 39), (44, 83, 100)),     # 黒緑
    ((33, 33, 33), (66, 66, 66)),      # チャコール
]


def find_font_path() -> str:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return path
    raise FileNotFoundError(
        "日本語フォントが見つかりません。"
        "Ubuntuなら `sudo apt install fonts-noto-cjk` を実行してください。"
    )


def generate_image(text: str, output_path: Path, seed: int | None = None) -> Path:
    """テキストを中央に配置した1080x1080の画像を生成して保存。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    top_color, bottom_color = rng.choice(GRADIENTS)

    img = _make_gradient(CANVAS_SIZE, CANVAS_SIZE, top_color, bottom_color)
    draw = ImageDraw.Draw(img)

    font_path = find_font_path()
    font, lines = _fit_text(text, font_path, max_width=CANVAS_SIZE - PADDING * 2)

    line_heights = [_line_box(draw, line, font)[1] for line in lines]
    line_gap = int(font.size * 0.35)
    total_h = sum(line_heights) + line_gap * (len(lines) - 1)

    y = (CANVAS_SIZE - total_h) // 2
    for line, lh in zip(lines, line_heights):
        lw, _ = _line_box(draw, line, font)
        x = (CANVAS_SIZE - lw) // 2
        # うっすら影を入れて視認性を上げる
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 120))
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += lh + line_gap

    # 右下に控えめな日付/署名スペース（任意）
    img.save(output_path, format="PNG", optimize=True)
    return output_path


def _make_gradient(w: int, h: int, top: tuple, bottom: tuple) -> Image.Image:
    base = Image.new("RGB", (w, h), top)
    top_arr = list(top)
    bottom_arr = list(bottom)
    for y in range(h):
        ratio = y / max(h - 1, 1)
        color = tuple(
            int(top_arr[i] + (bottom_arr[i] - top_arr[i]) * ratio) for i in range(3)
        )
        ImageDraw.Draw(base).line([(0, y), (w, y)], fill=color)
    return base


def _line_box(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _fit_text(text: str, font_path: str, max_width: int) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """文字数とフォントサイズを調整して画面に収める。改行は \\n を尊重。"""
    raw_lines = text.replace("\\n", "\n").split("\n")
    raw_lines = [ln.strip() for ln in raw_lines if ln.strip()]

    # 文字数からフォントサイズを推定（長いほど小さく）
    longest = max(len(ln) for ln in raw_lines)
    if longest <= 10:
        size = 110
    elif longest <= 16:
        size = 86
    elif longest <= 24:
        size = 64
    else:
        size = 52

    dummy = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(dummy)

    while size > 28:
        font = ImageFont.truetype(font_path, size)
        wrapped: list[str] = []
        for ln in raw_lines:
            wrapped.extend(_wrap_jp(ln, font, draw, max_width))
        if all(_line_box(draw, w, font)[0] <= max_width for w in wrapped):
            return font, wrapped
        size -= 6

    font = ImageFont.truetype(font_path, 28)
    wrapped = []
    for ln in raw_lines:
        wrapped.extend(_wrap_jp(ln, font, draw, max_width))
    return font, wrapped


def _wrap_jp(line: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, max_width: int) -> list[str]:
    """日本語向け：1文字ずつ計測して max_width を超える前で改行。"""
    if not line:
        return [""]
    out: list[str] = []
    cur = ""
    for ch in line:
        trial = cur + ch
        w, _ = _line_box(draw, trial, font)
        if w > max_width and cur:
            out.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        out.append(cur)
    return out


if __name__ == "__main__":
    out = Path("posts/local/sample.png")
    generate_image("一歩でも前へ。\n今日のあなたが\n明日を作る。", out, seed=42)
    print(f"saved: {out}")
