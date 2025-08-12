from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import readchar
from typing import Callable, Any, Dict, List

# ========== Key mapping ==========

class Decision(Enum):
    ACCEPT = "accepted"
    STASH = "stashed"
    REJECT = "rejected"
    NEXT = "next"
    PREV = "prev"
    UNDO = "undo"
    REOPEN = "reopen"
    HELP = "help"
    QUIT = "quit"
    NONE = "none"

KEYMAP = {
    # decisions
    "a": Decision.ACCEPT, "1": Decision.ACCEPT,
    "s": Decision.STASH,  "2": Decision.STASH,
    "d": Decision.REJECT, "3": Decision.REJECT,
    # moves
    "n": Decision.NEXT, "\r": Decision.NEXT, " ": Decision.NEXT,
    readchar.key.RIGHT: Decision.NEXT, "j": Decision.NEXT,
    "b": Decision.PREV,  readchar.key.LEFT: Decision.PREV, "k": Decision.PREV,
    # utils
    "u": Decision.UNDO,
    "o": Decision.REOPEN,
    "?": Decision.HELP,
    "q": Decision.QUIT, readchar.key.ESC: Decision.QUIT,
}

def read_action() -> Decision:
    ch = readchar.readkey()
    # 一部キーは str.lower が無い（→やEsc）。安全に拾う
    key = ch.lower() if isinstance(ch, str) else ch
    return KEYMAP.get(key, Decision.NONE)

# ========== State ==========

@dataclass
class ReviewState:
    index: int = 0
    show_help: bool = False
    # 直前の決定を戻すための履歴: (idx, prev_status, prev_decided_at)
    last_ops: list[tuple[int, str, Any]] = field(default_factory=list)

# ========== Rendering (最小表示) ==========

HELP_TEXT = "A:採用 S:保留 D:破棄 / N,Enter:次 B:戻 U:Undo O:開 Q,Esc:終了 ?ヘルプ"

def render_line(cur_item: Dict[str, Any], st: ReviewState, total: int) -> None:
    rel = cur_item.get("relpath", "?")
    stat = cur_item.get("status", "?")
    idx1 = st.index + 1
    line = f"[{idx1}/{total}] {stat:<8} - {rel}"
    print("\r" + " " * 120 + "\r", end="")  # 行クリア
    print(line, end="")
    if st.show_help:
        print("\n" + HELP_TEXT)
    else:
        print("", end="", flush=True)

# ========== Main loop ==========

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def review_loop(
    items: List[Dict[str, Any]],
    open_viewer: Callable[[Dict[str, Any]], None],
    save_record: Callable[[int, Dict[str, Any]], None],
    flush: Callable[[], None],
    start_index: int = 0,
    auto_open: bool = True,
) -> None:
    st = ReviewState(index=max(0, min(start_index, len(items) - 1)))
    try:
        if auto_open and items:
            open_viewer(items[st.index])

        while 0 <= st.index < len(items):
            cur = items[st.index]
            render_line(cur, st, len(items))

            act = read_action()
            if act == Decision.NONE:
                continue
            if act == Decision.QUIT:
                break
            if act == Decision.HELP:
                st.show_help = not st.show_help
                continue
            if act == Decision.REOPEN:
                open_viewer(cur)
                continue

            if act == Decision.UNDO and st.last_ops:
                idx, prev_status, prev_dt = st.last_ops.pop()
                cur2 = items[idx]
                cur2["status"] = prev_status
                cur2["decided_at"] = prev_dt
                save_record(idx, cur2)
                st.index = idx
                flush()
                continue

            if act in (Decision.ACCEPT, Decision.STASH, Decision.REJECT):
                prev_status = cur.get("status")
                prev_dt = cur.get("decided_at")
                st.last_ops.append((st.index, prev_status, prev_dt))

                cur["status"] = act.value
                cur["decided_at"] = now_iso()
                save_record(st.index, cur)
                st.index += 1
                if st.index < len(items) and auto_open:
                    open_viewer(items[st.index])
                flush()
                continue

            if act == Decision.NEXT:
                st.index = min(len(items) - 1, st.index + 1)
                if auto_open:
                    open_viewer(items[st.index])
                continue

            if act == Decision.PREV:
                st.index = max(0, st.index - 1)
                if auto_open:
                    open_viewer(items[st.index])
                continue

    except KeyboardInterrupt:
        # Ctrl+C でも安全保存
        pass
    finally:
        flush()
        print("\n保存して終了しました。")
