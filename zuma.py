import tkinter as tk # графическая библиотека для создания интерфейса
import math
import random
import bisect # алгоритм двоичного поиска для быстрого поиска позиции на пути
import sys # для корректного завершения программы

 # КОНФИГУРАЦИЯ ИГРЫ

# id - номер уровня
# настройка уровней
# target_score - очки, необходимые для прохождения
# chain_length - количество шаров в начальной цепочке
# rotations - количество полных оборотов спирали
LEVELS = [
    {"id": 1, "target_score": 2000, "chain_length": 25, "rotations": 2.0},
    {"id": 2, "target_score": 4000, "chain_length": 35, "rotations": 2.5},
    {"id": 3, "target_score": 10000, "chain_length": 50, "rotations": 3.0},
    {"id": 4, "target_score": 16000, "chain_length": 65, "rotations": 3.5},
]

# визуальные темы для каждого уровня:
# name - название темы
# base - основной цвет фона
# accent - акцентный цвет для декоративных элементов
# particles - количество фоновых частиц
# style - тип эффектов
LEVEL_THEMES = [
    {"name": "Cosmic",   "base": "#0b0b1a", "accent": "#00d9ff", "particles": 15, "style": "stars"},
    {"name": "Forest",   "base": "#0a120a", "accent": "#00ff88", "particles": 15, "style": "spores"},
    {"name": "Ember",    "base": "#120808", "accent": "#ff5500", "particles": 15, "style": "embers"},
    {"name": "Abyss",    "base": "#080a18", "accent": "#4488ff", "particles": 15, "style": "bubbles"}
]

# глобальные константы
COLORS = ["#E6192B", "#3CB44B", "#4363D8", "#F58231", "#911EB4", "#42D4F4", "#F0E442"]
BASE_W, BASE_H = 800, 600
FROG_POS = (400.0, 300.0) # координаты лягушки (центр экрана)
BALL_RADIUS = 14 # радиус шара в пикселях
BALL_SPACING = BALL_RADIUS * 2 + 1 # расстояние между центрами соседних шаров
PROJECTILE_SPEED = 20.5 # скорость летящего снаряда
BASE_CHAIN_SPEED = 0.45 # базовая скорость движения цепочки шаров
ROLLBACK_LERP = 0.6 # коэффициент плавности анимации

# КЛАССЫ ДАННЫХ

# описывает один шар
class Ball:
    def __init__(self, color, dist):
        self.color = color # цвет шара
        self.dist = dist # реальная позиция на пути (расстояние от начала)
        self.visual_dist = dist # визуальная позиция для плавной анимации

# описывает частицу взрыва (при уничтожении группы шаров)
class Particle:
    def __init__(self, x, y, color):
        self.x = x  # текущая координата Х
        self.y = y  # текущая координата Y
        self.color = color # цвет частиц (совпадает с цветом шара)
        angle = random.uniform(0, math.pi * 2) # случайное направление разлета (0...360)
        speed = random.uniform(1, 4) # случайная скорость
        self.vx = math.cos(angle) * speed # скорость по осям Х, Y
        self.vy = math.sin(angle) * speed
        self.life = 1.0 # время жизни частицы
        self.decay = random.uniform(0.02, 0.04) # скорость угасания

# ГЛАВНЫЙ ИГРОВОЙ КЛАСС

