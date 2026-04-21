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


def should_select_request(
    index: int,
    parsed_request: dict[str, str],
    indexes: list[int] | None,
    matches: list[str] | None,
) -> bool:
    index_matched = True if indexes is None else index in indexes
    match_matched = (
        True
        if matches is None
        else any(match in parsed_request["content"] for match in matches)
    )
    return index_matched and match_matched


def main() -> None:
    parser = argparse.ArgumentParser(
        description="使用 pyweixin.Contacts.check_new_friends 查看或处理好友请求。"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="通过好友验证",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="通过验证的上限，单次建议不超过 8 人",
    )
    parser.add_argument(
        "--remark-prefix",
        help="通过验证时自动备注前缀，最终格式为前缀+昵称+后缀",
    )
    parser.add_argument(
        "--remark-suffix",
        help="通过验证时自动备注后缀，最终格式为前缀+昵称+后缀",
    )
    parser.add_argument(
        "--index",
        dest="indexes",
        type=int,
        action="append",
        help="只处理指定序号(1-based)的好友请求，可重复传入",
    )
    parser.add_argument(
        "--match",
        dest="matches",
        action="append",
        help="只处理内容包含指定关键字的好友请求，可重复传入",
    )
    args = parser.parse_args()

    indexes = None if args.indexes is None else sorted(set(args.indexes))
    matches = None
    if args.matches is not None:
        matches = []
        for match in args.matches:
            normalized = match.strip()
            if not normalized:
                parser.error("--match 不能为空字符串")
            if normalized not in matches:
                matches.append(normalized)

    if not args.verify and (
        args.limit is not None
        or args.remark_prefix is not None
        or args.remark_suffix is not None
        or indexes is not None
        or matches is not None
    ):
        parser.error("--limit、--remark-prefix、--remark-suffix、--index、--match 仅在 --verify 下可用")
    if args.verify and indexes is None and matches is None:
        parser.error("--verify 必须搭配 --index、--match 或两者一起使用")
    if args.limit is not None and not 1 <= args.limit <= 8:
        parser.error("--limit 必须在 1 到 8 之间")
    if indexes is not None and indexes[0] < 1:
        parser.error("--index 必须是大于 0 的整数")

    GlobalConfig.is_maximize = False
    GlobalConfig.close_weixin = False
    GlobalConfig.window_size = WINDOW_SIZE
    GlobalConfig.window_position_mode = "top_left"

    verify_limit = 8 if args.limit is None else args.limit
    requests = Contacts.check_new_friends(
        verify=args.verify,
        limit=verify_limit,
        remark_prefix=args.remark_prefix,
        remark_suffix=args.remark_suffix,
        target_indexes=indexes,
        target_matches=matches,
        is_maximize=False,
        close_weixin=False,
    )

    print(f"mode: {'verify' if args.verify else 'list'}")
    if args.verify:
        print(f"limit: {verify_limit}")
        print(f"indexes: {indexes}")
        print(f"matches: {matches}")
        print(f"remark_prefix: {args.remark_prefix!r}")
        print(f"remark_suffix: {args.remark_suffix!r}")
    parsed_requests = [parse_request(request) for request in requests]
    matched_requests = [
        parsed_request
        for index, parsed_request in enumerate(parsed_requests, 1)
        if should_select_request(index, parsed_request, indexes, matches)
    ]
    if args.verify:
        matched_waiting = [
            request for request in matched_requests if request["status"] == "等待验证"
        ]
        print(f"matched_targets: {len(matched_requests)}")
        print(f"estimated_verifications: {min(len(matched_waiting), verify_limit)}")
        if not matched_requests:
            print("未找到匹配目标，未执行通过验证。")
    print(f"好友请求数: {len(requests)}")
    for index, parsed in enumerate(parsed_requests, 1):
        print(
            f"[{index}]: status={parsed['status']} "
            f"content={parsed['content']}"
        )


if __name__ == "__main__":
    main()
