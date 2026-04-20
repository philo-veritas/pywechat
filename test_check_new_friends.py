from __future__ import annotations

import argparse

from pyweixin import Contacts, GlobalConfig

WINDOW_SIZE = (1500, 1500)
STATUS_SUFFIXES = ("等待验证", "已添加", "已过期")


def parse_request(raw_text: str) -> dict[str, str]:
    status = ""
    content = raw_text
    for candidate in STATUS_SUFFIXES:
        if raw_text.endswith(candidate):
            status = candidate
            content = raw_text[: -len(candidate)]
            break

    return {
        "raw_text": raw_text,
        "content": content.strip(),
        "status": status or "未知",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="使用 pyweixin.Contacts.check_new_friends 打印好友请求列表。"
    )
    parser.parse_args()

    GlobalConfig.is_maximize = False
    GlobalConfig.close_weixin = False
    GlobalConfig.window_size = WINDOW_SIZE
    GlobalConfig.window_position_mode = "top_left"

    requests = Contacts.check_new_friends(
        verify=False,
        is_maximize=False,
        close_weixin=False,
    )

    print(f"好友请求数: {len(requests)}")
    for index, request in enumerate(requests, 1):
        parsed = parse_request(request)
        print(
            f"[{index}]: status={parsed['status']} "
            f"content={parsed['content']}"
        )


if __name__ == "__main__":
    main()
