# pyweixin 控件几何信息接口设计

## 1. 目标

为 `pyweixin` 增加一组调试/观测接口，用于返回任意 UIA 控件及其子控件的几何信息，重点服务以下场景：

- 调试微信 4.1+ 聊天区消息 `ListItem` 的控件树
- 观察某个控件是否暴露了可用于几何判定的子节点
- 为消息“我/对方”几何判定规则提供原始观测数据
- 辅助定位为什么某些 UIA 控件只有整行容器，没有真实气泡边界

## 2. 非目标

这组接口不负责：

- 保证一定拿到“真实气泡边界”
- 保证一定能区分“我/对方”
- 自动推断业务含义
- 替代截图法

根因很明确：如果微信当前 UIA 树没有暴露更细的子控件，这组接口只能如实返回现有树，无法凭空创造气泡节点。

## 3. 适用范围

- 平台：Windows
- 运行时：`pywinauto` + UI Automation
- 模块落点：`pyweixin/WeChatTools.py`
- 对外暴露入口：`pyweixin.Tools`

不建议放在：

- `utils.py`：这里更偏业务辅助函数，不适合作为通用调试工具
- `WeChatAuto.py`：这里是业务动作层，不应混入底层控件树采集逻辑

## 4. 总体设计

设计分两层：

1. 通用采集接口
- 输入任意控件
- 返回当前控件、子控件或后代控件的结构化几何信息

2. 消息场景封装
- 输入聊天消息 `ListItem`
- 返回“消息自身 + children + descendants + summary”
- 方便在脚本里直接调试聊天区消息结构

## 5. API 设计

### 5.1 通用接口

建议放在 `Tools` 内：

```python
@staticmethod
def collect_control_geometry(
    control,
    mode: Literal['children', 'descendants']='children',
    include_self: bool=False,
    max_depth: int|None=1,
    control_types: list[str]|None=None,
    visible_only: bool=False,
    enabled_only: bool=False,
    relative_to=None,
    max_nodes: int=200,
    with_runtime_id: bool=True,
    with_text_length: bool=True,
) -> list[dict]:
    ...
```

### 5.2 消息调试接口

```python
@staticmethod
def inspect_message_item_geometry(
    listitem,
    chat_list=None,
    recursive: bool=True,
    max_depth: int|None=4,
    visible_only: bool=False,
    max_nodes: int=100,
) -> dict:
    ...
```

### 5.3 轻量文本接口

为了方便直接打印调试结果，建议再提供一个压缩版接口：

```python
@staticmethod
def dump_control_geometry(
    control,
    mode: Literal['children', 'descendants']='children',
    include_self: bool=False,
    max_depth: int|None=1,
    relative_to=None,
    max_nodes: int=200,
) -> list[str]:
    ...
```

用途：

- 快速 CLI/脚本调试
- 不需要自己格式化结构化结果

这个接口本质上调用 `collect_control_geometry()`，只是把结果格式化成字符串列表。

## 6. 参数语义

### `control`

支持：

- `WindowSpecification`
- `ListItemWrapper`
- 其他 pywinauto wrapper

不支持：

- 原始句柄
- 普通 dict selector

如果用户传入 selector 或句柄，应先在上层完成 `window(...)` 或 `child_window(...)` 定位。

### `mode`

- `children`：只看一层直接子控件
- `descendants`：递归采集后代控件

建议默认 `children`，因为：

- 量更小
- 更利于先看结构边界
- 不容易一次拉出大量无关节点

### `include_self`

是否把传入控件本身也加入结果。

建议：

- 通用接口默认 `False`
- 消息调试接口内部固定额外返回 `self`

### `max_depth`

递归深度限制。

语义：

- `0`：只返回 self
- `1`：只返回直接子控件
- `2`：返回子控件及孙控件
- `None`：不限制深度，但仍受 `max_nodes` 限制

注意：

- `mode='children'` 时，`max_depth` 应自动视为 `1`

### `control_types`

仅保留这些 `control_type` 的控件。

例如：

```python
['Button', 'Text', 'Pane']
```

如果为 `None`，则不过滤。

### `visible_only`

是否只返回 `is_visible()==True` 的控件。

默认不启用，理由：

- 调试时隐藏控件也有价值
- 很多结构问题恰恰出在“控件存在但不可见”

### `enabled_only`

是否只返回 `is_enabled()==True` 的控件。

默认不启用。

### `relative_to`

