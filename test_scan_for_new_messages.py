from __future__ import annotations

import argparse
import io
from contextlib import redirect_stdout

from pyweixin import GlobalConfig
from pyweixin.utils import scan_for_new_messages

WINDOW_SIZE = (1500, 1500)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="调用 pyweixin.utils.scan_for_new_messages 并打印未读消息字典。"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="扫描会话列表翻页延迟，默认 0.3 秒",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="只扫描会话列表顶部前 N 个会话，默认 20",
    )
    args = parser.parse_args()

    GlobalConfig.is_maximize = False
    GlobalConfig.close_weixin = False
    GlobalConfig.window_size = WINDOW_SIZE
    GlobalConfig.window_position_mode = "top_left"

    with redirect_stdout(io.StringIO()):
        new_message_dict = scan_for_new_messages(
            delay=args.delay,
            is_maximize=False,
            close_weixin=False,
            top_n=args.top_n,
        )

    print(new_message_dict)


if __name__ == "__main__":
    main()
