#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import time
from model.control import Control
from model.map import maps
from drawing.display import Display
from drawing.box import Box
from model.box import Box as cube
import pygame
from copy import deepcopy
from heapq import heappop, heappush, heapify

def solution_to_moves(solution):
    """Convert a sequence of states (solution path) into a list of direction letters (U, D, L, R, SW)."""
    if not solution or len(solution) < 2:
        return []
    moves = []
    dir_names = {'move_up': 'U', 'move_down': 'D', 'move_left': 'L', 'move_right': 'R'}
    for i in range(len(solution) - 1):
        s_cur = solution[i]
        s_next = solution[i + 1]

        found = None
        # Split block state
        if isinstance(s_cur, tuple) and len(s_cur) == 3:
            loc1, loc2, active_idx = s_cur
            if isinstance(s_next, tuple) and len(s_next) == 3:
                next_loc1, next_loc2, next_active_idx = s_next
                if next_active_idx != active_idx and loc1 == next_loc1 and loc2 == next_loc2:
                    moves.append('SW')
                    continue
            cur_active_loc = loc1 if active_idx == 0 else loc2
            for move_fn, name in dir_names.items():
                b = cube('#', 1, deepcopy(cur_active_loc))
                getattr(b, move_fn)()
                if isinstance(s_next, tuple):
                    target = s_next[0] if active_idx == 0 else s_next[1]
                    if sorted(b.location) == sorted(target):
                        found = name
                        break
                elif isinstance(s_next, list):  # Merged
                    other_loc = loc2 if active_idx == 0 else loc1
                    merged = b.location + other_loc
                    if sorted(merged) == sorted(s_next):
                        found = name
                        break
        else:
            # Standard double box
            for move_fn, name in dir_names.items():
                b = cube('#', 2, deepcopy(s_cur))
                getattr(b, move_fn)()
                if isinstance(s_next, list):
                    if sorted(b.location) == sorted(s_next):
                        found = name
                        break
                elif isinstance(s_next, tuple):  # Triggered split switch
                    found = name
                    break

        # Fallback coordinate geometry deduction if cube simulation failed
        if found is None and isinstance(s_cur, list) and isinstance(s_next, list):
            cur_sorted = sorted(s_cur)
            next_sorted = sorted(s_next)
            # Case 1: standing -> lying
            if len(cur_sorted) == 1 and len(next_sorted) == 2:
                r, c = cur_sorted[0]
                if next_sorted == [[r, c + 1], [r, c + 2]]: found = 'R'
                elif next_sorted == [[r, c - 2], [r, c - 1]]: found = 'L'
                elif next_sorted == [[r + 1, c], [r + 2, c]]: found = 'D'
                elif next_sorted == [[r - 2, c], [r - 1, c]]: found = 'U'
            # Case 2: lying -> standing
            elif len(cur_sorted) == 2 and len(next_sorted) == 1:
                nr, nc = next_sorted[0]
                if cur_sorted[0][0] == cur_sorted[1][0]:
                    r = cur_sorted[0][0]
                    c1, c2 = min(cur_sorted[0][1], cur_sorted[1][1]), max(cur_sorted[0][1], cur_sorted[1][1])
                    if [nr, nc] == [r, c2 + 1]: found = 'R'
                    elif [nr, nc] == [r, c1 - 1]: found = 'L'
                elif cur_sorted[0][1] == cur_sorted[1][1]:
                    c = cur_sorted[0][1]
                    r1, r2 = min(cur_sorted[0][0], cur_sorted[1][0]), max(cur_sorted[0][0], cur_sorted[1][0])
                    if [nr, nc] == [r2 + 1, c]: found = 'D'
                    elif [nr, nc] == [r1 - 1, c]: found = 'U'
            # Case 3: lying -> lying (slide)
            elif len(cur_sorted) == 2 and len(next_sorted) == 2:
                dr0 = next_sorted[0][0] - cur_sorted[0][0]
                dc0 = next_sorted[0][1] - cur_sorted[0][1]
                dr1 = next_sorted[1][0] - cur_sorted[1][0]
                dc1 = next_sorted[1][1] - cur_sorted[1][1]
                if dr0 == dr1 and dc0 == dc1:
                    if (dr0, dc0) == (-1, 0): found = 'U'
                    elif (dr0, dc0) == (1, 0): found = 'D'
                    elif (dr0, dc0) == (0, -1): found = 'L'
                    elif (dr0, dc0) == (0, 1): found = 'R'

        moves.append(found if found else '?')
    return moves