用于计算相对坐标的参考控件。

典型值：

- 聊天区消息调试：传 `chat_list`
- 普通场景：传父容器

如果为空，则不生成相对坐标字段。

### `max_nodes`

保护阈值，防止：

- 递归时节点数量过大
- UIA 卡顿
- 调试脚本输出爆炸

建议默认 `200`。

## 7. 返回结构

### 7.1 单个节点结构

```python
{
    "index": 0,
    "parent_index": None,
    "depth": 0,
    "control_type": "Text",
    "class_name": "mmui::XTextView",
    "automation_id": "",
    "framework_id": "Qt",
    "title": "这个场景很丝滑",
    "visible": True,
    "enabled": True,
    "runtime_id": [42, 17, 9],
    "handle": 123456,
    "rect": {
        "left": 100,
        "top": 200,
        "right": 320,
        "bottom": 248,
        "width": 220,
        "height": 48,
        "mid_x": 210,
        "mid_y": 224
    },
    "relative_rect": {
        "left": 20,
        "top": 10,
        "right": 240,
        "bottom": 58,
        "width": 220,
        "height": 48,
        "mid_x": 130,
        "mid_y": 34
    },
    "relative_pct": {
        "left": 0.08,
        "right": 0.31,
        "top": 0.02,
        "bottom": 0.12,
        "width": 0.23,
        "height": 0.10
    },
    "text_length": 8
}
```

### 7.2 字段说明

- `index`：当前结果中的唯一索引
- `parent_index`：父节点索引，用于恢复树
- `depth`：深度
- `control_type`：UIA 控件类型
- `class_name`：类名
- `automation_id`：自动化 ID
- `framework_id`：框架，如 `Qt`、`Win32`
- `title`：`window_text()`
- `visible`：`is_visible()`
- `enabled`：`is_enabled()`
- `runtime_id`：底层运行时 ID，便于查重
- `handle`：尽量返回，失败则为 `None`
- `rect`：绝对屏幕坐标
- `relative_rect`：相对 `relative_to` 的坐标
- `relative_pct`：相对比例，专门给“左 30% / 右 30%”规则用
- `text_length`：便于快速筛选空文本节点

## 8. 消息调试接口返回结构

`inspect_message_item_geometry()` 建议返回：

```python
{
    "self": {...},
    "children": [...],
    "descendants": [...],
    "summary": {
        "children_count": 3,
        "descendants_count": 12,
        "visible_descendants_count": 7,
        "min_left": 102,
        "max_right": 614,
        "has_button": True,
        "has_text": True,
        "has_visible_button": False,
        "has_visible_text": True
    }
}
```

说明：

- `self`：消息项自身几何信息
- `children`：直接子节点
- `descendants`：递归后代
- `summary`：辅助判断 UIA 是否暴露了有价值结构

## 9. 内部实现流程

### 9.1 通用接口流程

1. 标准化输入控件
2. 读取当前控件自身信息
3. 根据 `mode` 决定 `children()` 或递归 `children()`
4. 对每个节点尝试采集：
   - `window_text()`
   - `class_name()`
   - `automation_id()`
   - `framework_id()`
   - `rectangle()`
   - `is_visible()`
   - `is_enabled()`
   - `runtime_id`
5. 如果采集失败：
   - 单字段失败不终止整节点
   - 单节点失败不终止整次遍历
6. 超过 `max_nodes` 立刻停止
7. 生成相对坐标和比例
8. 返回结构化结果

### 9.2 递归策略

推荐 DFS。

原因：

- 更容易保留父子关系
- 更容易使用 `depth`
- 输出更接近树结构

### 9.3 查重策略

不要只用 `runtime_id` 查重。

建议组合：

- 优先 `runtime_id`
- 退化到 `(control_type, class_name, rect, title)` 组合

因为：

- 某些节点可能拿不到 `runtime_id`
- 有些节点在不同遍历层级会重复暴露

## 10. 相对坐标设计

如果传了 `relative_to`，则：

```python
relative_left = node_left - base_left
relative_right = node_right - base_left
relative_width = node_width
left_pct = relative_left / base_width
right_pct = relative_right / base_width
width_pct = relative_width / base_width
```

注意：

- `right_pct` 是右边界相对父容器左边界的比例
- 如果你要判断“靠右 30%”，业务层更适合用：

```python
right_gap_pct = (base_right - node_right) / base_width
```

因此建议在 `relative_pct` 里额外加入：

