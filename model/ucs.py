"""
BIỂU DIỄN TRẠNG THÁI:
state = (cells, bridges, used)
  cells   : các ô block đang chiếm.
            1 ô  -> Block đang đứng
            2 ô  -> Block đang nằm
  bridges : tuple 0/1, trạng thái từng cây cầu (1 = mở, 0 = đóng)
  used    : tuple 0/1, công tắc đã bấm rồi

HÀNH ĐỘNG: U (lên), D (xuống), L (trái), R (phải)
ĐÍCH: Block đứng thẳng trên ô goal
"""
import heapq
import json
import time
import tracemalloc

# 4 hướng lăn
DIRS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}

# HÀM CHI PHÍ
class CostModel:
    """
    Chi phí = base
              + fragile_extra: nếu sau khi lăn có ô nào nằm trên ô fragile
              - switch_bonus: nếu lần lăn này bấm trúng công tắc

    Chọn base = 2, fragile_extra = 2, switch_bonus = 1 nên:
      - Lăn bình thường      : 2
      - Lăn lên ô fragile    : 4  
      - Lăn bấm công tắc     : 1 
    Nếu fragile_extra = 0 và switch_bonus = 0 thì mọi bước bằng nhau suy ra UCS = BFS.
    """

    def __init__(self, base=2, fragile_extra=2, switch_bonus=1):
        self.base = base
        self.fragile_extra = fragile_extra
        self.switch_bonus = switch_bonus

    def step_cost(self, on_fragile, pressed_switch):
        cost = self.base
        if on_fragile:
            cost = cost + self.fragile_extra
        if pressed_switch:
            cost = cost - self.switch_bonus
        if cost < 1:        
            cost = 1
        return cost


# So sánh với BFS (Mô hình chi phí đều với mỗi bước=1)
UNIFORM = CostModel(base=1, fragile_extra=0, switch_bonus=0)

# ĐỌC LEVEL VÀ LUẬT CHƠI
class Level:
    def __init__(self, path):
        f = open(path, "r", encoding="utf-8")
        data = json.load(f)
        f.close()

        self.rows = data["size"][0]
        self.cols = data["size"][1]
        self.goal = tuple(data["end"])

        # Vị trí đầu của block
        start_cells = []
        for c in data["box"]["location"]:
            start_cells.append(tuple(c))
        start_cells.sort()

        # Dựng bảng: 0 = trống, 1 = sàn thường, 2 = ô fragile
        orange = data["tiles"]["orange"]
        space = data["tiles"]["space"]
        self.grid = []
        for r in range(self.rows):
            line = []
            for c in range(self.cols):
                v = data["maps"][r][c]
                if v == orange:
                    line.append(2)
                elif v == space:
                    line.append(0)
                else:
                    line.append(1)
            self.grid.append(line)

        # CÂY CẦU
        bridge_index = {}       
        self.bridge_of_cell = {}  
        first_bridges = []      
        names = data["bridge"].get("symbol", [])
        for i in range(len(names)):
            name = names[i]
            bridge_index[name] = i
            if data["bridge"][name]["active"]:
                first_bridges.append(1)
            else:
                first_bridges.append(0)
            for c in data["bridge"][name]["location"]:
                self.bridge_of_cell[tuple(c)] = i

        # CÔNG TẮC
        # switch_at[ô] = danh sách (loại, vĩnh viễn, số cầu, số công tắc)
        # swQ = công tắc mềm, swX = công tắc nặng
        # type = 0: đảo qua lại, type khác 0: bấm 1 lần
        self.switch_at = {}
        count = 0
        for key in ["swQ", "swX"]:
            if key == "swQ":
                kind = "soft"
            else:
                kind = "heavy"
            for name in data[key].get("symbol", []):
                s = data[key][name]
                pos = tuple(s["location"])
                permanent = (s["type"] != 0)   
                item = (kind, permanent, bridge_index[s["bridge"]], count)
                if pos not in self.switch_at:
                    self.switch_at[pos] = []
                self.switch_at[pos].append(item)
                count = count + 1

        # Trạng thái bắt đầu
        self.start = (tuple(start_cells), tuple(first_bridges), tuple([0] * count))

    def is_goal(self, state):
        cells = state[0]
        return len(cells) == 1 and cells[0] == self.goal # Thắng khi block đứng đúng ô goal

    def can_stand(self, cells, bridges):
        standing = (len(cells) == 1)
        for cell in cells:
            r = cell[0]
            c = cell[1]
            # Ra khỏi bảng
            if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
                return False

            if cell in self.bridge_of_cell:
                # Ô thuộc cầu: chỉ đi được khi cầu đang mở
                if bridges[self.bridge_of_cell[cell]] == 0:
                    return False
            elif self.grid[r][c] == 0:
                # Ô trống: rơi ngoại trừ ô goal
                if cell != self.goal:
                    return False
            elif self.grid[r][c] == 2 and standing:
                # Ô fragile: đứng lên là vỡ
                return False
        return True

    def roll(self, cells, direction):
        # Lăn block theo một hướng, trả về ô mới
        dr = direction[0]
        dc = direction[1]

        if len(cells) == 1:
            # Đứng chuyển sang nằm, chiếm 2 ô theo hướng lăn
            r = cells[0][0]
            c = cells[0][1]
            new_cells = [(r + dr, c + dc), (r + 2 * dr, c + 2 * dc)]
        else:
            r1 = cells[0][0]
            c1 = cells[0][1]
            r2 = cells[1][0]
            c2 = cells[1][1]
            if (r2 - r1, c2 - c1) == (dr, dc):
                # Nằm dọc theo hướng lăn, đầu trước là ô thứ 2: chuyển sang đứng
                new_cells = [(r2 + dr, c2 + dc)]
            elif (r1 - r2, c1 - c2) == (dr, dc):
                # đầu trước là ô thứ 1: chuyển sang đứng
                new_cells = [(r1 + dr, c1 + dc)]
            else:
                # Nằm ngang so với hướng lăn: chuyển sang nằm, trượt sang 1 ô
                new_cells = [(r1 + dr, c1 + dc), (r2 + dr, c2 + dc)]
        new_cells.sort()
        return tuple(new_cells)

    def get_next_states(self, state, cost_model):
        # Trả về danh sách hợp lệ.
        cells = state[0]
        bridges = state[1]
        used = state[2]
        result = []

        for action in DIRS:
            new_cells = self.roll(cells, DIRS[action])

            # Kiểm tra cầu hiện tại, lăn xong có rơi không
            if not self.can_stand(new_cells, bridges):
                continue

            # Kiểm tra có bấm công tắc nào không
            new_bridges = list(bridges)
            new_used = list(used)
            pressed = False
            standing = (len(new_cells) == 1)

            for cell in new_cells:
                if cell not in self.switch_at:
                    continue
                for sw in self.switch_at[cell]:
                    kind = sw[0]
                    permanent = sw[1]
                    bridge_id = sw[2]
                    sw_id = sw[3]
                    if kind == "heavy" and not standing:
                        continue            
                    if permanent and new_used[sw_id] == 1:
                        continue            
                    # Đảo trạng thái cầu
                    new_bridges[bridge_id] = 1 - new_bridges[bridge_id]
                    if permanent:
                        new_used[sw_id] = 1
                    pressed = True

            new_bridges = tuple(new_bridges)
            new_used = tuple(new_used)

            # Kiểm tra cầu vừa đóng ngay dưới block thì block rơi không
            if pressed and not self.can_stand(new_cells, new_bridges):
                continue

            # Tính chi phí
            on_fragile = False
            for cell in new_cells:
                if self.grid[cell[0]][cell[1]] == 2:
                    on_fragile = True
            cost = cost_model.step_cost(on_fragile, pressed)

            new_state = (new_cells, new_bridges, new_used)
            result.append((action, new_state, cost))
        return result


