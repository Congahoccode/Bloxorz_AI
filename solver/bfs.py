"""Breadth-First Search (BFS) solver for the Bloxorz game."""

from collections import deque
import os
import time
import tracemalloc

try:
    from solver.ucs import Level, UNIFORM
except ImportError:
    from ucs import Level, UNIFORM


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


def _bfs(state_or_path):
    """
    Thuật toán Breadth-First Search (BFS) tối ưu cao độ:
    - Sử dụng mô hình Level nhẹ, không deepcopy đối tượng Control/pygame.
    - Kiểm tra đích ngay khi sinh trạng thái (Goal test on generation) đảm bảo tính tối ưu.
    - Hỗ trợ đầy đủ khối đôi, khối tách (swO), công tắc mềm/nặng và cầu.
    """
    level = Level(state_or_path)
    start = level.start
    if level.is_goal(start):
        cells = start[0]
        p = [[[c[0], c[1]] for c in cells]]
        return [], p, 0

    queue = deque([start])
    parent = {start: None}
    expanded = 0

    while queue:
        state = queue.popleft()
        expanded += 1

        for action, next_state, _ in level.get_next_states(state, UNIFORM):
            if next_state not in parent:
                parent[next_state] = (state, action)
                if level.is_goal(next_state):
                    actions, path = _reconstruct_path(parent, next_state)
                    return actions, path, expanded
                queue.append(next_state)

    return None, None, expanded


def bfs(state_or_path):
    """Return a shortest action sequence (fewest moves) and the number of expanded states."""
    actions, _, expanded = _bfs(state_or_path)
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
    Entry point used by run.py and GUI Launcher.
    Trả về: SolveResult(path, expanded, actions, cost) hoặc (None, 0)
    """
    try:
        actions, path, expanded = _bfs(state_or_path)
        if actions is None:
            return None, 0
        return SolveResult(path, expanded, actions=actions, cost=len(actions))
    except Exception as e:
        print(f"Lỗi khi thực thi thuật toán BFS: {e}")
        return None, 0


bfs_path = solve
bfs_search = solve
search = solve


def run_bfs(level_path):
    """Run BFS and return solution and performance metrics."""
    tracemalloc.start()
    t0 = time.perf_counter()
    actions, path, expanded = _bfs(level_path)
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
        raise SystemExit("Usage: python -m solver.bfs <level.json>")
    result = run_bfs(sys.argv[1])
    print(
        "BFS | solved=%s length=%s expanded=%s time=%.2f ms "
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
