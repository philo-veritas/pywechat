from __future__ import annotations

import argparse

from pyweixin import GlobalConfig, Messages

WINDOW_SIZE = (1500, 1500)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="使用 pyweixin.Messages.pull_messages 打印最近聊天消息。"
    )
    parser.add_argument("friend", help="好友备注或群聊名")
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=20,
        help="拉取最近消息条数，默认 20",
    )
    parser.add_argument(
        "--include-system",
        action="store_true",
        help="包含系统消息，例如时间分隔条、入群通知等",
    )
    args = parser.parse_args()

    GlobalConfig.is_maximize = False
    GlobalConfig.close_weixin = False
    GlobalConfig.window_size = WINDOW_SIZE
    GlobalConfig.window_position_mode = "top_left"
    GlobalConfig.search_pages = 0

    messages = Messages.pull_messages(
        friend=args.friend,
        number=args.number,
        chat_only=not args.include_system,
        search_pages=0,
        is_maximize=False,
        close_weixin=False,
        with_details=True,
    )

    print(f"会话: {args.friend}")
    print(f"拉取条数: {len(messages)}")
    print(f"chat_only: {not args.include_system}")

    for index, message in enumerate(messages, 1):
        item_rect = message.get("item_rect")
        if item_rect is not None:
            print(f"item_rect={item_rect}")
        print(
            f"[{index}]: sender={message.get('发送方')} "
            f"class={message.get('控件类型')} "
            f"text={message.get('消息内容')}"
        )


if __name__ == "__main__":
    main()