def format_moves(moves):
    """Format list of moves into a space-separated readable string."""
    return " ".join(moves) if moves else "(empty)"


def print_stack(stack, algorithm):
    if algorithm=="dfs":
        print("STACK: ")
        for state in stack[::-1]:
            print("( %s ) " % state[0])
    elif algorithm=="bfs":
        print("QUEUE: ")
        for state in stack:
            print("( %s ) " % state[0])


def dfs_recursion(state: Control):
    if state.check_goal():
        return
    current_state, current_maps = state.stack.pop()
    state.visted.append((current_state, current_maps))
    for move in state.moves:
        state.set_state(current_state, current_maps)
        if move():
            dfs_recursion(state)


def dfs_step_by_step(state: Control, timesleep=0.1):
    pygame.init()
    display = Display(title='Bloxorz Game', map_size=(state.size[0], state.size[1]))

    while state.stack:
        for event in pygame.event.get():
            if display.quit(event):
                pygame.quit()
                return None
        current_state, current_maps = state.stack.pop()
        
        print("POP: ( %s )" % current_state)
        
        state.visted.append((current_state, current_maps))

        for move in state.moves:
            state.set_state(current_state, current_maps)

            print_stack(state.stack, "dfs")
            state.maps.print_current()
            state.draw_box()
            state.draw_maps()
            display.update()
            time.sleep(timesleep)
            os.system("clear")

            if move():
                print_stack(state.stack, "dfs")
                state.maps.print_current()
                time.sleep(timesleep)
                os.system("clear")
                if state.check_goal():
                    print("WINNER!")
                    state.maps.print_current()
                    state.draw_box()
                    state.draw_maps()
                    display.update()
                    time.sleep(timesleep)
                    return state
        os.system("clear")
        

def bfs_step_by_step(state: Control, timesleep=0.2):
    pygame.init()
    display = Display(title='Bloxorz Game', map_size=(state.size[0], state.size[1]))

    while state.stack:
        for event in pygame.event.get():
            if display.quit(event):
                pygame.quit()
                return None
        current_state, current_maps = state.stack.pop(0)

        print("POP: ( %s )" % current_state)

        state.visted.append((current_state, current_maps))

        for move in state.moves:
            state.set_state(current_state, current_maps)

            print_stack(state.stack, "bfs")
            state.maps.print_current()
            state.draw_box()
            state.draw_maps()
            display.update()
            time.sleep(timesleep)
            os.system("clear")

            if move():
                print_stack(state.stack, "bfs")
                state.maps.print_current()
                time.sleep(timesleep)
                os.system("clear")
                if state.check_goal():
                    print("WINNER!")
                    state.maps.print_current()
                    state.draw_box()
                    state.draw_maps()
                    display.update()
                    time.sleep(timesleep)
                    return state
                    
            os.system("clear")

def dfs_path(state: Control):
    stack = [[state.start], ]
    while state.stack:
        current_state, current_maps = state.stack.pop()
        path = stack.pop()
        state.visted.append((current_state, current_maps))
        for move in state.moves:
            state.set_state(current_state, current_maps)
            if move():
                if state.check_goal():
                    result = path + [state.current]
                    return (result, len(state.visted))
                stack.append(path + [state.current])
                
    return (None, len(state.visted))

