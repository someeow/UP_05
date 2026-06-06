import tkinter as tk
import math
import random
import sys

# 🎮 КОНФИГУРАЦИЯ

DIFFICULTY = {
    "easy": {"speed_mult": 0.7, "max_colors": 4, "label": "Easy"},
    "medium": {"speed_mult": 1.0, "max_colors": 5, "label": "Medium"},
    "hard": {"speed_mult": 1.4, "max_colors": 6, "label": "Hard"}
}

LEVELS = [
    {"id": 1, "target_score": 4000, "chain_length": 25, "rotations": 2.0},
    {"id": 2, "target_score": 9000, "chain_length": 35, "rotations": 2.5},
    {"id": 3, "target_score": 16000, "chain_length": 50, "rotations": 3.0},
    {"id": 4, "target_score": 25000, "chain_length": 65, "rotations": 3.5},
]

LEVEL_THEMES = [
    {"name": "Cosmic",   "base": "#0b0b1a", "accent": "#00d9ff", "particles": 45, "style": "stars"},
    {"name": "Forest",   "base": "#0a120a", "accent": "#00ff88", "particles": 35, "style": "spores"},
    {"name": "Ember",    "base": "#120808", "accent": "#ff5500", "particles": 40, "style": "embers"},
    {"name": "Abyss",    "base": "#080a18", "accent": "#4488ff", "particles": 50, "style": "bubbles"}
]

COLORS = ["#E6192B", "#3CB44B", "#4363D8", "#F58231", "#911EB4", "#42D4F4", "#F0E442"]
FROG_POS = (400.0, 300.0)
BALL_RADIUS = 12
BALL_SPACING = BALL_RADIUS * 2 + 3
PROJECTILE_SPEED = 7.5
BASE_CHAIN_SPEED = 0.15
ROLLBACK_LERP = 0.18

class Ball:
    def __init__(self, color, dist):
        self.color = color
        self.dist = dist
        self.visual_dist = dist

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1, 4)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.02, 0.04)

