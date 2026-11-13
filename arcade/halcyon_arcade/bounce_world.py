"""Glow Bounce: the rules, physics and levels (no Qt).

Glowing balls roll across a dark glass table at a steady speed. You draw
short lines of light that they bounce off; each line fades after a few
seconds. Steer every ball into a pocket of its own colour (grey pockets take
any colour). A ball in the wrong pocket costs a life and starts again.

The table is 800 x 560 units; physics runs in fixed steps.

    python3 -m halcyon_arcade.bounce_world --selftest
"""
import math
import sys

W, H = 800, 560
BALL_R = 11
POCKET_R = 22
SPEED = 170.0                  # units per second; balls never slow down
LINE_LIFE = 4.0                # seconds a light line lasts
LINE_MAX = 170.0               # longest line you can draw
MAX_LINES = 3
LIVES = 3
STEP = 1 / 240                 # physics step
COLORS = {"cyan": (64, 220, 255), "magenta": (255, 80, 200), "lime": (150, 255, 90), "amber": (255, 190, 60)}

# --------------------------------------------------------------- levels ---
# balls: (x, y, angle in degrees, colour); pockets: (x, y, colour or "any")
# walls: (x1, y1, x2, y2); movers: (x, y, w, h, dx, dy, seconds) a block sliding back and forth
# gates: (x1, y1, x2, y2) passable only travelling to the left of the line's direction
# tiles: (x, y, w, h, colour) repaint any ball that rolls over them
LEVELS = [
    {"name": "First Light", "balls": [(200, 280, 20, "cyan")], "pockets": [(700, 120, "cyan")]},
    {"name": "Two of a Kind", "balls": [(150, 150, 35, "cyan"), (150, 410, -35, "magenta")],
     "pockets": [(680, 110, "magenta"), (680, 450, "cyan")]},
    {"name": "Any Port", "balls": [(400, 280, 75, "lime"), (400, 200, 200, "amber"), (300, 360, -20, "cyan")],
     "pockets": [(80, 80, "any"), (720, 480, "any"), (720, 80, "lime")]},
    {"name": "The Wall", "balls": [(150, 280, 10, "cyan"), (150, 200, -10, "amber")],
     "pockets": [(700, 280, "cyan"), (700, 100, "amber")],
     "walls": [(420, 60, 420, 240), (420, 320, 420, 500)]},
    {"name": "Corners", "balls": [(430, 310, 45, "magenta"), (370, 310, 135, "lime"), (370, 250, 225, "cyan"),
                                  (430, 250, 315, "amber")],
     "pockets": [(60, 60, "lime"), (740, 60, "magenta"), (60, 500, "cyan"), (740, 500, "amber")]},
    {"name": "Sliding Door", "balls": [(140, 280, 0, "cyan"), (140, 180, 15, "magenta")],
     "pockets": [(720, 280, "cyan"), (720, 120, "magenta")],
     "walls": [(400, 40, 400, 200), (400, 360, 400, 520)],
     "movers": [(390, 200, 20, 80, 0, 80, 3.0)]},
    {"name": "Paint Shop", "balls": [(150, 280, 30, "cyan"), (150, 360, -30, "cyan")],
     "pockets": [(700, 100, "magenta"), (700, 460, "lime")],
     "tiles": [(330, 80, 120, 120, "magenta"), (330, 360, 120, 120, "lime")]},
    {"name": "One Way", "balls": [(600, 280, 180, "amber"), (600, 200, 160, "lime")],
     "pockets": [(100, 280, "amber"), (100, 100, "lime")],
     "gates": [(400, 520, 400, 40)], "walls": [(250, 180, 250, 380)]},
    {"name": "Crossfire", "balls": [(100, 100, 30, "cyan"), (700, 100, 150, "magenta"), (100, 460, -30, "lime"),
                                    (700, 460, 210, "amber")],
     "pockets": [(400, 60, "any"), (400, 500, "any"), (60, 280, "cyan"), (740, 280, "magenta")],
     "movers": [(380, 240, 40, 80, 160, 0, 4.0)]},
    {"name": "Maze Runner", "balls": [(80, 80, 0, "lime"), (80, 480, 0, "cyan")],
     "pockets": [(720, 480, "lime"), (720, 80, "cyan")],
     "walls": [(220, 0, 220, 380), (420, 180, 420, 560), (620, 0, 620, 380)]},
    {"name": "Recolour", "balls": [(150, 140, 20, "amber"), (150, 420, -20, "amber"), (400, 280, 90, "lime")],
     "pockets": [(700, 80, "cyan"), (700, 480, "magenta"), (400, 520, "lime")],
     "tiles": [(380, 60, 90, 90, "cyan"), (380, 410, 90, 90, "magenta")],
     "walls": [(300, 230, 500, 230)]},
    {"name": "Grand Finale", "balls": [(120, 120, 25, "cyan"), (120, 440, -25, "magenta"), (680, 120, 155, "lime"),
                                       (680, 440, 205, "amber"), (400, 280, 60, "cyan")],
     "pockets": [(400, 40, "cyan"), (40, 280, "magenta"), (760, 280, "lime"), (400, 520, "amber"), (60, 60, "any")],
     "walls": [(250, 200, 250, 360), (550, 200, 550, 360)],
     "movers": [(380, 140, 40, 40, 0, 240, 5.0)],
     "gates": [(330, 280, 470, 280)],
     "tiles": [(560, 60, 80, 60, "cyan")]},
]


