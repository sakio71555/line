from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import os
import struct
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

LINE_API_BASE = "https://api.line.me"
LINE_DATA_API_BASE = "https://api-data.line.me"
RICH_MENU_WIDTH = 2500
RICH_MENU_HEIGHT = 1686
DEFAULT_IMAGE_PATH = "assets/line-rich-menu.png"


class RichMenuError(Exception):
    pass


def main(argv: Optional[list[str]] = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")
    args = parse_args(argv)

    image_path = resolve_image_path(repo_root, args.image_path)
    rich_menu = build_rich_menu(
        liff_id=os.getenv("LIFF_ID"),
        liff_base_url=os.getenv("LIFF_BASE_URL"),
        allow_placeholder=args.dry_run,
    )

    if args.dry_run:
        print(json.dumps(redact_liff_urls(rich_menu), ensure_ascii=False, indent=2))
        print("Dry-run: API送信は行いません。LIFF URLはマスクしています。")
        return 0

    access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    if not access_token:
        raise RichMenuError("LINE_CHANNEL_ACCESS_TOKEN is required")

    validate_image(image_path)
    rich_menu_id = create_rich_menu(access_token, rich_menu)
    upload_rich_menu_image(access_token, rich_menu_id, image_path)
    set_default_rich_menu(access_token, rich_menu_id)

    print("Rich menu created and set as default.")
    print(f"richMenuId: {rich_menu_id}")
    return 0


def parse_args(argv: Optional[list[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create and set the default LINE rich menu for the transport matching LIFF app.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="API送信せず、作成予定のrichMenu JSONを表示します。LIFF URLはマスクされます。",
    )
    parser.add_argument(
        "--image-path",
        default=None,
        help=f"リッチメニュー画像のパスです。未指定時はRICH_MENU_IMAGE_PATHまたは{DEFAULT_IMAGE_PATH}を使います。",
    )
    return parser.parse_args(argv)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_image_path(repo_root: Path, image_path_arg: Optional[str]) -> Path:
    raw_path = image_path_arg or os.getenv("RICH_MENU_IMAGE_PATH") or DEFAULT_IMAGE_PATH
    path = Path(raw_path)
    return path if path.is_absolute() else repo_root / path


def build_rich_menu(
    *,
    liff_id: Optional[str],
    liff_base_url: Optional[str],
    allow_placeholder: bool = False,
) -> dict[str, Any]:
    base_url = resolve_liff_base_url(liff_id=liff_id, liff_base_url=liff_base_url, allow_placeholder=allow_placeholder)
    return {
        "size": {"width": RICH_MENU_WIDTH, "height": RICH_MENU_HEIGHT},
        "selected": True,
        "name": "transport-main-menu",
        "chatBarText": "メニュー",
        "areas": [
            area(0, 0, 833, 843, {"type": "uri", "uri": build_liff_url(base_url, "post")}),
            area(833, 0, 834, 843, {"type": "uri", "uri": build_liff_url(base_url, "vehicle")}),
            area(1667, 0, 833, 843, {"type": "uri", "uri": build_liff_url(base_url, "list")}),
            area(0, 843, 833, 843, {"type": "uri", "uri": build_liff_url(base_url, "admin")}),
            area(833, 843, 834, 843, {"type": "message", "text": "使い方"}),
            area(1667, 843, 833, 843, {"type": "uri", "uri": build_liff_url(base_url, "companies")}),
        ],
    }


def resolve_liff_base_url(
    *,
    liff_id: Optional[str],
    liff_base_url: Optional[str],
    allow_placeholder: bool = False,
) -> str:
    if liff_base_url and liff_base_url.strip():
        return liff_base_url.strip()
    if liff_id and liff_id.strip():
        return f"https://liff.line.me/{liff_id.strip()}"
    if allow_placeholder:
        return "https://liff.line.me/{LIFF_ID}"
    raise RichMenuError("LIFF_ID or LIFF_BASE_URL is required")


def build_liff_url(base_url: str, tab: str) -> str:
    return append_query(base_url, {"tab": tab})


def append_query(url: str, params: dict[str, str]) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(params)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def area(x: int, y: int, width: int, height: int, action: dict[str, str]) -> dict[str, Any]:
    return {
        "bounds": {"x": x, "y": y, "width": width, "height": height},
        "action": action,
    }


def redact_liff_urls(rich_menu: dict[str, Any]) -> dict[str, Any]:
    redacted = copy.deepcopy(rich_menu)
    for item in redacted.get("areas", []):
        action = item.get("action") if isinstance(item, dict) else None
        if not isinstance(action, dict) or action.get("type") != "uri":
            continue
        uri = action.get("uri")
        tab = "unknown"
        if isinstance(uri, str):
            tab = dict(parse_qsl(urlsplit(uri).query)).get("tab", tab)
        action["uri"] = f"https://liff.line.me/{{LIFF_ID}}?tab={tab}"
    return redacted


def validate_image(path: Path) -> None:
    if not path.exists():
        raise RichMenuError(f"Rich menu image not found: {path}")
    if not path.is_file():
        raise RichMenuError(f"Rich menu image path is not a file: {path}")

    content_type = guess_content_type(path)
    if content_type not in {"image/png", "image/jpeg"}:
        raise RichMenuError("Rich menu image must be PNG or JPEG")

    size = image_size(path)
    if size != (RICH_MENU_WIDTH, RICH_MENU_HEIGHT):
        raise RichMenuError("Rich menu image must be 2500 x 1686 pixels")


def guess_content_type(path: Path) -> str:
    content_type, _encoding = mimetypes.guess_type(path.name)
    if content_type == "image/jpg":
        return "image/jpeg"
    return content_type or ""


def image_size(path: Path) -> Optional[tuple[int, int]]:
    with path.open("rb") as image_file:
        header = image_file.read(24)
        if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
            return struct.unpack(">II", header[16:24])
        image_file.seek(0)
        return jpeg_size(image_file.read())


def jpeg_size(data: bytes) -> Optional[tuple[int, int]]:
    if not data.startswith(b"\xff\xd8"):
        return None
    index = 2
    while index < len(data):
        while index < len(data) and data[index] != 0xFF:
            index += 1
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            break
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            break
        segment_length = int.from_bytes(data[index : index + 2], "big")
        if segment_length < 2 or index + segment_length > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if segment_length >= 7:
                height = int.from_bytes(data[index + 3 : index + 5], "big")
                width = int.from_bytes(data[index + 5 : index + 7], "big")
                return width, height
            break
        index += segment_length
    return None


def create_rich_menu(access_token: str, rich_menu: dict[str, Any]) -> str:
    response = httpx.post(
        f"{LINE_API_BASE}/v2/bot/richmenu",
        headers=auth_headers(access_token, "application/json"),
        json=rich_menu,
        timeout=20,
    )
    ensure_success(response, "create rich menu")
    rich_menu_id = response.json().get("richMenuId")
    if not isinstance(rich_menu_id, str) or not rich_menu_id:
        raise RichMenuError("LINE API did not return richMenuId")
    return rich_menu_id


def upload_rich_menu_image(access_token: str, rich_menu_id: str, image_path: Path) -> None:
    content_type = guess_content_type(image_path)
    response = httpx.post(
        f"{LINE_DATA_API_BASE}/v2/bot/richmenu/{rich_menu_id}/content",
        headers=auth_headers(access_token, content_type),
        content=image_path.read_bytes(),
        timeout=40,
    )
    ensure_success(response, "upload rich menu image")


def set_default_rich_menu(access_token: str, rich_menu_id: str) -> None:
    response = httpx.post(
        f"{LINE_API_BASE}/v2/bot/user/all/richmenu/{rich_menu_id}",
        headers=auth_headers(access_token, "application/json"),
        timeout=20,
    )
    ensure_success(response, "set default rich menu")


def auth_headers(access_token: str, content_type: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": content_type,
    }


def ensure_success(response: httpx.Response, operation: str) -> None:
    if response.status_code >= 400:
        raise RichMenuError(f"LINE API request failed during {operation}: status={response.status_code}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RichMenuError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
