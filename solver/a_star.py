"""
THUẬT TOÁN A* CHO BLOXORZ (A-STAR SEARCH ALGORITHM)
===================================================
1. BIỂU DIỄN TRẠNG THÁI:
   state = (cells, bridges, used)
     cells   : tuple toạ độ các ô block đang chiếm (sắp xếp tăng dần).
               - 1 ô : Block đang đứng thẳng ((r, c),)
               - 2 ô : Block đang nằm ((r1, c1), (r2, c2))
     bridges : tuple 0/1, trạng thái từng cây cầu (1 = mở, 0 = đóng)
     used    : tuple 0/1, ghi nhận các công tắc vĩnh viễn đã được kích hoạt

2. QUY ƯỚC CÁC HÀM CHI PHÍ VÀ ĐÁNH GIÁ:
   - g(m) : Chi phí thực tế từ trạng thái xuất phát s0 đến trạng thái hiện tại m.
            g(m) = g(parent(m)) + cost(parent(m), action, m)
            Mặc định: cost = 1 cho mỗi bước đi (độ dài đường đi ngắn nhất).
            Có thể cấu hình CostModel để gán trọng số đặc biệt (ô fragile, công tắc).
   - h(m) : Hàm heuristic ước lượng chi phí từ trạng thái m đến đích (goal).
            Các mô hình heuristic:
            + 'bloxorz_admissible' (Khuyên dùng - Chấp nhận được):
              Phân rã khoảng cách Manhattan theo 2 trục toạ độ:
              dr = min(|r - rg|), dc = min(|c - cg|)
              h(m) = ceil(dr / 2) + ceil(dc / 2)
              (kèm ràng buộc trạng thái đứng khi về đích).
              Đảm bảo tính chất Admissible: h(m) <= h*(m), tìm ra lời giải tối ưu.
            + 'manhattan' (Greedy):
              Khoảng cách Manhattan trực tiếp: min(|r - rg| + |c - cg|).
            + 'euclidean':
              Khoảng cách đường chim bay từ khối tâm: sqrt(dr^2 + dc^2) / 1.5.
   - f(m) : Hàm đánh giá tổng thể f(m) = g(m) + w * h(m)
            Với w = 1.0 : A* chuẩn (Optimal A*).
            Với w > 1.0 : Weighted A* (Tăng tốc tìm kiếm, mở rộng ít node hơn).

3. CƠ CHẾ TIE-BREAKING:
   Khi hai trạng thái có cùng f(m), ưu tiên trạng thái có g(m) lớn hơn (tức h(m) nhỏ hơn,
   ở gần đích hơn). Thứ tự hàng đợi ưu tiên: (f, -g, counter, state).
"""

import heapq
import json
import math
import os
import sys
import time
import tracemalloc

# Nhập cấu trúc Level, CostModel và các hướng lăn từ solver.ucs
try:
    from solver.ucs import Level, DIRS, CostModel, UNIFORM
except ImportError:
    from ucs import Level, DIRS, CostModel, UNIFORM


# ---------------------------------------------------------------------------
# CÁC HÀM HEURISTIC h(m)
# ---------------------------------------------------------------------------

def heuristic_bloxorz_admissible(cells, goal, min_step_cost=1.0):
    """
    Hàm heuristic phân rã theo trục toạ độ cho Bloxorz (Strictly Admissible).
    
    Chứng minh tính chấp nhận được (Admissibility):
    - Khối 1x1x2 trong 1 bước lăn (U, D, L, R) chỉ di chuyển trên ĐÚNG MỘT TRỤC (Row hoặc Col).
    - Trên mỗi trục, toạ độ của khối có thể thay đổi tối đa 2 đơn vị trong 1 bước
      (khi từ trạng thái đứng lật sang nằm).
    - Do đó, số bước tối thiểu để triệt tiêu khoảng cách dr là ceil(dr / 2),
      và khoảng cách dc là ceil(dc / 2).
    - Vì mỗi bước chỉ giảm khoảng cách trên một trục duy nhất, tổng số bước tối thiểu
      để đi từ vị trí hiện tại đến ô đích (rg, cg) bắt buộc phải thoả:
          h*(m) >= ceil(dr / 2) + ceil(dc / 2)
    - Ngoài ra, để hoàn thành màn chơi, khối phải ở trạng thái ĐỨNG THẲNG trên ô goal.
      Nếu khối đang nằm (len(cells) == 2) và khoảng cách h == 0 (đang nằm đè sát goal),
      khối vẫn cần ít nhất 1 bước lăn để dựng đứng vào goal.
    
    Hàm này đảm bảo h(m) <= h*(m) với mọi trạng thái m, suy ra A* luôn tìm ra lời giải tối ưu.
    """
    rg, cg = goal
    min_dr = min(abs(r - rg) for r, c in cells)
    min_dc = min(abs(c - cg) for r, c in cells)
    
    h_r = math.ceil(min_dr / 2.0)
    h_c = math.ceil(min_dc / 2.0)
    h = h_r + h_c
    
    # Ràng buộc trạng thái đứng khi khối ở sát đích
    if len(cells) == 2 and h == 0:
        h = 1
        
    return h * min_step_cost


