import pygame
import time
import math
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *


class Display:
    # Sidebar width constant
    SIDEBAR_W = 260

    def __init__(self, title='', size=(800, 600), map_size=(10, 6)):
        self.size = size
        self.title = title
        self.delta = 0
        self.currentFrame = self.get_time()
        self.lastFrame = self.get_time()

        self.surface = pygame.display.set_mode(self.size, DOUBLEBUF | OPENGL)
        pygame.display.set_caption(self.title)

        glClearColor(0.08, 0.09, 0.12, 1.0)

        # Board dimensions in grid units
        dim0 = map_size[0] if map_size[0] > 0 else 6
        dim1 = map_size[1] if map_size[1] > 0 else 10
        self.rows = dim0
        self.cols = dim1

        # Center of board in world space (X: 0 to cols, Y: 0 to -rows, Z: 0.5)
        self.target = [self.cols / 2.0, -self.rows / 2.0, 0.5]
        self.initial_target = list(self.target)

        # 3D Orbit Camera parameters
        self.distance = max(self.cols, self.rows) * 1.5 + 4.0
        self.initial_distance = self.distance
        self.yaw = -30.0    # Azimuth angle in degrees (horizontal orbit)
        self.pitch = 45.0   # Elevation angle in degrees (vertical orbit)
        self.initial_yaw = self.yaw
        self.initial_pitch = self.pitch
        self.fov = 60.0

        # Mouse interaction state
        self.is_dragging = False
        self.drag_button = None
        self.last_mouse_pos = (0, 0)

        # Sidebar state
        self.sidebar_visible = True

        # HUD fonts (lazy init)
        self._fonts_initialized = False
        self._font_title = None
        self._font_label = None
        self._font_value = None
        self._font_small = None
        self._font_key = None

        # OpenGL Render states
        glEnable(GL_POLYGON_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glLineWidth(2)
        glDepthFunc(GL_LESS)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_COLOR_MATERIAL)

        self.setup_camera()

    def _init_fonts(self):
        if self._fonts_initialized:
            return
        try:
            pygame.font.init()
            self._font_title = pygame.font.SysFont('Arial', 15, bold=True)
            self._font_label = pygame.font.SysFont('Arial', 11)
            self._font_value = pygame.font.SysFont('Arial', 13, bold=True)
            self._font_small = pygame.font.SysFont('Arial', 10)
            self._font_key = pygame.font.SysFont('Consolas', 10, bold=True)
            if not self._font_key:
                self._font_key = pygame.font.SysFont('monospace', 10, bold=True)
            self._fonts_initialized = True
        except Exception:
            pass

    def _get_viewport_rect(self):
        """Return the (x, y, w, h) for the 3D viewport area (excludes sidebar)."""
        sw, sh = self.size
        if self.sidebar_visible:
            return (0, 0, sw - self.SIDEBAR_W, sh)
        return (0, 0, sw, sh)

    def reset_camera(self):
        """Reset camera to initial default view."""
        self.target = list(self.initial_target)
        self.distance = self.initial_distance
        self.yaw = self.initial_yaw
        self.pitch = self.initial_pitch
        self.setup_camera()

    def setup_camera(self):
        """Set up 3D perspective projection and orbital camera view matrix."""
        vx, vy, vw, vh = self._get_viewport_rect()
        glViewport(vx, vy, vw, vh)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = vw / max(1, vh)
        gluPerspective(self.fov, aspect, 0.1, 120.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        rad_pitch = math.radians(self.pitch)
        rad_yaw = math.radians(self.yaw)

        # Eye position in spherical coordinates relative to target
        cam_x = self.target[0] + self.distance * math.cos(rad_pitch) * math.sin(rad_yaw)
        cam_y = self.target[1] - self.distance * math.cos(rad_pitch) * math.cos(rad_yaw)
        cam_z = self.target[2] + self.distance * math.sin(rad_pitch)

        up_z = 1.0 if math.cos(rad_pitch) >= 0 else -1.0
        gluLookAt(
            cam_x, cam_y, cam_z,
            self.target[0], self.target[1], self.target[2],
            0, 0, up_z
        )

    def handle_camera_event(self, event):
        """Handle 3D camera controls: mouse drag orbit 360 deg, mouse wheel zoom, view presets, rotation keys."""
        # Only handle mouse events inside the 3D viewport area
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION) and hasattr(event, 'pos'):
            vx, vy, vw, vh = self._get_viewport_rect()
            if event.pos[0] >= vw:
                return False

        # 1. Mouse wheel zoom
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # Wheel Up -> Zoom In
                self.distance = max(4.0, self.distance - 1.2)
                self.setup_camera()
                return True
            elif event.button == 5:  # Wheel Down -> Zoom Out
                self.distance = min(60.0, self.distance + 1.2)
                self.setup_camera()
                return True
            elif event.button in [1, 3]:  # Left or Right Click -> Start drag
                self.is_dragging = True
                self.drag_button = event.button
                self.last_mouse_pos = event.pos
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button in [1, 3]:
                self.is_dragging = False
                self.drag_button = None
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]
                self.last_mouse_pos = event.pos

                if self.drag_button == 1:
                    # Left click drag: Orbit around target (natural drag direction)
                    self.yaw -= dx * 0.4
                    if self.yaw > 180:
                        self.yaw -= 360
                    elif self.yaw < -180:
                        self.yaw += 360
                    # Pitch clamped between 5 and 85 degrees (drag up tilts up)
                    self.pitch = max(5.0, min(85.0, self.pitch - dy * 0.4))
                elif self.drag_button == 3:
                    # Right click drag: Pan target
                    self.target[0] += dx * 0.025
                    self.target[1] -= dy * 0.025

                self.setup_camera()
                return True

        elif event.type == pygame.MOUSEWHEEL:
            self.distance = max(4.0, min(60.0, self.distance - event.y * 1.5))
            self.setup_camera()
            return True

        # 2. Keyboard camera controls
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c:
                self.reset_camera()
                return True
            elif event.key == pygame.K_1:
                self.yaw, self.pitch = -30.0, 45.0
                self.setup_camera()
                return True
            elif event.key == pygame.K_2:
                self.yaw, self.pitch = 0.0, 85.0
                self.setup_camera()
                return True
            elif event.key == pygame.K_3:
                self.yaw, self.pitch = 0.0, 25.0
                self.setup_camera()
                return True
            elif event.key == pygame.K_4:
                self.yaw, self.pitch = 90.0, 35.0
                self.setup_camera()
                return True
            elif event.key in [pygame.K_j]:
                self.yaw += 8.0
                if self.yaw > 180:
                    self.yaw -= 360
                self.setup_camera()
                return True
            elif event.key in [pygame.K_l]:
                self.yaw -= 8.0
                if self.yaw < -180:
                    self.yaw += 360
                self.setup_camera()
                return True
            elif event.key in [pygame.K_i]:
                self.pitch = min(85.0, self.pitch + 5.0)
                self.setup_camera()
                return True
            elif event.key in [pygame.K_k]:
                self.pitch = max(5.0, self.pitch - 5.0)
                self.setup_camera()
                return True
            elif event.key == pygame.K_h:
                # Toggle sidebar visibility
                self.sidebar_visible = not self.sidebar_visible
                self.setup_camera()
                return True

        return False

    def update(self):
        self.delta = self.currentFrame - self.lastFrame
        pygame.display.flip()
        self.lastFrame = self.get_time()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        vx, vy, vw, vh = self._get_viewport_rect()
        glViewport(vx, vy, vw, vh)
        self.setup_camera()

    @staticmethod
    def quit(event):
        ESCAPE = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        QUIT = event.type == pygame.QUIT
        return ESCAPE or QUIT

    def _render_text_to_gl(self, surf, x, y):
        """Blit a pygame text surface onto the OpenGL framebuffer at (x, y) in screen coordinates (top-left origin)."""
        w, h = surf.get_size()
        screen_h = self.size[1]
        # Convert from top-left origin to OpenGL bottom-left origin
        gl_y = screen_h - y - h
        try:
            raw = pygame.image.tobytes(surf, "RGBA", True)
        except AttributeError:
            raw = pygame.image.tostring(surf, "RGBA", True)

        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, raw)

        glColor4f(1.0, 1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x, gl_y)
        glTexCoord2f(1, 0); glVertex2f(x + w, gl_y)
        glTexCoord2f(1, 1); glVertex2f(x + w, gl_y + h)
        glTexCoord2f(0, 1); glVertex2f(x, gl_y + h)
        glEnd()
        glDeleteTextures([tex_id])

    def draw_sidebar(self, info):
        """Draw a right-side info panel with level, replay/play, and camera details.

        info dict keys:
          mode: 'replay' (default) or 'play'
          level_name, algo_name, current_step, total_steps, status,
          moves_str, speed_label, metrics (optional dict with time_sec, peak_mem_kb, visited)
          shortcuts: optional list of (key_str, description) tuples to override default shortcuts
          move_count: total number of moves made (play mode)
          split_active: whether split mode is active (play mode)
        """
        if not self.sidebar_visible:
            return

        self._init_fonts()
        if not self._fonts_initialized:
            return

        sw, sh = self.size
        sb_x = sw - self.SIDEBAR_W
        sb_w = self.SIDEBAR_W

        # Switch to full-window 2D ortho for sidebar
        glViewport(0, 0, sw, sh)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, sw, 0, sh, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_DEPTH_TEST)

        # ── Sidebar background ──
        glColor4f(0.06, 0.07, 0.10, 0.95)
        glBegin(GL_QUADS)
        glVertex2f(sb_x, 0)
        glVertex2f(sw, 0)
        glVertex2f(sw, sh)
        glVertex2f(sb_x, sh)
        glEnd()

        # Left border accent
        glColor4f(0.055, 0.65, 0.91, 0.7)
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glVertex2f(sb_x, 0)
        glVertex2f(sb_x, sh)
        glEnd()

        glEnable(GL_TEXTURE_2D)

        # ── Content rendering (top-left origin coordinates) ──
        pad = 14
        cy = 12  # cursor y (top-left)

        mode = info.get('mode', 'replay')
        status = info.get('status', 'PAUSED')
        level_name = info.get('level_name', '?')
        algo_name = info.get('algo_name', '?')
        current_step = info.get('current_step', 0)
        total_steps = info.get('total_steps', 1)
        speed_label = info.get('speed_label', '1.0x')
        moves_str = info.get('moves_str', '')
        metrics = info.get('metrics', None)

        # ── Status badge ──
        if status == "GOAL REACHED":
            badge_col = (40, 220, 110)
            badge_text = "GOAL REACHED"
        elif status == "GAME OVER":
            badge_col = (220, 60, 60)
            badge_text = "GAME OVER"
        elif status == "PLAYING":
            badge_col = (14, 165, 233)
            badge_text = "PLAYING"
        elif status == "READY":
            badge_col = (6, 182, 212)
            badge_text = "READY"
        else:
            badge_col = (180, 180, 190)
            badge_text = "PAUSED"

        badge_surf = self._font_title.render(f"  {badge_text}  ", True, (255, 255, 255))
        bw, bh = badge_surf.get_size()
        badge_gl_y = sh - cy - bh - 4
        r, g, b = badge_col
        glColor4f(r / 255, g / 255, b / 255, 0.9)
        glDisable(GL_TEXTURE_2D)
        glBegin(GL_QUADS)
        glVertex2f(sb_x + pad, badge_gl_y - 2)
        glVertex2f(sb_x + pad + bw + 4, badge_gl_y - 2)
        glVertex2f(sb_x + pad + bw + 4, badge_gl_y + bh + 2)
        glVertex2f(sb_x + pad, badge_gl_y + bh + 2)
        glEnd()
        glEnable(GL_TEXTURE_2D)
        self._render_text_to_gl(badge_surf, sb_x + pad + 2, cy + 2)
        cy += bh + 14

        # ── Separator helper ──
        def draw_sep():
            nonlocal cy
            glDisable(GL_TEXTURE_2D)
            glColor4f(0.2, 0.25, 0.35, 0.6)
            sep_gl_y = sh - cy
            glBegin(GL_LINES)
            glVertex2f(sb_x + pad, sep_gl_y)
            glVertex2f(sw - pad, sep_gl_y)
            glEnd()
            glEnable(GL_TEXTURE_2D)
            cy += 8

        # ── Label-value helper ──
        def draw_label_value(label, value, val_color=(255, 255, 255)):
            nonlocal cy
            if label:
                ls = self._font_label.render(label, True, (140, 155, 175))
                self._render_text_to_gl(ls, sb_x + pad, cy)
                cy += ls.get_height() + 1
            vs = self._font_value.render(str(value), True, val_color)
            self._render_text_to_gl(vs, sb_x + pad + 6, cy)
            cy += vs.get_height() + 6

        draw_sep()

        # ── Section: Level & Algorithm ──
        sec = self._font_small.render("LEVEL INFO", True, (14, 165, 233))
        self._render_text_to_gl(sec, sb_x + pad, cy)
        cy += sec.get_height() + 4

        draw_label_value("Level:", level_name)
        if mode == 'replay':
            draw_label_value("Algorithm:", algo_name, (14, 200, 233))
        else:
            draw_label_value("Mode:", "Manual Play", (16, 185, 129))

        draw_sep()

        if mode == 'replay':
            # ── Section: Replay Progress ──
            sec2 = self._font_small.render("REPLAY PROGRESS", True, (14, 165, 233))
            self._render_text_to_gl(sec2, sb_x + pad, cy)
            cy += sec2.get_height() + 4

            # Progress bar
            prog_w = sb_w - pad * 2 - 4
            prog_h = 10
            progress = current_step / max(1, total_steps - 1) if total_steps > 1 else 1.0
            fill_w = int(prog_w * progress)

            glDisable(GL_TEXTURE_2D)
            prog_gl_y = sh - cy - prog_h
            glColor4f(0.15, 0.18, 0.25, 1.0)
            glBegin(GL_QUADS)
            glVertex2f(sb_x + pad, prog_gl_y)
            glVertex2f(sb_x + pad + prog_w, prog_gl_y)
            glVertex2f(sb_x + pad + prog_w, prog_gl_y + prog_h)
            glVertex2f(sb_x + pad, prog_gl_y + prog_h)
            glEnd()
            if fill_w > 0:
                if status == "GOAL REACHED":
                    glColor4f(0.16, 0.86, 0.5, 1.0)
                else:
                    glColor4f(0.055, 0.65, 0.91, 1.0)
                glBegin(GL_QUADS)
                glVertex2f(sb_x + pad, prog_gl_y)
                glVertex2f(sb_x + pad + fill_w, prog_gl_y)
                glVertex2f(sb_x + pad + fill_w, prog_gl_y + prog_h)
                glVertex2f(sb_x + pad, prog_gl_y + prog_h)
                glEnd()
            glEnable(GL_TEXTURE_2D)
            cy += prog_h + 6

            step_str = f"Step: {current_step} / {total_steps - 1}"
            draw_label_value("", step_str, (255, 255, 255))
            draw_label_value("Speed:", speed_label, (249, 115, 22))

            # ── Interactive Start / Pause Button ──
            btn_play_w = sb_w - pad * 2
            btn_play_h = 28
            self.replay_btn_rect = pygame.Rect(sb_x + pad, cy, btn_play_w, btn_play_h)

            glDisable(GL_TEXTURE_2D)
            btn_gl_y = sh - cy - btn_play_h
            if status == "PLAYING":
                glColor4f(0.18, 0.22, 0.32, 1.0)
                btn_txt = "|| PAUSE (Space)"
            elif status == "GOAL REACHED":
                glColor4f(0.16, 0.72, 0.45, 1.0)
                btn_txt = "R: RESTART (R)"
            else:
                glColor4f(0.06, 0.72, 0.50, 1.0)
                btn_txt = "> START REPLAY (Space)"

            glBegin(GL_QUADS)
            glVertex2f(sb_x + pad, btn_gl_y)
            glVertex2f(sb_x + pad + btn_play_w, btn_gl_y)
            glVertex2f(sb_x + pad + btn_play_w, btn_gl_y + btn_play_h)
            glVertex2f(sb_x + pad, btn_gl_y + btn_play_h)
            glEnd()

            glEnable(GL_TEXTURE_2D)
            btn_surf = self._font_key.render(btn_txt, True, (255, 255, 255))
            bx_txt = sb_x + pad + (btn_play_w - btn_surf.get_width()) // 2
            by_txt = cy + (btn_play_h - btn_surf.get_height()) // 2
            self._render_text_to_gl(btn_surf, bx_txt, by_txt)
            cy += btn_play_h + 8

            draw_sep()

            # ── Section: Moves ──
            sec3 = self._font_small.render("MOVES", True, (14, 165, 233))
            self._render_text_to_gl(sec3, sb_x + pad, cy)
            cy += sec3.get_height() + 4

            max_chars = (sb_w - pad * 2) // 7
            if max_chars < 10:
                max_chars = 30
            move_lines = []
            remaining = moves_str
            while remaining:
                move_lines.append(remaining[:max_chars])
                remaining = remaining[max_chars:]
            max_move_lines = 4
            for ml in move_lines[:max_move_lines]:
                ms = self._font_small.render(ml, True, (180, 220, 255))
                self._render_text_to_gl(ms, sb_x + pad + 2, cy)
                cy += ms.get_height() + 1
            if len(move_lines) > max_move_lines:
                dots = self._font_small.render("...", True, (120, 140, 160))
                self._render_text_to_gl(dots, sb_x + pad + 2, cy)
                cy += dots.get_height() + 1
            cy += 4

        else:
            # ── Section: Play Mode Info ──
            sec2 = self._font_small.render("GAME STATUS", True, (14, 165, 233))
            self._render_text_to_gl(sec2, sb_x + pad, cy)
            cy += sec2.get_height() + 4

            move_count = info.get('move_count', 0)
            draw_label_value("Moves made:", str(move_count), (255, 255, 255))

            split_active = info.get('split_active', False)
            if split_active:
                draw_label_value("Block state:", "SPLIT ACTIVE (Space to switch)", (249, 115, 22))
            else:
                draw_label_value("Block:", "Normal (1x1x2)", (180, 200, 220))

            draw_sep()

        # ── Section: Metrics (if available) ──
        if metrics:
            draw_sep()
            sec4 = self._font_small.render("METRICS", True, (14, 165, 233))
            self._render_text_to_gl(sec4, sb_x + pad, cy)
            cy += sec4.get_height() + 4

            if 'time_sec' in metrics:
                draw_label_value("Search time:", f"{metrics['time_sec']:.4f} s", (6, 182, 212))
            if 'peak_mem_kb' in metrics:
                draw_label_value("Peak RAM:", f"{metrics['peak_mem_kb']:.1f} KB", (249, 115, 22))
            if 'visited' in metrics:
                draw_label_value("Explored states:", f"{metrics['visited']:,}", (180, 180, 200))

        # ── Section: Keyboard Shortcuts (bottom) ──
        shortcut_block = info.get('shortcuts', None)
        if shortcut_block is None:
            if mode == 'replay':
                shortcut_block = [
                    ("[Space]", "Play / Pause"),
                    ("[<- / ->]", "Step back / fwd"),
                    ("[R]", "Reset to start"),
                    ("[+/-]", "Change speed"),
                    ("[Left-drag]", "360° Orbit"),
                    ("[Scroll]", "Zoom In/Out"),
                    ("[1] [2] [3] [4]", "View presets"),
                    ("[C]", "Reset camera"),
                    ("[H]", "Toggle sidebar"),
                    ("[ESC]", "Exit to Menu"),
                ]
            else:
                shortcut_block = [
                    ("[Arrow Keys]", "Move block"),
                    ("[Space]", "Switch block (split)"),
                    ("[R]", "Restart level"),
                    ("[Left-drag]", "360° Orbit"),
                    ("[Scroll]", "Zoom In/Out"),
                    ("[1] [2] [3] [4]", "View presets"),
                    ("[C]", "Reset camera"),
                    ("[H]", "Toggle sidebar"),
                    ("[ESC]", "Exit to Menu"),
                ]

        # Render from bottom up
        sc_y = sh - 14
        for key, desc in reversed(shortcut_block):
            sc_y -= 15
            ks = self._font_key.render(key, True, (180, 200, 230))
            ds = self._font_small.render(f" {desc}", True, (110, 120, 140))
            self._render_text_to_gl(ks, sb_x + pad, sc_y)
            self._render_text_to_gl(ds, sb_x + pad + ks.get_width() + 2, sc_y + 1)

        # Section label above shortcuts
        sc_y -= 6
        sc_label = self._font_small.render("CONTROLS", True, (100, 110, 130))
        self._render_text_to_gl(sc_label, sb_x + pad, sc_y - sc_label.get_height())

        # Separator above shortcuts
        glDisable(GL_TEXTURE_2D)
        glColor4f(0.2, 0.25, 0.35, 0.6)
        sep_y2 = sh - (sc_y - sc_label.get_height() - 6)
        glBegin(GL_LINES)
        glVertex2f(sb_x + pad, sep_y2)
        glVertex2f(sw - pad, sep_y2)
        glEnd()

        glEnable(GL_DEPTH_TEST)
        glDisable(GL_TEXTURE_2D)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

        # Restore 3D viewport
        vx, vy, vw, vh = self._get_viewport_rect()
        glViewport(vx, vy, vw, vh)

    def draw_hud(self, lines, font_size=15):
        self._init_fonts()
        if not self._fonts_initialized:
            return
        if not self._font_label:
            return

        screen_w, screen_h = self.size
        hud_font = self._font_label

        rendered_lines = []
        max_w = 0
        total_h = 0
        for item in lines:
            if isinstance(item, tuple):
                text, color = item[0], item[1]
            else:
                text, color = str(item), (255, 255, 255)
            surf = hud_font.render(text, True, color)
            rendered_lines.append((surf, surf.get_size()))
            max_w = max(max_w, surf.get_width())
            total_h += surf.get_height() + 4

        # Switch to 2D Ortho projection
        glViewport(0, 0, screen_w, screen_h)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, screen_w, 0, screen_h, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_DEPTH_TEST)

        # Draw semi-transparent background box
        margin = 12
        pad = 8
        box_x = margin
        box_y = margin
        box_w = min(max_w + pad * 2, screen_w - margin * 2)
        box_h = total_h + pad * 2

        glColor4f(0.04, 0.05, 0.08, 0.85)
        glBegin(GL_QUADS)
        glVertex2f(box_x, box_y)
        glVertex2f(box_x + box_w, box_y)
        glVertex2f(box_x + box_w, box_y + box_h)
        glVertex2f(box_x, box_y + box_h)
        glEnd()

        # Border
        glColor4f(0.2, 0.6, 0.9, 0.8)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex2f(box_x, box_y)
        glVertex2f(box_x + box_w, box_y)
        glVertex2f(box_x + box_w, box_y + box_h)
        glVertex2f(box_x, box_y + box_h)
        glEnd()

        # Draw text lines
        glEnable(GL_TEXTURE_2D)
        cur_y = box_y + box_h - pad
        for surf, (w, h) in rendered_lines:
            cur_y -= h
            try:
                raw_data = pygame.image.tobytes(surf, "RGBA", True)
            except AttributeError:
                raw_data = pygame.image.tostring(surf, "RGBA", True)

            tex_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, raw_data)

            glColor4f(1.0, 1.0, 1.0, 1.0)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(box_x + pad, cur_y)
            glTexCoord2f(1, 0); glVertex2f(box_x + pad + w, cur_y)
            glTexCoord2f(1, 1); glVertex2f(box_x + pad + w, cur_y + h)
            glTexCoord2f(0, 1); glVertex2f(box_x + pad, cur_y + h)
            glEnd()

            glDeleteTextures([tex_id])
            cur_y -= 4

        glDisable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

        # Restore viewport
        vx, vy, vw, vh = self._get_viewport_rect()
        glViewport(vx, vy, vw, vh)

    @staticmethod
    def get_time():
        return time.time() * 1000

    @staticmethod
    def loadTexture():
        textureSurface = pygame.image.load('./drawing/images.jpg')
        try:
            textureData = pygame.image.tobytes(textureSurface, "RGBA", 1)
        except AttributeError:
            textureData = pygame.image.tostring(textureSurface, "RGBA", 1)
        width = textureSurface.get_width()
        height = textureSurface.get_height()

        texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texid)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, textureData)
        glEnable(GL_TEXTURE_2D)
