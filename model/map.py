#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Map"""
try:
    import simplejson as json
except ImportError:
    import json
from copy import deepcopy
from model.sw import swO, swQ, swX
from model.box import Box
from model.bridge import Bridge
from model.tiles import tile


class goal:
    def __init__(self, symbol, location):
        self.symbol = symbol
        self.location = location


class maps:
    def __init__(self, path_to_level=None):
        self.files = None
        self.jsonObj = None
        self.maps = list()
        self.level = None
        self.size = None
        self.start = None
        self.end = None 
        self.current_box = None
        self.types_tile = None
        self.swQ = list()
        self.swX = list()
        self.swO = list()
        self.Brid = list()
        self.is_split = False
        self.split_boxes = list()
        self.active_box_index = 0
        self.path = path_to_level  # Store level file path for restart
        if path_to_level != None:
            self.loadLevel(path_to_level)

    def loadLevel(self, path_to_level=None):
        if path_to_level != None:
            with open(path_to_level, "r") as f:
                self.jsonObj = json.loads(f.read())
            self.files = None

            # Name Level
            self.level = self.jsonObj["level"]
            # Size Map
            self.size = self.jsonObj["size"]
            # Start Location
            self.start = self.jsonObj["start"]
            # End Location
            self.end = self.jsonObj["end"]
            # Types of tiles
            self.types_tile = [self.jsonObj["tiles"]["orange"], self.jsonObj["tiles"]["rock"], self.jsonObj["tiles"]["space"]]
            # Current Box
            boxObj = self.jsonObj["box"]
            self.current_box = Box(boxObj["symbol"], boxObj["state"], boxObj["location"])
            self.is_split = False
            self.split_boxes = []
            self.active_box_index = 0

            # 1. Load Bridges first (shared instances)
            self.__loadBridges()
            # 2. Load swX
            self.__loadSWX()
            # 3. Load swQ
            self.__loadSWQ()
            # 4. Load swO
            self.__loadSWO()
            # 5. Load Maps
            self.__loadMap()
            # 6. Update Maps
            self.updateMaps()

        else:
            print("Path_to_level not None")

    def __loadBridges(self):
        bridObj = self.jsonObj.get("bridge", {})
        count = int(bridObj.get("count", 0))
        if count > 0:
            symbols = bridObj.get("symbol", [])
            for sym in symbols:
                if sym in bridObj:
                    chidBrid = bridObj[sym]
                    mode = chidBrid.get("mode", "toggle")
                    newBrid = Bridge(sym, chidBrid["active"], chidBrid["location"], mode=mode)
                    self.Brid.append(newBrid)

    def _get_or_create_bridge(self, nameBrid):
        for b in self.Brid:
            if b.symbol == nameBrid:
                return b
        bridObj = self.jsonObj.get("bridge", {})
        if int(bridObj.get("count", 0)) > 0 and nameBrid in bridObj:
            chidBrid = bridObj[nameBrid]
            mode = chidBrid.get("mode", "toggle")
            newBrid = Bridge(nameBrid, chidBrid["active"], chidBrid["location"], mode=mode)
            self.Brid.append(newBrid)
            return newBrid
        return None

    def _resolve_bridges(self, bridge_field):
        if not bridge_field:
            return []
        if isinstance(bridge_field, list):
            res = []
            for name in bridge_field:
                b = self._get_or_create_bridge(name)
                if b:
                    res.append(b)
            return res
        b = self._get_or_create_bridge(bridge_field)
        return [b] if b else []

    def __loadMap(self):
        # Load tiles to Maps
        maps = self.jsonObj["maps"]
        for i in range(self.size[0]):
            line = []
            for j in range(self.size[1]):
                if maps[i][j] == self.types_tile[0]: # orange tile
                    newtile = tile(2, None, [i, j])
                    line.append(newtile)
                elif maps[i][j] == self.types_tile[1]: # rock tile
                    newtile = tile(1, None, [i, j])
                    line.append(newtile)
                elif maps[i][j] == self.types_tile[2]: # space title
                    newtile = tile(0, None, [i, j])
                    if self.end == [i, j]:
                        newtile.set_obj(goal("$", [i, j])) # End game
                    line.append(newtile)
                else:
                    newtile = tile(1, None, [i, j])
                    line.append(newtile)
            self.maps.append(line)

    def updateMaps(self):
        # Load swO to Maps
        if len(self.swO) != 0:
            for child in self.swO:
                self.maps[int(child.location[0])][int(child.location[1])].set_obj(child)
        # Load swQ to Maps
        if len(self.swQ) != 0:
            for child in self.swQ:
                self.maps[int(child.location[0])][int(child.location[1])].set_obj(child)
        # Load swX to Maps
        if len(self.swX) != 0:
            for child in self.swX:
                self.maps[int(child.location[0])][int(child.location[1])].set_obj(child)

        if len(self.Brid) != 0:
            for child in self.Brid:
                tile_type = 1 if child.active else 0
                for pos in child.location:
                    y, x = int(pos[0]), int(pos[1])
                    self.maps[y][x].type = tile_type
                    self.maps[y][x].set_obj(child)

    def refreshBox(self):
        if not self.__onFloor(self.current_box):
            self.current_box.location = deepcopy(self.current_box.pre_location)
            return False
        # If box was successfully moved, check merge if split
        if self.is_split:
            self.check_merge_boxes()
        return True

    def checkSWQ(self):
        triggered = set()
        for child in self.current_box.location:
            y, x = int(child[0]), int(child[1])
            obj = self.maps[y][x].obj
            if isinstance(obj, swQ) and obj not in triggered:
                triggered.add(obj)
                if obj.change_active():
                    self.__updateSWQ(obj)

    def checkSWX(self):
        if not (self.current_box.is_doubleBox() and self.current_box.is_standing()):
            return
        triggered = set()
        for child in self.current_box.location:
            y, x = int(child[0]), int(child[1])
            obj = self.maps[y][x].obj
            if isinstance(obj, swX) and obj not in triggered:
                triggered.add(obj)
                if obj.change_active():
                    self.__updateSWX(obj)

    def checkSWO(self):
        if not (self.current_box.is_doubleBox() and self.current_box.is_standing()):
            return False
        for child in self.current_box.location:
            y, x = int(child[0]), int(child[1])
            obj = self.maps[y][x].obj
            if isinstance(obj, swO):
                self.split_box(obj)
                return True
        return False

    def split_box(self, swo_obj):
        swo_obj.change_active()
        self.__updateSWO(swo_obj)

        if swo_obj.box1 and swo_obj.box2:
            loc1 = deepcopy(swo_obj.box1.location)
            loc2 = deepcopy(swo_obj.box2.location)
        else:
            cy, cx = self.current_box.location[0]
            loc1 = [[cy, cx]]
            loc2 = [[cy, cx + 1]]

        b1 = Box("#1", 1, loc1)
        b2 = Box("#2", 1, loc2)
        b1.on()
        b2.off()
        self.is_split = True
        self.split_boxes = [b1, b2]
        self.active_box_index = 0
        self.current_box = b1

        # Check soft switch at destination of b1
        self.checkSWQ()

    def switch_active_box(self):
        if not self.is_split or len(self.split_boxes) != 2:
            return False
        self.active_box_index = 1 - self.active_box_index
        self.current_box = self.split_boxes[self.active_box_index]
        self.split_boxes[self.active_box_index].on()
        self.split_boxes[1 - self.active_box_index].off()
        return True

    def check_merge_boxes(self):
        if not self.is_split or len(self.split_boxes) != 2:
            return False
        b1 = self.split_boxes[0]
        b2 = self.split_boxes[1]
        y1, x1 = b1.location[0]
        y2, x2 = b2.location[0]

        is_adjacent = False
        merged_loc = None
        if y1 == y2 and abs(x1 - x2) == 1:
            merged_loc = [[y1, min(x1, x2)], [y1, max(x1, x2)]]
            is_adjacent = True
        elif x1 == x2 and abs(y1 - y2) == 1:
            merged_loc = [[min(y1, y2), x1], [max(y1, y2), x1]]
            is_adjacent = True

        if is_adjacent:
            merged_box = Box("#", 2, merged_loc)
            merged_box.on()
            self.current_box = merged_box
            self.is_split = False
            self.split_boxes = []
            self.active_box_index = 0
            # Newly merged box might trigger switches
            self.checkSWQ()
            self.checkSWX()
            self.checkSWO()
            return True
        return False

    def __updateSWX(self, swXObj):
        for child in self.swX:
            if child.symbol == swXObj.symbol:
                child.active = swXObj.active
        self.__updateBrid(swXObj.bridge)

    def __updateSWQ(self, swQObj):
        for child in self.swQ:
            if child.symbol == swQObj.symbol:
                child.active = swQObj.active
        self.__updateBrid(swQObj.bridge)

    def __updateSWO(self, swOObj):
        for child in self.swO:
            if child.symbol == swOObj.symbol:
                self.swO[self.swO.index(child)] = swOObj
        if swOObj.bridge:
            self.__updateBrid(swOObj.bridge)

    def __is_goal(self):
        return self.end == self.current_box.location[0]

    def check_goal(self):
        return self.current_box.is_standing() and self.current_box.is_doubleBox() and self.__is_goal()

    def __is_valid(self, box):
        # 1. Check tile validity first before triggering any switch
        if len(box.location) == 1:
            y, x = int(box.location[0][0]), int(box.location[0][1])
            if not self.maps[y][x].check_material_tile(box):
                return False
        elif len(box.location) == 2:
            for child in box.location:
                y, x = int(child[0]), int(child[1])
                if not self.maps[y][x].check_material_tile(box):
                    return False
        else:
            return False

        # If split, active box cannot occupy the exact same tile as the inactive box
        if self.is_split and len(self.split_boxes) == 2:
            inactive_box = self.split_boxes[1 - self.active_box_index]
            if box.location[0] == inactive_box.location[0]:
                return False

        # 2. Only trigger switches if the box safely landed on the floor
        self.checkSWQ()
        self.checkSWX()
        self.checkSWO()
        return True

    def __onFloor(self, box):
        width, height = self.size
        if len(box.location) == 1:
            y, x = int(box.location[0][0]), int(box.location[0][1])
            if y < 0 or y >= width or x < 0 or x >= height:
                return False
            return self.__is_valid(box)
        elif len(box.location) == 2:
            for child in box.location:
                y, x = int(child[0]), int(child[1])
                if y < 0 or y >= width or x < 0 or x >= height:
                    return False
            return self.__is_valid(box)

    def __updateBrid(self, bridObj):
        if not bridObj:
            return
        bridges = bridObj if isinstance(bridObj, list) else [bridObj]
        for b in bridges:
            tile_type = 1 if b.active else 0
            for pos in b.location:
                y, x = int(pos[0]), int(pos[1])
                self.maps[y][x] = tile(tile_type, b, [y, x])

    def __loadSWX(self):
        swXObj = self.jsonObj.get("swX", {})
        count = int(swXObj.get("count", 0))
        if count > 0:
            symbols = swXObj.get("symbol", [])
            for sym in symbols:
                symObj = swXObj[sym]
                bridges = self._resolve_bridges(symObj.get("bridge"))
                br = bridges[0] if len(bridges) == 1 else (bridges if len(bridges) > 1 else None)
                newswX = swX(sym, symObj.get("type", 0), symObj["active"], symObj["location"], bridge=br)
                self.swX.append(newswX)

    def __loadSWQ(self):
        swQObj = self.jsonObj.get("swQ", {})
        count = int(swQObj.get("count", 0))
        if count > 0:
            symbols = swQObj.get("symbol", [])
            for sym in symbols:
                symObj = swQObj[sym]
                bridges = self._resolve_bridges(symObj.get("bridge"))
                br = bridges[0] if len(bridges) == 1 else (bridges if len(bridges) > 1 else None)
                newswQ = swQ(sym, symObj.get("type", 0), symObj["active"], symObj["location"], bridge=br)
                self.swQ.append(newswQ)

    def __loadSWO(self):
        swOObj = self.jsonObj.get("swO", {})
        count = int(swOObj.get("count", 0))
        if count > 0:
            symbols = swOObj.get("symbol", [])
            for sym in symbols:
                symObj = swOObj[sym]
                bridges = self._resolve_bridges(symObj.get("bridge"))
                br = bridges[0] if len(bridges) == 1 else (bridges if len(bridges) > 1 else None)
                newswO = swO(sym, symObj["location"], symObj.get("split", True), bridge=br, typ=symObj.get("type", 0))
                box1, box2 = symObj.get("box1"), symObj.get("box2")
                if box1:
                    newswO.set_box1(box1.get("symbol", "#1"), box1.get("state", 1), box1["location"])
                if box2:
                    newswO.set_box2(box2.get("symbol", "#2"), box2.get("state", 1), box2["location"])
                self.swO.append(newswO)

    def print_current(self):
        for i in self.maps:
            print("------" * self.size[1])
            print('{0: <3}'.format("|"), end='')
            for j in i:
                if j.type == 0:
                    content = " "
                    if j.obj != None:
                        if j.obj.symbol == "$":
                            content = "$"
                elif j.type == 1 or j.type == 2:
                    if j.obj != None:
                        content = j.obj.symbol
                    else:
                        content = str(j.type)
                if self.is_split and len(self.split_boxes) == 2:
                    if j.location in self.split_boxes[0].location:
                        content = "#1" if self.active_box_index == 0 else "1"
                    elif j.location in self.split_boxes[1].location:
                        content = "#2" if self.active_box_index == 1 else "2"
                else:
                    if j.location in self.current_box.location:
                        content = "#"
                print('{0: <2}'.format(content), "|", end='')
                print('{0: <2}'.format(""), end='')
            print("\n", end='')
        print("------" * self.size[1])
