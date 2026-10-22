#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Bridge"""

class Bridge:
    def __init__(self, symbol, active, location, mode='toggle'):
        self.symbol = symbol
        self.times_active = 0
        self.active = bool(active)
        self.location = location
        self.type = len(location)
        self.mode = str(mode).lower()
        self.is_permanent = (self.mode == 'permanent' and self.times_active > 0)

    def check_times_active(self):
        return self.times_active > 0

    def toggle(self):
        if self.is_permanent:
            return False
        self.times_active += 1
        self.active = not self.active
        return True

    def set_permanent(self, target_state=True):
        if not self.is_permanent:
            self.times_active += 1
            self.active = bool(target_state)
            self.is_permanent = True
            return True
        return False

    def change_active(self, mode=None, target_state=True):
        act_mode = mode if mode is not None else self.mode
        if str(act_mode).lower() == 'permanent':
            return self.set_permanent(target_state)
        return self.toggle()
