import unittest
import json
import os
from copy import deepcopy
from model.map import maps
from model.control import Control
from model.box import Box
from model.tiles import tile
from model.bridge import Bridge
from model.sw import swQ, swX, swO

class TestAdvancedTiles(unittest.TestCase):
    def setUp(self):
        # Base JSON template for testing
        self.base_level = {
            "level": 99,
            "size": [6, 10],
            "swX": {"count": 0, "symbol": []},
            "swQ": {"count": 0, "symbol": []},
            "swO": {"count": 0, "symbol": []},
            "bridge": {"count": 0, "symbol": []},
            "start": [1, 1],
            "end": [1, 8],
            "box": {"state": 2, "symbol": "#", "location": [[1, 1]]},
            "tiles": {"orange": 2, "rock": 1, "space": 0},
            "maps": [
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 0, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            ]
        }
        self.test_json_path = "/tmp/test_bloxorz_level.json"

    def tearDown(self):
        if os.path.exists(self.test_json_path):
            os.remove(self.test_json_path)

    def _create_map(self, custom_dict):
        d = deepcopy(self.base_level)
        d.update(custom_dict)
        with open(self.test_json_path, "w") as f:
            json.dump(d, f)
        return maps(self.test_json_path)

    # 1. Fragile tiles (orange)
    def test_fragile_tiles_standing_falls(self):
        # [1, 2] is orange
        custom = deepcopy(self.base_level)
        custom["maps"][1][2] = 2
        m = self._create_map(custom)
        ctrl = Control(m)
        # Block at [1, 1] standing. Move right -> lies at [[1, 2], [1, 3]]. Valid.
        self.assertTrue(ctrl.move_right())
        # Move right again -> stands at [[1, 4]]. Valid.
        self.assertTrue(ctrl.move_right())
        # Let's test standing directly on orange:
        # Place orange at [1, 4]
        custom2 = deepcopy(self.base_level)
        custom2["maps"][1][4] = 2
        m2 = self._create_map(custom2)
        ctrl2 = Control(m2)
        self.assertTrue(ctrl2.move_right()) # lying at [1, 2], [1, 3]
        # Move right -> stands on [1, 4] which is orange -> should fall!
        res = ctrl2.move_right()
        self.assertFalse(res, "Standing upright on fragile tile should fall!")

    def test_fragile_tiles_lying_survives(self):
        # Orange at [1, 2] and [1, 3]
        custom = deepcopy(self.base_level)
        custom["maps"][1][2] = 2
        custom["maps"][1][3] = 2
        m = self._create_map(custom)
        ctrl = Control(m)
        # Standing at [1, 1], move right -> lies horizontally on [[1, 2], [1, 3]]
        self.assertTrue(ctrl.move_right(), "Lying horizontally on orange tiles should survive!")

    def test_fragile_tiles_single_box_survives(self):
        custom = deepcopy(self.base_level)
        custom["maps"][1][2] = 2
        m = self._create_map(custom)
        # Create single box at [1, 2]
        single_box = Box("#1", 1, [[1, 2]])
        tile_obj = m.maps[1][2]
        self.assertTrue(tile_obj.check_material_tile(single_box), "Single 1x1x1 box should survive on orange tile!")

    # 2. Bridges
    def test_bridge_closed_falls_open_survives(self):
        # Bridge at [1, 2], initially closed (active = False)
        custom = deepcopy(self.base_level)
        custom["bridge"] = {
            "count": 1,
            "symbol": ["b1"],
            "b1": {"active": False, "location": [[1, 2], [1, 3]]}
        }
        m = self._create_map(custom)
        ctrl = Control(m)
        # Move right onto closed bridge -> should fall!
        self.assertFalse(ctrl.move_right(), "Moving onto closed bridge should fall!")

        # Bridge initially open (active = True)
        custom["bridge"]["b1"]["active"] = True
        m2 = self._create_map(custom)
        ctrl2 = Control(m2)
        self.assertTrue(ctrl2.move_right(), "Moving onto open bridge should survive!")

    # 3. Soft Switch (swQ)
    def test_soft_switch_activates_by_standing_lying_and_single(self):
        # Bridge at [3, 3], closed. swQ at [1, 2] toggles bridge b1.
        custom = deepcopy(self.base_level)
        custom["bridge"] = {
            "count": 1,
            "symbol": ["b1"],
            "b1": {"active": False, "location": [[3, 3]]}
        }
        custom["swQ"] = {
            "count": 1,
            "symbol": ["q1"],
            "q1": {"type": 0, "active": False, "location": [1, 2], "bridge": "b1"}
        }
        m = self._create_map(custom)
        ctrl = Control(m)
        self.assertFalse(m.Brid[0].active)
        # Move right -> box lies horizontally covering [1, 2] and [1, 3] -> touches swQ!
        ctrl.move_right()
        self.assertTrue(m.Brid[0].active, "Soft switch should activate when lying horizontally across it!")

        # Now test single box on swQ
        m.Brid[0].active = False
        m.current_box = Box("#1", 1, [[1, 2]])
        m.checkSWQ()
        self.assertTrue(m.Brid[0].active, "Soft switch should activate when touched by a single 1x1x1 box!")

    # 4. Heavy Switch (swX)
    def test_heavy_switch_only_activates_standing(self):
        custom = deepcopy(self.base_level)
        custom["bridge"] = {
            "count": 1,
            "symbol": ["b1"],
            "b1": {"active": False, "location": [[3, 3]]}
        }
        # Heavy switch at [1, 2]
        custom["swX"] = {
            "count": 1,
            "symbol": ["x1"],
            "x1": {"type": 0, "active": False, "location": [1, 2], "bridge": "b1"}
        }
        m = self._create_map(custom)
        ctrl = Control(m)
        # Move right -> box lies on [1, 2] and [1, 3]. Heavy switch should NOT trigger!
        ctrl.move_right()
        self.assertFalse(m.Brid[0].active, "Heavy switch must NOT activate when block is lying down!")

        # Single box on swX -> should NOT trigger
        m.current_box = Box("#1", 1, [[1, 2]])
        m.checkSWX()
        self.assertFalse(m.Brid[0].active, "Heavy switch must NOT activate for a single 1x1x1 box!")

        # Double box standing on swX -> SHOULD trigger!
        m.current_box = Box("#", 2, [[1, 2]])
        m.checkSWX()
        self.assertTrue(m.Brid[0].active, "Heavy switch MUST activate when standing upright on it!")

    # 5. Split Switch (swO)
    def test_split_switch_standing_only_and_splits(self):
        custom = deepcopy(self.base_level)
        custom["swO"] = {
            "count": 1,
            "symbol": ["o1"],
            "o1": {
                "split": True,
                "location": [1, 4],
                "box1": {"symbol": "#1", "state": 1, "location": [[2, 2]]},
                "box2": {"symbol": "#2", "state": 1, "location": [[4, 4]]}
            }
        }
        m = self._create_map(custom)
        ctrl = Control(m)
        # Move right twice: [1, 1] standing -> lying at [1, 2],[1, 3] -> standing at [1, 4]
        ctrl.move_right()
        self.assertFalse(m.is_split)
        ctrl.move_right() # Lands standing on [1, 4] which is swO!
        self.assertTrue(m.is_split, "Standing upright on swO must split the box!")
        self.assertEqual(len(m.split_boxes), 2)
        self.assertEqual(m.split_boxes[0].location, [[2, 2]])
        self.assertEqual(m.split_boxes[1].location, [[4, 4]])
        self.assertEqual(m.active_box_index, 0)
        self.assertEqual(m.current_box.location, [[2, 2]])

    # 6. Control split blocks
    def test_split_block_control_and_switching(self):
        custom = deepcopy(self.base_level)
        custom["swO"] = {
            "count": 1,
            "symbol": ["o1"],
            "o1": {
                "split": True,
                "location": [1, 4],
                "box1": {"symbol": "#1", "state": 1, "location": [[2, 2]]},
                "box2": {"symbol": "#2", "state": 1, "location": [[4, 4]]}
            }
        }
        m = self._create_map(custom)
        ctrl = Control(m)
        ctrl.move_right()
        ctrl.move_right() # Split triggered
        self.assertTrue(m.is_split)

        # Move active box (box1 at [2, 2]) right -> moves to [2, 3]
        ctrl.move_right()
        self.assertEqual(m.split_boxes[0].location, [[2, 3]])
        self.assertEqual(m.split_boxes[1].location, [[4, 4]])

        # Switch active box
        ctrl.switch_box()
        self.assertEqual(m.active_box_index, 1)
        self.assertEqual(m.current_box, m.split_boxes[1])

        # Move active box (box2 at [4, 4]) up -> moves to [3, 4]
        ctrl.move_up()
        self.assertEqual(m.split_boxes[1].location, [[3, 4]])
        self.assertEqual(m.split_boxes[0].location, [[2, 3]])

    # 7. Merge split blocks (Ghép khối)
    def test_merge_split_blocks(self):
        custom = deepcopy(self.base_level)
        custom["swO"] = {
            "count": 1,
            "symbol": ["o1"],
            "o1": {
                "split": True,
                "location": [1, 4],
                "box1": {"symbol": "#1", "state": 1, "location": [[2, 2]]},
                "box2": {"symbol": "#2", "state": 1, "location": [[2, 4]]}
            }
        }
        m = self._create_map(custom)
        ctrl = Control(m)
        ctrl.move_right()
        ctrl.move_right() # Split
        self.assertTrue(m.is_split)

        # Box1 is at [2, 2], Box2 is at [2, 4]. Active is Box1.
        # Move Box1 right -> lands at [2, 3], adjacent to Box2 at [2, 4]!
        ctrl.move_right()
        # Should automatically merge!
        self.assertFalse(m.is_split, "Blocks should automatically merge when adjacent!")
        self.assertTrue(m.current_box.is_doubleBox())
        self.assertTrue(m.current_box.is_horizontal())
        self.assertEqual(sorted(m.current_box.location), [[2, 3], [2, 4]])

    # 8. Bridge activation: Toggle vs Permanent
    def test_bridge_activation_toggle_and_permanent(self):
        # Bridge 1 toggle mode, Bridge 2 permanent mode
        custom = deepcopy(self.base_level)
        custom["bridge"] = {
            "count": 2,
            "symbol": ["b_tog", "b_perm"],
            "b_tog": {"active": False, "location": [[3, 1]], "mode": "toggle"},
            "b_perm": {"active": False, "location": [[3, 2]], "mode": "permanent"}
        }
        custom["swQ"] = {
            "count": 2,
            "symbol": ["q_tog", "q_perm"],
            "q_tog": {"type": 0, "active": False, "location": [1, 2], "bridge": "b_tog"},
            "q_perm": {"type": 1, "active": False, "location": [1, 3], "bridge": "b_perm"}
        }
        m = self._create_map(custom)
        b_tog = m.Brid[0]
        b_perm = m.Brid[1]
        self.assertFalse(b_tog.active)
        self.assertFalse(b_perm.active)

        # Trigger toggle switch 1st time -> b_tog becomes True
        m.swQ[0].change_active()
        self.assertTrue(b_tog.active)
        # Trigger toggle switch 2nd time -> b_tog toggles back to False
        m.swQ[0].change_active()
        self.assertFalse(b_tog.active)

        # Trigger permanent switch 1st time -> b_perm becomes True
        m.swQ[1].change_active()
        self.assertTrue(b_perm.active)
        # Trigger permanent switch 2nd time -> b_perm MUST STAY True!
        m.swQ[1].change_active()
        self.assertTrue(b_perm.active, "Permanent bridge must not toggle back off!")

    # 9. Single box cannot win
    def test_single_box_cannot_win(self):
        custom = deepcopy(self.base_level)
        custom["end"] = [1, 8]
        m = self._create_map(custom)
        # Place single box on goal
        m.current_box = Box("#1", 1, [[1, 8]])
        self.assertFalse(m.check_goal(), "Single box must not be able to complete the level!")

    # 10. Level 16 Full Integration (Split, Coop Switches, Merge, Heavy Switch, Fragile, Win)
    def test_level_16_full_walkthrough(self):
        m = maps("level/16_split_coop.json")
        ctrl = Control(m)

        # Move to swO and split
        self.assertTrue(ctrl.move_right())
        self.assertTrue(ctrl.move_right())
        self.assertTrue(m.is_split)

        # Box 1 opens bridge c2
        self.assertTrue(ctrl.move_right())
        self.assertTrue(m.Brid[1].active)

        # Switch to Box 2, opens bridge c1, advances to [5, 5]
        self.assertTrue(ctrl.switch_box())
        self.assertTrue(ctrl.move_right())
        self.assertTrue(m.Brid[0].active)
        self.assertTrue(ctrl.move_right())
        self.assertTrue(ctrl.move_right())
        self.assertTrue(ctrl.move_right())

        # Switch to Box 1, advances to [3, 5]
        self.assertTrue(ctrl.switch_box())
        self.assertTrue(ctrl.move_right())
        self.assertTrue(ctrl.move_right())
        self.assertTrue(ctrl.move_right())

        # Box 1 moves down to [4, 5] -> merges with Box 2!
        self.assertTrue(ctrl.move_down())
        self.assertFalse(m.is_split)
        self.assertTrue(m.current_box.is_doubleBox())

        # Merged moves:
        self.assertTrue(ctrl.move_up())
        self.assertTrue(ctrl.move_right())
        self.assertTrue(ctrl.move_right()) # Stands on swX
        self.assertTrue(m.Brid[2].active)  # Bridge c3 opened permanently

        self.assertTrue(ctrl.move_right()) # Lies across fragile tile [4, 9] + bridge c3 [4, 10]
        self.assertTrue(ctrl.move_right()) # Stands on [4, 11]
        self.assertTrue(ctrl.move_down())
        self.assertTrue(ctrl.move_right())
        self.assertTrue(ctrl.move_up())    # Stands on Goal [4, 12]!

        self.assertTrue(ctrl.check_goal())

    # 11. Level 17 Full Integration (Soft Switch, Toggle Bridge, Fragile Orange, Heavy Switch, BFS & A* Solvers)
    def test_level_17_full_walkthrough(self):
        from model.solver import bfs_path, astar
        m = maps("level/17_fragile_bridges.json")
        ctrl = Control(m)

        self.assertTrue(ctrl.move_up())    # [2, 1], [1, 1] -> touches swQ at [2, 1]
        self.assertTrue(m.Brid[0].active)  # bridge c1 opened
        self.assertTrue(ctrl.move_right()) # [2, 2], [1, 2]
        self.assertTrue(ctrl.move_right()) # [2, 3], [1, 3] (across bridge c1!)
        self.assertTrue(ctrl.move_right()) # [2, 4], [1, 4]
        self.assertTrue(ctrl.move_right()) # [2, 5], [1, 5]
        self.assertTrue(ctrl.move_right()) # [2, 6], [1, 6]
        self.assertTrue(ctrl.move_right()) # [2, 7], [1, 7]
        self.assertTrue(ctrl.move_up())    # Stands on [0, 7]
        self.assertTrue(ctrl.move_right()) # Lies across orange fragile tiles [0, 8], [0, 9]!
        self.assertTrue(ctrl.move_right()) # Stands upright on swX [0, 10]
        self.assertTrue(m.Brid[1].active)  # Bridge c2 opened permanently
        self.assertTrue(ctrl.move_right()) # Across bridge c2
        self.assertTrue(ctrl.move_down())
        self.assertTrue(ctrl.move_down())
        self.assertTrue(ctrl.move_left())  # Stands on Goal [2, 10]!
        self.assertTrue(ctrl.check_goal())

        # Also verify automated search algorithms solve Level 17
        bfs_ctrl = Control(maps("level/17_fragile_bridges.json"))
        bfs_solution, _ = bfs_path(bfs_ctrl)
        self.assertIsNotNone(bfs_solution)
        self.assertEqual(len(bfs_solution), 15)

        astar_ctrl = Control(maps("level/17_fragile_bridges.json"))
        astar_solution, _ = astar(astar_ctrl)
        self.assertIsNotNone(astar_solution)
        self.assertEqual(len(astar_solution), 15)

if __name__ == '__main__':
    unittest.main()

