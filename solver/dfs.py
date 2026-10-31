"""Depth-First Search (DFS) solver for the Bloxorz game."""

import os
import time
import tracemalloc

try:
    from solver.ucs import Level, UNIFORM
except ImportError:
    from ucs import Level, UNIFORM


# Thứ tự ưu tiên nhánh duyệt chuẩn cho DFS Bloxorz:
# U (lên), D (xuống), R (phải), L (trái), SW (đổi khối nếu tách)
DFS_ORDER = ("U", "D", "R", "L", "SW")


def _reconstruct_path(parent, goal_state):
    """Truy vết lại danh sách actions và path từ goal_state về start qua parent dict."""
    actions = []
    states = []
    curr = goal_state
    while curr is not None:
        states.append(curr)
        if parent[curr] is None:
            curr = None
        else:
            p_s, act = parent[curr]
            actions.append(act)
            curr = p_s
    actions.reverse()
    states.reverse()

    path = []
    for s in states:
        cells = s[0]
        if len(cells) == 3:
            loc1 = [[cells[0][0][0], cells[0][0][1]]]
            loc2 = [[cells[1][0][0], cells[1][0][1]]]
            path.append((loc1, loc2, cells[2]))
        else:
            path.append([[c[0], c[1]] for c in cells])

    return actions, path


def _dfs(state_or_path):
    """
    Thuật toán Depth-First Search (DFS) tối ưu cao độ:
    - Sử dụng mô hình Level nhẹ, không deepcopy đối tượng Control/pygame.
    - Quản lý visited set để tránh vòng lặp chu trình.
    - Hỗ trợ đầy đủ khối đôi, khối tách (swO), công tắc mềm/nặng và cầu.
    """
    level = Level(state_or_path)
    start = level.start
    if level.is_goal(start):
        cells = start[0]
        p = [[[c[0], c[1]] for c in cells]]
        return [], p, 0

    stack = [start]
    parent = {start: None}
    visited = {start}
    expanded = 0

    while stack:
        state = stack.pop()
        if level.is_goal(state):
            actions, path = _reconstruct_path(parent, state)
            return actions, path, expanded

        expanded += 1
        next_states_map = {action: nxt for action, nxt, _ in level.get_next_states(state, UNIFORM)}
        # Duyệt theo thứ tự đảo ngược khi đẩy vào LIFO stack để hành động đầu tiên được pop ra trước:
        for action in reversed(DFS_ORDER):
            if action in next_states_map:
                next_state = next_states_map[action]
                if next_state not in visited:
                    visited.add(next_state)
                    parent[next_state] = (state, action)
                    stack.append(next_state)

    return None, None, expanded


def dfs(state_or_path):
    """Return a DFS action sequence and the number of expanded states."""
    actions, _, expanded = _dfs(state_or_path)
    return actions, expanded


class SolveResult(tuple):
    """Tuỳ biến tuple trả về để vừa tương thích (path, expanded) vừa chứa actions và cost."""
    def __new__(cls, path, expanded, actions=None, cost=None):
        return super().__new__(cls, (path, expanded))

    def __init__(self, path, expanded, actions=None, cost=None):
        self.path = path
        self.expanded = expanded
        self.actions = actions
        self.cost = cost


def solve(state_or_path):
    """
    Entry point được sử dụng bởi run.py và GUI Launcher.
    Trả về: SolveResult(path, expanded, actions, cost) hoặc (None, 0)
    """
    try:
        actions, path, expanded = _dfs(state_or_path)
        if actions is None:
            return None, 0
        return SolveResult(path, expanded, actions=actions, cost=len(actions))
    except Exception as e:
        print(f"Lỗi khi thực thi thuật toán DFS: {e}")
        return None, 0


dfs_path = solve
dfs_search = solve
search = solve


def run_dfs(level_path):
    """Chạy thuật giải DFS và trả về các chỉ số giải pháp và hiệu năng"""
    tracemalloc.start()
    t0 = time.perf_counter()
    actions, path, expanded = _dfs(level_path)
    elapsed = time.perf_counter() - t0
    peak_memory = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    return {
        "solved": actions is not None,
        "time_s": elapsed,
        "peak_mem_kb": peak_memory / 1024.0,
        "expanded": expanded,
        "length": len(actions) if actions is not None else None,
        "cost": len(actions) if actions is not None else None,
        "actions": actions,
        "path": path,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m solver.dfs <level.json>")
    result = run_dfs(sys.argv[1])
    print(
        "DFS | solved=%s length=%s expanded=%s time=%.2f ms "
        "peak_mem=%.1f KB"
        % (
            result["solved"],
            result["length"],
            result["expanded"],
            result["time_s"] * 1000,
            result["peak_mem_kb"],
        )
    )
    print("Moves:", " ".join(result["actions"]) if result["actions"] else None)
