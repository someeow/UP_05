import tkinter as tk # графическая библиотека
import math
import random
import bisect # для двоичного поиска
import sys # для корректного завершения программы

# 🎮 КОНФИГУРАЦИЯ
# настройка уровней
# target_score - очки для прохождения
# chain_length - начальная длина цепочки
# rotations - витки спирали
LEVELS = [
    {"id": 1, "target_score": 2000, "chain_length": 25, "rotations": 2.0},
    {"id": 2, "target_score": 4000, "chain_length": 35, "rotations": 2.5},
    {"id": 3, "target_score": 10000, "chain_length": 50, "rotations": 3.0},
    {"id": 4, "target_score": 16000, "chain_length": 65, "rotations": 3.5},
]

# Темы уровней определяет: цвет фона, подсветки, количество фоновых частиц, тип эффектов
LEVEL_THEMES = [
    {"name": "Cosmic",   "base": "#0b0b1a", "accent": "#00d9ff", "particles": 15, "style": "stars"},
    {"name": "Forest",   "base": "#0a120a", "accent": "#00ff88", "particles": 15, "style": "spores"},
    {"name": "Ember",    "base": "#120808", "accent": "#ff5500", "particles": 15, "style": "embers"},
    {"name": "Abyss",    "base": "#080a18", "accent": "#4488ff", "particles": 15, "style": "bubbles"}
]

# глобальные константы
COLORS = ["#E6192B", "#3CB44B", "#4363D8", "#F58231", "#911EB4", "#42D4F4", "#F0E442"]
FROG_POS = (400.0, 300.0) # координаты лягушки
BALL_RADIUS = 13 # радиус шара
BALL_SPACING = BALL_RADIUS * 2 + 3 # расстояние между шарами
PROJECTILE_SPEED = 20.5 # скорость выстрела
BASE_CHAIN_SPEED = 0.45 # скорость движения цепочки
ROLLBACK_LERP = 0.6 # коэффициент сглаживания движения

# описывает один шар
class Ball:
    def __init__(self, color, dist):
        self.color = color # цвет
        self.dist = dist # реальная позиция на пути
        self.visual_dist = dist # позиция для плавной анимации

# для взрывов
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, math.pi * 2) # случайное направление
        speed = random.uniform(1, 4) # случайная скорость
        self.vx = math.cos(angle) * speed #скорость по осям
        self.vy = math.sin(angle) * speed
        self.life = 1.0 # время жизни частицы
        self.decay = random.uniform(0.02, 0.04)

