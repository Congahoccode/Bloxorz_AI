#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Run"""
import pygame
import sys
import os
import time
import tracemalloc
import importlib
import inspect
from copy import deepcopy
from model.solver import handle, solution_to_moves, format_moves
from drawing.display import Display
from drawing.gui_menu import GuiMenu
from model.map import maps
from model.control import Control
from model.box import Box
import timeit


class Algorithm:
    BFS = 1
    DFS = 2
    UCS = 3
    ASTAR = 4


algorithm_names = {
    1: 'BFS',
    2: 'DFS',
    3: 'UCS',
    4: 'A*'
}

algorithm_by_str = {
    'bfs': Algorithm.BFS,
    'dfs': Algorithm.DFS,
    'ucs': Algorithm.UCS,
    'astar': Algorithm.ASTAR,
    'a_star': Algorithm.ASTAR,
    'a*': Algorithm.ASTAR
}

ALGO_CONFIGS = {
    Algorithm.BFS: {
        'name': 'BFS',
        'module_name': 'solver.bfs',
        'candidates': ['solve', 'bfs', 'bfs_path', 'bfs_search', 'search']
    },
    Algorithm.DFS: {
        'name': 'DFS',
        'module_name': 'solver.dfs',
        'candidates': ['solve', 'dfs', 'dfs_path', 'dfs_search', 'search']
    },
    Algorithm.UCS: {
        'name': 'UCS',
        'module_name': 'solver.ucs',
        'candidates': ['solve', 'ucs', 'ucs_path', 'uniform_cost_search', 'ucs_search', 'search']
    },
    Algorithm.ASTAR: {
        'name': 'A*',
        'module_name': 'solver.a_star',
        'candidates': ['solve', 'astar', 'a_star', 'astar_path', 'a_star_path', 'a_star_search', 'search']
    }
}


class Level:
    lv1 = "./level/1.json"
    lv2 = "./level/2.json"
    lv3 = "./level/3.json"
    lv4 = "./level/4.json"
    lv5 = "./level/5.json"
    lv6 = "./level/6.json"
    lv7 = "./level/7.json"
    lv8 = "./level/8.json"
    lv9 = "./level/9.json"
    lv10 = "./level/10.json"
    lv11 = "./level/11.json"
    lv12 = "./level/12.json"
    lv13 = "./level/13.json"
    lv14 = "./level/14.json"
    lv15 = "./level/15.json"
    lv16 = "./level/16.json"
    lv17 = "./level/17.json"
    lv18 = "./level/18.json"
    lv19 = "./level/19.json"
    lv20 = "./level/20.json"
    lv21 = "./level/21.json"


def deltatime(start_time):
    result = time.time() - start_time
    print("Time: ", result)


def flatMap(path):
    return [y for x in path for y in x]


def performance(solution, level, algorithm):
    if solution != None:
        print(f"Success with {algorithm_names[algorithm]}")
        print("Step: %d" % len(solution))
        return
    else:
        print("Unable to find path for maps!")
        print("Dir Level: %s" % level)
        return


def build_snapshots(level_path, solution, actions=None):
    """Precompute physical state snapshots for each step in solution to allow instant bidirectional replay."""
    m = maps(level_path)
    ctrl = Control(m)
    ctrl.Play_handle = True

    def snapshot():
        return {
            'current': deepcopy(ctrl.current),
            'maps': deepcopy(ctrl.maps.maps),
            'is_split': ctrl.maps.is_split,
            'split_boxes': deepcopy(ctrl.maps.split_boxes),
            'active_box_index': ctrl.maps.active_box_index
        }

    if actions is not None:
        snapshots = [snapshot()]
        move_map = {
            'U': ctrl.move_up,
            'D': ctrl.move_down,
            'R': ctrl.move_right,
            'L': ctrl.move_left,
        }
        for action in actions:
            if action == 'SW':
                moved = ctrl.switch_box()
            else:
                move = move_map.get(action)
                moved = move() if move else False
            if not moved:
                raise ValueError(f"Cannot replay invalid solver action: {action}")
            snapshots.append(snapshot())
        return snapshots

    snapshots = []
    for step in solution:
        ctrl.set_state(step, ctrl.curr_maps)
        ctrl.maps.refreshBox()
        ctrl.update_current_location()
        snapshots.append(snapshot())
    return snapshots


