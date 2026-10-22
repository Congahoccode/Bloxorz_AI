#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Switch"""

from model.box import Box

class swQ:
    """Switch Bat Giac (Soft switch) - triggered by any contact"""
    def __init__(self, symbol, typ, active, location, bridge=None):
        self.symbol = symbol
        self.type = typ  # 0 or 'toggle' for toggle mode; 1 or 'permanent' for permanent mode
        self.active = bool(active)
        self.location = location
        self.bridge = bridge

    def set_bridge(self, bridge):
        self.bridge = bridge

    def change_active(self):
        self.active = not self.active
        bridges = self.bridge if isinstance(self.bridge, list) else ([self.bridge] if self.bridge else [])
        if len(bridges) == 0:
            return True

        changed_any = False
        for b in bridges:
            if self.type == 1 or str(self.type).lower() in ['permanent', 'open', 'close', 'true', 'false'] or b.mode == 'permanent':
                target_state = True
                if str(self.type).lower() in ['close', 'false']:
                    target_state = False
                if b.set_permanent(target_state):
                    changed_any = True
            else:
                if b.toggle():
                    changed_any = True
        return True

    def get_location(self):
        return self.location

    def get_bridge(self):
        return self.bridge


class swX:
    """Switch X (Heavy switch) - triggered only when standing upright"""
    def __init__(self, symbol, typ, active, location, bridge=None):
        self.symbol = symbol
        self.type = typ  # 0 or 'toggle'; 1 or 'permanent'
        self.active = bool(active)
        self.location = location
        self.bridge = bridge

    def set_bridge(self, bridge):
        self.bridge = bridge

    def change_active(self):
        self.active = not self.active
        bridges = self.bridge if isinstance(self.bridge, list) else ([self.bridge] if self.bridge else [])
        if len(bridges) == 0:
            return True

        changed_any = False
        for b in bridges:
            if self.type == 1 or str(self.type).lower() in ['permanent', 'open', 'close', 'true', 'false'] or b.mode == 'permanent':
                target_state = True
                if str(self.type).lower() in ['close', 'false']:
                    target_state = False
                if b.set_permanent(target_state):
                    changed_any = True
            else:
                if b.toggle():
                    changed_any = True
        return True

    def get_location(self):
        return self.location

    def get_bridge(self):
        return self.bridge


class swO:
    """Switch tach doi (Split switch) - splits into two 1x1x1 boxes"""
    def __init__(self, symbol, location, split=True, box1=None, box2=None, bridge=None, typ=0):
        self.symbol = symbol
        self.location = location
        self.split = split
        self.box1 = box1
        self.box2 = box2
        self.bridge = bridge
        self.type = typ
        self.active = 1

    def set_box1(self, symbol, state, location):
        if len(location) > 0 and isinstance(location[0], int):
            location = [location]
        self.box1 = Box(symbol, state, location)

    def set_box2(self, symbol, state, location):
        if len(location) > 0 and isinstance(location[0], int):
            location = [location]
        self.box2 = Box(symbol, state, location)

    def set_bridge(self, bridge):
        self.bridge = bridge

    def change_active(self):
        if self.active != 1:
            self.active = 1
            if self.box1 and self.box2:
                self.box1.on()
                self.box2.off()
        else:
            self.active = 2
            if self.box1 and self.box2:
                self.box2.on()
                self.box1.off()

        bridges = self.bridge if isinstance(self.bridge, list) else ([self.bridge] if self.bridge else [])
        for b in bridges:
            b.change_active()
        return True

    def get_active_box(self):
        if self.active == 1:
            return self.box1
        return self.box2

    def get_all_box(self):
        return (self.box1, self.box2)

    def get_location(self):
        return self.location