def bfs_path(state: Control):
    stack = [[state.start], ]
    while state.stack:
        current_state, current_maps = state.stack.pop(0)
        path = stack.pop(0)
        state.visted.append((current_state, current_maps))
        for move in state.moves:
            state.set_state(current_state, current_maps)
            if move():
                if state.check_goal():
                    result = path + [state.current]
                    return (result, len(state.visted))
                stack.append(path + [state.current])
                
    return (None, len(state.visted))

    
def hill_climbing(state: Control,verbose=None):
    state.eval_func()
    if verbose:
        print("Eval_Maps")
        print(state.eval_maps)
    count = 0
    path = [] 
    all_accept_state = []
    best_state = []

    while True:
        current_state = state.get_state()
        current_maps = state.get_maps()
        current_eval = state.evaluate()

        path.append(current_state)
        accept_state = []

        state.visted.append((current_state, current_maps))

        for move in state.moves:
            if move():
                delta = state.evaluate()
                if delta <= current_eval:
                    count +=1
                    better_state = state.get_state()
                    get_maps = state.get_maps()
                    accept_state.append((delta, better_state, get_maps))
                
            state.set_state(current_state, current_maps)
                  
        if accept_state != []:
            next_eval, next_state, next_maps = min(accept_state)
            best_state.append(next_state)
            all_accept_state.extend(sorted(accept_state))

            if next_state == state.end:
                path.append(next_state)
                return (path, count)

            state.set_state(next_state, next_maps)
        else: 
            try:
                
                if verbose:
                    print("Try again!", count)
                    print(path)
                while True:
                    count +=1
                    next_eval, next_state, next_maps = all_accept_state.pop()
                    if next_state in best_state:
                        path.pop()
                        continue
                    else:
                        path.pop()
                        state.set_state(next_state, next_maps)
                    break
            except:
                return (None, count)

def heuristic(state, goal,heur='none'):
    if heur == 'none':
        return 0
    if heur == 'l1':
        return sum([abs(x-y) for x,y in zip(state,goal)])
             
def cost_maps(maps):
    cost = 0
    inc = 10
    for child in maps.swQ: 
        if child.active:     
            cost+=inc
    for child in maps.swO:   
        if child.active:     
            cost+=inc
    for child in maps.swX:   
        if child.active:     
            cost+=inc
    return 0
         

def astar_base(state: Control, heur: str = 'none'):
    stack = [[0, [state.start]], ]
    heap = [[0, state.start], ]
    costs = {tuple(tuple(x) for x in state.start) : (0, None)}
    step = 0
    while heap:
        step+=1
        _, current_state = heappop(heap)
        for _, current_maps in state.stack:
            if _ ==current_state:
                break
        current_cost, _ = costs[tuple(tuple(x) for x in current_state)]
        state.visted.append((current_state, current_maps))
        for move in state.moves:
            state.set_state(current_state, current_maps)
            if move():
                if state.check_goal():
                    costs[tuple(tuple(x) for x in state.current)] = (current_cost + 1, current_state)
                    path = []
                    cur = state.current
                    while cur:
                        path.append(cur)
                        cur = costs[tuple(tuple(x) for x in cur)][1]
                    path.reverse()
                    return (path, step)
                if tuple(tuple(x) for x in state.current) not in costs:
                    costs[tuple(tuple(x) for x in state.current)] = (current_cost + 1, current_state)
                    heappush(heap, [current_cost + 1 + heuristic(state.current[0],state.end[0], heur)- cost_maps(state.maps), state.current])
                elif current_cost + 1 - cost_maps(state.maps) < costs[tuple(tuple(x) for x in state.current)][0]:
                    costs[tuple(tuple(x) for x in state.current)] = (current_cost + 1 - cost_maps(state.maps),current_state)
    return None, step


def dijkstra(state: Control):
    return astar_base(state, 'none')


def astar(state: Control):
    return astar_base(state, 'l1')


def _get_avail_levels():
    import re
    lvl_dir = "./level"
    if not os.path.exists(lvl_dir):
        return []
    def n_key(s):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]
    return [os.path.join(lvl_dir, f) for f in sorted(os.listdir(lvl_dir), key=n_key) if f.endswith(".json")]


