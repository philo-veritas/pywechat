from __future__ import annotations

import argparse
import os
import time

WINDOW_SIZE = (1500, 1500)


def resolve_media_paths(media_paths: list[str] | None, parser: argparse.ArgumentParser) -> list[str]:
    if media_paths is None:
        return []

    resolved_paths: list[str] = []
    for media_path in media_paths:
        if not os.path.isfile(media_path):
            parser.error(f"--media 路径不存在或不是文件: {media_path}")
        resolved_paths.append(media_path)
    return resolved_paths


def configure_weixin() -> None:
    from pyweixin import GlobalConfig

    GlobalConfig.is_maximize = False
    GlobalConfig.close_weixin = False
    GlobalConfig.window_size = WINDOW_SIZE
    GlobalConfig.window_position_mode = "top_left"
    GlobalConfig.search_pages = 0


def print_summary(
    *,
    dry_run: bool,
    friend: str,
    compose: bool,
    send: bool,
    text: str,
    media_paths: list[str],
) -> None:
    print(f"dry_run: {str(dry_run).lower()}")
    print(f"friend: {friend}")
    print(f"compose: {str(compose).lower()}")
    print(f"send: {str(send).lower()}")
    print(f"text: {text!r}")
    print(f"media_count: {len(media_paths)}")
    for index, media_path in enumerate(media_paths, 1):
        print(f"[{index}] {media_path}")


def open_edit_area(friend: str):
    from pyweixin import Navigator
    from pyweixin.Uielements import Edits

    edits = Edits()
    main_window = Navigator.open_dialog_window(
        friend=friend,
        search_pages=0,
        is_maximize=False,
    )
    edit_area = main_window.child_window(**edits.CurrentChatEdit)
    if not edit_area.exists(timeout=0.1):
        raise RuntimeError("非正常好友或群聊，无法找到消息输入框")
    edit_area.click_input()
    return edit_area


def compose_message(edit_area, text: str, media_paths: list[str], send_delay: float) -> None:
    import pyautogui

    from pyweixin.WinSettings import SystemSettings

    edit_area.click_input()
    pyautogui.hotkey("ctrl", "end", _pause=False)

    if text:
        SystemSettings.copy_text_to_clipboard(text)
        pyautogui.hotkey("ctrl", "v", _pause=False)
        time.sleep(send_delay)

    if media_paths:
        SystemSettings.copy_files_to_clipboard(filepaths_list=media_paths)
        pyautogui.hotkey("ctrl", "v", _pause=False)
        time.sleep(send_delay)


def send_current_message(edit_area, send_delay: float) -> None:
    import pyautogui

    edit_area.click_input()
    time.sleep(send_delay)
    pyautogui.hotkey("alt", "s", _pause=False)


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if not args.compose and not args.send:
        parser.error("--compose 和 --send 至少提供一个")

    has_content = bool(args.messages) or bool(args.media_paths)
    if has_content and not args.compose:
        parser.error("传入 --message 或 --media 时必须同时传入 --compose")

    if args.compose and not has_content:
        parser.error("--compose 需要至少提供一个 --message 或 --media")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="打开指定会话，向消息输入框追加内容，或发送当前输入框内容。默认 dry-run，传 --yes 才真正执行。"
    )
    parser.add_argument("friend", help="好友备注或群聊名")
    parser.add_argument(
        "-m",
        "--message",
        dest="messages",
        action="append",
        help="追加到输入框的文本，可重复传入；多条文本会直接拼接",
    )
    parser.add_argument(
        "--media",
        dest="media_paths",
        action="append",
        help="追加到输入框的本地图片或文件路径，可重复传入",
    )
    parser.add_argument(
        "--compose",
        action="store_true",
        help="把 --message 或 --media 追加到当前消息输入框，不清空已有内容",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="发送当前消息输入框内容",
    )
    parser.add_argument(
        "--send-delay",
        type=float,
        default=None,
        help="粘贴内容或发送前的等待秒数，默认使用 GlobalConfig.send_delay",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="确认真正执行 UI 操作。不传时只打印将执行的动作",
    )
    args = parser.parse_args()

    validate_args(args, parser)
    media_paths = resolve_media_paths(args.media_paths, parser)
    text = "".join(args.messages or [])

    print_summary(
        dry_run=not args.yes,
        friend=args.friend,
        compose=args.compose,
        send=args.send,
        text=text,
        media_paths=media_paths,
    )

    if not args.yes:
        return

    configure_weixin()
    from pyweixin import GlobalConfig

    send_delay = args.send_delay if args.send_delay is not None else GlobalConfig.send_delay
    edit_area = open_edit_area(args.friend)

    if args.compose:
        compose_message(
            edit_area=edit_area,
            text=text,
            media_paths=media_paths,
            send_delay=send_delay,
        )
    if args.send:
        send_current_message(edit_area=edit_area, send_delay=send_delay)

    print("executed: true")


if __name__ == "__main__":
    main()