def heuristic_manhattan(cells, goal, min_step_cost=1.0):
    """
    Khoảng cách Manhattan trực tiếp từ ô gần đích nhất của khối tới đích.
    h(m) = min(|r - rg| + |c - cg|) * min_step_cost.
    Định hướng tham lam (greedy) rất mạnh, giúp tìm đường rất nhanh.
    """
    rg, cg = goal
    d_min = min(abs(r - rg) + abs(c - cg) for r, c in cells)
    return d_min * min_step_cost


def heuristic_euclidean(cells, goal, min_step_cost=1.0):
    """
    Khoảng cách Euclidean từ trọng tâm khối tới đích, chuẩn hoá theo độ dài bước.
    """
    rg, cg = goal
    cr = sum(r for r, c in cells) / len(cells)
    cc = sum(c for r, c in cells) / len(cells)
    dist = math.sqrt((cr - rg) ** 2 + (cc - cg) ** 2)
    return (dist / 1.5) * min_step_cost


def calc_heuristic(cells, goal, heur_type='bloxorz_admissible', min_step_cost=1.0):
    """Điều phối tính toán hàm heuristic theo loại cấu hình."""
    if heur_type in ('bloxorz_admissible', 'admissible', 'optimal'):
        return heuristic_bloxorz_admissible(cells, goal, min_step_cost)
    elif heur_type in ('manhattan', 'l1', 'greedy'):
        return heuristic_manhattan(cells, goal, min_step_cost)
    elif heur_type in ('euclidean', 'l2'):
        return heuristic_euclidean(cells, goal, min_step_cost)
    elif heur_type in ('none', 'zero'):
        return 0.0
    return heuristic_bloxorz_admissible(cells, goal, min_step_cost)


# ---------------------------------------------------------------------------
# THUẬT TOÁN A* SEARCH
# ---------------------------------------------------------------------------

def astar(level, heur_type='bloxorz_admissible', weight=1.0, cost_model=None):
    """
    Thuật toán tìm kiếm A* cho Bloxorz.
    
    Tham số:
      - level      : Đối tượng Level chứa bản đồ và quy tắc trò chơi.
      - heur_type  : Loại heuristic ('bloxorz_admissible', 'manhattan', 'euclidean').
      - weight     : Trọng số heuristic w (mặc định 1.0 cho A* chuẩn; > 1.0 cho Weighted A*).
      - cost_model : Mô hình chi phí CostModel (mặc định UNIFORM: 1 cost / 1 move).
      
    Trả về:
      - Dictionary kết quả: {"actions": chuỗi nước đi, "path": danh sách toạ độ,
                             "cost": tổng chi phí, "expanded": số node mở rộng}
      - Hoặc None nếu không tìm thấy lời giải.
    """
    if cost_model is None:
        cost_model = UNIFORM

    start = level.start
    goal = level.goal
    min_step_cost = getattr(cost_model, 'base', 1.0)

    counter = 0
    h0 = calc_heuristic(start[0], goal, heur_type, min_step_cost)
    f0 = 0.0 + weight * h0

    # Priority queue: (f(m), -g(m), counter, state)
    # Tie-breaking bằng -g(m): khi f bằng nhau, ưu tiên g lớn hơn (h nhỏ hơn, gần đích hơn)
    frontier = [(f0, 0.0, counter, start)]

    best_g = {start: 0.0}
    parent = {start: None}
    closed = set()
    expanded = 0

    while len(frontier) > 0:
        f_val, neg_g, _, state = heapq.heappop(frontier)
        g_val = -neg_g

        # Bỏ qua trạng thái đã nằm trong closed set
        if state in closed:
            continue

        # Kiểm tra trạng thái đích
        if level.is_goal(state):
            return build_result(level, state, parent, g_val, expanded)

        closed.add(state)
        expanded += 1

        # Mở rộng các trạng thái kế tiếp
        for action, next_state, step_cost in level.get_next_states(state, cost_model):
            new_g = g_val + step_cost

            if next_state in closed:
                continue

            # Nếu tìm thấy đường đi tới next_state với chi phí g tốt hơn
            if next_state not in best_g or new_g < best_g[next_state]:
                best_g[next_state] = new_g
                parent[next_state] = (state, action)

                h_val = calc_heuristic(next_state[0], goal, heur_type, min_step_cost)
                new_f = new_g + weight * h_val

                counter += 1
                heapq.heappush(frontier, (new_f, -new_g, counter, next_state))

    return None