def handle(state: Control, map_size=(0, 0)):
    state.Play_handle = True
    pygame.init()
    display = Display(title='Bloxorz Game - Play Mode', map_size=map_size)
    result = True
    clock = pygame.time.Clock()

    # Save initial state for restart & level switching
    initial_maps_obj = state.maps
    level_path = initial_maps_obj.path if hasattr(initial_maps_obj, 'path') else None

    available_levels = _get_avail_levels()
    if not available_levels and level_path:
        available_levels = [level_path]

    current_level_idx = 0
    if level_path:
        cur_abs = os.path.abspath(level_path) if os.path.exists(level_path) else level_path
        for idx, lp in enumerate(available_levels):
            if os.path.abspath(lp) == cur_abs or os.path.basename(lp) == os.path.basename(level_path):
                current_level_idx = idx
                level_path = lp
                break

    algo_names_list = ['A*', 'BFS', 'DFS', 'UCS']
    current_algo_idx = 0

    move_count = 0
    move_history = []  # list of direction chars
    status = "PLAYING"

    lvl_name = os.path.basename(level_path).replace(".json", "") if level_path else "?"

    def build_sidebar_info():
        moves_display = " ".join(move_history[-30:]) if move_history else "(no moves yet)"
        if len(move_history) > 30:
            moves_display = "... " + moves_display
        return {
            'mode': 'play',
            'level_name': lvl_name,
            'algo_name': algo_names_list[current_algo_idx],
            'current_step': move_count,
            'total_steps': move_count + 1,
            'status': status,
            'moves_str': moves_display,
            'speed_label': '',
            'metrics': None,
            'move_count': move_count,
            'split_active': state.maps.is_split,
        }

    def load_level(new_path):
        nonlocal state, level_path, lvl_name, result, move_count, move_history, status
        level_path = new_path
        lvl_name = os.path.basename(level_path).replace(".json", "")
        new_maps = maps(level_path)
        state.__init__(new_maps)
        state.Play_handle = True
        result = True
        move_count = 0
        move_history = []
        status = "PLAYING"

        display.rows = new_maps.size[0] if new_maps.size[0] > 0 else 6
        display.cols = new_maps.size[1] if new_maps.size[1] > 0 else 10
        display.target = [display.cols / 2.0, -display.rows / 2.0, 0.5]
        display.initial_target = list(display.target)
        display.distance = max(display.cols, display.rows) * 1.5 + 4.0
        display.initial_distance = display.distance
        display.setup_camera()

    def do_restart():
        if level_path and os.path.exists(level_path):
            load_level(level_path)

    def launch_solver_replay(lvl, algo_str):
        try:
            from main import run_solver, draw_path_3D, algorithm_by_str
            algo_enum = algorithm_by_str.get(algo_str.lower(), 4)
            sol, metrics = run_solver(lvl, algo_enum)
            m = maps(lvl)
            draw_path_3D(
                sol,
                level=lvl,
                map_size=(m.size[0], m.size[1]),
                algo_name=algo_str,
                metrics=metrics,
                algorithm_enum=algo_enum
            )
            return
        except Exception as e:
            print(f"Error launching solver replay: {e}")

    # Initial render
    state.draw_maps()
    state.draw_box()
    display.draw_sidebar(build_sidebar_info())
    display.update()

    while True:
        moved = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key in [pygame.K_ESCAPE, pygame.K_q]):
                pygame.quit()
                return

            # Mouse button clicks in sidebar
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Level < button
                if hasattr(display, 'btn_prev_level_rect') and display.btn_prev_level_rect.collidepoint(event.pos):
                    if available_levels:
                        current_level_idx = (current_level_idx - 1) % len(available_levels)
                        load_level(available_levels[current_level_idx])
                        moved = True
                        continue
                # Level > button
                elif hasattr(display, 'btn_next_level_rect') and display.btn_next_level_rect.collidepoint(event.pos):
                    if available_levels:
                        current_level_idx = (current_level_idx + 1) % len(available_levels)
                        load_level(available_levels[current_level_idx])
                        moved = True
                        continue
                # Algorithm < button
                elif hasattr(display, 'btn_prev_algo_rect') and display.btn_prev_algo_rect.collidepoint(event.pos):
                    current_algo_idx = (current_algo_idx - 1) % len(algo_names_list)
                    launch_solver_replay(available_levels[current_level_idx], algo_names_list[current_algo_idx])
                    return
                    moved = True
                    continue
                # Algorithm > button
                elif hasattr(display, 'btn_next_algo_rect') and display.btn_next_algo_rect.collidepoint(event.pos):
                    current_algo_idx = (current_algo_idx + 1) % len(algo_names_list)
                    launch_solver_replay(available_levels[current_level_idx], algo_names_list[current_algo_idx])
                    return
                    moved = True
                    continue

            if display.handle_camera_event(event):
                continue

            if event.type == pygame.KEYDOWN:
                # Restart
                if event.key == pygame.K_r:
                    do_restart()
                    moved = True
                    continue

                # Level navigation shortcuts: [ / ] or , / . or PageUp / PageDown or < / >
                if event.key in [pygame.K_LEFTBRACKET, pygame.K_COMMA, pygame.K_PAGEUP, pygame.K_LESS]:
                    if available_levels:
                        current_level_idx = (current_level_idx - 1) % len(available_levels)
                        load_level(available_levels[current_level_idx])
                        moved = True
                        continue
                elif event.key in [pygame.K_RIGHTBRACKET, pygame.K_PERIOD, pygame.K_PAGEDOWN, pygame.K_GREATER]:
                    if available_levels:
                        current_level_idx = (current_level_idx + 1) % len(available_levels)
                        load_level(available_levels[current_level_idx])
                        moved = True
                        continue

                # Algorithm / AI solve shortcuts: Tab or A
                elif event.key == pygame.K_TAB:
                    mods = pygame.key.get_mods()
                    direction = -1 if (mods & pygame.KMOD_SHIFT) else 1
                    current_algo_idx = (current_algo_idx + direction) % len(algo_names_list)
                    launch_solver_replay(available_levels[current_level_idx], algo_names_list[current_algo_idx])
                    return
                    moved = True
                    continue
                elif event.key == pygame.K_a:
                    current_algo_idx = (current_algo_idx + 1) % len(algo_names_list)
                    launch_solver_replay(available_levels[current_level_idx], algo_names_list[current_algo_idx])
                    return
                    moved = True
                    continue

                if status != "PLAYING":
                    continue

                if state.Play_handle:
                    if event.key == pygame.K_SPACE:
                        if state.maps.is_split:
                            state.switch_box()
                            moved = True
                    elif event.key == pygame.K_UP:
                        result = state.move_up()
                        moved = True
                        move_count += 1
                        move_history.append("U")
                    elif event.key == pygame.K_DOWN:
                        result = state.move_down()
                        moved = True
                        move_count += 1
                        move_history.append("D")
                    elif event.key == pygame.K_RIGHT:
                        result = state.move_right()
                        moved = True
                        move_count += 1
                        move_history.append("R")
                    elif event.key == pygame.K_LEFT:
                        result = state.move_left()
                        moved = True
                        move_count += 1
                        move_history.append("L")

        if moved and status == "PLAYING":
            if state.check_goal():
                status = "GOAL REACHED"
                state.draw_maps()
                state.draw_box()
                display.draw_sidebar(build_sidebar_info())
                display.update()
                # Stay in loop so player can view the result and press R or ESC
                continue

            if result == False:
                status = "GAME OVER"
                state.draw_maps()
                state.draw_box()
                display.draw_sidebar(build_sidebar_info())
                display.update()
                # Stay in loop so player can press R to restart or ESC to exit
                continue

        state.draw_maps()
        state.draw_box()
        display.draw_sidebar(build_sidebar_info())
        display.update()
        clock.tick(30)