def apply_snapshot(ctrl, snap):
    """Restore Control state and maps from snapshot."""
    ctrl.current = deepcopy(snap['current'])
    ctrl.curr_maps = deepcopy(snap['maps'])
    ctrl.maps.maps = ctrl.curr_maps
    ctrl.maps.is_split = snap['is_split']
    ctrl.maps.split_boxes = deepcopy(snap['split_boxes'])
    ctrl.maps.active_box_index = snap['active_box_index']
    if snap['is_split'] and len(snap['split_boxes']) == 2:
        ctrl.maps.current_box = ctrl.maps.split_boxes[snap['active_box_index']]
    else:
        merged_box = Box("#", 2, deepcopy(ctrl.current))
        merged_box.on()
        ctrl.maps.current_box = merged_box


def draw_path_3D(solution, timesleep=0.60, level=Level.lv1, map_size=(0, 0), algo_name="Solver", metrics=None, algorithm_enum=None):
    """Interactive 3D Replay with interactive [<] and [>] buttons for Level and Algorithm,
    sidebar info panel, Play/Pause, Step forward/back, Reset, Speed adjustment, and Manual Play transition.
    """
    algo_list = [Algorithm.BFS, Algorithm.DFS, Algorithm.UCS, Algorithm.ASTAR]

    if algorithm_enum in algo_list:
        current_algo = algorithm_enum
    else:
        # Match from algo_name or metrics
        a_str = str((metrics or {}).get('algorithm') or algo_name).lower().replace(" ", "").replace("*", "star")
        if 'astar' in a_str or 'a_star' in a_str:
            current_algo = Algorithm.ASTAR
        elif 'dfs' in a_str:
            current_algo = Algorithm.DFS
        elif 'ucs' in a_str:
            current_algo = Algorithm.UCS
        else:
            current_algo = Algorithm.BFS
    current_algo_idx = algo_list.index(current_algo)

    available_levels = get_available_levels()
    if not available_levels:
        available_levels = [level]

    current_level = level
    cur_lvl_abs = os.path.abspath(level) if os.path.exists(level) else level
    current_level_idx = 0
    for idx, lp in enumerate(available_levels):
        if os.path.abspath(lp) == cur_lvl_abs or os.path.basename(lp) == os.path.basename(level):
            current_level_idx = idx
            current_level = lp
            break

    lvl_name = os.path.basename(current_level).replace(".json", "")
    algo_name = ALGO_CONFIGS[current_algo]['name']

    pygame.init()
    display = Display(title=f'Bloxorz 3D Replay', map_size=map_size)
    clock = pygame.time.Clock()

    ctrl = Control(maps(current_level))
    ctrl.Play_handle = True

    # Precompute snapshots or fallback
    if solution is not None and len(solution) > 0:
        moves = (metrics or {}).get('actions') or solution_to_moves(solution)
        try:
            snapshots = build_snapshots(current_level, solution, (metrics or {}).get('actions'))
            total_steps = len(snapshots)
        except Exception:
            snapshots = []
            total_steps = 1
        status = "READY"
    else:
        moves = []
        snapshots = []
        total_steps = 1
        status = "NO SOLUTION"

    if not snapshots:
        snapshots = [{
            'current': deepcopy(ctrl.current),
            'maps': deepcopy(ctrl.maps.maps),
            'is_split': ctrl.maps.is_split,
            'split_boxes': deepcopy(ctrl.maps.split_boxes),
            'active_box_index': ctrl.maps.active_box_index
        }]
        total_steps = 1

    # Speeds list (seconds per step) and labels
    speeds = [1.35, 0.85, 0.60, 0.35, 0.18, 0.09]
    speed_labels = ['0.4x', '0.7x', '1.0x', '1.7x', '3.3x', '6.5x']
    speed_idx = 2  # Default 0.60s per step
    is_dragging_speed = False

    current_step = 0
    is_playing = False
    last_advance_time = time.time()

    # Build metrics dict for sidebar
    sidebar_metrics = None
    if metrics:
        sidebar_metrics = {
            'time_sec': metrics.get('time_sec', 0),
            'peak_mem_kb': metrics.get('peak_mem_kb', 0),
            'visited': metrics.get('visited', 0),
        }

    def switch_level_and_algo(new_level, new_algo):
        nonlocal current_level, current_algo, current_algo_idx, current_level_idx
        nonlocal ctrl, solution, moves, snapshots, total_steps, current_step, is_playing, last_advance_time
        nonlocal lvl_name, algo_name, sidebar_metrics, status

        current_level = new_level
        current_algo = new_algo
        current_algo_idx = algo_list.index(current_algo)
        current_level_idx = available_levels.index(current_level) if current_level in available_levels else 0

        lvl_name = os.path.basename(current_level).replace(".json", "")
        algo_name = ALGO_CONFIGS[current_algo]['name']

        # Update board dimensions & camera target/distance
        m_new = maps(current_level)
        display.rows = m_new.size[0] if m_new.size[0] > 0 else 6
        display.cols = m_new.size[1] if m_new.size[1] > 0 else 10
        display.target = [display.cols / 2.0, -display.rows / 2.0, 0.5]
        display.initial_target = list(display.target)
        display.distance = max(display.cols, display.rows) * 1.5 + 4.0
        display.initial_distance = display.distance
        display.setup_camera()

        ctrl = Control(m_new)
        ctrl.Play_handle = True

        # Render "SOLVING..." frame so UI gives immediate responsive feedback
        pygame.display.set_caption(f"Bloxorz 3D - Solving {lvl_name} with {algo_name}...")
        ctrl.draw_maps()
        ctrl.draw_box()
        display.draw_sidebar({
            'level_name': lvl_name,
            'algo_name': algo_name,
            'current_step': 0,
            'total_steps': 1,
            'status': "SOLVING...",
            'moves_str': "Computing path...",
            'speed_label': speed_labels[speed_idx],
            'speed_idx': speed_idx,
            'speed_count': len(speeds),
            'metrics': None,
        })
        display.update()

        # Run solver
        sol, met = run_solver(current_level, current_algo)
        solution = sol
        sidebar_metrics = {
            'time_sec': met.get('time_sec', 0),
            'peak_mem_kb': met.get('peak_mem_kb', 0),
            'visited': met.get('visited', 0),
        }

        if solution and len(solution) > 0:
            moves = met.get('actions') or solution_to_moves(solution)
            try:
                snapshots = build_snapshots(current_level, solution, met.get('actions'))
                total_steps = len(snapshots)
            except Exception as e:
                print(f"Error building snapshots: {e}")
                snapshots = [{
                    'current': deepcopy(ctrl.current),
                    'maps': deepcopy(ctrl.maps.maps),
                    'is_split': ctrl.maps.is_split,
                    'split_boxes': deepcopy(ctrl.maps.split_boxes),
                    'active_box_index': ctrl.maps.active_box_index
                }]
                total_steps = 1
            current_step = 0
            is_playing = False
            status = "READY"
        else:
            moves = []
            snapshots = [{
                'current': deepcopy(ctrl.current),
                'maps': deepcopy(ctrl.maps.maps),
                'is_split': ctrl.maps.is_split,
                'split_boxes': deepcopy(ctrl.maps.split_boxes),
                'active_box_index': ctrl.maps.active_box_index
            }]
            total_steps = 1
            current_step = 0
            is_playing = False
            status = "NO SOLUTION"

    while True:
        # 1. Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_q]):
                pygame.quit()
                return

            # Mouse button clicks in sidebar
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Speed slider bar click
                if hasattr(display, 'speed_bar_rect') and display.speed_bar_rect.collidepoint(event.pos):
                    rel_x = event.pos[0] - display.speed_bar_rect.x
                    ratio = max(0.0, min(0.999, rel_x / max(1, display.speed_bar_rect.width)))
                    speed_idx = int(ratio * len(speeds))
                    is_dragging_speed = True
                    continue

                # Level < button
                elif hasattr(display, 'btn_prev_level_rect') and display.btn_prev_level_rect.collidepoint(event.pos):
                    new_l_idx = (current_level_idx - 1) % len(available_levels)
                    switch_level_and_algo(available_levels[new_l_idx], current_algo)
                    continue

                # Level > button
                elif hasattr(display, 'btn_next_level_rect') and display.btn_next_level_rect.collidepoint(event.pos):
                    new_l_idx = (current_level_idx + 1) % len(available_levels)
                    switch_level_and_algo(available_levels[new_l_idx], current_algo)
                    continue

                # Algorithm < button
                elif hasattr(display, 'btn_prev_algo_rect') and display.btn_prev_algo_rect.collidepoint(event.pos):
                    new_a_idx = (current_algo_idx - 1) % len(algo_list)
                    switch_level_and_algo(current_level, algo_list[new_a_idx])
                    continue

                # Algorithm > button
                elif hasattr(display, 'btn_next_algo_rect') and display.btn_next_algo_rect.collidepoint(event.pos):
                    new_a_idx = (current_algo_idx + 1) % len(algo_list)
                    switch_level_and_algo(current_level, algo_list[new_a_idx])
                    continue

                # Replay Start/Pause button
                elif hasattr(display, 'replay_btn_rect') and display.replay_btn_rect.collidepoint(event.pos):
                    if status not in ["NO SOLUTION", "SOLVING..."]:
                        if current_step == total_steps - 1:
                            current_step = 0
                            is_playing = True
                            last_advance_time = time.time()
                        else:
                            is_playing = not is_playing
                            if is_playing:
                                last_advance_time = time.time()
                    continue

            # Mouse button release
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                is_dragging_speed = False

            # Mouse drag on speed slider
            if event.type == pygame.MOUSEMOTION and is_dragging_speed:
                if hasattr(display, 'speed_bar_rect') and display.speed_bar_rect.width > 0:
                    rel_x = event.pos[0] - display.speed_bar_rect.x
                    ratio = max(0.0, min(0.999, rel_x / max(1, display.speed_bar_rect.width)))
                    speed_idx = int(ratio * len(speeds))
                    continue

            if display.handle_camera_event(event):
                continue

            if event.type == pygame.KEYDOWN:
                # Level navigation: [ / ] or , / . or PageUp / PageDown or < / >
                if event.key in [pygame.K_LEFTBRACKET, pygame.K_COMMA, pygame.K_PAGEUP, pygame.K_LESS]:
                    new_l_idx = (current_level_idx - 1) % len(available_levels)
                    switch_level_and_algo(available_levels[new_l_idx], current_algo)
                    continue
                elif event.key in [pygame.K_RIGHTBRACKET, pygame.K_PERIOD, pygame.K_PAGEDOWN, pygame.K_GREATER]:
                    new_l_idx = (current_level_idx + 1) % len(available_levels)
                    switch_level_and_algo(available_levels[new_l_idx], current_algo)
                    continue

                # Algorithm navigation: Tab or A
                elif event.key == pygame.K_TAB:
                    mods = pygame.key.get_mods()
                    direction = -1 if (mods & pygame.KMOD_SHIFT) else 1
                    new_a_idx = (current_algo_idx + direction) % len(algo_list)
                    switch_level_and_algo(current_level, algo_list[new_a_idx])
                    continue
                elif event.key == pygame.K_a:
                    new_a_idx = (current_algo_idx + 1) % len(algo_list)
                    switch_level_and_algo(current_level, algo_list[new_a_idx])
                    continue

                # Manual Play shortcut: P
                elif event.key == pygame.K_p:
                    m_p = maps(current_level)
                    p_state = Control(m_p)
                    p_state.Play_handle = True
                    handle(p_state, map_size=(m_p.size[0], m_p.size[1]))
                    return
                    continue

                # Playback controls
                elif event.key == pygame.K_SPACE:
                    if status not in ["NO SOLUTION", "SOLVING..."]:
                        if current_step == total_steps - 1:
                            current_step = 0
                            is_playing = True
                            last_advance_time = time.time()
                        else:
                            is_playing = not is_playing
                            if is_playing:
                                last_advance_time = time.time()
                elif event.key in [pygame.K_RIGHT, pygame.K_n]:
                    is_playing = False
                    if current_step < total_steps - 1:
                        current_step += 1
                elif event.key in [pygame.K_LEFT]:
                    is_playing = False
                    if current_step > 0:
                        current_step -= 1
                elif event.key == pygame.K_r:
                    current_step = 0
                    is_playing = False
                elif event.key in [pygame.K_UP, pygame.K_PLUS, pygame.K_EQUALS]:
                    if speed_idx < len(speeds) - 1:
                        speed_idx += 1
                elif event.key in [pygame.K_DOWN, pygame.K_MINUS]:
                    if speed_idx > 0:
                        speed_idx -= 1

        # 2. Auto playback logic
        current_delay = speeds[speed_idx]
        if is_playing:
            now = time.time()
            if now - last_advance_time >= current_delay:
                if current_step < total_steps - 1:
                    current_step += 1
                    last_advance_time = now
                else:
                    is_playing = False

        # 3. Apply snapshot for current step
        if current_step < len(snapshots):
            apply_snapshot(ctrl, snapshots[current_step])

        # 4. Status
        if status in ["NO SOLUTION", "SOLVING..."]:
            pass
        elif current_step == total_steps - 1 and total_steps > 1:
            status = "GOAL REACHED"
        elif is_playing:
            status = "PLAYING"
        elif current_step == 0:
            status = "READY"
        else:
            status = "PAUSED"

        # 5. Build moves display string (windowed around current step)
        formatted_moves_sub = []
        for i, m in enumerate(moves):
            if i == current_step - 1:
                formatted_moves_sub.append(f"[{m}]")
            else:
                formatted_moves_sub.append(m)
        moves_sub_str = " ".join(formatted_moves_sub)
        if len(moves_sub_str) > 80:
            start_idx = max(0, current_step - 6)
            end_idx = min(len(moves), current_step + 10)
            moves_sub_str = "..." + " ".join(formatted_moves_sub[start_idx:end_idx]) + "..."

        pygame.display.set_caption(f"Bloxorz 3D Replay - {lvl_name} ({algo_name})")

        # 6. Render 3D scene, sidebar, and update
        ctrl.draw_maps()
        ctrl.draw_box()
        display.draw_sidebar({
            'level_name': lvl_name,
            'algo_name': algo_name,
            'current_step': current_step,
            'total_steps': total_steps,
            'status': status,
            'moves_str': moves_sub_str if moves else ("No solution found" if status == "NO SOLUTION" else ""),
            'speed_label': speed_labels[speed_idx],
            'speed_idx': speed_idx,
            'speed_count': len(speeds),
            'metrics': sidebar_metrics,
        })
        display.update()

        clock.tick(60)