# главный игровой класс
class ZumaGame:
    def __init__(self):
        self.root = tk.Tk() # создает окно
        self.root.title("Zuma")
        window_width = 800
        window_height = 600
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.resizable(False, False)
        self.root.configure(bg="#008080") # исходный цвет меню
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # холст для рисования
        self.canvas = tk.Canvas(self.root, width=800, height=600, bg="#008080", highlightthickness=0)
        self.canvas.focus_set()
        self.canvas.pack(fill="both", expand=True)
        # привязка событий
        self.canvas.bind("<Motion>", self.on_mouse_move) # движения мыши
        self.canvas.bind("<Button-1>", self.on_click) # ЛКМ
        self.root.bind_all("<Key>", self.on_key) # клавиатура

        #состояния
        self.state = "menu"
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
            "resume": (280, 295, 520, 345, "Продолжить"),
        }

        self.game_buttons = {
            "menu": (620, 10, 790, 45, "Меню")
        }

        self.start_choice_buttons = {
            "back": (15, 20, 125, 70, "Назад"),
            "yes": (260, 340, 360, 390, "Да"),
            "no": (440, 340, 540, 390, "Нет")
        }

        self.speed = BASE_CHAIN_SPEED
        self.colors_pool = COLORS.copy()
        self._generate_path() # создает спираль
        self._setup_menu_background()
        self._start_loop()
        self.root.mainloop()

    def _generate_path(self):
        if self.current_level_idx >= len(LEVELS):
            return
        lvl = LEVELS[self.current_level_idx]
        raw_pts = []
        num_pts = 450 # точки пути
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

    # по расстоянию вдоль пути вычисляет координаты
    def _get_pos_from_dist(self, dist):
        if dist <= 0: return self.path_pts[0]
        if dist >= self.path_total_len: return self.path_pts[-1]

        idx = bisect.bisect_left(self.path_cum_dist, dist) - 1
        if idx < 0: idx = 0

        seg_len = self.path_cum_dist[idx + 1] - self.path_cum_dist[idx]
        if seg_len > 0: frac = (dist - self.path_cum_dist[idx]) / seg_len
        else: frac = 0
        p1, p2 = self.path_pts[idx], self.path_pts[idx + 1]
        return (p1[0] + (p2[0] - p1[0]) * frac, p1[1] + (p2[1] - p1[1]) * frac)

    # спавн цепочки
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

    # игровой цикл
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

        path_line = [coord for i, p in enumerate(self.path_pts) for coord in p if i % 4 == 0]
        self.canvas.create_line(path_line, fill="#1a1a2e", width=8, smooth=True, tags="bg_layer")
        self.canvas.create_line(path_line, fill="#16213e", width=5, smooth=True, tags="bg_layer")
        self.canvas.create_line(path_line, fill="#0f3460", width=2, smooth=True, tags="bg_layer")

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

    def _setup_menu_background(self):
        self.canvas.delete("bg_layer")
        self.canvas.delete("bg_ambient")

        self._draw_gradient("#0f172a", "#005f73")
        self.bg_particles.clear()

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

    # количество частиц взрыва
    def _spawn_explosion(self, x, y, color, count=6):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    # обновление физики
    def _update_physics(self):
        for ball in self.chain:
            ball.dist += self.speed # каждый шар продвигается вперед
        self.chain = [b for b in self.chain if b.dist < self.path_total_len - 20]

        # обновление координат выстрела
        if self.projectile:
            self.projectile["x"] += self.projectile["dx"]
            self.projectile["y"] += self.projectile["dy"]
            if not (0 <= self.projectile["x"] <= 800 and 0 <= self.projectile["y"] <= 600):
                self.projectile = None

        for ball in self.chain:
            # сглаживание
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
                        self._spawn_explosion(pos[0], pos[1], c, 4)

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
                if self.current_level_idx == len(LEVELS) - 1:
                    self.state = "victory"
                    return
                self.current_level_idx += 1
                self.state = "level_complete"
                self._generate_path()
                self._setup_background()
            else:
                self._spawn_wave()

    def _spawn_wave(self):
        for i in range(15):
            self.chain.append(Ball(random.choice(self.colors_pool), -i * BALL_SPACING))
        self.chain.sort(key=lambda b: b.dist)

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _draw_gradient(self, color1, color2):
        r1, g1, b1 = self._hex_to_rgb(color1)
        r2, g2, b2 = self._hex_to_rgb(color2)
        for i in range(600):
            ratio = i / 600
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            self.canvas.create_line(0, i, 800, i, fill=color, tags="bg_layer")

    # текст с обводкой для заголовков
    def _draw_outlined_text(self, x, y, text, fill_color, font, tags="menu_layer"):
        # черная обводка
        for dx, dy in [(-3, -3), (-3, 0), (-3, 3), (0, -3), (0, 3), (3, -3),  (3, 0),  (3, 3)]:
            self.canvas.create_text(x + dx, y + dy, text=text, fill="black", font=font, tags=tags)
        # основной текст
        self.canvas.create_text( x, y, text=text, fill=fill_color, font=font, tags=tags)

    # текст с обводкой для кнопок
    def _draw_button_text(self, x, y, text, font, tags="menu_layer"):
        # белая обводка
        for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
            self.canvas.create_text(x + dx, y + dy, text=text, fill="white", font=font, tags=tags)
        # основной темно-синий
        self.canvas.create_text(x, y, text=text, fill="#0f172a", font=font, tags=tags)

    def _draw_gradient_ball(self, x, y, radius, color, outline=True, tags="game_layer"):
        r, g, b = self._hex_to_rgb(color)

        glow_factor = min(1.0, self.glow_intensity)
        if glow_factor > 0.5:
            for i in range(1, 0, -1):
                gr = int(r * 0.4)
                gg = int(g * 0.4)
                gb = int(b * 0.4)
                glow_color = f'#{gr:02x}{gg:02x}{gb:02x}'
                self.canvas.create_oval(
                    x - radius - i * 3, y - radius - i * 3,
                    x + radius + i * 3, y + radius + i * 3,
                    fill=glow_color, outline="", tags=tags
                )

        for i in range(2, 0, -1):
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

    def _draw_button(self, x1, y1, x2, y2, text, hover=False, tags="menu_layer"):
        fill_color = "#6BB4D4" if hover else "#5FA8C7"
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="#0f172a", width=4, tags=tags)
        self._draw_button_text((x1 + x2) // 2, (y1 + y2) // 2, text, ("Segoe UI", 14), tags)

    def _draw(self):
        self.canvas.delete("game_layer")
        self.canvas.delete("pause_layer")
        self.canvas.delete("menu_layer")

        if self.state == "menu":
            self._draw_menu()
            return
        if self.state == "start_choice":
            self._draw_start_choice()
            return
        if self.state =="levels":
            self._draw_levels_menu()
            return
        elif self.state == "rules":
            self._draw_rules()
            return

        #Игровой процесс

        for ball in self.chain:
            x, y = self._get_pos_from_dist(ball.visual_dist)
            self._draw_gradient_ball(x, y, BALL_RADIUS, ball.color, tags="game_layer")

        for p in self.particles:
            r, g, b = self._hex_to_rgb(p.color)
            color = f'#{r:02x}{g:02x}{b:02x}'
            size = int(4 * p.life)
            self.canvas.create_oval(p.x - size, p.y - size, p.x + size, p.y + size, fill=color, outline="", tags="game_layer")

        self._draw_frog()

        if self.projectile:
            self._draw_gradient_ball(self.projectile["x"], self.projectile["y"], BALL_RADIUS, self.projectile["color"], tags="game_layer")

        fx, fy = FROG_POS
        self.canvas.create_oval(fx - 40, fy - 40, fx - 20, fy - 20, fill="#1a1a2e", outline="#0f3460", width=2, tags="game_layer")
        self._draw_gradient_ball(fx - 30, fy - 30, 8, self.next_ball, tags="game_layer")
        self.canvas.create_text(fx - 30, fy - 52, text="СЛЕД.", fill="#533483", font=("Segoe UI", 9, "bold"), tags="game_layer")

        lvl = LEVELS[self.current_level_idx]
        self.canvas.create_rectangle(10, 10, 280, 55, fill="#1a1a2e", outline="#0f3460", width=2, tags="game_layer")
        self._draw_outlined_text(90, 22, f"УРОВЕНЬ {lvl['id']}", "#bdefff", ("Segoe UI", 14, "bold"), "game_layer")
        self.canvas.create_text(40, 33, text=f"Очки: {self.score} / {lvl['target_score']}", anchor="nw", fill="#ffffff", font=("Segoe UI", 11), tags="game_layer")

        x1, y1, x2, y2, text = self.game_buttons["menu"]
        hover = x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2
        self._draw_button(x1, y1, x2, y2, text, hover=hover, tags="game_layer")

        if self.state == "level_complete":
            self._draw_overlay(f"УРОВЕНЬ {self.current_level_idx} ПРОЙДЕН!", "#00d9ff", "Нажмите ПРОБЕЛ для следующего уровня")
        elif self.state == "game_over":
            self._draw_overlay("ИГРА ОКОНЧЕНА", "#e94560", "Нажмите R для рестарта")
        elif self.state == "victory":
            self._draw_overlay("ПОБЕДА!", "#00ff88", f"Итоговый счёт: {self.score} | Нажмите R для меню")

        # Если пауза - рисуем поверх игры
        if self.state == "paused":
            self._draw_pause()

        self.glow_intensity *= 0.95

    def _draw_pause(self):
        # Затемнение фона
        self.canvas.create_rectangle(0, 0, 800, 600, fill="#000000", stipple="gray50", tags="pause_layer")

        # Заголовок
        self._draw_outlined_text(400, 180, "ПАУЗА", "#bdefff", ("Segoe UI", 48, "bold"))

        # Кнопки
        for key, (x1, y1, x2, y2, text) in self.pause_buttons.items():
            hover = x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2
            self._draw_button(x1, y1, x2, y2, text, hover=hover, tags="pause_layer")

        # Подсказка
        self.canvas.create_text(400, 420, text="Нажмите 'P' или кнопку 'Продолжить'", fill="#888", font=("Segoe UI", 12), tags="pause_layer")

    def _draw_menu(self):
        self._draw_outlined_text(400, 100, "ZUMA", "#bdefff", ("Segoe UI", 48, "bold"))
        self.canvas.create_text(400, 170, text="Главное меню:", fill="#ffffff", font=("Segoe UI", 18), tags="menu_layer")

        for key, (x1, y1, x2, y2, text) in self.menu_buttons.items():
            hover = x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2
            self._draw_button(x1, y1, x2, y2, text, hover=hover, tags="menu_layer")

    def _draw_levels_menu(self):
        self._draw_outlined_text(400, 80, "ВЫБОР УРОВНЯ", "#bdefff", ("Segoe UI", 32, "bold"))

        for key, (x1, y1, x2, y2, text) in self.level_buttons.items():
            hover = x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2
            self._draw_button(x1, y1, x2, y2, text, hover=hover, tags="menu_layer")

        hover = 280 <= self.mouse_x <= 520 and 500 <= self.mouse_y <= 550
        self._draw_button(280, 500, 520, 550, "Назад", hover=hover, tags="menu_layer")

    def _draw_rules(self):
        self._draw_outlined_text(400, 60, "ПРАВИЛА ИГРЫ", "#bdefff", ("Segoe UI", 32, "bold"))

        rules_text = """
        1. Стреляйте цветными шарами из лягушки

        2. Собирайте 3 или более шара одного цвета

        3. Не дайте шарам достичь центра

        4. Набирайте очки для прохождения уровня

        5. Цепочки исчезновений дают бонусы

        Управление:
        • Мышь - прицеливание
        • ЛКМ - выстрел
        • P - Пауза
        • R - Рестарт
        """

        self.canvas.create_rectangle(120, 130, 680, 470, fill="#bdefff", outline="#000000", width=2, tags="menu_layer")
        self.canvas.create_text(390, 300, text=rules_text, fill="#0f172a", font=("Segoe UI", 12), tags="menu_layer", justify="center")

        hover = 280 <= self.mouse_x <= 520 and 500 <= self.mouse_y <= 550
        self._draw_button(280, 500, 520, 550, "Назад", hover=hover, tags="menu_layer")

    def _draw_start_choice(self):
        self._draw_outlined_text(405, 265, "Запустить начальный уровень?", "#bdefff", ("Segoe UI", 25))

        for key, (x1, y1, x2, y2, text) in self.start_choice_buttons.items():
            hover = x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2
            self._draw_button(x1, y1, x2, y2, text, hover=hover, tags="menu_layer")

    def _draw_frog(self):
        fx, fy = FROG_POS
        ang = self.frog_angle

        breathe_scale = 1 + math.sin(self.frog_breathe) * 0.03

        self.canvas.create_oval(fx - 25, fy + 18, fx + 25, fy + 28, fill="#000000", outline="", tags="game_layer")

        body_size = 22 * breathe_scale
        self.canvas.create_oval(fx - body_size, fy - body_size, fx + body_size, fy + body_size, fill="#2d6a4f", outline="#1b4332", width=3, tags="game_layer")

        self.canvas.create_oval(fx - 14, fy - 10, fx + 14, fy + 16, fill="#40916c", outline="", tags="game_layer")

        mx = fx + math.cos(ang) * 26
        my = fy + math.sin(ang) * 26
        self.canvas.create_oval(mx - 10, my - 10, mx + 10, my + 10, fill="#1b4332", outline="#0d2b1d", width=2, tags="game_layer")
        self._draw_gradient_ball(mx, my, 7, self.current_ball, tags="game_layer")

        for off in [-0.6, 0.6]:
            ex = fx + math.cos(ang + off) * 14
            ey = fy + math.sin(ang + off) * 14
            self.canvas.create_oval(ex - 6, ey - 6, ex + 6, ey + 6, fill="#fff", outline="#1b4332", width=1, tags="game_layer")
            self.canvas.create_oval(ex - 3, ey - 3, ex + 3, ey + 3, fill="#0a0a0f", tags="game_layer")
            self.canvas.create_oval(ex - 2, ey - 2, ex - 0.5, ey - 0.5, fill="#fff", tags="game_layer")

    def _draw_overlay(self, title, color, sub):
        self.canvas.create_rectangle(0, 0, 800, 600, fill="#000000")
        self._draw_outlined_text(400, 250, title, "#bdefff", ("Segoe UI", 42, "bold"))
        self.canvas.create_text(400, 320, text=sub, fill="#ccc", font=("Segoe UI", 18))

    def _check_button_click(self, x, y):
        if self.state == "menu":
            for key, (x1, y1, x2, y2, text) in self.menu_buttons.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    if key == "play":
                        self.state = "start_choice"
                    elif key == "levels":
                        self.state = "levels"
                    elif key == "rules":
                        self.state = "rules"
                    elif key == "exit":
                        self.on_close()
                    return True
        elif self.state == "start_choice":
            if 15<= x <= 125 and 20 <= y <= 70:
                self.state = "menu"
                return True
            if 260 <= x <= 360 and 340 <=y <= 390:
                self.current_level_idx = 0
                self._start_game()
                return True
            if 440 <= x <= 540 and 340 <= y <= 390:
                self.state = "levels"
                return True
        elif self.state == "levels":
            if 280 <= x <= 520 and 500 <= y <= 550:
                self.state = "menu"
                self._setup_menu_background()
                return True
            for key, (x1, y1, x2, y2, text) in self.level_buttons.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self.current_level_idx = key - 1
                    self._start_game()
                    return True
        elif self.state == "rules":
            if 280 <= x <= 520 and 500 <= y <= 550:
                self.state = "menu"
                self._setup_menu_background()
                return True
        elif self.state == "paused":
            for key, (x1, y1, x2, y2, text) in self.pause_buttons.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    if key == "resume":
                        self.state = "playing"
                    return True
        elif self.state == "playing":
            x1, y1, x2, y2, text = self.game_buttons["menu"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.state = "menu"
                self.score = 0
                self.current_level_idx = 0
                self._setup_menu_background()
                return True
        return False

    def on_mouse_move(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

        # Если не пауза, лягушка следит за мышью
        if self.state == "playing":
            dx = event.x - FROG_POS[0]
            dy = event.y - FROG_POS[1]
            self.frog_angle = math.atan2(dy, dx)

    def on_click(self, event):
        x, y = event.x, event.y

        if self.state in ("menu", "start_choice", "levels", "rules", "paused", "playing"):
            if self._check_button_click(x, y):
                return

        if self.state == "playing":
            if self.projectile:
                return
            rad = self.frog_angle
            self.projectile = {
                "x": FROG_POS[0], "y": FROG_POS[1],
                "dx": math.cos(rad) * PROJECTILE_SPEED,
                "dy": math.sin(rad) * PROJECTILE_SPEED,
                "color": self.current_ball
            }
            self.current_ball = self.next_ball
            self.next_ball = random.choice(self.colors_pool)

    def on_key(self, event):
        key = event.keysym.lower()

        if key == "p":
            # Переключение паузы
            if self.state == "playing":
                self.state = "paused"
            elif self.state == "paused":
                self.state = "playing"
            return

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
                self._setup_menu_background()

    def _start_game(self):
        self.state = "playing"
        # 1 уровень = 4 цвета, 2 = 5, 3 = 6, 4 = 7
        colors_count = min(4 + self.current_level_idx, 7)
        self.colors_pool = COLORS[:colors_count]
        self._generate_path()
        self._spawn_chain()
        self._setup_background()
        self.current_ball = random.choice(self.colors_pool)
        self.next_ball = random.choice(self.colors_pool)
        self.particles.clear()

    def _reset_game(self):
        self.score = 0
        self.current_level_idx = 0

        self.chain.clear()
        self.particles.clear()
        self.projectile = None

        self._start_game()

    def on_close(self):
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    ZumaGame()