# THUẬT TOÁN UCS
def ucs(level, cost_model):
    start = level.start

    counter = 0
    frontier = [(0, counter, start)] # heap các phần tử

    best_g = {start: 0}         # Chi phí nhỏ nhất 
    parent = {start: None}     
    closed = set()              # Các state đã mở rộng xong
    expanded = 0                # Đếm số node đã mở rộng

    while len(frontier) > 0:
        g, _, state = heapq.heappop(frontier)

        # Một state với g khác nhau có thể bị đẩy heap nhiều lần
        # Mở rộng rồi thì bỏ qua bản cũ
        if state in closed:
            continue

        # Kiểm tra đích
        if level.is_goal(state):
            return build_result(level, state, parent, g, expanded)

        closed.add(state)
        expanded = expanded + 1

        for action, next_state, cost in level.get_next_states(state, cost_model):
            new_g = g + cost
            if next_state in closed:
                continue
            if next_state not in best_g or new_g < best_g[next_state]:
                best_g[next_state] = new_g
                parent[next_state] = (state, action)
                counter = counter + 1
                heapq.heappush(frontier, (new_g, counter, next_state))

    return None


def build_result(level, goal_state, parent, total_cost, expanded):
    #Truy ngược từ đích về đầu bằng parent để lấy đường đi
    actions = []
    states = []
    state = goal_state
    while state is not None:
        states.append(state)
        if parent[state] is None:
            state = None
        else:
            actions.append(parent[state][1])
            state = parent[state][0]
    actions.reverse()
    states.reverse()

    # Đổi sang dạng list
    path = []
    for s in states:
        cells = []
        for c in s[0]:
            cells.append([c[0], c[1]])
        path.append(cells)

    return {"actions": "".join(actions), "path": path,
            "cost": total_cost, "expanded": expanded}


# CHẠY VÀ ĐO SỐ LIỆU
def run_ucs(level_path, cost_model=None):
    # Chạy UCS và ghi lại 4 số liệu trên 1 level
    if cost_model is None:
        cost_model = CostModel()
    level = Level(level_path)

    tracemalloc.start()                 # Bắt đầu đo bộ nhớ
    t0 = time.perf_counter()            # Bắt đầu bấm giờ
    res = ucs(level, cost_model)
    elapsed = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]   # Bộ nhớ đỉnh 
    tracemalloc.stop()

    out = {"solved": res is not None, "time_s": elapsed, "peak_mem_kb": peak / 1024,
           "expanded": None, "length": None, "cost": None,
           "actions": None, "path": None}
    if res is not None:
        out["expanded"] = res["expanded"]
        out["length"] = len(res["actions"])
        out["cost"] = res["cost"]
        out["actions"] = res["actions"]
        out["path"] = res["path"]
    return out