def draw_path_2D(solution, timesleep=0.60, level=Level.lv1, algo_name="Solver"):
    """Interactive 2D Console Replay."""
    if solution is None:
        print("Unable to find path for maps!")
        print("Dir Level: %s" % level)
        return

    moves = solution_to_moves(solution)
    print("\n" + "=" * 50)
    print(f"2D SOLUTION REPLAY - {algo_name}")
    print(f"Total Steps: {len(solution)} | Total Moves: {len(moves)}")
    print(f"Directions: {format_moves(moves)}")
    print("=" * 50)

    choiselv = maps(level)
    ctrl = Control(choiselv)
    ctrl.Play_handle = True

    for i, path in enumerate(solution):
        os.system("clear")
        move_str = moves[i - 1] if i > 0 and i - 1 < len(moves) else "START"
        print(f"--- Step {i}/{len(solution) - 1} (Move: {move_str}) ---")
        ctrl.current = path
        ctrl.update_box_locaton_for_maps(path)
        ctrl.maps.refreshBox()
        ctrl.update_current_location()
        ctrl.print_maps()
        time.sleep(timesleep)

    if ctrl.check_goal():
        print("\n🎉 WINNER! Reached the goal!")
    input("\nPress Enter to continue...")


def run_solver(level_path, algorithm_enum):
    """Run search algorithm from solver package with time and memory tracking."""
    cfg = ALGO_CONFIGS.get(algorithm_enum, ALGO_CONFIGS[Algorithm.BFS])
    name = cfg['name']
    mod_name = cfg['module_name']
    candidates = cfg['candidates']

    m = maps(level_path)
    state = Control(m)

    # Dynamically load / reload solver module so user edits take effect immediately
    try:
        mod = importlib.import_module(mod_name)
        mod = importlib.reload(mod)
    except Exception as e:
        print(f"⚠️  Could not import '{mod_name}': {e}")
        mod = None

    func = None
    if mod is not None:
        for c in candidates:
            cand = getattr(mod, c, None)
            if cand and callable(cand):
                func = cand
                break
        if func is None:
            # Look for any callable defined directly in the module
            for _, attr_val in inspect.getmembers(mod, inspect.isfunction):
                if getattr(attr_val, '__module__', None) == mod.__name__:
                    func = attr_val
                    break

    tracemalloc.start()
    t_start = time.perf_counter()

    sol = None
    visited_count = 0
    solver_actions = None

    if func is not None:
        try:
            sig = inspect.signature(func)
            param_names = [
                p.name.lower() for p in sig.parameters.values()
                if p.default == inspect.Parameter.empty and p.kind in (
                    inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD
                )
            ]
            if len(param_names) == 1 and ('path' in param_names[0] or 'file' in param_names[0]):
                res = func(level_path)
            elif len(param_names) == 1 and 'map' in param_names[0]:
                res = func(m)
            else:
                res = func(state)
        except TypeError:
            try:
                res = func(state)
            except Exception as e:
                print(f"⚠️  Error calling {func.__name__} in {mod_name}: {e}")
                res = None
        except Exception as e:
            print(f"⚠️  Error executing {func.__name__} in {mod_name}: {e}")
            res = None

        if res is not None:
            if isinstance(res, tuple):
                if len(res) >= 2:
                    sol, visited_count = res[0], res[1]
                elif len(res) == 1:
                    sol = res[0]
                    visited_count = len(sol) if isinstance(sol, (list, tuple)) else 0
                if hasattr(res, 'actions') and res.actions:
                    if isinstance(res.actions, str):
                        import re
                        solver_actions = res.actions.split() if ' ' in res.actions else (re.findall(r'SW|[UDLR]', res.actions) if 'SW' in res.actions else list(res.actions))
                    else:
                        solver_actions = list(res.actions)
            elif isinstance(res, dict):
                sol = res.get('path') or res.get('solution') or res.get('moves')
                visited_count = res.get('visited') or res.get('visited_count') or res.get('expanded') or 0
                if res.get('actions'):
                    acts = res.get('actions')
                    if isinstance(acts, str):
                        import re
                        solver_actions = acts.split() if ' ' in acts else (re.findall(r'SW|[UDLR]', acts) if 'SW' in acts else list(acts))
                    else:
                        solver_actions = list(acts) if isinstance(acts, (list, tuple)) else None
            elif isinstance(res, list):
                sol = res
                visited_count = len(res)
            else:
                sol = res
                visited_count = 0
    else:
        if mod is not None:
            print(f"⚠️  No solver function defined yet in '{mod_name}.py'. (e.g. define 'def solve(state):')")

    t_elapsed = time.perf_counter() - t_start
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # If the solver returned move strings, convert them to a replayable state sequence.
    move_tokens = {'U', 'D', 'L', 'R', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'SW', 'SPACE'}
    if isinstance(sol, list) and all(
        isinstance(move, str) and move.upper() in move_tokens
        for move in sol
    ):
        solver_actions = [move.upper() for move in sol]
        move_map = {
            'U': 'move_up', 'UP': 'move_up',
            'D': 'move_down', 'DOWN': 'move_down',
            'L': 'move_left', 'LEFT': 'move_left',
            'R': 'move_right', 'RIGHT': 'move_right',
            'SW': 'switch', 'SPACE': 'switch'
        }
        m_temp = maps(level_path)
        c_temp = Control(m_temp)
        c_temp.Play_handle = True
        states = [deepcopy(c_temp.current)]
        for m_str in sol:
            action = move_map.get(m_str.upper())
            if action == 'switch':
                c_temp.switch_box()
            elif action:
                getattr(c_temp, action)()
            states.append(deepcopy(c_temp.current))
        moves = solver_actions
        sol = states
    else:
        moves = solver_actions if solver_actions else (solution_to_moves(sol) if sol else [])

    metrics = {
        'algorithm': name,
        'level': level_path,
        'solved': sol is not None,
        'steps': len(sol) if sol else 0,
        'moves_count': len(moves),
        'moves_str': format_moves(moves) if moves else "—",
        'actions': solver_actions,
        'visited': visited_count,
        'time_sec': t_elapsed,
        'peak_mem_kb': peak_mem / 1024.0
    }
    return sol, metrics