```python
{
    "left_gap": ...,
    "right_gap": ...
}
```

## 11. 文本接口格式

`dump_control_geometry()` 建议输出单行格式：

```text
[0] depth=0 parent=None type=ListItem class=mmui::ChatTextItemView auto_id= title='这个场景很丝滑' visible=True rect=(100,200,320,248) rel=(20,10,240,58) pct=(left=0.08,right=0.31)
```

这样方便直接：

- `print()`
- 写日志
- 存文件

## 12. 建议的方法签名细化

### 12.1 通用采集接口

```python
@staticmethod
def collect_control_geometry(
    control,
    mode: Literal['children', 'descendants']='children',
    include_self: bool=False,
    max_depth: int|None=1,
    control_types: list[str]|None=None,
    visible_only: bool=False,
    enabled_only: bool=False,
    relative_to=None,
    max_nodes: int=200,
    with_runtime_id: bool=True,
    with_text_length: bool=True,
) -> list[dict]:
    """返回控件树的结构化几何信息"""
```

### 12.2 消息项调试接口

```python
@staticmethod
def inspect_message_item_geometry(
    listitem,
    chat_list=None,
    recursive: bool=True,
    max_depth: int|None=4,
    visible_only: bool=False,
    max_nodes: int=100,
) -> dict:
    """返回聊天消息项的自身/子节点/后代节点几何信息"""
```

### 12.3 文本调试接口

```python
@staticmethod
def dump_control_geometry(
    control,
    mode: Literal['children', 'descendants']='children',
    include_self: bool=False,
    max_depth: int|None=1,
    relative_to=None,
    max_nodes: int=200,
) -> list[str]:
    """返回适合打印的单行调试文本"""
```

## 13. 边界条件

### 13.1 `window_text()` 为空

不能丢弃。

原因：

- 很多容器控件没文本
- 真实气泡容器可能正是无文本节点

### 13.2 `rectangle()` 获取失败

跳过该节点，但保留其他节点。

### 13.3 节点过多

当超过 `max_nodes` 时：

- 停止遍历
- 在返回结果中增加：

```python
"truncated": True
```

### 13.4 `relative_to` 无法取矩形

不抛异常，直接不生成 `relative_rect` 和 `relative_pct`

### 13.5 循环引用或重复暴露

必须做去重，否则：

- 结果爆炸
- 调试价值下降

## 14. 对消息发送方判断的价值

这组接口只能解决“看清楚现在 UIA 树长什么样”。

对你当前场景，它的价值是：

1. 证实是不是只有整行 `ListItem`
2. 看有没有更细的 `Button/Text/Pane/Custom` 节点
3. 看这些节点的 `relative_pct.left/right`
4. 决定后续是继续走 UIA 几何，还是改走截图法

它不能自动解决：

- 微信 4.1 没暴露气泡子控件

## 15. 使用示例

### 15.1 调试聊天消息项

```python
from pyweixin import Navigator, Tools
from pyweixin.Uielements import Lists

main_window = Navigator.open_dialog_window(friend='xx', search_pages=0, is_maximize=False)
lists = Lists()
chat_list = main_window.child_window(**lists.FriendChatList)
item = chat_list.children(control_type='ListItem')[0]

info = Tools.inspect_message_item_geometry(item, chat_list=chat_list, recursive=True, max_depth=4)
print(info['summary'])
```

### 15.2 打印 descendants

```python
lines = Tools.dump_control_geometry(
    item,
    mode='descendants',
    include_self=True,
    max_depth=4,
    relative_to=chat_list,
    max_nodes=100,
)
for line in lines:
    print(line)
```

## 16. 实现优先级

建议顺序：

1. `collect_control_geometry`
2. `dump_control_geometry`
3. `inspect_message_item_geometry`

原因：

- 通用接口是底座
- 文本接口便于立刻验证
- 消息接口只是一个轻封装

## 17. 验收标准

- 对任意控件可返回 `children` 的结构化几何信息
- 对任意控件可返回 `descendants` 的结构化几何信息
- 对聊天消息 `ListItem` 至少能稳定返回自身矩形
- 如果没有更细 UIA 子节点，结果必须明确体现“只有整行容器”
- 结果能直接被 `test_current_messages.py` 这类脚本消费

## 18. 一句话结论

这组接口的本质是“把 UIA 已暴露的控件几何完整拿出来”，它对调试是高价值、对实现是高可行，但它不是气泡识别算法本身。