class ZumaGame:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Zuma")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        self.root.configure(bg="#111115")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.canvas = tk.Canvas(self.root, width=800, height=600, bg="#111115", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<Key>", self.on_key)

        #состояния
        self.state = "menu"
        self.difficulty = "medium"
        self.current_level_idx = 0
        self.score = 0
        self.chain = []
        self.path_pts = []
        self.path_cum_dist = []
        self.path_total_len = 0
        self.frog_angle = -math.pi / 2
        self.projectile = None
        self.current_ball = random.choice(COLORS)
        self.next_ball = random.choice(COLORS)
        self.speed = BASE_CHAIN_SPEED
        self.colors_pool = []
        self.particles = []
        self.frog_breathe = 0
        self.glow_intensity = 0
        self.bg_particles = []
        self.current_theme = None
        self.mouse_x = 0
        self.mouse_y = 0

        #Кнопки меню
        self.menu_buttons = {
            "play": (280, 220, 520, 270, "Играть"),
            "levels": (280, 290, 520, 340, "Уровни"),
            "rules": (280, 360, 520, 410, "Правила"),
            "exit": (280, 430, 520, 480, "Выход")
        }

        self.level_buttons = {}
        for i in range(4):
            y_start = 180 + i * 70
            self.level_buttons[i + 1] = (280, y_start, 520, y_start + 50, f'Уровень {i + 1}')

         # Кнопки паузы
        self.pause_buttons = {
            "resume": (280, 260, 520, 310, "Продолжить"),
            "menu": (280, 330, 520, 380, "В главное меню")
        }

        self._apply_difficulty()
        self._generate_path()
        self._start_loop()
        self.root.mainloop()

    def _apply_difficulty(self):
        cfg = DIFFICULTY[self.difficulty]
        self.speed = BASE_CHAIN_SPEED * cfg["speed_mult"]
        self.colors_pool = COLORS[:cfg["max_colors"]]

    def _generate_path(self):
        if self.current_level_idx >= len(LEVELS):
            return
        lvl = LEVELS[self.current_level_idx]
        raw_pts = []
        num_pts = 1500
        start_r, end_r = 290, 60
        total_rot = lvl["rotations"]
        start_angle = random.uniform(0, math.pi * 2)

        for i in range(num_pts):
            t = i / (num_pts - 1)
            r = start_r - (start_r - end_r) * t
            angle = start_angle + t * total_rot * 2 * math.pi
            raw_pts.append((FROG_POS[0] + r * math.cos(angle), FROG_POS[1] + r * math.sin(angle)))

        self.path_pts = raw_pts
        self.path_cum_dist = [0.0]
        for i in range(len(raw_pts) - 1):
            dx = raw_pts[i + 1][0] - raw_pts[i][0]
            dy = raw_pts[i + 1][1] - raw_pts[i][1]
            self.path_cum_dist.append(self.path_cum_dist[-1] + math.hypot(dx, dy))
        self.path_total_len = self.path_cum_dist[-1]

    def _get_pos_from_dist(self, dist):
        if dist <= 0: return self.path_pts[0]
        if dist >= self.path_total_len: return self.path_pts[-1]

        idx = 0
        while idx < len(self.path_cum_dist) - 1 and self.path_cum_dist[idx + 1] < dist:
            idx += 1

        seg_len = self.path_cum_dist[idx + 1] - self.path_cum_dist[idx]
        frac = (dist - self.path_cum_dist[idx]) / seg_len if seg_len > 0 else 0
        p1, p2 = self.path_pts[idx], self.path_pts[idx + 1]
        return (p1[0] + (p2[0] - p1[0]) * frac, p1[1] + (p2[1] - p1[1]) * frac)

    def _spawn_chain(self):
        lvl = LEVELS[self.current_level_idx]
        self.chain.clear()
        start_dist = 0
        for i in range(lvl["chain_length"]):
            self.chain.append(Ball(random.choice(self.colors_pool), start_dist - i * BALL_SPACING))
        self.chain.sort(key=lambda b: b.dist)

    def _recalc_spacing(self, start_idx=0):
        for i in range(start_idx, len(self.chain)):
            min_dist = (self.chain[i - 1].dist + BALL_SPACING) if i > 0 else 0
            if self.chain[i].dist < min_dist:
                self.chain[i].dist = min_dist
            elif i > 0 and self.chain[i].dist > self.chain[i - 1].dist + BALL_SPACING + 0.1:
                self.chain[i].dist = self.chain[i - 1].dist + BALL_SPACING

    def _start_loop(self):
        self._tick()

    def _tick(self):
        # Если пауза - только рисуем, не обновляем физику
        if self.state == "paused":
            self._draw()
            self.root.after(16, self._tick)
            return

        if self.state == "playing":
            self._update_physics()
            self._check_collisions()
            self._check_win_lose()

        self.frog_breathe += 0.05
        self._update_particles()
        if self.state == "playing":
            self._update_background()
        self._draw()
        self.root.after(16, self._tick)

    def _setup_background(self):
        self.canvas.delete("bg_layer")
        self.canvas.delete("bg_ambient")
        self.bg_particles = []

        theme = LEVEL_THEMES[self.current_level_idx % len(LEVEL_THEMES)]
        self.current_theme = theme

        self.canvas.create_rectangle(0, 0, 800, 600, fill=theme["base"], tags="bg_layer")

        for r in range(400, 50, -20):
            br, bg, bb = self._hex_to_rgb(theme["base"])
            dark = f"#{max(0,br-15):02x}{max(0,bg-15):02x}{max(0,bb-15):02x}"
            self.canvas.create_oval(400-r, 300-r, 400+r, 300+r, outline=dark, width=4, tags="bg_layer")

        if theme["style"] == "stars":
            for _ in range(20):
                x, y = random.uniform(0, 800), random.uniform(0, 600)
                self.canvas.create_line(x-4, y, x+4, y, fill=theme["accent"], width=1, tags="bg_layer")
        elif theme["style"] == "spores":
            for _ in range(12):
                x, y = random.uniform(0, 800), random.uniform(0, 600)
                self.canvas.create_polygon(x-6,y-6, x+6,y, x-6,y+6, fill=theme["accent"], tags="bg_layer")

        r, g, b = self._hex_to_rgb(theme["accent"])
        dim_color = f"#{r // 5:02x}{g // 5:02x}{b // 5:02x}"

        for _ in range(theme["particles"]):
            x = random.uniform(0, 800)
            y = random.uniform(0, 600)
            size = random.uniform(1, 3.5)
            vx = random.uniform(-0.15, 0.15)
            vy = random.uniform(-0.2, -0.05) if theme["style"] != "embers" else random.uniform(-0.3, -0.1)

            oid = self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=dim_color, outline="", tags="bg_ambient")
            self.bg_particles.append({"id": oid, "x": x, "y": y, "vx": vx, "vy": vy, "size": size})

    def _update_background(self):
        if not self.bg_particles: return
        for p in self.bg_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["y"] < -10: p["y"] = 610
            if p["y"] > 610: p["y"] = -10
            if p["x"] < -10: p["x"] = 810
            if p["x"] > 810: p["x"] = -10

            self.canvas.coords(p["id"], p["x"] - p["size"], p["y"] - p["size"], p["x"] + p["size"], p["y"] + p["size"])

    def _update_particles(self):
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= p.decay
            p.vx *= 0.98
            p.vy *= 0.98
            if p.life <= 0:
                self.particles.remove(p)

    def _spawn_explosion(self, x, y, color, count=15):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def _update_physics(self):
        for ball in self.chain:
            ball.dist += self.speed
        self.chain = [b for b in self.chain if b.dist < self.path_total_len - 20]

        if self.projectile:
            self.projectile["x"] += self.projectile["dx"]
            self.projectile["y"] += self.projectile["dy"]
            if not (0 <= self.projectile["x"] <= 800 and 0 <= self.projectile["y"] <= 600):
                self.projectile = None

        for ball in self.chain:
            ball.visual_dist += (ball.dist - ball.visual_dist) * ROLLBACK_LERP

        self._recalc_spacing()

    def _check_collisions(self):
        if not self.projectile:
            return
        px, py = self.projectile["x"], self.projectile["y"]

        best_idx = -1
        best_dist_sq = float("inf")
        for i, ball in enumerate(self.chain):
            pos = self._get_pos_from_dist(ball.visual_dist)
            d2 = (pos[0] - px) ** 2 + (pos[1] - py) ** 2
            if d2 < best_dist_sq:
                best_dist_sq = d2
                best_idx = i

        if best_idx != -1 and best_dist_sq < (BALL_RADIUS * 1.8) ** 2:
            insert_dist = self.chain[best_idx].dist - BALL_SPACING
            new_ball = Ball(self.projectile["color"], insert_dist)
            self.chain.insert(best_idx, new_ball)
            self.chain.sort(key=lambda b: b.dist)

            self.projectile = None  # Снаряд поглощён цепью
            self._recalc_spacing(best_idx)
            self._resolve_matches()

    def _resolve_matches(self):
        changed = True
        combo = 1
        while changed:
            changed = False
            i = 0
            while i < len(self.chain) - 2:
                c = self.chain[i].color
                j = i + 1
                while j < len(self.chain) and self.chain[j].color == c:
                    j += 1
                count = j - i
                if count >= 3:
                    for k in range(i, j):
                        pos = self._get_pos_from_dist(self.chain[k].visual_dist)
                        self._spawn_explosion(pos[0], pos[1], c, 8)

                    pts = self._calc_zuma_score(count) * combo
                    self.score += pts
                    self.glow_intensity = min(1.0, self.glow_intensity + 0.3)
                    del self.chain[i:j]
                    self._recalc_spacing(i)
                    changed = True
                    combo += 1
                    i = max(0, i - 2)
                else:
                    i += 1

    def _calc_zuma_score(self, count):
        if count == 3: return 100
        if count == 4: return 200
        return 300 + (count - 5) * 50

    def _check_win_lose(self):
        if any(b.dist >= self.path_total_len - 20 for b in self.chain):
            self.state = "game_over"
            return

        if not self.chain:
            lvl = LEVELS[self.current_level_idx]
            if self.score >= lvl["target_score"]:
                self.current_level_idx += 1
                if self.current_level_idx >= len(LEVELS):
                    self.state = "victory"
                else:
                    self.state = "level_complete"
                    self._generate_path()
            else:
                self._spawn_wave()

    def _spawn_wave(self):
        for i in range(15):
            self.chain.append(Ball(random.choice(self.colors_pool), -i * BALL_SPACING))
        self.chain.sort(key=lambda b: b.dist)

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _draw_gradient_ball(self, x, y, radius, color, outline=True, tags="game_layer"):
        r, g, b = self._hex_to_rgb(color)

        glow_factor = min(1.0, self.glow_intensity)
        if glow_factor > 0.1:
            for i in range(3, 0, -1):
                gr = int(r * 0.4)
                gg = int(g * 0.4)
                gb = int(b * 0.4)
                glow_color = f'#{gr:02x}{gg:02x}{gb:02x}'
                self.canvas.create_oval(
                    x - radius - i * 3, y - radius - i * 3,
                    x + radius + i * 3, y + radius + i * 3,
                    fill=glow_color, outline="", tags=tags
                )

        for i in range(5, 0, -1):
            ratio = i / 5
            nr = int(r * (0.6 + 0.4 * ratio))
            ng = int(g * (0.6 + 0.4 * ratio))
            nb = int(b * (0.6 + 0.4 * ratio))
            grad_color = f'#{nr:02x}{ng:02x}{nb:02x}'
            self.canvas.create_oval(
                x - radius + i, y - radius + i,
                x + radius - i, y + radius - i,
                fill=grad_color, outline="", tags=tags
            )

        self.canvas.create_oval(
            x - radius // 3, y - radius // 3,
            x - radius // 6, y - radius // 6,
            fill="#ffffff", outline="", tags=tags
        )

        if outline:
            dark_color = f'#{max(0, r-40):02x}{max(0, g-40):02x}{max(0, b-40):02x}'
            self.canvas.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                outline=dark_color, width=2, tags=tags
            )

    def _draw(self):
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, 800, 600, fill="#111115")

        if self.state == "menu":
            self._draw_menu()
            return
        if self.state =="levels":
            self._draw_levels_menu()
            return

        path_line = [coord for i, p in enumerate(self.path_pts) for coord in p if i % 4 == 0]
        self.canvas.create_line(path_line, fill="#2a2a35", width=4, smooth=True)

        for ball in self.chain:
            x, y = self._get_pos_from_dist(ball.visual_dist)
            self.canvas.create_oval(x - BALL_RADIUS, y - BALL_RADIUS, x + BALL_RADIUS, y + BALL_RADIUS,
                                    fill=ball.color, outline="")

        self._draw_frog()

        if self.projectile:
            self.canvas.create_oval(self.projectile["x"] - BALL_RADIUS, self.projectile["y"] - BALL_RADIUS,
                                    self.projectile["x"] + BALL_RADIUS, self.projectile["y"] + BALL_RADIUS,
                                    fill=self.projectile["color"], outline="white", width=2)

        fx, fy = FROG_POS
        self.canvas.create_oval(fx - 35, fy - 35, fx - 25, fy - 25, fill=self.next_ball)
        self.canvas.create_text(fx - 30, fy - 48, text="NEXT", fill="#888", font=("Consolas", 8))

        lvl = LEVELS[self.current_level_idx]
        self.canvas.create_text(20, 20, text=f"LVL {lvl['id']}  |  Score: {self.score}/{lvl['target_score']}",
                                anchor="nw", fill="#eee", font=("Consolas", 14, "bold"))
        self.canvas.create_text(780, 20, text=f"Diff: {DIFFICULTY[self.difficulty]['label']}",
                                anchor="ne", fill="#aaa", font=("Consolas", 12))

        if self.state == "level_complete":
            self._draw_overlay(f"LEVEL {self.current_level_idx} COMPLETE!", "#4363D8", "Press SPACE for Next Level")
        elif self.state == "game_over":
            self._draw_overlay("GAME OVER", "#E6192B", "Press R to Restart")
        elif self.state == "victory":
            self._draw_overlay("YOU WON ALL LEVELS!", "#3CB44B", f"Final Score: {self.score} | Press R for Menu")

    def _draw_frog(self):
        fx, fy = FROG_POS
        ang = self.frog_angle
        self.canvas.create_oval(fx - 20, fy - 20, fx + 20, fy + 20, fill="#228B22", outline="#004400", width=2)
        mx = fx + math.cos(ang) * 24
        my = fy + math.sin(ang) * 24
        self.canvas.create_oval(mx - 8, my - 8, mx + 8, my + 8, fill=self.current_ball, outline="")
        for off in [-0.5, 0.5]:
            ex = fx + math.cos(ang + off) * 12
            ey = fy + math.sin(ang + off) * 12
            self.canvas.create_oval(ex - 4, ey - 4, ex + 4, ey + 4, fill="white")
            self.canvas.create_oval(ex - 2, ey - 2, ex + 2, ey + 2, fill="black")

    def _draw_button(self, x1, y1, x2, y2, text, hover=False, tags="menu_layer"):
        fill_color = "#f0f0f0" if hover else "#ffffff"
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="#000000", width=2, tags=tags)
        self.canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=text, fill="#000000", font=("Segoe UI", 14), tags=tags)

    def _draw_menu(self):
        '''Главное меню'''
        self.canvas.create_text(400,100,text="ZUMA", fill="#FFFFFF")
        self.canvas.create_text(400, 170, text="Главное меню:", fill="#FFFFFFF")

    def _draw_levels_menu(self):
        self.canvas.create_text(400, 80, text="ВЫБОР УРОВНЯ", fill="#000000", font=("Segoe UI", 32, "bold"), tags="menu_layer")
        # Показываем текущую сложность (статично)
        self.canvas.create_text(400, 130, text=f"Сложность: {DIFFICULTY[self.difficulty]['label']}", fill="#666666", font=("Segoe UI", 14), tags="menu_layer")

        for key, (x1, y1, x2, y2, text) in self.level_buttons.items():
            hover = x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2
            self._draw_button(x1, y1, x2, y2, text, hover=hover, tags="menu_layer")

        self.canvas.create_rectangle(280, 500, 520, 550, fill="#ffffff", outline="#000000", width=2, tags="menu_layer")
        self.canvas.create_text(400, 525, text="Назад", fill="#000000", font=("Segoe UI", 14), tags="menu_layer")


    def _draw_overlay(self, title, color, sub):
        self.canvas.create_rectangle(0, 0, 800, 600, fill="#000000")
        self.canvas.create_text(400, 250, text=title, fill=color, font=("Segoe UI", 42, "bold"))
        self.canvas.create_text(400, 320, text=sub, fill="#ccc", font=("Segoe UI", 18))

    def on_mouse_move(self, event):
        dx = event.x - FROG_POS[0]
        dy = event.y - FROG_POS[1]
        self.frog_angle = math.atan2(dy, dx)

    def on_click(self, event):
        if self.state != "playing" or self.projectile:
            return
        rad = self.frog_angle
        self.projectile = {
            "x": FROG_POS[0], "y": FROG_POS[1],
            "dx": math.cos(rad) * PROJECTILE_SPEED,
            "dy": math.sin(rad) * PROJECTILE_SPEED,
            "color": self.current_ball
        }
        # 🔥 Механика оригинала: шар расходуется сразу при выстреле.
        # Если он улетит в пустоту или врежется в цепь - он уже "потрачен".
        self.current_ball = self.next_ball
        self.next_ball = random.choice(self.colors_pool)

    def on_key(self, event):
        key = event.keysym.lower()
        if self.state == "menu":
            if key in ("1", "2", "3"):
                diff_keys = list(DIFFICULTY.keys())
                idx = int(key) - 1
                if 0 <= idx < len(diff_keys):
                    self.difficulty = diff_keys[idx]
                    self._apply_difficulty()
                    self._start_game()
        elif self.state == "playing":
            if key == "r":
                self._reset_game()
        elif self.state == "level_complete":
            if key == "space":
                self._start_game()
        elif self.state in ("game_over", "victory"):
            if key == "r":
                self.state = "menu"
                self.score = 0
                self.current_level_idx = 0
                self._apply_difficulty()

    def _start_game(self):
        self.state = "playing"
        self._generate_path()
        self._spawn_chain()
        self.current_ball = random.choice(self.colors_pool)
        self.next_ball = random.choice(self.colors_pool)

    def _reset_game(self):
        self.score = 0
        self.current_level_idx = 0
        self._start_game()

    def on_close(self):
        self.root.destroy()
        sys.exit()


if __name__ == "__main__":
    ZumaGame()