def print_metrics(m):
    print("\n" + "-" * 60)
    print(f"📊 SOLVER RESULTS:")
    print(f"   Algorithm      : {m['algorithm']}")
    print(f"   Level          : {m['level']}")
    print(f"   Status         : {'SUCCESS ✅' if m['solved'] else 'FAILED ❌'}")
    print(f"   Search Time    : {m['time_sec']:.5f} s")
    print(f"   Peak Memory    : {m['peak_mem_kb']:.2f} KB")
    print(f"   States Visited : {m['visited']}")
    print(f"   Solution Length: {m['moves_count']} moves ({m['steps']} states)")
    print(f"   Move Sequence  : {m['moves_str']}")
    print("-" * 60 + "\n")


def benchmark_all_algorithms(level_path):
    print("\n" + "=" * 80)
    print(f"🏁 BENCHMARK ALL ALGORITHMS ON: {level_path}")
    print("=" * 80)
    print(f"{'Algorithm':<15} | {'Status':<8} | {'Moves':<6} | {'Visited':<8} | {'Time (s)':<10} | {'Memory (KB)':<12}")
    print("-" * 80)

    for algo_enum in [Algorithm.BFS, Algorithm.DFS, Algorithm.UCS, Algorithm.ASTAR]:
        sol, m = run_solver(level_path, algo_enum)
        status_str = "OK" if m['solved'] else "FAIL"
        moves_str = str(m['moves_count']) if m['solved'] else "-"
        print(f"{m['algorithm']:<15} | {status_str:<8} | {moves_str:<6} | {m['visited']:<8} | {m['time_sec']:<10.5f} | {m['peak_mem_kb']:<12.2f}")
    print("=" * 80 + "\n")
    input("Press Enter to continue...")


