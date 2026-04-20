from __future__ import annotations

import argparse
from typing import Iterable

from pyweixin import GlobalConfig, Navigator, Tools
from pyweixin.Uielements import Lists


def rect_tuple(ctrl) -> tuple[int, int, int, int] | None:
    try:
        rect = ctrl.rectangle()
        return rect.left, rect.top, rect.right, rect.bottom
    except Exception:
        return None


def is_visible(ctrl) -> bool:
    try:
        return ctrl.is_visible()
    except Exception:
        return False


def unique_controls(controls: Iterable) -> list:
    seen = set()
    unique = []
    for ctrl in controls:
        key = rect_tuple(ctrl)
        if key is None or key in seen:
            continue
        seen.add(key)
        unique.append(ctrl)
    return unique


def collect_candidate_rects(item, chat_list) -> list[tuple[int, int, int, int]]:
    chat_rect = chat_list.rectangle()
    chat_width = chat_rect.right - chat_rect.left
    item_rect = item.rectangle()
    item_height = item_rect.bottom - item_rect.top

    controls = []
    try:
        controls.extend(item.children())
    except Exception:
        pass

    for control_type in ("Button", "Text", "Image", "Pane", "Group", "Custom"):
        try:
            controls.extend(item.descendants(control_type=control_type))
        except Exception:
            pass

    rects: list[tuple[int, int, int, int]] = []
    for ctrl in unique_controls(controls):
        bounds = rect_tuple(ctrl)
        if bounds is None:
            continue
        left, top, right, bottom = bounds
        width = right - left
        height = bottom - top

        if width <= 2 or height <= 2:
            continue

        # 只剔除几乎覆盖整个聊天区的超大容器。
        if width >= chat_width * 0.98:
            continue

        # 过滤远大于当前消息行高度的异常容器。
        if height >= max(item_height * 2.0, 240):
            continue

        rects.append(bounds)

    return rects


def extract_sender_hint(item) -> str | None:
    try:
        buttons = item.descendants(control_type="Button")
    except Exception:
        return None

    for button in buttons:
        if not is_visible(button):
            continue
        try:
            text = button.window_text().strip()
        except Exception:
            text = ""
        if text:
            return text
    return None


def infer_side_by_geometry(item, chat_list, threshold: float) -> tuple[str, dict]:
    chat_rect = chat_list.rectangle()
    chat_left = chat_rect.left
    chat_right = chat_rect.right
    chat_width = chat_right - chat_left
    zone_width = chat_width * threshold
    item_rect = item.rectangle()

    rects = collect_candidate_rects(item, chat_list)
    if not rects:
        bubble_left = item_rect.left
        bubble_right = item_rect.right
        left_gap = bubble_left - chat_left
        right_gap = chat_right - bubble_right
        return "未知", {
            "source": "item_rect_only",
            "bubble_left": bubble_left,
            "bubble_right": bubble_right,
            "left_gap": round(left_gap, 1),
            "right_gap": round(right_gap, 1),
            "candidate_count": 0,
        }

    bubble_rects = []
    for left, top, right, bottom in rects:
        width = right - left
        height = bottom - top
        if width <= chat_width * 0.75 and height <= max((item_rect.bottom - item_rect.top) * 1.5, 200):
            bubble_rects.append((left, top, right, bottom))

    if bubble_rects:
        bubble_left = min(rect[0] for rect in bubble_rects)
        bubble_right = max(rect[2] for rect in bubble_rects)
        source = "bubble_rects"
    else:
        # 退化为“边缘锚点”判定：看候选子控件谁更贴近聊天区左右边界。
        bubble_left = min(rect[0] for rect in rects)
        bubble_right = max(rect[2] for rect in rects)
        source = "anchor_rects"

    left_gap = bubble_left - chat_left
    right_gap = chat_right - bubble_right

    if left_gap <= zone_width and right_gap > zone_width:
        side = "对方"
    elif right_gap <= zone_width and left_gap > zone_width:
        side = "我"
    elif left_gap <= zone_width and right_gap <= zone_width:
        if left_gap < right_gap:
            side = "对方"
        elif right_gap < left_gap:
            side = "我"
        else:
            side = "未知"
    else:
        side = "未知"

    return side, {
        "source": source,
        "bubble_left": bubble_left,
        "bubble_right": bubble_right,
        "left_gap": round(left_gap, 1),
        "right_gap": round(right_gap, 1),
        "candidate_count": len(rects),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="搜索指定会话并打印当前可见消息，发送方按几何规则判断。"
    )
    parser.add_argument("friend", help="好友备注或群聊名")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.30,
        help="左右边界阈值，占聊天区宽度比例，默认 0.30",
    )
    parser.add_argument(
        "--search-pages",
        type=int,
        default=0,
        help="为 0 时直接使用顶部搜索，默认 0",
    )
    parser.add_argument(
        "--dump-geometry",
        action="store_true",
        help="为每条可见消息打印完整控件几何信息",
    )
    args = parser.parse_args()

    GlobalConfig.is_maximize = False
    GlobalConfig.close_weixin = False

    main_window = Navigator.open_dialog_window(
        friend=args.friend,
        is_maximize=False,
        search_pages=args.search_pages,
    )

    lists = Lists()
    chat_list = main_window.child_window(**lists.FriendChatList)
    items = chat_list.children(control_type="ListItem")

    print(f"会话: {args.friend}")
    print(f"当前可见消息条数: {len(items)}")
    print(f"几何阈值: {args.threshold:.2f}")

    for index, item in enumerate(items, 1):
        try:
            text = item.window_text().strip()
        except Exception:
            text = ""

        if not text:
            continue

        side, debug_info = infer_side_by_geometry(item, chat_list, args.threshold)
        sender_hint = extract_sender_hint(item)

        print(
            f"[{index}] side={side} "
            f"source={debug_info['source']} "
            f"candidate_count={debug_info['candidate_count']} "
            f"sender_hint={sender_hint!r} "
            f"left_gap={debug_info['left_gap']} "
            f"right_gap={debug_info['right_gap']} "
            f"text={text}"
        )

        geometry_needed = args.dump_geometry or debug_info["source"] == "item_rect_only"
        if geometry_needed:
            geometry_info = Tools.inspect_message_item_geometry(
                item,
                chat_list=chat_list,
                recursive=True,
                max_depth=4,
                visible_only=False,
                max_nodes=80,
            )
            print(f"    geometry_summary={geometry_info['summary']}")

        if args.dump_geometry:
            lines = Tools.dump_control_geometry(
                item,
                mode="descendants",
                include_self=True,
                max_depth=4,
                relative_to=chat_list,
                max_nodes=80,
            )
            for line in lines:
                print(f"    {line}")


if __name__ == "__main__":
    main()
