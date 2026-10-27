import sys
from drawing.box import Box as Cube
from model.box import Box 
from copy import deepcopy
from model.map import maps as Maps
from model.tiles import tile as Tile
import math
import numpy as np

class Control:
    Play_handle = False
    def __init__(self, maps: Maps):
        if maps is None:
            print("Maps not None")
            sys.exit()
        
        # BOX
        self.start = maps.current_box.location
        self.current = maps.current_box.location
        
        # MAP
        self.maps = maps
        self.start_maps = self.maps.maps[:]
        self.curr_maps = self.start_maps
        self.size = maps.size

        self.stack = [(self.start, self.start_maps)] 
        self.visted = [(self.start, self.start_maps)]
        self.eval_maps = None
        self.curr_evaluate =  0
        self.end = [maps.end]
        
        self.moves = (self.move_up, self.move_down, self.move_right, self.move_left)

    def switch_box(self):
        if self.maps.switch_active_box():
            self.update_current_location()
            return True
        return False

    def move_up(self):
        self.maps.current_box.move_up()
        if not self.check_box_on_maps():
            return False
        else:
            self.update_current_location()
            if not self.Play_handle:
                return self.add_stack() 
            return True 
    
    def move_down(self):
        self.maps.current_box.move_down()
        if not self.check_box_on_maps():
            return False
        else:
            self.update_current_location()
            if not self.Play_handle:
                return self.add_stack()  
            return True 
    
    def move_right(self):
        self.maps.current_box.move_right()
        if not self.check_box_on_maps():
            return False
        else:
            self.update_current_location()
            if not self.Play_handle:
                return self.add_stack()   
            return True 
    
    def move_left(self):
        self.maps.current_box.move_left()
        if not self.check_box_on_maps():
            #print('left_failed')
            return False
        else:
            self.update_current_location()
            #print('left_suc')
            if not self.Play_handle:
                return self.add_stack() 
            return True

    def update_current_location(self):
        if self.maps.is_split and len(self.maps.split_boxes) == 2:
            self.current = (
                deepcopy(self.maps.split_boxes[0].location),
                deepcopy(self.maps.split_boxes[1].location),
                self.maps.active_box_index
            )
        else:
            self.current = deepcopy(self.maps.current_box.location)
        self.curr_maps = deepcopy(self.maps.maps)
        
    def update_box_locaton_for_maps(self, location):
        self.maps.current_box.location = location

    def check_box_on_maps(self):
        return self.maps.refreshBox()
    
    def set_state(self, state, maps):
        self.current = deepcopy(state)
        self.curr_maps = deepcopy(maps)
        self.maps.maps = self.curr_maps
        if isinstance(state, tuple) and len(state) == 3:
            loc1, loc2, active_idx = state
            b1 = Box("#1", 1, deepcopy(loc1))
            b2 = Box("#2", 1, deepcopy(loc2))
            self.maps.is_split = True
            self.maps.split_boxes = [b1, b2]
            self.maps.active_box_index = active_idx
            self.maps.current_box = b1 if active_idx == 0 else b2
        else:
            self.maps.is_split = False
            self.maps.split_boxes = []
            merged_box = Box("#", 2, deepcopy(self.current))
            merged_box.on()
            self.maps.current_box = merged_box
        
    def get_state(self):
        return deepcopy(self.current)
    
    def get_maps(self):
        return deepcopy(self.curr_maps)
    
    def add_stack(self):
        state = self.current
        maps = self.curr_maps
        if state in [i for (i, j) in self.visted]:
            return False
        else:
            self.stack.append((state, maps))
            return True
    
    def check_goal(self):
        return self.maps.check_goal()
    
    @staticmethod
    def Distance(pointA, pointB):
        X2 = math.pow(pointA[0]-pointB[0], 2)
        Y2 = math.pow(pointA[1]-pointB[1], 2)
        return math.sqrt(X2+Y2)

    def eval_func(self):
        goal = self.maps.end
        y , x =  self.size
        eval_maps = np.full((y, x), 0)
       
        for i in range(y):
            for j in range(x):
                delta = self.Distance([i,j], goal)
                eval_maps[i, j] = delta

        eval_maps[goal[0]][goal[1]] = 0

        self.eval_maps = eval_maps
        return eval_maps

    def evaluate(self):
        if self.eval_maps is None:
            return 0
        if isinstance(self.current, tuple):
            p1 = self.current[0][0]
            p2 = self.current[1][0]
            self.curr_evaluate = (self.eval_maps[p1[0], p1[1]] + self.eval_maps[p2[0], p2[1]]) / 2
            return self.curr_evaluate
        elif len(self.current) == 2:
            point1, point2 = self.current
            self.curr_evaluate = (self.eval_maps[point1[0], point1[1]] + self.eval_maps[point2[0], point2[1]])/2
            return self.curr_evaluate
        elif len(self.current) == 1:
            point = self.current[0]
            self.curr_evaluate = self.eval_maps[point[0], point[1]]
            return self.curr_evaluate
    
    def get_evaluate(self):
        return self.curr_evaluate

    def set_evaluate(self, value):
        self.curr_evaluate = value
        
    def print_maps(self):
        self.maps.print_current()
    
    def draw_maps(self, path=None):
        height, width = self.size
        maps = self.curr_maps
        for x in range(width):
            for y in range(height):
                tile = maps[int(y)][int(x)]
                if tile.type != 0:
                    Cube.draw_box(position=(x, y), size=(1, 1, -0.3), face_color=tile.colors)
                else:
                    if tile.obj != None and tile.obj.symbol == "$":
                        Cube.draw_box(position=(x, y), size=(1, 1, -0.3), face_color=tile.colors)

    def draw_box(self):
        if self.maps.is_split and len(self.maps.split_boxes) == 2:
            b1 = self.maps.split_boxes[0]
            b2 = self.maps.split_boxes[1]
            if self.maps.active_box_index == 0:
                Cube.draw_box(position=(b1.location[0][1], b1.location[0][0]), size=(1, 1, 1),
                              face_color=(0.2, 0.7, 1.0, 0.95), border_color=(1.0, 1.0, 0.0, 1.0))
                Cube.draw_box(position=(b2.location[0][1], b2.location[0][0]), size=(1, 1, 1),
                              face_color=(0.3, 0.4, 0.6, 0.90), border_color=(0.5, 0.5, 0.5, 1.0))
            else:
                Cube.draw_box(position=(b1.location[0][1], b1.location[0][0]), size=(1, 1, 1),
                              face_color=(0.3, 0.4, 0.6, 0.90), border_color=(0.5, 0.5, 0.5, 1.0))
                Cube.draw_box(position=(b2.location[0][1], b2.location[0][0]), size=(1, 1, 1),
                              face_color=(0.2, 0.7, 1.0, 0.95), border_color=(1.0, 1.0, 0.0, 1.0))
            return

        # Ensure current_box has correct state for merged/normal double box
        if hasattr(self.maps, 'current_box') and self.maps.current_box:
            if not self.maps.is_split and self.maps.current_box.state != 2:
                self.maps.current_box.state = 2
                self.maps.current_box.symbol = "#"

        face_col = (0.2470588235294118, 0.2823529411764706, 0.8, 0.95)
        border_col = (0.8, 0.8, 0.8, 1.0)

        if len(self.current) == 2:
            c1, c2 = self.current
            min_r = min(c1[0], c2[0])
            min_c = min(c1[1], c2[1])
            if c1[0] == c2[0]:
                # Horizontal (along row, spans 2 columns)
                Cube.draw_box(position=(min_c, min_r), size=(2, 1, 1), face_color=face_col, border_color=border_col)
            else:
                # Vertical (along column, spans 2 rows)
                Cube.draw_box(position=(min_c, min_r), size=(1, 2, 1), face_color=face_col, border_color=border_col)
        elif len(self.current) == 1:
            Cube.draw_box(position=(self.current[0][1], self.current[0][0]), size=(1, 1, 2), face_color=face_col, border_color=border_col)
    
    def draw_StartBox(self):
        face_col = (0.2470588235294118, 0.2823529411764706, 0.8, 0.95)
        border_col = (0.8, 0.8, 0.8, 1.0)

        if len(self.start) == 2:
            c1, c2 = self.start
            min_r = min(c1[0], c2[0])
            min_c = min(c1[1], c2[1])
            if c1[0] == c2[0]:
                Cube.draw_box(position=(min_c, min_r), size=(2, 1, 1), face_color=face_col, border_color=border_col)
            else:
                Cube.draw_box(position=(min_c, min_r), size=(1, 2, 1), face_color=face_col, border_color=border_col)
        elif len(self.start) == 1:
            Cube.draw_box(position=(self.start[0][1], self.start[0][0]), size=(1, 1, 2), face_color=face_col, border_color=border_col)
    
    def draw_StartMaps(self):
        height, width = self.size
        maps = self.start_maps
        for x in range(width):
            for y in range(height):
                tile = maps[int(y)][int(x)]
                if tile.type != 0:
                    Cube.draw_box(position=(x, y), size=(1, 1, -0.3), face_color=tile.colors)
