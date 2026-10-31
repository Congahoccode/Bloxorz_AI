import pygame
import os
import sys
from model.map import maps

# Color Palette
C_BG = (18, 22, 32)
C_PANEL = (28, 34, 48)
C_PANEL_LIGHT = (35, 42, 60)
C_BORDER = (48, 58, 80)
C_BORDER_ACCENT = (14, 165, 233)
C_TEXT = (245, 248, 252)
C_TEXT_MUTED = (145, 155, 175)
C_TEXT_DIM = (95, 105, 125)
C_BLUE = (14, 165, 233)
C_CYAN = (6, 182, 212)
C_GREEN = (16, 185, 129)
C_GREEN_HOVER = (20, 205, 145)
C_ORANGE = (249, 115, 22)
C_PURPLE = (168, 85, 247)
C_RED = (239, 68, 68)
C_BTN_DEFAULT = (38, 46, 64)
C_BTN_HOVER = (50, 60, 84)


class Button:
    def __init__(self, rect, text, subtext="", badge="", callback_data=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.subtext = subtext
        self.badge = badge
        self.callback_data = callback_data
        self.selected = False
        self.active_color = C_BLUE

    def draw(self, surface, mouse_pos, font_main, font_sub=None, font_badge=None):
        is_hover = self.rect.collidepoint(mouse_pos)

        # Background color
        if self.selected:
            bg_col = self.active_color
            border_col = (255, 255, 255)
            text_col = (255, 255, 255)
        elif is_hover:
            bg_col = C_BTN_HOVER
            border_col = C_BLUE
            text_col = C_TEXT
        else:
            bg_col = C_BTN_DEFAULT
            border_col = C_BORDER
            text_col = C_TEXT_MUTED

        pygame.draw.rect(surface, bg_col, self.rect, border_radius=6)
        pygame.draw.rect(surface, border_col, self.rect, width=1, border_radius=6)

        # Main text
        if self.subtext:
            text_surf = font_main.render(self.text, True, text_col)
            surface.blit(text_surf, (self.rect.x + 10, self.rect.y + 6))
            if font_sub:
                sub_col = (220, 220, 220) if self.selected else C_TEXT_DIM
                sub_surf = font_sub.render(self.subtext, True, sub_col)
                surface.blit(sub_surf, (self.rect.x + 10, self.rect.y + 24))
        else:
            text_surf = font_main.render(self.text, True, text_col)
            text_rect = text_surf.get_rect(center=self.rect.center)
            surface.blit(text_surf, text_rect)

        # Badge
        if self.badge and font_badge:
            badge_surf = font_badge.render(self.badge, True, C_ORANGE if not self.selected else (255, 255, 255))
            b_rect = badge_surf.get_rect(topright=(self.rect.right - 8, self.rect.y + 6))
            surface.blit(badge_surf, b_rect)

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


class GuiMenu:
    def __init__(self, size=(980, 680)):
        self.size = size
        self.screen = None
        self.clock = pygame.time.Clock()
        self.running = True

        # Fonts
        self._init_fonts()

        # Levels available
        self.level_files = self._load_level_files()
        self.selected_level_idx = 0
        self.selected_mode = 0  # 0: Play, 1: AI Solver, 2: Benchmark
        self.selected_algo = 'bfs'
        # Cached level info
        self.level_info_cache = {}

        # Build UI Elements
        self._init_buttons()

    def _init_fonts(self):
        pygame.font.init()
        self.font_title = pygame.font.SysFont('Arial', 28, bold=True)
        self.font_section = pygame.font.SysFont('Arial', 18, bold=True)
        self.font_btn = pygame.font.SysFont('Arial', 15, bold=True)
        self.font_sub = pygame.font.SysFont('Arial', 12)
        self.font_badge = pygame.font.SysFont('Arial', 11, bold=True)
        self.font_info = pygame.font.SysFont('Arial', 14)

    def _load_level_files(self):
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

    def _get_level_info(self, path):
        if path in self.level_info_cache:
            return self.level_info_cache[path]
        try:
            m = maps(path)
            orange_count = sum(row.count(2) for row in m.jsonObj.get("maps", []))
            info = {
                'name': m.level,
                'size': m.size,
                'start': m.start,
                'end': m.end,
                'swQ': len(m.swQ),
                'swX': len(m.swX),
                'swO': len(m.swO),
                'bridge': len(m.Brid),
                'orange': orange_count
            }
        except Exception:
            info = {'name': 'Unknown', 'size': [0, 0], 'start': [0, 0], 'end': [0, 0], 'swQ': 0, 'swX': 0, 'swO': 0, 'bridge': 0, 'orange': 0}
        self.level_info_cache[path] = info
        return info

    def _init_buttons(self):
        # 1. Mode buttons (Left top) - Clean, simple names, no subtitles
        self.btn_modes = [
            Button((40, 110, 115, 38), "Play", callback_data=0),
            Button((162, 110, 120, 38), "AI Solver", callback_data=1),
            Button((290, 110, 110, 38), "Benchmark", callback_data=2)
        ]
        self.btn_modes[1].selected = True
        self.selected_mode = 1

        # 2. Algorithm buttons: 4 core algorithms (BFS, DFS, UCS, A*)
        self.btn_algos = [
            Button((40, 190, 360, 36), "BFS", callback_data='bfs'),
            Button((40, 232, 360, 36), "DFS", callback_data='dfs'),
            Button((40, 274, 360, 36), "UCS", callback_data='ucs'),
            Button((40, 316, 360, 36), "A* Search", callback_data='astar')
        ]
        self.btn_algos[0].selected = True

        # Action buttons (prominently placed in the launch panel)
        self.btn_start = Button((445, 575, 330, 54), "START", "")
        self.btn_start.active_color = C_GREEN
        self.btn_start.selected = True

        self.btn_exit = Button((790, 575, 150, 54), "EXIT", "")

        # 5. Level grid buttons (Right column) - Clean names, no tags, auto-fit rows
        self.btn_levels = []
        n_lvls = len(self.level_files)
        cols = 4 if n_lvls <= 24 else 5
        btn_w = 118 if cols == 4 else 93
        btn_h = 31 if n_lvls <= 24 else 28
        gap_x = 8 if cols == 4 else 7
        gap_y = 6 if n_lvls <= 24 else 5
        start_x = 445
        start_y = 110

        for i, lp in enumerate(self.level_files):
            r = i // cols
            c = i % cols
            bx = start_x + c * (btn_w + gap_x)
            by = start_y + r * (btn_h + gap_y)

            bname = os.path.basename(lp).replace(".json", "")
            if bname.isdigit():
                display_name = f"Level {bname}"
            else:
                clean_name = bname.replace("level_", "").replace("_", " ").title()
                display_name = f"Level {clean_name[:8]}"

            btn = Button((bx, by, btn_w, btn_h), display_name, callback_data=i)
            self.btn_levels.append(btn)

        num_rows = (n_lvls + cols - 1) // cols if n_lvls > 0 else 1
        self.level_grid_bottom = start_y + num_rows * (btn_h + gap_y) - gap_y

        if self.btn_levels:
            self.btn_levels[0].selected = True

    def draw(self, surface):
        surface.fill(C_BG)
        mouse_pos = pygame.mouse.get_pos()

        # Top Header Bar - Clean title, no subtitle, no icons
        pygame.draw.rect(surface, C_PANEL, (0, 0, self.size[0], 65))
        pygame.draw.line(surface, C_BORDER, (0, 65), (self.size[0], 65), 1)

        title_surf = self.font_title.render("BLOXORZ", True, C_TEXT)
        surface.blit(title_surf, (40, 16))

        # Left Container Panel
        pygame.draw.rect(surface, C_PANEL, (25, 75, 390, 580), border_radius=8)
        pygame.draw.rect(surface, C_BORDER, (25, 75, 390, 580), width=1, border_radius=8)

        # Section 1: Mode
        sec1_surf = self.font_section.render("GAME MODE", True, C_CYAN)
        surface.blit(sec1_surf, (40, 85))
        for btn in self.btn_modes:
            btn.draw(surface, mouse_pos, self.font_btn)

        # Section 2: Algorithm (only active in AI Solver mode)
        if self.selected_mode in [1, 2]:
            sec2_title = "SEARCH ALGORITHM" if self.selected_mode == 1 else "BENCHMARK ALGORITHMS"
            sec2_surf = self.font_section.render(sec2_title, True, C_CYAN)
            surface.blit(sec2_surf, (40, 162))
            for btn in self.btn_algos:
                btn.draw(surface, mouse_pos, self.font_btn)

        # Section 3: Guide & Controls Panel
        if self.selected_mode == 1:
            info_box = pygame.Rect(40, 390, 360, 245)
            pygame.draw.rect(surface, C_PANEL_LIGHT, info_box, border_radius=6)
            pygame.draw.rect(surface, C_BORDER, info_box, width=1, border_radius=6)
            txts = [
                ("3D CAMERA CONTROLS", C_CYAN),
                ("- Left-drag: Orbit camera 360 deg", C_TEXT),
                ("- Mouse wheel: Zoom In / Out", C_TEXT_MUTED),
                ("- Right-drag: Pan target view", C_TEXT_MUTED),
                ("- Keys 1, 2, 3, 4: Preset view angles", C_TEXT_MUTED),
                ("- Key C: Reset camera | Key H: Toggle sidebar", C_TEXT_MUTED),
                ("", C_TEXT),
                ("REPLAY CONTROLS", C_CYAN),
                ("- Space: Start / Pause / Resume replay", C_TEXT),
                ("- Left / Right: Step backward / forward", C_TEXT_MUTED),
                ("- Key R: Reset replay to beginning", C_TEXT_MUTED),
                ("- Key +/-: Increase / decrease speed", C_TEXT_MUTED),
                ("- Key ESC: Exit replay to Menu", C_ORANGE)
            ]
            iy = 400
            for t, col in txts:
                if t:
                    ts = self.font_info.render(t, True, col)
                    surface.blit(ts, (52, iy))
                iy += 17
        elif self.selected_mode == 0:
            # Info box for human play
            info_box = pygame.Rect(40, 175, 360, 460)
            pygame.draw.rect(surface, C_PANEL_LIGHT, info_box, border_radius=6)
            pygame.draw.rect(surface, C_BORDER, info_box, width=1, border_radius=6)

            txts = [
                ("HOW TO PLAY", C_CYAN),
                ("- Arrow Keys: Roll block (U/D/L/R)", C_TEXT),
                ("- SPACE: Switch active block when split", C_TEXT),
                ("- Orange tiles: Fragile (stand upright = fall)", C_TEXT_MUTED),
                ("- Heavy switch (swX): Stand upright to trigger", C_TEXT_MUTED),
                ("- Soft switch (swQ): Any contact triggers", C_TEXT_MUTED),
                ("- Bridges: Open/close by linked switches", C_TEXT_MUTED),
                ("- Key R: Restart level from beginning", C_TEXT_MUTED),
                ("- Key ESC: Return to Menu", C_ORANGE),
                ("", C_TEXT),
                ("3D CAMERA CONTROLS", C_CYAN),
                ("- Left-drag: Orbit camera 360 deg", C_TEXT_MUTED),
                ("- Mouse wheel: Zoom In / Out", C_TEXT_MUTED),
                ("- Right-drag: Pan camera target", C_TEXT_MUTED),
                ("- Keys 1, 2, 3, 4: Preset view angles", C_TEXT_MUTED),
                ("- Key C: Reset camera | Key H: Toggle sidebar", C_TEXT_MUTED),
            ]
            iy = 190
            for t, col in txts:
                if t:
                    ts = self.font_info.render(t, True, col)
                    surface.blit(ts, (52, iy))
                iy += 21
        elif self.selected_mode == 2:
            # Info box for Benchmark
            info_box = pygame.Rect(40, 390, 360, 245)
            pygame.draw.rect(surface, C_PANEL_LIGHT, info_box, border_radius=6)
            pygame.draw.rect(surface, C_BORDER, info_box, width=1, border_radius=6)
            txts = [
                ("BENCHMARK ALGORITHMS", C_CYAN),
                ("- Runs BFS, DFS, UCS, A* Search", C_TEXT),
                ("- Measures execution time (wall-clock)", C_TEXT_MUTED),
                ("- Measures peak memory usage (tracemalloc)", C_TEXT_MUTED),
                ("- Counts explored states & solution steps", C_TEXT_MUTED),
                ("- Displays interactive comparison table", C_TEXT_MUTED),
                ("- Click any row to view full move sequence", C_TEXT_MUTED),
            ]
            iy = 410
            for t, col in txts:
                ts = self.font_info.render(t, True, col)
                surface.blit(ts, (52, iy))
                iy += 24

        # Right Container Panel (Levels & Launch Setup)
        pygame.draw.rect(surface, C_PANEL, (430, 75, 525, 580), border_radius=8)
        pygame.draw.rect(surface, C_BORDER, (430, 75, 525, 580), width=1, border_radius=8)

        # Level Grid Title
        lvl_title = self.font_section.render(f"SELECT LEVEL ({len(self.level_files)} LEVELS)", True, C_CYAN)
        surface.blit(lvl_title, (445, 85))

        # Draw Level Buttons
        for btn in self.btn_levels:
            btn.draw(surface, mouse_pos, self.font_btn)

        # Launch Setup Card
        card_top = max(290, getattr(self, 'level_grid_bottom', 260) + 14)
        card_h = max(160, 558 - card_top)
        card_rect = pygame.Rect(445, card_top, 495, card_h)
        pygame.draw.rect(surface, C_PANEL_LIGHT, card_rect, border_radius=8)
        pygame.draw.rect(surface, C_BORDER, card_rect, width=1, border_radius=8)

        card_title = self.font_section.render("SETUP & LAUNCH", True, C_TEXT)
        surface.blit(card_title, (465, card_top + 14))

        cur_path = self.level_files[self.selected_level_idx] if (0 <= self.selected_level_idx < len(self.level_files)) else ""
        lvl_bname = os.path.basename(cur_path) if cur_path else "None"
        lvl_disp_name = lvl_bname.replace(".json", "")
        if lvl_disp_name.isdigit():
            lvl_disp_name = f"Level {lvl_disp_name}"

        mode_names = {0: "Manual Play (Keyboard)", 1: "AI Solver (Search & 3D Replay)", 2: "Algorithm Benchmark"}
        algo_names = {
            'bfs': 'BFS (Breadth-First Search)',
            'dfs': 'DFS (Depth-First Search)',
            'ucs': 'UCS (Uniform Cost Search)',
            'astar': 'A* Search'
        }

        setup_details = [
            f"- Mode: {mode_names.get(self.selected_mode, 'Unknown')}",
            f"- Level: {lvl_disp_name}",
        ]
        if self.selected_mode in [1, 2]:
            setup_details.append(f"- Algorithm: {algo_names.get(self.selected_algo, self.selected_algo.upper())}")

        setup_details.append("")
        setup_details.append("Click START to launch the game.")

        dy = card_top + 48
        step_y = 26 if card_h >= 210 else 22
        for d in setup_details:
            if d:
                is_key = d.startswith("- ")
                col = C_TEXT if is_key else C_TEXT_MUTED
                font_to_use = self.font_btn if is_key else self.font_info
                dsurf = font_to_use.render(d, True, col)
                surface.blit(dsurf, (465, dy))
            dy += step_y

        # Action Buttons (Start / Exit) - located right under the setup card
        self.btn_start.draw(surface, mouse_pos, self.font_btn)
        self.btn_exit.draw(surface, mouse_pos, self.font_btn)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return {'action': 'exit'}

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return {'action': 'exit'}

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Mode selection
            for btn in self.btn_modes:
                if btn.rect.collidepoint(event.pos):
                    for b in self.btn_modes:
                        b.selected = False
                    btn.selected = True
                    self.selected_mode = btn.callback_data

            # Algorithm selection
            for btn in self.btn_algos:
                if btn.rect.collidepoint(event.pos):
                    for b in self.btn_algos:
                        b.selected = False
                    btn.selected = True
                    self.selected_algo = btn.callback_data

            # Level selection
            for btn in self.btn_levels:
                if btn.rect.collidepoint(event.pos):
                    for b in self.btn_levels:
                        b.selected = False
                    btn.selected = True
                    self.selected_level_idx = btn.callback_data

            # Exit button
            if self.btn_exit.rect.collidepoint(event.pos):
                return {'action': 'exit'}

            # Start button
            if self.btn_start.rect.collidepoint(event.pos):
                level_path = self.level_files[self.selected_level_idx]
                if self.selected_mode == 0:
                    return {'action': 'start', 'mode': 'play', 'level': level_path}
                elif self.selected_mode == 1:
                    return {
                        'action': 'start',
                        'mode': 'solve',
                        'level': level_path,
                        'algo': self.selected_algo,
                        'view': '3'
                    }
                elif self.selected_mode == 2:
                    return {'action': 'start', 'mode': 'benchmark', 'level': level_path}

        return None

    def show_benchmark_window(self, results, level_path):
        """Display an on-screen visual modal table showing benchmark metrics and full move view."""
        # Enlarge window for benchmark
        bm_size = (1100, 750)
        self.screen = pygame.display.set_mode(bm_size)
        pygame.display.set_caption("Bloxorz AI - Benchmark Results")

        btn_back = Button((bm_size[0] - 210, bm_size[1] - 56, 175, 42), "< Back to Menu", "")
        btn_back.selected = True
        btn_back.active_color = C_BLUE

        # Fonts for benchmark (enlarged and clear)
        font_head = pygame.font.SysFont('Arial', 15, bold=True)
        font_data = pygame.font.SysFont('Arial', 14)
        font_data_bold = pygame.font.SysFont('Arial', 14, bold=True)
        font_moves = pygame.font.SysFont('Consolas', 12)
        if not font_moves:
            font_moves = pygame.font.SysFont('monospace', 12)
        font_annot = pygame.font.SysFont('Arial', 13)

        # Scroll state for the moves detail panel
        selected_row = -1  # -1 means no row expanded
        moves_scroll_y = 0

        # Layout metrics
        table_top = 70
        header_h = 36
        sep_y = table_top + header_h
        row_start_y = sep_y + 8
        row_step = 52
        table_h = header_h + len(results) * row_step + 10
        table_h = max(table_h, 240)

        detail_top = table_top + table_h + 14
        detail_h = bm_size[1] - detail_top - 68

        columns = [
            {"title": "Algorithm",     "w": 140, "align": "left"},
            {"title": "Status",        "w": 105, "align": "left"},
            {"title": "Steps",         "w": 85,  "align": "right"},
            {"title": "Expanded",      "w": 110, "align": "right"},
            {"title": "Time",          "w": 125, "align": "right"},
            {"title": "Peak RAM",      "w": 125, "align": "right"},
            {"title": "Move Sequence", "w": 310, "align": "left"},
        ]

        modal_running = True
        while modal_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    modal_running = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_back.rect.collidepoint(event.pos):
                        modal_running = False
                    # Check row click with exact hit-test
                    for idx in range(len(results)):
                        row_rect = pygame.Rect(35, row_start_y + idx * row_step - 3, bm_size[0] - 70, row_step - 6)
                        if row_rect.collidepoint(event.pos):
                            if selected_row == idx:
                                selected_row = -1
                            else:
                                selected_row = idx
                                moves_scroll_y = 0
                            break
                # Scroll inside moves detail panel
                if event.type == pygame.MOUSEWHEEL and selected_row >= 0:
                    moves_scroll_y = max(0, moves_scroll_y - event.y * 18)

            mouse_pos = pygame.mouse.get_pos()
            self.screen.fill(C_BG)

            # Title
            t_surf = self.font_title.render("BENCHMARK PERFORMANCE RESULTS", True, C_TEXT)
            self.screen.blit(t_surf, (bm_size[0] // 2 - t_surf.get_width() // 2, 14))

            lvl_name = os.path.basename(level_path)
            sub_surf = self.font_sub.render(f"Level: {lvl_name}   |   File: {level_path}", True, C_CYAN)
            self.screen.blit(sub_surf, (bm_size[0] // 2 - sub_surf.get_width() // 2, 44))

            # Table Container
            tbl_rect = pygame.Rect(30, table_top, bm_size[0] - 60, table_h)
            pygame.draw.rect(self.screen, C_PANEL, tbl_rect, border_radius=8)
            pygame.draw.rect(self.screen, C_BORDER, tbl_rect, width=1, border_radius=8)

            # Header row
            hx = 50
            for col in columns:
                hs = font_head.render(col["title"], True, C_CYAN)
                if col["align"] == "right":
                    self.screen.blit(hs, (hx + col["w"] - hs.get_width() - 8, table_top + 10))
                else:
                    self.screen.blit(hs, (hx, table_top + 10))
                hx += col["w"]

            # Header separator
            pygame.draw.line(self.screen, C_BORDER, (40, sep_y), (bm_size[0] - 40, sep_y), 1)

            # Data rows
            best_time = min((r['time_sec'] for r in results if r['solved']), default=None)
            best_steps = min((r['moves_count'] for r in results if r['solved']), default=None)
            best_mem = min((r['peak_mem_kb'] for r in results if r['solved']), default=None)

            for idx, r in enumerate(results):
                ry = row_start_y + idx * row_step
                row_rect = pygame.Rect(35, ry - 3, bm_size[0] - 70, row_step - 6)
                is_hover = row_rect.collidepoint(mouse_pos)
                is_sel = (selected_row == idx)

                if is_sel:
                    pygame.draw.rect(self.screen, (28, 45, 70), row_rect, border_radius=4)
                    pygame.draw.rect(self.screen, C_BORDER_ACCENT, row_rect, width=1, border_radius=4)
                elif is_hover:
                    pygame.draw.rect(self.screen, (25, 32, 50), row_rect, border_radius=4)

                rx = 50
                # 1. Algorithm name
                algo_surf = font_data_bold.render(r['algorithm'], True, C_TEXT)
                self.screen.blit(algo_surf, (rx, ry + 12))
                rx += columns[0]["w"]

                # 2. Status
                st_col = C_GREEN if r['solved'] else C_RED
                st_txt = "Success" if r['solved'] else "Failed"
                self.screen.blit(font_data_bold.render(st_txt, True, st_col), (rx, ry + 12))
                rx += columns[1]["w"]

                # 3. Steps (right-aligned)
                steps_str = str(r['moves_count']) if r['solved'] else "-"
                steps_col = C_GREEN if (r['solved'] and best_steps is not None and r['moves_count'] == best_steps) else C_TEXT
                ss = font_data.render(steps_str, True, steps_col)
                self.screen.blit(ss, (rx + columns[2]["w"] - ss.get_width() - 8, ry + 12))
                rx += columns[2]["w"]

                # 4. Expanded states (right-aligned)
                vis_str = f"{r['visited']:,}"
                vs = font_data.render(vis_str, True, C_TEXT_MUTED)
                self.screen.blit(vs, (rx + columns[3]["w"] - vs.get_width() - 8, ry + 12))
                rx += columns[3]["w"]

                # 5. Time (right-aligned, highlight best)
                time_str = f"{r['time_sec']:.5f} s"
                time_col = C_GREEN if (r['solved'] and best_time is not None and r['time_sec'] == best_time) else C_CYAN
                ts = font_data.render(time_str, True, time_col)
                self.screen.blit(ts, (rx + columns[4]["w"] - ts.get_width() - 8, ry + 12))
                rx += columns[4]["w"]

                # 6. Peak memory (right-aligned, highlight best)
                mem_str = f"{r['peak_mem_kb']:.1f} KB"
                mem_col = C_GREEN if (r['solved'] and best_mem is not None and r['peak_mem_kb'] == best_mem) else C_ORANGE
                ms = font_data.render(mem_str, True, mem_col)
                self.screen.blit(ms, (rx + columns[5]["w"] - ms.get_width() - 8, ry + 12))
                rx += columns[5]["w"]

                # 7. Moves preview
                if r['solved']:
                    full_moves = r['moves_str']
                    max_preview = 36
                    preview = (full_moves[:max_preview] + "...") if len(full_moves) > max_preview else full_moves
                    m_col = (200, 220, 255) if is_sel else C_TEXT_MUTED
                    self.screen.blit(font_moves.render(preview, True, m_col), (rx, ry + 12))
                else:
                    self.screen.blit(font_data.render("-", True, C_TEXT_DIM), (rx, ry + 12))

                # Row separator
                pygame.draw.line(self.screen, (32, 40, 56), (40, ry + row_step - 5), (bm_size[0] - 40, ry + row_step - 5), 1)

            # Expanded moves detail panel
            detail_rect = pygame.Rect(30, detail_top, bm_size[0] - 60, detail_h)
            pygame.draw.rect(self.screen, C_PANEL, detail_rect, border_radius=8)
            pygame.draw.rect(self.screen, C_BORDER, detail_rect, width=1, border_radius=8)

            if selected_row >= 0 and selected_row < len(results):
                sr = results[selected_row]
                dt_title = font_head.render(
                    f"FULL MOVE SEQUENCE - {sr['algorithm']}  ({sr['moves_count']} moves)",
                    True, C_CYAN
                )
                self.screen.blit(dt_title, (45, detail_top + 10))

                if sr['solved']:
                    full_text = sr['moves_str']
                    chars_per_line = 105
                    wrapped = []
                    for i in range(0, len(full_text), chars_per_line):
                        wrapped.append(full_text[i:i + chars_per_line])

                    clip_rect = pygame.Rect(38, detail_top + 34, bm_size[0] - 76, detail_h - 44)
                    self.screen.set_clip(clip_rect)
                    ty = detail_top + 36 - moves_scroll_y
                    line_h = 18
                    for line_text in wrapped:
                        if ty + line_h > detail_top + 30 and ty < detail_top + detail_h - 6:
                            self.screen.blit(font_moves.render(line_text, True, C_TEXT), (45, ty))
                        ty += line_h
                    max_scroll = max(0, len(wrapped) * line_h - (detail_h - 44))
                    if moves_scroll_y > max_scroll:
                        moves_scroll_y = max_scroll
                    self.screen.set_clip(None)

                    if max_scroll > 0:
                        bar_h = max(14, int((detail_h - 44) * (detail_h - 44) / (len(wrapped) * line_h)))
                        bar_y = detail_top + 34 + int((detail_h - 44 - bar_h) * moves_scroll_y / max_scroll)
                        bar_rect = pygame.Rect(bm_size[0] - 48, bar_y, 6, bar_h)
                        pygame.draw.rect(self.screen, C_BORDER_ACCENT, bar_rect, border_radius=3)
                else:
                    no_sol = font_data.render("The algorithm could not find a solution for this level.", True, C_RED)
                    self.screen.blit(no_sol, (45, detail_top + 36))
            else:
                hint_surf = font_data.render("Click any row in the table to view the full move sequence", True, C_TEXT_DIM)
                self.screen.blit(hint_surf, (bm_size[0] // 2 - hint_surf.get_width() // 2, detail_top + detail_h // 2 - 8))

            # Legend bar (bottom left)
            legend_y = bm_size[1] - 44
            legend_items = [
                (C_GREEN, "Best metric"),
                (C_CYAN, "Search Time"),
                (C_ORANGE, "Peak Memory"),
            ]
            lx = 45
            for color, label in legend_items:
                pygame.draw.rect(self.screen, color, pygame.Rect(lx, legend_y + 3, 12, 12), border_radius=2)
                lab_s = font_annot.render(label, True, C_TEXT_DIM)
                self.screen.blit(lab_s, (lx + 18, legend_y))
                lx += 18 + lab_s.get_width() + 24

            # Back button (bottom right)
            btn_back.draw(self.screen, mouse_pos, self.font_btn)
            pygame.display.flip()
            self.clock.tick(30)

        # Restore original window size
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption("Bloxorz AI - Menu Launcher")

    def run(self):
        """Main loop of the GUI menu."""
        pygame.init()
        self._init_fonts()
        self.screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption("Bloxorz AI - Menu Launcher")
        self.clock = pygame.time.Clock()
        self.running = True

        while self.running:
            for event in pygame.event.get():
                action = self.handle_event(event)
                if action:
                    return action

            self.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(60)

        return {'action': 'exit'}