# ------------------------------------------------------------ geometry ---
def closest_on_segment(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L))
    return x1 + t * dx, y1 + t * dy


def reflect(vx, vy, nx, ny):
    """Bounce a velocity off a surface with unit normal (nx, ny)."""
    d = vx * nx + vy * ny
    return vx - 2 * d * nx, vy - 2 * d * ny


def rect_segments(x, y, w, h):
    return [(x, y, x + w, y), (x + w, y, x + w, y + h), (x + w, y + h, x, y + h), (x, y + h, x, y)]


class Ball:
    def __init__(self, x, y, angle, color):
        a = math.radians(angle)
        self.start = (x, y, angle, color)
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = math.cos(a) * SPEED, math.sin(a) * SPEED
        self.color = color
        self.trail = []

    def reset(self):
        self.__init__(*self.start)


class World:
    """One level in play."""
    def __init__(self, level_index):
        self.index = level_index
        L = LEVELS[level_index]
        self.name = L["name"]
        self.balls = [Ball(*b) for b in L["balls"]]
        self.pockets = list(L["pockets"])
        self.walls = list(L.get("walls", []))
        self.movers = [list(m) for m in L.get("movers", [])]
        self.gates = list(L.get("gates", []))
        self.tiles = list(L.get("tiles", []))
        self.lines = []                         # [x1, y1, x2, y2, age]
        self.time = 0.0
        self.lives = LIVES
        self.points = 0
        self.events = []                        # ("sunk"|"wrong"|"bounce"|"paint", x, y) for sounds and sparkles

    # -- player
    def add_line(self, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy)
        if d < 12:
            return False
        if d > LINE_MAX:                        # clip to the longest allowed
            x2, y2 = x1 + dx / d * LINE_MAX, y1 + dy / d * LINE_MAX
        self.lines.append([x1, y1, x2, y2, 0.0])
        del self.lines[:-MAX_LINES]
        return True

    # -- state
    @property
    def done(self):
        return not self.balls

    @property
    def lost(self):
        return self.lives <= 0

    def mover_rect(self, m):
        x, y, w, h, dx, dy, secs = m
        f = (1 - math.cos(self.time / secs * math.tau)) / 2       # 0 -> 1 -> 0, smoothly
        return x + dx * f, y + dy * f, w, h

    def solid_segments(self):
        segs = [tuple(w) for w in self.walls]
        segs += [(l[0], l[1], l[2], l[3]) for l in self.lines]
        for m in self.movers:
            segs += rect_segments(*self.mover_rect(m))
        return segs

    # -- physics
    def update(self, dt):
        steps = max(1, int(round(dt / STEP)))
        for _ in range(steps):
            self._step(dt / steps)
        for l in self.lines:
            l[4] += dt
        self.lines = [l for l in self.lines if l[4] < LINE_LIFE]

    def _step(self, dt):
        self.time += dt
        segs = self.solid_segments()
        for b in self.balls:
            px, py = b.x, b.y
            b.x += b.vx * dt
            b.y += b.vy * dt
            # table edges
            if b.x < BALL_R:
                b.x, b.vx = BALL_R, abs(b.vx)
            elif b.x > W - BALL_R:
                b.x, b.vx = W - BALL_R, -abs(b.vx)
            if b.y < BALL_R:
                b.y, b.vy = BALL_R, abs(b.vy)
            elif b.y > H - BALL_R:
                b.y, b.vy = H - BALL_R, -abs(b.vy)
            for s in segs:
                self._collide(b, *s)
            for g in self.gates:
                self._gate(b, px, py, *g)
            for tx, ty, tw, th, color in self.tiles:
                if tx <= b.x <= tx + tw and ty <= b.y <= ty + th and b.color != color:
                    b.color = color
                    self.events.append(("paint", b.x, b.y))
        self._balls_bounce()
        self._pockets()

    def _collide(self, b, x1, y1, x2, y2):
        cx, cy = closest_on_segment(b.x, b.y, x1, y1, x2, y2)
        dx, dy = b.x - cx, b.y - cy
        d = math.hypot(dx, dy)
        if d >= BALL_R:
            return False
        if d < 1e-6:                           # dead centre on the line: use the line's normal
            lx, ly = x2 - x1, y2 - y1
            ln = math.hypot(lx, ly) or 1
            dx, dy, d = -ly / ln, lx / ln, 1.0
        nx, ny = dx / d, dy / d
        if b.vx * nx + b.vy * ny < 0:          # only bounce when moving into it
            b.vx, b.vy = reflect(b.vx, b.vy, nx, ny)
            self.events.append(("bounce", b.x, b.y))
        b.x, b.y = cx + nx * BALL_R, cy + ny * BALL_R
        return True

    def _gate(self, b, px, py, x1, y1, x2, y2):
        """A one-way gate: crossing from its right side to its left is allowed, the other way bounces."""
        side = lambda x, y: (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        before, after = side(px, py), side(b.x, b.y)
        if before < 0 <= after or before <= 0 < after:
            pass                                # right -> left: through
        elif before > 0 >= after:
            cx, cy = closest_on_segment(b.x, b.y, x1, y1, x2, y2)
            if math.hypot(b.x - cx, b.y - cy) <= BALL_R * 1.5:
                lx, ly = x2 - x1, y2 - y1
                ln = math.hypot(lx, ly) or 1
                nx, ny = -ly / ln, lx / ln      # pointing to the allowed side's opposite
                b.vx, b.vy = reflect(b.vx, b.vy, nx, ny)
                b.x, b.y = px, py
                self.events.append(("bounce", b.x, b.y))

    def _balls_bounce(self):
        bs = self.balls
        for i in range(len(bs)):
            for j in range(i + 1, len(bs)):
                a, b = bs[i], bs[j]
                dx, dy = b.x - a.x, b.y - a.y
                d = math.hypot(dx, dy)
                if 0 < d < BALL_R * 2:
                    nx, ny = dx / d, dy / d
                    va, vb = a.vx * nx + a.vy * ny, b.vx * nx + b.vy * ny
                    if va - vb > 0:             # approaching: swap the normal parts (equal masses)
                        a.vx += (vb - va) * nx
                        a.vy += (vb - va) * ny
                        b.vx += (va - vb) * nx
                        b.vy += (va - vb) * ny
                    for ball in (a, b):        # balls keep a steady speed: only directions change
                        v = math.hypot(ball.vx, ball.vy) or 1
                        ball.vx, ball.vy = ball.vx / v * SPEED, ball.vy / v * SPEED
                    push = (BALL_R * 2 - d) / 2
                    a.x -= nx * push
                    a.y -= ny * push
                    b.x += nx * push
                    b.y += ny * push

    def _pockets(self):
        keep = []
        for b in self.balls:
            sunk = False
            for px, py, color in self.pockets:
                if math.hypot(b.x - px, b.y - py) < POCKET_R - BALL_R * 0.3:
                    sunk = True
                    if color in ("any", b.color):
                        self.points += 100 if color == b.color else 50
                        self.events.append(("sunk", px, py))
                    else:
                        self.lives -= 1
                        self.events.append(("wrong", px, py))
                        b.reset()
                        keep.append(b)
                    break
            if not sunk:
                keep.append(b)
        self.balls = keep

    def bonus(self):
        """Clearing a level quickly earns extra points."""
        return max(0, int(600 - self.time * 6)) + self.lives * 100


def validate(level):
    """Problems with a level's data (empty list = fine)."""
    out = []
    for key in ("name", "balls", "pockets"):
        if key not in level:
            out.append(f"missing {key}")
    pocket_colors = {p[2] for p in level.get("pockets", [])}
    tile_colors = {t[4] for t in level.get("tiles", [])}
    for x, y, a, c in level.get("balls", []):
        if c not in COLORS:
            out.append(f"unknown colour {c}")
        if not (BALL_R <= x <= W - BALL_R and BALL_R <= y <= H - BALL_R):
            out.append(f"ball outside the table at {x},{y}")
        reachable = {c} | tile_colors
        if not (pocket_colors & reachable or "any" in pocket_colors):
            out.append(f"no pocket for a {c} ball")
    for x, y, c in level.get("pockets", []):
        if c != "any" and c not in COLORS:
            out.append(f"unknown pocket colour {c}")
        if not (0 <= x <= W and 0 <= y <= H):
            out.append(f"pocket outside the table at {x},{y}")
    return out


# ---------------------------------------------------------------- selftest ---
def _selftest():
    assert reflect(1, 0, -1, 0) == (-1, 0)
    assert closest_on_segment(5, 5, 0, 0, 10, 0) == (5, 0)
    assert closest_on_segment(-5, 5, 0, 0, 10, 0) == (0, 0)
    # a ball heading at a wall bounces back
    w = World(0)
    b = w.balls[0]
    b.x, b.y, b.vx, b.vy = 400, 300, SPEED, 0
    w.walls = [(430, 200, 430, 400)]
    w.pockets = []
    w.update(0.5)
    assert b.vx < 0 and b.x < 430, (b.x, b.vx)
    # a light line works the same way, and fades
    w = World(0)
    b = w.balls[0]
    b.x, b.y, b.vx, b.vy = 400, 300, 0, SPEED
    w.pockets = []
    assert w.add_line(350, 340, 450, 340)
    assert not w.add_line(10, 10, 12, 12)          # too short
    w.update(0.5)
    assert b.vy < 0, b.vy
    w.update(LINE_LIFE)
    assert not w.lines
    # lines are clipped to LINE_MAX and only MAX_LINES are kept
    w.add_line(0, 0, 1000, 0)
    assert abs(math.hypot(w.lines[-1][2], w.lines[-1][3]) - LINE_MAX) < 1e-6
    for i in range(5):
        w.add_line(0, i * 30, 50, i * 30)
    assert len(w.lines) == MAX_LINES
    # right pocket scores, wrong pocket costs a life and restarts the ball
    w = World(1)
    w.pockets = [(400, 300, "cyan"), (100, 100, "magenta")]
    cyan = next(b for b in w.balls if b.color == "cyan")
    mag = next(b for b in w.balls if b.color == "magenta")
    cyan.x, cyan.y = 400, 300
    mag.x, mag.y = 600, 450
    w._pockets()
    assert cyan not in w.balls and w.points == 100
    mag.x, mag.y = 400, 300
    w._pockets()
    assert w.lives == LIVES - 1 and mag in w.balls and (mag.x, mag.y) == mag.start[:2]
    # balls never leave the table and keep their speed
    for i in range(len(LEVELS)):
        w = World(i)
        for _ in range(600):
            w.update(1 / 60)
        for b in w.balls:
            assert BALL_R - 1 <= b.x <= W - BALL_R + 1 and BALL_R - 1 <= b.y <= H - BALL_R + 1, (i, b.x, b.y)
            assert abs(math.hypot(b.vx, b.vy) - SPEED) < 1.0, (i, math.hypot(b.vx, b.vy))
    # a one-way gate lets balls through one way only
    w = World(0)
    w.pockets = []
    w.gates = [(400, 560, 400, 0)]                     # pointing up: its left side is x > 400... check both
    b = w.balls[0]
    b.x, b.y, b.vx, b.vy = 380, 280, SPEED, 0
    w.update(0.4)
    went_right = b.x > 400
    b.x, b.y, b.vx, b.vy = 420, 280, -SPEED, 0
    w.update(0.4)
    went_left = b.x < 400
    assert went_right != went_left, (went_right, went_left)
    # tiles repaint
    w = World(6)
    b = w.balls[0]
    b.x, b.y = 390, 140
    w._step(STEP)
    assert b.color == "magenta"
    for i, L in enumerate(LEVELS):
        assert not validate(L), (i, validate(L))
    assert len(LEVELS) >= 12
    print(f"bounce selftest ok: {len(LEVELS)} levels")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
