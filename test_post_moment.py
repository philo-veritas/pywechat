from __future__ import annotations

import argparse
import mimetypes
import os
import shutil
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

WINDOW_SIZE = (1500, 1500)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def parse_image_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("--image-url 仅支持 HTTP/HTTPS URL")
    return url


def resolve_media_paths(media_paths: list[str] | None, parser: argparse.ArgumentParser) -> list[str]:
    if media_paths is None:
        return []

    resolved_paths: list[str] = []
    for media_path in media_paths:
        if not os.path.exists(media_path):
            parser.error(f"--media 路径不存在: {media_path}")
        resolved_paths.append(media_path)
    return resolved_paths


def infer_extension(url: str, content_type: str | None) -> str:
    suffix = Path(unquote(urlsplit(url).path)).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return suffix

    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
        if guessed in IMAGE_EXTENSIONS:
            return guessed

    return ".jpg"


def download_image(url: str, target_dir: Path, index: int) -> str:
    request = Request(url, headers={"User-Agent": "pyweixin-test-post-moment/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type")
            extension = infer_extension(url, content_type)
            target_path = target_dir / f"image_url_{index}{extension}"
            with target_path.open("wb") as target_file:
                shutil.copyfileobj(response, target_file)
    except HTTPError as exc:
        raise RuntimeError(f"下载失败: {url} HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"下载失败: {url} {exc.reason}") from exc

    return str(target_path)


def download_image_urls(urls: list[str] | None, target_dir: Path) -> list[str]:
    if urls is None:
        return []

    downloaded_paths: list[str] = []
    for index, url in enumerate(urls, 1):
        downloaded_paths.append(download_image(url, target_dir, index))
    return downloaded_paths


def print_summary(dry_run: bool, text: str, media_paths: list[str], image_urls: list[str] | None) -> None:
    print(f"dry_run: {str(dry_run).lower()}")
    print(f"text: {text!r}")
    print(f"media_count: {len(media_paths)}")
    for index, media_path in enumerate(media_paths, 1):
        print(f"[{index}] {media_path}")
    if image_urls:
        print("image_urls:")
        for index, image_url in enumerate(image_urls, 1):
            print(f"[{index}] {image_url}")


def post_moment(text: str, media_paths: list[str]) -> None:
    from pyweixin import GlobalConfig, Moments

    GlobalConfig.is_maximize = False
    GlobalConfig.close_weixin = False
    GlobalConfig.window_size = WINDOW_SIZE
    GlobalConfig.window_position_mode = "top_left"

    Moments.post_moments(
        texts=text,
        medias=media_paths,
        is_maximize=False,
        close_weixin=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="使用 pyweixin.Moments.post_moments 发布朋友圈。默认 dry-run，传 --yes 才真正发布。"
    )
    parser.add_argument(
        "--text",
        default="",
        help="朋友圈文本内容，默认空字符串",
    )
    parser.add_argument(
        "--media",
        dest="media_paths",
        action="append",
        help="本地图片或视频路径，可重复传入",
    )
    parser.add_argument(
        "--image-url",
        dest="image_urls",
        action="append",
        type=parse_image_url,
        help="远程图片 URL，可重复传入。脚本会先下载到临时目录再发布",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="确认真正发布朋友圈。不传时只打印将发布的内容",
    )
    args = parser.parse_args()

    if not args.text and not args.media_paths and not args.image_urls:
        parser.error("--text、--media、--image-url 至少提供一个")

    local_media_paths = resolve_media_paths(args.media_paths, parser)

    with tempfile.TemporaryDirectory(prefix="pyweixin_moment_") as temp_dir:
        try:
            downloaded_paths = download_image_urls(args.image_urls, Path(temp_dir))
        except RuntimeError as exc:
            parser.error(str(exc))

        media_paths = local_media_paths + downloaded_paths
        if not media_paths:
            parser.error("当前 pyweixin.Moments.post_moments 实现不支持纯文字朋友圈，请提供 --media 或 --image-url")

        print_summary(
            dry_run=not args.yes,
            text=args.text,
            media_paths=media_paths,
            image_urls=args.image_urls,
        )

        if not args.yes:
            return

        post_moment(text=args.text, media_paths=media_paths)
        print("posted: true")


if __name__ == "__main__":
    main()
