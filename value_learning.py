import pygame
import sys
import os
import time
from model.solver import dfs_path, bfs_path, handle, hill_climbing, dfs_step_by_step, bfs_step_by_step
from drawing.display import Display
from model.map import maps
from model.control import Control
import numpy as np
class Level:
    lv1  = "./level/1.json"
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

def draw_path_3D(solution, timesleep=0.5, level=Level.lv1, map_size = (0,0)):
    pygame.init()
    display = Display(title='Bloxorz Game', map_size=map_size)
    if solution != None:
        print("Success!")
        print("Step: %d" % len(solution))
        print(solution)
        choiselv = maps(level)

        level = Control(choiselv)
        level.draw_StartBox()
        level.draw_StartMaps()
        display.update() 

        for path in solution:
            time.sleep(timesleep)
            level.current = path
            level.update_box_locaton_for_maps(path)
            
            if level.maps.refreshBox():
                level.update_current_location()
            else: 
                print("Solution Fail!")
                return

            level.draw_box() 
            level.draw_maps()   
            display.update()
        return
    else:
        print("Unable to find path for maps!")
        print("Dir Level: %s" % level)
        return
def draw_path_2D(solution, timesleep=0.5, level=Level.lv1):
    if solution != None:
        print("Success!")
        print("Step: %d" % len(solution))
        print(solution)
        choiselv = maps(level)

        level = Control(choiselv)
        level.print_maps()
        
        time.sleep(timesleep)

        for path in solution:
            os.system("clear")
            level.current = path
            level.update_box_locaton_for_maps(path)
            level.maps.refreshBox()

            if level.maps.refreshBox():
                level.update_current_location()
            else: 
                print("Solution Fail!")
                return

            level.print_maps()
            time.sleep(timesleep)
        return
    else:
        print("Unable to find path for maps!")
        print("Dir Level: %s" % level)
        return
def walk(state: Control, V, N, exp=0.5):
    path = [tuple(sorted([tuple(j)for j in state.current]))]
    visited = [tuple(sorted([tuple(j)for j in state.current]))]
    for i in range(N):
        if not state.stack:
            print('empty')
            break
        current_state, current_maps = state.stack.pop()
        state.visted.append((current_state, current_maps))
        #print(state.current)
        old = state.current
        good_moves = []
        not_bad_moves = []
        best_move=None
        best_curr=None
        for move in state.moves:
            state.set_state(current_state, current_maps)
            if move():
                current = tuple(sorted([tuple(j)for j in state.current]))
                not_bad_moves += [move]
                if current not in V:
                    V[current]=0
                if current not in visited:
                    good_moves+=[move]
                    if best_move is None or V[best_curr]<V[current]:
                        best_curr=current
                        best_move=move
                state.current = old
        state.set_state(current_state, current_maps)
        if len(not_bad_moves)==0:
            #print('bad_behave')
            return path, -0.5
        elif len(good_moves)==0:
            move = not_bad_moves[np.random.choice(len(not_bad_moves))]
            #print('no_moves')
            #return path, -0.3
            #break
        elif (np.random.uniform(0, 1)<exp):
            move = good_moves[np.random.choice(len(good_moves))]
        else:
            move = best_move
        if move():
            current = tuple(sorted([tuple(j)for j in state.current]))
            if current in visited:
                print("visited")
                break
            else:
                path += [tuple(sorted([tuple(j)for j in state.current]))]
                if state.check_goal():
                    #print("WIN")
                    
                    return path, 1
                    break
        else:
            print("wrong")
    print("stucked")
    return path, -0.3
def ValueLearning(learn_rate=0.1, exp=0.5, N=100, M=100, level=Level.lv1):
    V=dict()
    gamma_win=0.9
    gamma_lose=0.2
    wins=0
    bad=0
    win_len = 0
    for j in range(N):
        Maps = maps(level)
        size = Maps.size
        state = Control(Maps)
        path, r = walk(state, V, M, exp)
        if r>0:
            gamma=gamma_win
            wins+=1
            win_len+=len(path)
        else:
            gamma=gamma_lose
            
        for i in reversed(path):
            if i not in V:
                V[i]=0
            V[i] = learn_rate*r+(1-learn_rate)*V[i]
            r*=gamma
    
    if wins>0:
        str_res = f"wins %.2f, win_len %.1f"%(wins/N, win_len/wins)
    else:
        str_res = "no wins"
    print(str_res)
    return V, str_res


if __name__=="__main__":
    if len(sys.argv) >= 1:
        level = sys.argv[1]
    V, str_res=ValueLearning(learn_rate=0.1, exp=0.2, N=1, M=100, level=level)   # you can change parameters here!
    Maps = maps(level)
    size = Maps.size
    state = Control(Maps)
    path, r = walk(state, V=V, N=100, exp=0)
    result = [[list(j) for j in i] for i in path]

    draw_path_2D(result, level=level)
    print(str_res)
    print("Path length:,", len(path))
