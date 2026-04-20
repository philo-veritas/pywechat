from __future__ import annotations

import argparse

from pyweixin import Contacts, GlobalConfig

WINDOW_SIZE = (1500, 1500)


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
        print(f"[{index}]: {request}")


if __name__ == "__main__":
    main()