class ZumaGame:
    def __init__(self):
        # ИНИЦИАЛИЗАЦИЯ ОКНА ПРИЛОЖЕНИЯ
        self.root = tk.Tk() # создает окно
        # ПОЛНОЭКРАННЫЙ РЕЖИМ
        self.root.attributes('-fullscreen', True) # включаем полноэкранный режим
        self.screen_w = self.root.winfo_screenwidth() # ширина экрана монитора
        self.screen_h = self.root.winfo_screenheight()  # высота экрана монитора
        # коэффициенты масштабирования
        self.sx = self.screen_w / BASE_W # по оси Х
        self.sy = self.screen_h / BASE_H  # по оси Y
        self.sc = (self.sx + self.sy) / 2  # средний масштаб
        self.root.geometry(f"{self.screen_w}x{self.screen_h}+0+0") # размер и позиция окна
        self.root.resizable(False, False) # запрет изменения окна пользователем
        self.root.configure(bg="#008080") # исходный цвет меню
        self.root.protocol("WM_DELETE_WINDOW", self.on_close) # обработчик закрытия окна
        self.root.bind_all("<Escape>", lambda e: self.on_close()) # Esc для выхода
        # ХОЛСТ ДЛЯ РИИСОВАНИЯ
        self.canvas = tk.Canvas(self.root, width=self.screen_w, height=self.screen_h, bg="#008080", highlightthickness=0, borderwidth=0)
        self.canvas.focus_set() # установить фокус для клавиатурных событий
        self.canvas.pack(fill="both", expand=True) # растянуть canvas на все окно
        # масштабирование ключевых элементов под размер окна
        self.FROG_POS = (self.screen_w / 2, self.screen_h / 2)  # лягушка в центре экрана
        self.BALL_RADIUS = int(13 * self.sc)  # масштабированный радиус шара
        self.BALL_SPACING = self.BALL_RADIUS * 2 + int(3 * self.sc) # масштабированное расстояние
        # ПРИВЯЗКА СОБЫТИЙ МЫШИ И КЛАВИАТУРЫ
        self.canvas.bind("<Motion>", self.on_mouse_move) # движения мыши - обновление угла лягушки
        self.canvas.bind("<Button-1>", self.on_click) # ЛКМ - выстрел или клик по кнопке
        self.root.bind_all("<Key>", self.on_key) # клавиатура

        # ИНИЦИАЛИЗАЦИЯ ИГРОВЫХ ПЕРЕМЕННЫХ
        self.state = "menu" # текущее состояние игры
        self.current_level_idx = 0 # индекс текущего уровня
        self.score = 0 # набранные очки
        self.chain = [] # список объектов Ball (цепочка шаров)
        self.path_pts = [] # список точек пути
        self.path_cum_dist = [] # накопленные расстояния по пути для двоичного поиска
        self.path_total_len = 0 # общая длина пути в пикселях
        self.frog_angle = -math.pi / 2 # угол поворота лягушки
        self.projectile = None # летящий снаряд
        self.current_ball = random.choice(COLORS) # цвет текущего шара в лягушке
        self.next_ball = random.choice(COLORS) # цвет следующего шара
        self.speed = BASE_CHAIN_SPEED # текущая скорость движения цепочки
        self.colors_pool = [] # доступные цвета для текущего уровня
        self.particles = [] # список активных частиц взрыва
        self.frog_breathe = 0 # фаза анимации дыхания лягушки
        self.glow_intensity = 0 # интенсивность свечения шаров при комбо
        self.bg_particles = [] # фоновые частицы
        self.current_theme = None # тема текущего уровня
        self.mouse_x = 0 # текущие координаты мыши X, Y
        self.mouse_y = 0

        # КОНФИГУРАЦИЯ КНОПОК МЕНЮ
        # каждая кнопка: (x1, y1, x2, y2, текст)
        self.menu_buttons = {
            "play": self._btn(280, 220, 520, 270, "Играть"),
            "levels": self._btn(280, 290, 520, 340, "Уровни"),
            "rules": self._btn(280, 360, 520, 410, "Правила"),
            "exit": self._btn(280, 430, 520, 480, "Выход")
        }
        # кнопки выбора уровня
        self.level_buttons = {}
        for i in range(4):
            y_start = 180 + i * 70 # вертикальное смещение для каждой кнопки
            self.level_buttons[i + 1] =  self._btn(280, y_start, 520, y_start + 50, f'Уровень {i + 1}')

         # кнопки паузы
        self.pause_buttons = {"resume": self._btn(280, 295, 520, 345, "Продолжить")}
        # кнопка выхода в меню во время игры
        self.game_buttons = {"menu": self._btn(620, 10, 790, 45, "Меню")}
        # кнопка диалога "Запустить начальный уровень?"
        self.start_choice_buttons = {
            "back": self._btn(15, 20, 125, 70, "Назад"),
            "yes": self._btn(260, 340, 360, 390, "Да"),
            "no": self._btn(440, 340, 540, 390, "Нет")
        }
        # НАЧАЛЬНАЯ ИНИЦИАЛИЗАЦИЯ
        self.speed = BASE_CHAIN_SPEED
        self.colors_pool = COLORS.copy()
        self._generate_path() # создание спирали для уровня 1
        self._setup_menu_background() # фон для меню
        self._start_loop() # запуск игрового цикла
        self.root.mainloop() # вход в главный цикл обработки событий tkinter

    def _btn(self, x1, y1, x2, y2, text):
        """Масштабирует координаты кнопки, согласно размеру экрана"""
        return (int(x1 * self.sx), int(y1 * self.sy),
                int(x2 * self.sx), int(y2 * self.sy), text)

    # ГЕОМЕТРИЯ ПУТИ
    def _generate_path(self):
        """
        Генерирует специальную траекторию от края экрана к центру.
        Используется параметрическое уравнение спирали Архимеда
        """
        if self.current_level_idx >= len(LEVELS):
            return
        lvl = LEVELS[self.current_level_idx]
        raw_pts = []
        num_pts = 450 # точки пути
        # вычисляет радиусы спирали на основе размера экрана
        max_radius = min(self.screen_w, self.screen_h) * 0.47
        start_r = max_radius # начальный радиус (край)
        end_r = max_radius * 0.3 # конечный радиус (центр)
        total_rot = lvl["rotations"] # количество полных оборотов спирали
        start_angle = random.uniform(0, math.pi * 2) # случайный начальный угол
        fx, fy = self.FROG_POS # центр спирали (позиция лягушки)
        # генерация точек спирали
        for i in range(num_pts):
            t = i / (num_pts - 1) # прогресс от 0 до 1
            r = start_r - (start_r - end_r) * t # радиус уменьшается линейно
            angle = start_angle + t * total_rot * 2 * math.pi # угол увеличивается
            # преобразуем полярные координаты (r, angle) в декартовы (x, y)
            raw_pts.append((fx + r * math.cos(angle), fy + r * math.sin(angle)))
        # вычисляет накопленные расстояния для быстрого двоичного поиска
        self.path_pts = raw_pts
        self.path_cum_dist = [0.0] # расстояние от начала пути до точки i
        for i in range(len(raw_pts) - 1):
            dx = raw_pts[i + 1][0] - raw_pts[i][0]
            dy = raw_pts[i + 1][1] - raw_pts[i][1]
            self.path_cum_dist.append(self.path_cum_dist[-1] + math.hypot(dx, dy))
        self.path_total_len = self.path_cum_dist[-1] # общая длина пути

    # УПРАВЛЕНИЕ СКОРОСТЬЮ
    def _update_speed_for_level(self):
        """
       Увеличивает скорость цепочки на 20% за каждый уровень.
       Формула: базовая_скорость * (1+номер_уровня*0.2)
       Максимум: 1.5
        """
        self.speed = min(BASE_CHAIN_SPEED * (1 + self.current_level_idx * 0.2), 1.5) # максимум 1.5

    # ПРЕОБРАЗОВЫВАЕТ РАССТОЯНИЕ В КООРДИНАТЫ
    def _get_pos_from_dist(self, dist):
        """
        По расстоянию вдоль пути возвращает координаты (x, y).
        Использует двоичный поиск (bisect) для нахождения сегмента пути,
        затем линейную интерполяцию для точной позиции внутри сегмента.
        Аргументы: dist: расстояние от начала пути в пикселях
        Возвращает: кортеж (x, y)
        """
        # граничные случаи
        if dist <= 0: return self.path_pts[0] # начало пути
        if dist >= self.path_total_len: return self.path_pts[-1] # конец пути
        # двоичный поиск: находим индекс сегмента, в котором лежит dist
        idx = bisect.bisect_left(self.path_cum_dist, dist) - 1
        if idx < 0: idx = 0
        # линейная интерполяция внутри сегмента
        seg_len = self.path_cum_dist[idx + 1] - self.path_cum_dist[idx]
        if seg_len > 0: frac = (dist - self.path_cum_dist[idx]) / seg_len # доля внутри сегмента
        else: frac = 0
        p1, p2 = self.path_pts[idx], self.path_pts[idx + 1]
        # интерполируем координаты
        return p1[0] + (p2[0] - p1[0]) * frac, p1[1] + (p2[1] - p1[1]) * frac

    # СПАВН ЦЕПОЧКИ ШАРОВ
    def _spawn_chain(self):
        """
        Создает начальную цепочку шаров для текущего уровня.
        Шары располагаются с отрицательным смещением, чтобы они появлялись постепенно.
        """
        lvl = LEVELS[self.current_level_idx]
        self.chain.clear()
        for i in range(lvl["chain_length"]):
            # каждый следующий шар на BALL_SPACING позади предыдущего
            self.chain.append(Ball(random.choice(self.colors_pool), -i * self.BALL_SPACING))
        # сортирует по расстоянию (от начала пути к концу)
        self.chain.sort(key=lambda b: b.dist)

    # КОРРЕКТИРОВКА РАССТОЯНИЙ МЕЖДУ ШАРАМИ
    def _recalc_spacing(self, start_idx=0):
        """
        Корректирует расстояние между шарами, чтобы они не перекрывались.
        Если шары слишком близко - раздвигает их.
        Если слишком далеко - сдвигает друг к другу.
        Аргументы: start_index: индекс, с которого начать проверку (для оптимизации)
        """
        for i in range(start_idx, len(self.chain)):
            # минимальное расстояние = позиция предыдущего шара + BALL_SPACING
            min_dist = (self.chain[i - 1].dist + self.BALL_SPACING) if i > 0 else 0
            if self.chain[i].dist < min_dist:
                # шар слишком близко - отодвигаем назад
                self.chain[i].dist = min_dist
            elif i > 0 and self.chain[i].dist > self.chain[i - 1].dist + self.BALL_SPACING + 0.1:
                # шар слишком далеко - подтягиваем обратно
                self.chain[i].dist = self.chain[i - 1].dist + self.BALL_SPACING

    # ИГРОВОЙ ЦИКЛ
    # запускает бесконечный цикл обновления игры (60 FPS)
    def _start_loop(self):
        self._tick()

    def _tick(self):
        """
        один кадр игры: обновление физики, проверка столкновений, отрисовка.
        Вызывается каждые 16 мс (примерно 60 кадров в секунду).
        """
        # если игра на паузе - только отрисовывает, физику не трогает
        if self.state == "paused":
            self._draw()
            self.root.after(16, self._tick)
            return
        # если игра активна - обновляем физику и проверяем условия
        if self.state == "playing":
            self._update_physics() # движение шаров и снаряда
            self._check_collisions() # столкновение снарядов с цепочкой
            self._check_win_lose() # проверка победы/поражения

        self.frog_breathe += 0.05 # анимация дыхания лягушки (всегда активна)
        self._update_particles() # обновляет взрывные частицы
        # фоновые частицы обновляются только во время игры
        if self.state == "playing":
            self._update_background()
        self._draw() # отрисовка всего текущего состояния
        self.root.after(16, self._tick) # запланированный следующий кадр через 16 мс

    # ФОНОВЫЕ ЭФФЕКТЫ
    def _setup_background(self):
        """
        Создает фон для игрового уровня в соответствии с темой.
        Включает: заливку цветом, концентрические кольца, путь, декор, частицы.
        """
        # удаляем старые фоновые элементы
        self.canvas.delete("bg_layer")
        self.canvas.delete("bg_ambient")
        self.bg_particles = []

        # выбор темы для текущего уровня
        theme = LEVEL_THEMES[self.current_level_idx % len(LEVEL_THEMES)]
        self.current_theme = theme

        # заливка фона цветом темы
        self.canvas.create_rectangle(0, 0, self.screen_w, self.screen_h, fill=theme["base"], tags="bg_layer")
        # декоративные концентрические кольца
        cx, cy = self.FROG_POS
        for r in range(int(400 * self.sc), int(50 * self.sc), -int(20 * self.sc)):
            br, bg, bb = self._hex_to_rgb(theme["base"])
            # создание более темного оттенка для колец
            dark = f"#{max(0,br-15):02x}{max(0,bg-15):02x}{max(0,bb-15):02x}"
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=dark, width=int(4*self.sc), tags="bg_layer")

        # отрисовка пути (тройная линия для эффекта объема)
        path_line = [coord for i, p in enumerate(self.path_pts) for coord in p if i % 4 == 0]
        self.canvas.create_line(path_line, fill="#1a1a2e", width=int(8*self.sc), smooth=True, tags="bg_layer")
        self.canvas.create_line(path_line, fill="#16213e", width=int(5*self.sc), smooth=True, tags="bg_layer")
        self.canvas.create_line(path_line, fill="#0f3460", width=int(2*self.sc), smooth=True, tags="bg_layer")

        # специфические элементы темы (звезды, споры)
        if theme["style"] == "stars":
            for _ in range(20):
                x, y = random.uniform(0, 800), random.uniform(0, 600)
                self.canvas.create_line(x-4, y, x+4, y, fill=theme["accent"], width=1, tags="bg_layer")
        elif theme["style"] == "spores":
            for _ in range(12):
                x, y = random.uniform(0, 800), random.uniform(0, 600)
                self.canvas.create_polygon(x-6,y-6, x+6,y, x-6,y+6, fill=theme["accent"], tags="bg_layer")
        # фоновые парящие частицы
        r, g, b = self._hex_to_rgb(theme["accent"])
        dim_color = f"#{r // 5:02x}{g // 5:02x}{b // 5:02x}" # приглушенный цвет

        for _ in range(theme["particles"]):
            x = random.uniform(0, self.screen_w)
            y = random.uniform(0, self.screen_h)
            size = random.uniform(1, 3.5) * self.sc
            vx = random.uniform(-0.15, 0.15) * self.sx
            vy = random.uniform(-0.2, -0.05) * self.sy if theme["style"] != "embers" else random.uniform(-0.3, -0.1) * self.sy

            oid = self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=dim_color, outline="", tags="bg_ambient")
            # сохраняем данные частицы для обновления
            self.bg_particles.append({"id": oid, "x": x, "y": y, "vx": vx, "vy": vy, "size": size})

    def _setup_menu_background(self):
        """ создает фон для меню (градиент без частиц)"""
        # полная очистка всех слоев
        self.canvas.delete("all")
        self.canvas.delete("bg_layer")
        self.canvas.delete("bg_ambient")
        self.canvas.delete("menu_layer")
        self.canvas.delete("game_layer")
        self.canvas.delete("pause_layer")

        self._draw_gradient("#0f172a", "#005f73") # от темно синего к бирюзовому
        self.bg_particles.clear()

    def _update_background(self):
        """
        Обновляет координаты фоновых частиц и перерисовывает их.
        Создает эффект парящих частиц.
        """
        if not self.bg_particles: return
        for p in self.bg_particles:
            p["x"] += p["vx"] # обновление Х
            p["y"] += p["vy"] # обновление Y
            # зацикливание при выходе за границы экрана
            if p["y"] < -10: p["y"] = self.screen_h + 10
            if p["y"] > self.screen_h + 10: p["y"] = -10
            if p["x"] < -10: p["x"] = self.screen_w + 10
            if p["x"] > self.screen_w + 10: p["x"] = -10
            # обновление позиции на canvas
            self.canvas.coords(p["id"], p["x"] - p["size"], p["y"] - p["size"], p["x"] + p["size"], p["y"] + p["size"])

    # ЧАСТИЦЫ ВЗРЫВА
    def _update_particles(self):
        """
        Обновляет взрывные частицы: движение, угасание, удаление мертвых.
        """
        for p in self.particles[:]: # копируем список, чтобы безопасно удалить
            p.x += p.vx # движение
            p.y += p.vy
            p.life -= p.decay # угасание
            p.vx *= 0.98 # затухание скорости
            p.vy *= 0.98
            if p.life <= 0:
                self.particles.remove(p) # удаление мертвой частицы

    def _spawn_explosion(self, x, y, color, count=6):
        """
        Создает count частиц взрыва в заданной точке.
        Вызывается при уничтожении группы шаров.
        """
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    # ОБНОВЛЕНИЕ ФИЗИКИ
    def _update_physics(self):
        """
        Обновляет физику: движение цепочки, снаряда, сглаживание визуальных позиций.
        """
        for ball in self.chain: # движение шаров вдоль пути
            ball.dist += self.speed * self.sc # каждый шар продвигается вперед на speed пикселей
        # убирает шары, которые ушли за пределы пути (достигли центра)
        self.chain = [b for b in self.chain if b.dist < self.path_total_len - 20 * self.sc]

        # движение снаряда (если есть)
        if self.projectile:
            self.projectile["x"] += self.projectile["dx"]
            self.projectile["y"] += self.projectile["dy"]
            # если снаряд вылетел за пределы экрана - убираем его
            if not (0 <= self.projectile["x"] <= self.screen_w and 0 <= self.projectile["y"] <= self.screen_h):
                self.projectile = None

        for ball in self.chain: # плавное сглаживание визуальных позиций шаров
            # стремится к dist с коэффициентом ROLLBACK_LERP
            ball.visual_dist += (ball.dist - ball.visual_dist) * ROLLBACK_LERP

        self._recalc_spacing() # корректировка расстояний, чтобы шары не наезжали друг на друга

    # ПРОВЕРКА СТОЛКНОВЕНИЙ
    def _check_collisions(self):
        """
        Проверяет, попал ли снаряд в цепочку шаров.
        Если да - вставляет шар в цепочку и проверяет совпадения.
        """
        if not self.projectile:
            return
        px, py = self.projectile["x"], self.projectile["y"]
        # ищет ближайший к снаряду шар
        best_idx = -1
        best_dist_sq = float("inf")
        for i, ball in enumerate(self.chain):
            pos = self._get_pos_from_dist(ball.visual_dist)
            d2 = (pos[0] - px) ** 2 + (pos[1] - py) ** 2 # квадрат расстояния
            if d2 < best_dist_sq:
                best_dist_sq = d2
                best_idx = i
        # если расстояние меньше порога (радиус шара*1.8) - произошло попадание
        if best_idx != -1 and best_dist_sq < (self.BALL_RADIUS * 1.8) ** 2:
            # вычисляет позицию для вставки нового шара (перед шаром, в который попали)
            insert_dist = self.chain[best_idx].dist - self.BALL_SPACING
            new_ball = Ball(self.projectile["color"], insert_dist)
            self.chain.insert(best_idx, new_ball)
            self.chain.sort(key=lambda b: b.dist) # сортировка по расстоянию

            self.projectile = None  # снаряд исчезает
            self._recalc_spacing(best_idx) # корректировка расстояний
            self._resolve_matches() # поиск и удаление групп из 3+ шаров

    # ОБРАБОТКА ГРУПП (МАТЧЕЙ) И ОЧКИ
    def _resolve_matches(self):
        """
        Находит все группы из 3 и более одинаковых шаров, удаляет их,
        начисляет очки, создает взрывы и повторяет процесс (каскад).
        """
        changed = True
        combo = 1 # множитель комбо (увеличивается с каждым каскадом)
        while changed:
            changed = False
            i = 0
            # расширяет группу, пока цвет совпадает
            while i < len(self.chain) - 2:
                c = self.chain[i].color
                j = i + 1
                while j < len(self.chain) and self.chain[j].color == c:
                    j += 1
                count = j - i # количество шаров в группе
                if count >= 3:
                    # взрыв для каждого шара в группе
                    for k in range(i, j):
                        pos = self._get_pos_from_dist(self.chain[k].visual_dist)
                        self._spawn_explosion(pos[0], pos[1], c, 4)
                    # начисление очков (базовые очки * множитель комбо)
                    pts = self._calc_zuma_score(count) * combo
                    self.score += pts
                    self.glow_intensity = min(1.0, self.glow_intensity + 0.3) # усиление свечения
                    del self.chain[i:j] # удаляет всю группу
                    self._recalc_spacing(i)
                    changed = True
                    combo += 1
                    i = max(0, i - 2) # откат на 2 шара назад, для проверки новых комбинаций
                else:
                    i += 1

    def _calc_zuma_score(self, count):
        """
        Расчет очков за уничтоженную группу:
        3 шара = 100
        4 шара = 200
        5+ шаров = 300 + (count - 5) * 50
        """
        if count == 3: return 100
        if count == 4: return 200
        return 300 + (count - 5) * 50

    # ПРОВЕРКА ПОБЕДЫ/ПОРАЖЕНИЯ
    def _check_win_lose(self):
        """
        Проверяет условия победы и поражения.
        Поражение: шар достигает центра
        Победа: цепочка пуста и набрано достаточно очков
        """
        # проверка поражения
        if any(b.dist >= self.path_total_len - 20 * self.sc for b in self.chain):
            self.state = "game_over"
            return
        # если цепочка пуста
        if not self.chain:
            lvl = LEVELS[self.current_level_idx]
            # пройден текущий уровень
            if self.score >= lvl["target_score"]:
                if self.current_level_idx == len(LEVELS) - 1:
                    self.state = "victory" # пройдены все уровни
                    return
                self.current_level_idx += 1
                self._update_speed_for_level()
                self.state = "level_complete"
                self._generate_path() # новая спираль для следующего уровня
                self._setup_background() # обновление фона
            else:
                self._spawn_wave() # очков недостаточно - добавляет новую волну шаров

    def _spawn_wave(self):
        """
        Добавляет 15 новых шаров в начало цепочки, когда игрок очистил ее,
        но не набрал достаточно очков.
        """
        for i in range(15):
            self.chain.append(Ball(random.choice(self.colors_pool), -i * self.BALL_SPACING))
        self.chain.sort(key=lambda b: b.dist)

    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ ГРАФИКИ И ЦВЕТА
    def _hex_to_rgb(self, hex_color):
        """
        Преобразует шестнадцатеричный цвет вида "#RRGGBB" в кортеж (R, G, B).
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _draw_gradient(self, color1, color2):
        """
        Рисует вертикальный градиент фона от color1 (верх) до color2 (низ).
        Используется для фона меню.
        """
        r1, g1, b1 = self._hex_to_rgb(color1)
        r2, g2, b2 = self._hex_to_rgb(color2)
        step = 4
        self.canvas.delete("bg_layer")
        for i in range(0, self.screen_h, step):
            ratio = i / self.screen_h # прогресс от 0 до 1
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            self.canvas.create_line(0, i, self.screen_w, i + step, fill=color, width=step, tags="bg_layer")

    # ОТРИСОВКА ТЕКСТА
    def _draw_outlined_text(self, x, y, text, fill_color, font, tags="menu_layer"):
        """
        Рисует текст с черной обводкой (для заголовков).
        Обводка создается путем рисования текста 8 раз со смещением.
        """
        # масштабируует размер шрифта
        if isinstance(font, tuple):
            name = font[0]
            size = int(font[1] * self.sc)
            weight = font[2] if len(font) > 2 else ""
            scaled_font = (name, size, weight) if weight else (name, size)
        else:
            scaled_font = font
        # черная обводка со смещением по 8 направлениям
        for dx, dy in [(-2, -2), (-2, 0), (-2, 2), (0, -2), (0, 2), (2, -2),  (2, 0),  (2, 2)]:
            sdx = int(dx * self.sc)
            sdy = int(dy * self.sc)
            self.canvas.create_text(x + sdx, y + sdy, text=text, fill="black", font=scaled_font, tags=tags)
        # основной цвет текста
        self.canvas.create_text( x, y, text=text, fill=fill_color, font=scaled_font, tags=tags)

    def _draw_button_text(self, x, y, text, font, tags="menu_layer"):
        """
        Рисует текст с белой обводкой (для кнопок).
        """
        # масштабирует размер шрифта
        if isinstance(font, tuple):
            name = font[0]
            size = int(font[1] * self.sc)
            weight = font[2] if len(font) > 2 else ""
            scaled_font = (name, size, weight) if weight else (name, size)
        else:
            scaled_font = font
        # белая обводка
        for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
            sdx = int(dx * self.sc)
            sdy = int(dy * self.sc)
            self.canvas.create_text(x + sdx, y + sdy, text=text, fill="white", font=scaled_font, tags=tags)
        # основной цвет текста темно-синий
        self.canvas.create_text(x, y, text=text, fill="#0f172a", font=scaled_font, tags=tags)

    # ОТРИСОВКА ШАРОВ
    def _draw_gradient_ball(self, x, y, radius, color, outline=True, tags="game_layer"):
        """
        Рисует объемный шар с градиентом, бликом и опциональным свечением.
        Свечение появляется при комбо.
        """
        r, g, b = self._hex_to_rgb(color)

        glow_factor = min(1.0, self.glow_intensity)
        if glow_factor > 0.5: # свечение при комбо
            for i in range(1, 0, -1):
                gr = int(r * 0.4)
                gg = int(g * 0.4)
                gb = int(b * 0.4)
                glow_color = f'#{gr:02x}{gg:02x}{gb:02x}'
                self.canvas.create_oval(
                    x - radius - i * 3 * self.sc, y - radius - i * 3 * self.sc,
                    x + radius + i * 3 * self.sc, y + radius + i * 3 * self.sc,
                    fill=glow_color, outline="", tags=tags
                )
        # градиентная заливка (два слоя для эффекта объема)
        for i in range(2, 0, -1):
            ratio = i / 5
            nr = int(r * (0.6 + 0.4 * ratio))
            ng = int(g * (0.6 + 0.4 * ratio))
            nb = int(b * (0.6 + 0.4 * ratio))
            grad_color = f'#{nr:02x}{ng:02x}{nb:02x}'
            self.canvas.create_oval(
                x - radius + i * self.sc, y - radius + i * self.sc,
                x + radius - i * self.sc, y + radius - i * self.sc,
                fill=grad_color, outline="", tags=tags
            )
        # блик
        self.canvas.create_oval(
            x - radius // 3, y - radius // 3,
            x - radius // 6, y - radius // 6,
            fill="#ffffff", outline="", tags=tags
        )
        # контур
        if outline:
            dark_color = f'#{max(0, r-40):02x}{max(0, g-40):02x}{max(0, b-40):02x}'
            self.canvas.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                outline=dark_color, width=max(1, int(2 * self.sc)), tags=tags
            )

    # ОТРИСОВКА КНОПОК
    def _draw_button(self, x1, y1, x2, y2, text, hover=False, tags="menu_layer"):
        """
        Рисует кнопку с текстом
        hover = True - кнопка подсвечивается при наведении мыши.
        """
        fill_color = "#6BB4D4" if hover else "#5FA8C7" # светлее при наведении
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="#0f172a", width=max(2, int(4 * self.sc)), tags=tags)
        self._draw_button_text((x1 + x2) // 2, (y1 + y2) // 2, text, ("Segoe UI", 14), tags)

    # ОСНОВНАЯ ОТРИСОВКА
    def _draw(self):
        """
        Главный метод отрисовки: очищает слои и вызывает соответствующие экраны
        или игровую графику в зависимости от состояния.
        """
        # очищает динамические слои
        self.canvas.delete("game_layer")
        self.canvas.delete("pause_layer")
        self.canvas.delete("menu_layer")

        # обработка разных состояний (мен., выбор уровня, правила)
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

        # ИГРОВОЙ ПРОЦЕСС

        for ball in self.chain: # рисует цепочку шаров
            x, y = self._get_pos_from_dist(ball.visual_dist)
            self._draw_gradient_ball(x, y, self.BALL_RADIUS, ball.color, tags="game_layer")

        for p in self.particles: # рисует взрывные частицы
            r, g, b = self._hex_to_rgb(p.color)
            color = f'#{r:02x}{g:02x}{b:02x}'
            size = int(4 * p.life) # размер уменьшается со временем
            self.canvas.create_oval(p.x - size, p.y - size, p.x + size, p.y + size, fill=color, outline="", tags="game_layer")

        self._draw_frog() # лягушка

        if self.projectile: # снаряд
            self._draw_gradient_ball(self.projectile["x"], self.projectile["y"], self.BALL_RADIUS, self.projectile["color"], tags="game_layer")
        # индикатор следующего шара
        fx, fy = self.FROG_POS
        self.canvas.create_oval(fx - int(50*self.sc), fy - int(50*self.sc), fx - int(25*self.sc), fy - int(20*self.sc), fill="#1a1a2e", outline="#0f3460", width=2, tags="game_layer")
        self._draw_gradient_ball(fx - int(37*self.sc), fy - int(37*self.sc), int(11*self.sc), self.next_ball, tags="game_layer")
        self.canvas.create_text(fx - int(37*self.sc), fy - int(62*self.sc), text="СЛЕД.", fill="#533483", font=("Segoe UI", 11, "bold"), tags="game_layer")
        # информационная панель (уровень, очки)
        lvl = LEVELS[self.current_level_idx]
        self.canvas.create_rectangle(int(10*self.sx), int(10*self.sy), int(280*self.sx), int(55*self.sy), fill="#1a1a2e", outline="#0f3460", width=2, tags="game_layer")
        self._draw_outlined_text(int(55*self.sx), int(22*self.sy), f"УРОВЕНЬ {lvl['id']}", "#bdefff", ("Segoe UI", 14, "bold"), "game_layer")
        self.canvas.create_text(int(30*self.sx), int(33*self.sy), text=f"Очки: {self.score} / {lvl['target_score']}", anchor="nw", fill="#ffffff", font=("Segoe UI", 11), tags="game_layer")
        # кнопка меню во время игры
        x1, y1, x2, y2, text = self.game_buttons["menu"]
        hover = x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2
        self._draw_button(x1, y1, x2, y2, text, hover=hover, tags="game_layer")
        # оверлеи для разных состояний (завершение уровня, победа, поражение)
        if self.state == "level_complete":
            self._draw_overlay(f"УРОВЕНЬ {self.current_level_idx} ПРОЙДЕН!", "#00d9ff", "Нажмите ПРОБЕЛ для следующего уровня")
        elif self.state == "game_over":
            self._draw_overlay("ИГРА ОКОНЧЕНА", "#e94560", "Нажмите R для рестарта")
        elif self.state == "victory":
            self._draw_overlay("ПОБЕДА!", "#00ff88", f"Итоговый счёт: {self.score} | Нажмите R для меню")

        # Если пауза - рисуем поверх игры
        if self.state == "paused":
            self._draw_pause()

        self.glow_intensity *= 0.95 # плавное затухание свечения

    # ЭКРАНЫ МЕНЮ
    def _draw_pause(self):
        """
        Экран паузы с затемнением, заголовком и кнопкой продолжить.
        """
        # полупрозрачное затемнение фона
        self.canvas.create_rectangle(0, 0, self.screen_w, self.screen_h, fill="#000000", stipple="gray50", tags="pause_layer")

        # заголовок
        self._draw_outlined_text(self.screen_w // 2, int(180*self.sy), "ПАУЗА", "#bdefff", ("Segoe UI", 48, "bold"))

        # кнопки
        for key, (x1, y1, x2, y2, text) in self.pause_buttons.items():
            hover = x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2
            self._draw_button(x1, y1, x2, y2, text, hover=hover, tags="pause_layer")

        # подсказка
        self.canvas.create_text(self.screen_w // 2, int(420*self.sy), text="Нажмите 'P' или кнопку 'Продолжить'", fill="#888", font=("Segoe UI", 12), tags="pause_layer")

    def _draw_menu(self):
        # главное меню
        self._draw_outlined_text(self.screen_w // 2, int(100*self.sy), "ZUMA", "#bdefff", ("Segoe UI", 48, "bold"))
        self.canvas.create_text(self.screen_w // 2, int(170*self.sy), text="Главное меню:", fill="#ffffff", font=("Segoe UI", 18), tags="menu_layer")

        for key, (x1, y1, x2, y2, text) in self.menu_buttons.items():
            hover = x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2
            self._draw_button(x1, y1, x2, y2, text, hover=hover, tags="menu_layer")

    def _draw_levels_menu(self):
        # меню выбора уровня
        self._draw_outlined_text(self.screen_w // 2, int(80*self.sy), "ВЫБОР УРОВНЯ", "#bdefff", ("Segoe UI", 32, "bold"))

        for key, (x1, y1, x2, y2, text) in self.level_buttons.items():
            hover = x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2
            self._draw_button(x1, y1, x2, y2, text, hover=hover, tags="menu_layer")
        # кнопка назад
        bx1, by1 = int(280 * self.sx), int(500 * self.sy)
        bx2, by2 = int(520 * self.sx), int(550 * self.sy)
        hover = bx1 <= self.mouse_x <= bx2 and by1 <= self.mouse_y <= by2
        self._draw_button(bx1, by1, bx2, by2, "Назад", hover=hover, tags="menu_layer")

    def _draw_rules(self):
        # экран с правилами игры
        self._draw_outlined_text(self.screen_w // 2, int(60*self.sy), "ПРАВИЛА ИГРЫ", "#bdefff", ("Segoe UI", 32, "bold"))

        rules_text = (
        "1. Стреляйте цветными шарами из лягушки\n\n"
        "2. Собирайте 3 или более шара одного цвета\n\n"
        "3. Не дайте шарам достичь центра\n\n"
        "4. Набирайте очки для прохождения уровня\n\n"
        "5. Цепочки исчезновений дают бонусы\n\n"
        "Управление:\n"
        "- Мышь - прицеливание\n"
        "- ЛКМ - выстрел\n"
        "- P - Пауза\n"
        "- R - Рестарт\n"
        "- Esc - Выход"
    )
        rx1, ry1 = int(100 * self.sx), int(90 * self.sy)
        rx2, ry2 = int(700 * self.sx), int(500 * self.sy)
        self.canvas.create_rectangle(rx1, ry1, rx2, ry2, fill="#bdefff", outline="#000000", width=2, tags="menu_layer")
        self.canvas.create_text((rx1+rx2)//2, (ry1+ry2)//2, text=rules_text, fill="#0f172a", font=("Segoe UI", int(11*self.sc)), tags="menu_layer", justify="center")
        # кнопка назад
        bx1, by1 = int(280 * self.sx), int(520 * self.sy)
        bx2, by2 = int(520 * self.sx), int(570 * self.sy)
        hover = bx1 <= self.mouse_x <= bx2 and by1 <= self.mouse_y <= by2
        self._draw_button(bx1, by1, bx2, by2, "Назад", hover=hover, tags="menu_layer")

    def _draw_start_choice(self):
        # всплывающее окно: запустить начальный уровень
        self.canvas.delete("menu_layer")
        self._draw_outlined_text(self.screen_w // 2, int(265*self.sy), "Запустить начальный уровень?", "#bdefff", ("Segoe UI", 25))

        for key, (x1, y1, x2, y2, text) in self.start_choice_buttons.items():
            hover = x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2
            self._draw_button(x1, y1, x2, y2, text, hover=hover, tags="menu_layer")

    # ОТРИСОВКА ЛЯГУШКИ
    def _draw_frog(self):
        """
        Анимированная лягушка: тело, глаза, рот со снарядом.
        Поворачивается вслед за мышью, дышит (масштаб меняется).
        """
        fx, fy = self.FROG_POS
        ang = self.frog_angle
        # дыхание: масштаб тела меняется со временем
        breathe_scale = 1 + math.sin(self.frog_breathe) * 0.03
        s = self.sc
        # тень под лягушкой
        self.canvas.create_oval(fx - int(25*s), fy + int(18*s), fx + int(25*s), fy + int(28*s), fill="#000000", outline="", tags="game_layer")
        # тело
        body_size = int(24 * s * breathe_scale)
        self.canvas.create_oval(fx - body_size, fy - body_size, fx + body_size, fy + body_size, fill="#2d6a4f", outline="#1b4332", width=max(1, int(3*s)), tags="game_layer")
        # светлое брюшко
        self.canvas.create_oval(fx - int(14*s), fy - int(10*s), fx + int(14*s), fy + int(16*s), fill="#40916c", outline="", tags="game_layer")
        # рот, куда вставляется шар
        mx = fx + math.cos(ang) * 28 * s
        my = fy + math.sin(ang) * 28 * s
        mr = int(11 * s)
        self.canvas.create_oval(mx - mr, my - mr, mx + mr, my + mr, fill="#1b4332", outline="#0d2b1d", width=max(1, int(2*s)), tags="game_layer")
        self._draw_gradient_ball(mx, my, int(7*s), self.current_ball, tags="game_layer")
        # глаза (два, поворачиваются вместе с головой)
        for off in [-0.6, 0.6]:
            ex = fx + math.cos(ang + off) * 16 * s
            ey = fy + math.sin(ang + off) * 16 * s
            er = int(7 * s)
            self.canvas.create_oval(ex - er, ey - er, ex + er, ey + er, fill="#fff", outline="#1b4332", width=1, tags="game_layer")
            pr = int(4 * s)
            self.canvas.create_oval(ex - pr, ey - pr, ex + pr, ey + pr, fill="#0a0a0f", tags="game_layer")
            hr = int(2 * s)
            self.canvas.create_oval(ex - hr, ey - hr, ex - int(0.5*s), ey - int(0.5*s), fill="#fff", tags="game_layer")

    def _draw_overlay(self, title, sub):
        """
        Затемненный оверлей с текстом (для завершения уровня, победы, поражения)
        """
        self.canvas.create_rectangle(0, 0, self.screen_w, self.screen_h, fill="#000000")
        self._draw_outlined_text(self.screen_w // 2, int(250*self.sy), title, "#bdefff", ("Segoe UI", 42, "bold"))
        self.canvas.create_text(self.screen_w // 2, int(320*self.sy), text=sub, fill="#ccc", font=("Segoe UI", int(18*self.sc)))

    # ОБРАБОТЧИК СОБЫТИЙ
    def _check_button_click(self, x, y):
        """
        Обрабатывает нажатия на все кнопки в зависимости от текущего состояния.
        Возвращает True, если клик был обработан кнопкой.
        """
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
            for key, (x1, y1, x2, y2, text) in self.start_choice_buttons.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    if key == "back":
                        self.state = "menu"
                        return True
                    elif key == "yes":
                        self.current_level_idx = 0
                        self._start_game()
                        return True
                    elif key == "no":
                        self.state = "levels"
                        return True
        elif self.state == "levels":
            # кнопка назад
            bx1, by1 = int(280 * self.sx), int(500 * self.sy)
            bx2, by2 = int(520 * self.sx), int(550 * self.sy)
            if bx1 <= x <= bx2 and by1 <= y <= by2:
                self.state = "menu"
                self._setup_menu_background()
                return True
            for key, (x1, y1, x2, y2, text) in self.level_buttons.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self.current_level_idx = key - 1
                    self._start_game()
                    return True
        elif self.state == "rules":
            # кнопка назад
            bx1, by1 = int(280 * self.sx), int(500 * self.sy)
            bx2, by2 = int(520 * self.sx), int(550 * self.sy)
            if bx1 <= x <= bx2 and by1 <= y <= by2:
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
            # кнопка меню в правом верхнем углу
            x1, y1, x2, y2, text = self.game_buttons["menu"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.state = "menu"
                self.score = 0
                self.current_level_idx = 0
                self._setup_menu_background()
                return True
        return False

    def on_mouse_move(self, event):
        """
        Отслеживает движения мыши: обновляет координаты для hover и угол лягушки.
        """
        self.mouse_x = event.x
        self.mouse_y = event.y

        # если не пауза, лягушка следит за мышью
        if self.state == "playing":
            dx = event.x - self.FROG_POS[0]
            dy = event.y - self.FROG_POS[1]
            self.frog_angle = math.atan2(dy, dx) # вычисляет угол

    def on_click(self, event):
        """
        Обработка клика мыши: кнопка меню или выстрел.
        """
        x, y = event.x, event.y
        # сначала проверка: не нажата ли какая-либо кнопка
        if self.state in ("menu", "start_choice", "levels", "rules", "paused", "playing"):
            if self._check_button_click(x, y):
                return
        # если игра активна и нет летящего снаряда - производит выстрел
        if self.state == "playing":
            if self.projectile:
                return # уже есть летящий снаряд
            rad = self.frog_angle
            speed = PROJECTILE_SPEED * self.sc
            self.projectile = {
                "x": self.FROG_POS[0], "y": self.FROG_POS[1],
                "dx": math.cos(rad) * speed,
                "dy": math.sin(rad) * speed,
                "color": self.current_ball
            }
            # текущий шар заменяется следующим, следующий генерируется заново
            self.current_ball = self.next_ball
            self.next_ball = random.choice(self.colors_pool)

    def on_key(self, event):
        """
        Обработка нажатий клавиш:
        P - пауза
        R - рестарт (с 1 уровня)
        Space - следующий уровень
        Escape - выход
        """
        key = event.keysym.lower()

        if key == "escape": # выход
            self.on_close(); return

        if key == "p": # пауза
            # переключение паузы
            if self.state == "playing":
                self.state = "paused"
            elif self.state == "paused":
                self.state = "playing"
            return
        # другие клавиши в зависимости от состояния
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

    # УПРАВЛЕНИЕ ИГРОЙ
    def _start_game(self):
        """
        Запуск новой игры: сброс состояния, генерация пути, спавн цепочки, настройка фона.
        """
        self.state = "playing"
        self._update_speed_for_level()
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
        """
        Полный сброс игры до начального уровня (при нажатии R).
        """
        self.score = 0
        self.current_level_idx = 0

        self.chain.clear()
        self.particles.clear()
        self.projectile = None

        self._start_game()

    def on_close(self):
        """
        Закрытие окна с корректным завершением программы.
        """
        self.root.destroy()
        sys.exit()
# ТОЧКА ВХОДА В ПРОГРАММУ
if __name__ == "__main__":
    ZumaGame()