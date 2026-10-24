"""Depth-First Search solver for the Bloxorz game."""

from copy import deepcopy
import os
import time
import tracemalloc

from model.control import Control
from model.map import maps


MOVES = (
    ("U", "move_up"),
    ("D", "move_down"),
    ("R", "move_right"),
    ("L", "move_left"),
)
MOVE_METHODS = dict(MOVES)


def _make_control(state_or_path):
    if isinstance(state_or_path, Control):
        control = deepcopy(state_or_path)
    elif isinstance(state_or_path, maps):
        control = Control(deepcopy(state_or_path))
    elif isinstance(state_or_path, (str, os.PathLike)):
        control = Control(maps(os.fspath(state_or_path)))
    else:
        raise TypeError("DFS expects a level path, maps instance, or Control state")

    control.Play_handle = True
    return control


def _location_key(location):
    return tuple(tuple(cell) for cell in location)


def _state_key(control):
    game_map = control.maps
    current = control.current
    if game_map.is_split and len(game_map.split_boxes) == 2:
        block_state = (
            _location_key(game_map.split_boxes[0].location),
            _location_key(game_map.split_boxes[1].location),
            game_map.active_box_index,
        )
    else:
        block_state = _location_key(current)

    tile_state = tuple(
        tuple(tile.type for tile in row)
        for row in game_map.maps
    )
    bridge_state = tuple(
        (
            bridge.symbol,
            bridge.active,
            bridge.is_permanent,
        )
        for bridge in game_map.Brid
    )
    switch_state = tuple(
        (switch.symbol, switch.active)
        for switch in (*game_map.swQ, *game_map.swX, *game_map.swO)
    )
    return (
        block_state,
        game_map.is_split,
        tile_state,
        bridge_state,
        switch_state,
    )


def _step(control, action):
    next_control = deepcopy(control)
    next_control.Play_handle = True
    if action == "SW":
        if not next_control.switch_box():
            return None
    else:
        method_name = MOVE_METHODS.get(action)
        if method_name is None or not getattr(next_control, method_name)():
            return None
    return next_control


def dfs(state_or_path):
    """Return a DFS action sequence and the number of expanded states."""
    start = _make_control(state_or_path)
    start_key = _state_key(start)
    frontier = [(start_key, start)]
    parents = {start_key: None}
    visited = {start_key}
    expanded = 0

    while frontier:
        key, state = frontier.pop()
        if state.check_goal():
            actions = []
            while parents[key] is not None:
                key, action = parents[key]
                actions.append(action)
            actions.reverse()
            return actions, expanded

        expanded += 1
        actions = [move[0] for move in MOVES]
        if state.maps.is_split:
            actions.append("SW")

        for action in reversed(actions):
            next_state = _step(state, action)
            if next_state is None:
                continue
            next_key = _state_key(next_state)
            if next_key in visited:
                continue
            visited.add(next_key)
            parents[next_key] = (key, action)
            frontier.append((next_key, next_state))

    return None, expanded


def run_dfs(level_path):
    """Run DFS and return solution and performance metrics."""
    tracemalloc.start()
    try:
        start_time = time.perf_counter()
        actions, expanded = dfs(level_path)
        elapsed = time.perf_counter() - start_time
        peak_memory = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()

    path = None
    if actions is not None:
        control = _make_control(level_path)
        path = [deepcopy(control.current)]
        for action in actions:
            control = _step(control, action)
            if control is None:
                raise RuntimeError(f"DFS returned an invalid action: {action}")
            path.append(deepcopy(control.current))

    return {
        "solved": actions is not None,
        "time_s": elapsed,
        "peak_mem_kb": peak_memory / 1024,
        "expanded": expanded,
        "length": len(actions) if actions is not None else None,
        "cost": None,
        "actions": actions,
        "path": path,
    }


def solve(state_or_path):
    """Entry point used by the application solver runner."""
    return dfs(state_or_path)


dfs_path = solve


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