def get_available_levels():
    import re
    def natural_sort_key(s):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]
    lvl_files = []
    lvl_dir = "./level"
    if os.path.exists(lvl_dir):
        for f in sorted(os.listdir(lvl_dir), key=natural_sort_key):
            if f.endswith(".json"):
                lvl_files.append(os.path.join(lvl_dir, f))
    return lvl_files


def interactive_menu():
    while True:
        os.system("clear")
        print("=" * 65)
        print("                 === BLOXORZ GAME & SOLVER ===")
        print("=" * 65)
        print(" 1. Manual Play (Arrow keys & Space)")
        print(" 2. Solve Level & Watch 3D Replay (BFS, A*, DFS, etc.)")
        print(" 3. Benchmark All Algorithms")
        print(" 4. Exit")
        print("=" * 65)

        choice = input("Select option (1-4): ").strip()
        if choice == '4' or choice.lower() in ['q', 'exit']:
            print("Goodbye!")
            sys.exit(0)

        levels = get_available_levels()
        if not levels:
            print("No level files found in ./level directory!")
            input("Press Enter to retry...")
            continue

        print("\nAvailable levels:")
        for idx, lp in enumerate(levels, 1):
            bname = os.path.basename(lp)
            print(f"  {idx:2d}. {bname}")
        print("   0. Enter custom level JSON path")

        lvl_choice = input(f"Select level (1-{len(levels)}): ").strip()
        if lvl_choice == '0':
            selected_level = input("Enter JSON file path: ").strip()
        else:
            try:
                idx = int(lvl_choice) - 1
                if 0 <= idx < len(levels):
                    selected_level = levels[idx]
                else:
                    selected_level = levels[0]
            except ValueError:
                selected_level = levels[0]

        if not os.path.exists(selected_level):
            print(f"File not found: {selected_level}")
            time.sleep(1.5)
            continue

        if choice == '1':
            # Human Play mode
            m = maps(selected_level)
            state = Control(m)
            state.Play_handle = True
            handle(state, map_size=(m.size[0], m.size[1]))

        elif choice == '2':
            # Solve and replay in 3D
            print("\nSelect search algorithm:")
            print("  1. BFS (Breadth-First Search)")
            print("  2. DFS (Depth-First Search)")
            print("  3. UCS (Uniform Cost Search)")
            print("  4. A* Search")
            algo_choice = input("Choose algorithm (1-4, default 1): ").strip()
            algo_map = {'1': Algorithm.BFS, '2': Algorithm.DFS, '3': Algorithm.UCS, '4': Algorithm.ASTAR}
            chosen_algo = algo_map.get(algo_choice, Algorithm.BFS)

            print("\nSolving level, please wait...")
            sol, metrics = run_solver(selected_level, chosen_algo)
            print_metrics(metrics)

            m = maps(selected_level)
            draw_path_3D(
                sol,
                timesleep=0.60,
                level=selected_level,
                map_size=(m.size[0], m.size[1]),
                algo_name=metrics['algorithm'],
                metrics=metrics,
                algorithm_enum=chosen_algo
            )

        elif choice == '3':
            benchmark_all_algorithms(selected_level)


