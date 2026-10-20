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


def handle(state: Control, map_size=(0, 0)):
    state.Play_handle = True
    pygame.init()
    display = Display(title='Bloxorz Game - Play Mode', map_size=map_size)
    result = True
    print("Use Arrow Keys to move. Press ESC, Space, or Close Window to exit.")
    clock = pygame.time.Clock()

    # Initial render
    state.draw_maps()
    state.draw_box()
    display.update()

    while True:
        moved = False
        for event in pygame.event.get():
            if display.quit(event):
                print("Exited game.")
                pygame.quit()
                return

            if state.Play_handle and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    result = state.move_up()
                    moved = True
                elif event.key == pygame.K_DOWN:
                    result = state.move_down()
                    moved = True
                elif event.key == pygame.K_RIGHT:
                    result = state.move_right()
                    moved = True
                elif event.key == pygame.K_LEFT:
                    result = state.move_left()
                    moved = True

        if moved:
            state.draw_maps()
            state.draw_box()
            display.update()

            if state.check_goal():
                print("WINNER! Congratulations, you reached the goal!")
                time.sleep(1.5)
                pygame.quit()
                return

            if result == False:
                print("LOSER! The block fell off the board.")
                time.sleep(1.5)
                pygame.quit()
                return
        else:
            state.draw_maps()
            state.draw_box()
            display.update()

        clock.tick(30)