def build_result(level, goal_state, parent, total_cost, expanded):
    """Truy vết lại đường đi từ goal_state về start qua parent dictionary."""
    actions = []
    states = []
    curr = goal_state
    while curr is not None:
        states.append(curr)
        if parent[curr] is None:
            curr = None
        else:
            actions.append(parent[curr][1])
            curr = parent[curr][0]
    actions.reverse()
    states.reverse()

    path = []
    for s in states:
        cells = [[c[0], c[1]] for c in s[0]]
        path.append(cells)

    return {
        "actions": "".join(actions),
        "path": path,
        "cost": total_cost,
        "expanded": expanded
    }


# ---------------------------------------------------------------------------
# CHẠY VÀ ĐO LƯỜNG HIỆU NĂNG (BENCHMARK INTERFACE)
# ---------------------------------------------------------------------------

def run_astar(level_path, heur_type='bloxorz_admissible', weight=1.0, cost_model=None):
    """
    Thực thi A* trên một level và đo đạc các chỉ số: thời gian, RAM đỉnh, số bước, số node mở rộng.
    """
    if cost_model is None:
        cost_model = UNIFORM
    level = Level(level_path)

    tracemalloc.start()
    t0 = time.perf_counter()
    res = astar(level, heur_type=heur_type, weight=weight, cost_model=cost_model)
    elapsed = time.perf_counter() - t0
    peak_mem = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    out = {
        "solved": res is not None,
        "time_s": elapsed,
        "peak_mem_kb": peak_mem / 1024.0,
        "expanded": None,
        "length": None,
        "cost": None,
        "actions": None,
        "path": None
    }
    if res is not None:
        out["expanded"] = res["expanded"]
        out["length"] = len(res["actions"])
        out["cost"] = res["cost"]
        out["actions"] = res["actions"]
        out["path"] = res["path"]
    return out


class SolveResult(tuple):
    """Tuỳ biến tuple trả về để vừa tương thích (path, expanded) vừa chứa actions và cost."""
    def __new__(cls, path, expanded, actions=None, cost=None):
        return super().__new__(cls, (path, expanded))

    def __init__(self, path, expanded, actions=None, cost=None):
        self.path = path
        self.expanded = expanded
        self.actions = actions
        self.cost = cost


# ---------------------------------------------------------------------------
# ENTRY POINT CHO RUN.PY VÀ GUI
# ---------------------------------------------------------------------------

def solve(state_or_path, heur_type='bloxorz_admissible', weight=1.0, cost_model=None):
    """
    Điểm vào giải bài toán chuẩn tương thích với run.py và GUI Launcher.
    
    Nhận:
      - state_or_path : đường dẫn JSON, đối tượng Control, hoặc đối tượng Level.
      - heur_type     : 'bloxorz_admissible' (mặc định), 'manhattan', 'euclidean'.
      - weight        : 1.0 (chuẩn tối ưu) hoặc > 1.0 (weighted).
      - cost_model    : UNIFORM (mặc định) hoặc CostModel tuỳ chỉnh.
      
    Trả về:
      - SolveResult(path, expanded, actions, cost) nếu tìm thấy lời giải.
      - (None, 0) nếu không có đường đi.
    """
    if cost_model is None:
        cost_model = UNIFORM
    try:
        level = Level(state_or_path)
        res = astar(level, heur_type=heur_type, weight=weight, cost_model=cost_model)
        if res is None:
            return None, 0
        return SolveResult(res["path"], res["expanded"], actions=res["actions"], cost=res["cost"])
    except Exception as e:
        print(f"Lỗi khi thực thi thuật toán A*: {e}")
        return None, 0


# Các bí danh (aliases) tương thích với run.py và các trình gọi khác
a_star = solve
astar_func = solve
astar_path = solve

