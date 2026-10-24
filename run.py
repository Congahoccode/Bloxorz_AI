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
    lv16 = "./level/16_split_coop.json"
    lv17 = "./level/17_fragile_bridges.json"


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
        ctrl.current = deepcopy(step)
        ctrl.update_box_locaton_for_maps(deepcopy(step))
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
        ctrl.maps.current_box.location = deepcopy(ctrl.current)
        ctrl.maps.current_box.pre_location = deepcopy(ctrl.current)


def draw_path_3D(solution, timesleep=0.60, level=Level.lv1, map_size=(0, 0), algo_name="Solver", metrics=None):
    """Interactive 3D Replay with sidebar info panel, Play/Pause, Step forward/back, Reset, Speed adjustment."""
    if solution is None or len(solution) == 0:
        print("No solution to display!")
        return

    moves = (metrics or {}).get('actions') or solution_to_moves(solution)
    snapshots = build_snapshots(level, solution, (metrics or {}).get('actions'))
    total_steps = len(snapshots)

    pygame.init()
    display = Display(title=f'Bloxorz 3D Replay', map_size=map_size)
    clock = pygame.time.Clock()

    ctrl = Control(maps(level))
    ctrl.Play_handle = True

    # Speeds list (seconds per step) and labels - calibrated 1.7x slower
    speeds = [1.35, 0.85, 0.60, 0.35, 0.18, 0.09]
    speed_labels = ['0.4x', '0.7x', '1.0x', '1.7x', '3.3x', '6.5x']
    speed_idx = 2  # Default is 0.60s per step

    current_step = 0
    is_playing = False  # Start paused in READY state so user can setup camera and speed before starting
    last_advance_time = time.time()

    lvl_name = os.path.basename(level).replace(".json", "")

    # Build metrics dict for sidebar
    sidebar_metrics = None
    if metrics:
        sidebar_metrics = {
            'time_sec': metrics.get('time_sec', 0),
            'peak_mem_kb': metrics.get('peak_mem_kb', 0),
            'visited': metrics.get('visited', 0),
        }

    while True:
        # 1. Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_q]):
                pygame.quit()
                return

            # Click on Replay Start/Pause button in sidebar
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hasattr(display, 'replay_btn_rect') and display.replay_btn_rect.collidepoint(event.pos):
                    if current_step == total_steps - 1:
                        current_step = 0
                        is_playing = True
                        last_advance_time = time.time()
                    else:
                        is_playing = not is_playing
                        if is_playing:
                            last_advance_time = time.time()
                    continue

            if display.handle_camera_event(event):
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
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
                elif event.key in [pygame.K_LEFT, pygame.K_p]:
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
        apply_snapshot(ctrl, snapshots[current_step])

        # 4. Status
        if current_step == total_steps - 1:
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
            'moves_str': moves_sub_str,
            'speed_label': speed_labels[speed_idx],
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
            elif isinstance(res, dict):
                sol = res.get('path') or res.get('solution') or res.get('moves')
                visited_count = res.get('visited') or res.get('visited_count') or res.get('expanded') or 0
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
        moves = solution_to_moves(sol) if sol else []

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
    lvl_files = []
    lvl_dir = "./level"
    if os.path.exists(lvl_dir):
        for f in sorted(os.listdir(lvl_dir)):
            if f.endswith(".json"):
                lvl_files.append(os.path.join(lvl_dir, f))
    return lvl_files


def interactive_menu():
    while True:
        os.system("clear")
        print("=" * 65)
        print("                 🎮 BLOXORZ GAME & SOLVER 🎮")
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

            if metrics['solved']:
                m = maps(selected_level)
                draw_path_3D(
                    sol,
                    timesleep=0.60,
                    level=selected_level,
                    map_size=(m.size[0], m.size[1]),
                    algo_name=metrics['algorithm'],
                    metrics=metrics
                )
            else:
                input("No solution found! Press Enter to return to menu...")

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
        if metrics['solved']:
            draw_path_3D(sol, level=level, map_size=(size[0], size[1]), algo_name=metrics['algorithm'], metrics=metrics)


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
            if metrics['solved']:
                m = maps(level_path)
                draw_path_3D(
                    sol,
                    timesleep=0.60,
                    level=level_path,
                    map_size=(m.size[0], m.size[1]),
                    algo_name=metrics['algorithm'],
                    metrics=metrics
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