def main(level=Level.lv1, Play_handle=False, algorithm=Algorithm.BFS, view='3'):
    Maps = maps(level)
    size = Maps.size
    state = Control(Maps)

    if Play_handle:
        state.Play_handle = True
        handle(state, map_size=(size[0], size[1]))
    else:
        sol, metrics = run_solver(level, algorithm)
        print_metrics(metrics)
        draw_path_3D(sol, level=level, map_size=(size[0], size[1]), algo_name=metrics['algorithm'], metrics=metrics, algorithm_enum=algorithm)


def run_gui_launcher():
    """Graphical User Interface Menu Launcher."""
    menu = GuiMenu()
    while True:
        action = menu.run()
        if not action or action.get('action') == 'exit':
            pygame.quit()
            sys.exit(0)

        level_path = action.get('level', Level.lv1)
        mode = action.get('mode', 'solve')

        if mode == 'play':
            m = maps(level_path)
            state = Control(m)
            state.Play_handle = True
            handle(state, map_size=(m.size[0], m.size[1]))

        elif mode == 'solve':
            algo_key = action.get('algo', 'bfs')
            algo_enum = algorithm_by_str.get(algo_key, Algorithm.BFS)

            sol, metrics = run_solver(level_path, algo_enum)
            print_metrics(metrics)
            m = maps(level_path)
            draw_path_3D(
                sol,
                timesleep=0.60,
                level=level_path,
                map_size=(m.size[0], m.size[1]),
                algo_name=metrics['algorithm'],
                metrics=metrics,
                algorithm_enum=algo_enum
            )

        elif mode == 'benchmark':
            results = []
            for a_enum in [Algorithm.BFS, Algorithm.DFS, Algorithm.UCS, Algorithm.ASTAR]:
                _, m_data = run_solver(level_path, a_enum)
                results.append(m_data)
            menu.show_benchmark_window(results, level_path)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--cli', '-c', 'cli']:
            interactive_menu()
        else:
            level_arg = sys.argv[1]
            if len(sys.argv) > 2:
                opt = sys.argv[2].lower()
                view_arg = sys.argv[3] if len(sys.argv) > 3 else '3'
                if opt == 'handle':
                    main(level=level_arg, Play_handle=True)
                elif opt in algorithm_by_str:
                    main(level=level_arg, Play_handle=False, algorithm=algorithm_by_str[opt], view=view_arg)
                else:
                    print(f"Unknown option '{opt}'. Usage: python3 run.py <level.json> <bfs|dfs|ucs|astar|handle> [view]")
            else:
                main(level=level_arg, Play_handle=False, algorithm=Algorithm.BFS, view='3')
    else:
        # Launch graphical GUI menu by default!
        run_gui_launcher()
