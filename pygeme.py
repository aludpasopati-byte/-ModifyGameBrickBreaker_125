import array
import math
import random

import pygame

# Mixer harus diatur sebelum pygame.init() (mono, 16-bit)
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# Dimensi layar
WIDTH, HEIGHT = 600, 500

# Warna
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 80, 80)
CYAN = (60, 220, 255)
YELLOW = (255, 225, 80)
ICE = (170, 220, 255)  # blok kaca (tahan 2 kali pukul)

# Warna blok normal, satu warna per baris
ROW_COLORS = [
    (255, 90, 110),
    (255, 160, 70),
    (255, 220, 80),
    (110, 230, 130),
    (90, 170, 255),
    (190, 120, 255),
]

font = pygame.font.Font('freesansbold.ttf', 15)
bigFont = pygame.font.Font('freesansbold.ttf', 30)
popFont = pygame.font.Font('freesansbold.ttf', 22)

# Warna teks "Aguyy!"
POP_COLORS = [
    (255, 235, 90),
    (255, 140, 200),
    (120, 255, 170),
    (130, 210, 255),
    (255, 170, 80),
]

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Block Breaker")

clock = pygame.time.Clock()
FPS = 30


# ---------------------------------------------------------------
# Latar belakang gradasi (dibuat sekali saja)
# ---------------------------------------------------------------
def makeBackground():
    surf = pygame.Surface((WIDTH, HEIGHT))
    top, bottom = (15, 10, 45), (5, 40, 70)
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t)
                      for i in range(3))
        pygame.draw.line(surf, color, (0, y), (WIDTH, y))
    return surf


background = makeBackground()


# ---------------------------------------------------------------
# Suara (dibuat lewat kode, tanpa file eksternal)
# ---------------------------------------------------------------
def makeSound(samples):
    """Ubah list nilai -1..1 menjadi pygame Sound."""
    buf = array.array('h')
    for v in samples:
        v = max(-1.0, min(1.0, v))
        buf.append(int(v * 32767 * 0.6))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def glassBreakSound():
    # Retakan noise singkat + pecahan denting frekuensi tinggi
    sr, dur = 44100, 0.6
    freqs = [random.uniform(2500, 7000) for _ in range(14)]
    starts = [random.uniform(0, 0.28) for _ in freqs]
    out = []
    for i in range(int(sr * dur)):
        t = i / sr
        v = random.uniform(-1, 1) * math.exp(-t * 55) * 0.9
        for f, s in zip(freqs, starts):
            if t >= s:
                dt = t - s
                v += math.sin(2 * math.pi * f * dt) * math.exp(-dt * 16) * 0.11
        out.append(v)
    return makeSound(out)


def tinkSound():
    # Denting kaca pendek untuk blok yang retak
    sr, dur = 44100, 0.18
    out = []
    for i in range(int(sr * dur)):
        t = i / sr
        v = (math.sin(2 * math.pi * 3200 * t)
             + 0.5 * math.sin(2 * math.pi * 4800 * t)) * math.exp(-t * 28)
        out.append(v * 0.5)
    return makeSound(out)


def thumpSound():
    # Pantulan di striker
    sr, dur = 44100, 0.12
    out = []
    for i in range(int(sr * dur)):
        t = i / sr
        out.append(math.sin(2 * math.pi * 220 * t) * math.exp(-t * 30) * 0.8)
    return makeSound(out)


try:
    if pygame.mixer.get_init() is None:
        raise pygame.error("mixer tidak tersedia")
    SND_BREAK = [glassBreakSound() for _ in range(3)]  # beberapa variasi
    SND_TINK = tinkSound()
    SND_THUMP = thumpSound()
except pygame.error:
    SND_BREAK, SND_TINK, SND_THUMP = [], None, None


def play(sound):
    if sound is not None:
        sound.play()


def playBreak():
    if SND_BREAK:
        random.choice(SND_BREAK).play()


# ---------------------------------------------------------------
# Partikel pecahan kaca
# ---------------------------------------------------------------
particles = []


def spawnShards(rect, color, count=14):
    for _ in range(count):
        particles.append({
            "x": rect.centerx + random.uniform(-rect.width / 2, rect.width / 2),
            "y": rect.centery + random.uniform(-rect.height / 2, rect.height / 2),
            "vx": random.uniform(-4, 4),
            "vy": random.uniform(-5, 1),
            "life": random.randint(15, 30),
            "size": random.randint(3, 7),
            "angle": random.uniform(0, math.tau),
            "color": color,
        })


def updateParticles():
    for p in particles[:]:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.4  # gravitasi
        p["angle"] += 0.3
        p["life"] -= 1
        if p["life"] <= 0:
            particles.remove(p)


def drawParticles():
    for p in particles:
        s = p["size"]
        a = p["angle"]
        pts = [(p["x"] + math.cos(a + k * 2.1) * s * (1.2 if k == 0 else 0.7),
                p["y"] + math.sin(a + k * 2.1) * s * (1.2 if k == 0 else 0.7))
               for k in range(3)]
        fade = min(1.0, p["life"] / 12)
        color = tuple(int(c * fade) for c in p["color"])
        pygame.draw.polygon(screen, color, pts)


# ---------------------------------------------------------------
# Api di belakang bola
# ---------------------------------------------------------------
flames = []


def spawnFlames(ball, count=3):
    for _ in range(count):
        life = random.randint(8, 16)
        flames.append({
            "x": ball.posx + random.uniform(-3, 3),
            "y": ball.posy + random.uniform(-3, 3),
            # Api menyembur ke belakang arah gerak bola dan sedikit naik
            "vx": -ball.xFac * random.uniform(0.3, 1.5) + random.uniform(-1, 1),
            "vy": -ball.yFac * random.uniform(0.3, 1.5) - random.uniform(0.5, 2),
            "life": life,
            "maxlife": life,
            "size": ball.radius,
        })


def updateFlames():
    for f in flames[:]:
        f["x"] += f["vx"]
        f["y"] += f["vy"]
        f["life"] -= 1
        if f["life"] <= 0:
            flames.remove(f)


def drawFlames():
    for f in flames:
        ratio = f["life"] / f["maxlife"]
        if ratio > 0.66:
            color = (255, 225, 100)   # kuning (panas)
        elif ratio > 0.33:
            color = (255, 140, 30)    # oranye
        else:
            color = (200, 45, 20)     # merah (mulai padam)
        radius = max(1, int(f["size"] * ratio) + 1)
        pygame.draw.circle(screen, color, (int(f["x"]), int(f["y"])), radius)


# ---------------------------------------------------------------
# Teks "Aguyy!" yang melayang saat bola kena blok
# ---------------------------------------------------------------
popups = []


def spawnPopup(rect):
    color = random.choice(POP_COLORS)
    word = "Aguyy!"
    base = popFont.render(word, True, color)
    outline = popFont.render(word, True, BLACK)

    surf = pygame.Surface(
        (base.get_width() + 4, base.get_height() + 4), pygame.SRCALPHA)
    for dx, dy in ((0, 2), (4, 2), (2, 0), (2, 4)):  # garis tepi hitam
        surf.blit(outline, (dx, dy))
    surf.blit(base, (2, 2))

    r = surf.get_rect(center=rect.center)
    r.clamp_ip(screen.get_rect())  # jangan sampai keluar layar
    popups.append({"surf": surf, "x": r.x, "y": float(r.y),
                   "life": 25, "maxlife": 25})


def updatePopups():
    for p in popups[:]:
        p["y"] -= 1.5
        p["life"] -= 1
        if p["life"] <= 0:
            popups.remove(p)


def drawPopups():
    for p in popups:
        p["surf"].set_alpha(int(255 * p["life"] / p["maxlife"]))
        screen.blit(p["surf"], (p["x"], int(p["y"])))


# ---------------------------------------------------------------
# Petir di sekitar bola
# ---------------------------------------------------------------
def lightningPoints(x0, y0, angle, length, segments, jitter):
    """Buat garis bergerigi dari (x0, y0) ke arah angle."""
    pts = [(x0, y0)]
    for k in range(1, segments + 1):
        d = length * k / segments
        px = x0 + math.cos(angle) * d
        py = y0 + math.sin(angle) * d
        if k < segments:  # ujung petir tidak digeser
            off = random.uniform(-jitter, jitter)
            px += -math.sin(angle) * off
            py += math.cos(angle) * off
        pts.append((px, py))
    return pts


def drawLightning(ball):
    # Saat bola kena blok (zap > 0), petirnya lebih banyak dan lebih panjang
    strong = ball.zap > 0
    count = random.randint(5, 7) if strong else random.randint(2, 4)

    for _ in range(count):
        angle = random.uniform(0, math.tau)
        if strong:
            length = random.uniform(50, 90)
            segments, jitter = 7, 8
        else:
            length = random.uniform(18, 38)
            segments, jitter = 5, 5
        pts = lightningPoints(ball.posx, ball.posy, angle,
                              length, segments, jitter)
        pygame.draw.lines(screen, (70, 130, 255), False, pts, 4)   # cahaya biru
        pygame.draw.lines(screen, (190, 230, 255), False, pts, 2)  # inti terang
        pygame.draw.lines(screen, WHITE, False, pts, 1)            # pusat putih


# ---------------------------------------------------------------
# Kelas Striker
# ---------------------------------------------------------------
class Striker:
    def __init__(self, posx, posy, width, height, speed, color):
        self.posx, self.posy = posx, posy
        self.width, self.height = width, height
        self.speed = speed
        self.color = color
        self.strikerRect = pygame.Rect(
            self.posx, self.posy, self.width, self.height)

    def display(self):
        pygame.draw.rect(screen, self.color, self.strikerRect,
                         border_radius=8)
        shine = pygame.Rect(self.strikerRect.x + 6, self.strikerRect.y + 3,
                            self.width - 12, 4)
        pygame.draw.rect(screen, WHITE, shine, border_radius=2)

    def update(self, xFac):
        self.posx += self.speed * xFac
        if self.posx <= 0:
            self.posx = 0
        elif self.posx + self.width >= WIDTH:
            self.posx = WIDTH - self.width
        self.strikerRect = pygame.Rect(
            self.posx, self.posy, self.width, self.height)

    def getRect(self):
        return self.strikerRect


# ---------------------------------------------------------------
# Kelas Block
# ---------------------------------------------------------------
class Block:
    def __init__(self, posx, posy, width, height, color, tough=False):
        self.posx, self.posy = posx, posy
        self.width, self.height = width, height
        self.color = color
        self.tough = tough
        self.damage = 100
        self.health = 200 if tough else 100
        self.blockRect = pygame.Rect(
            self.posx, self.posy, self.width, self.height)

    def display(self):
        if self.health <= 0:
            return
        r = self.blockRect
        pygame.draw.rect(screen, self.color, r, border_radius=4)
        # Highlight di atas supaya terlihat mengkilap
        light = tuple(min(255, c + 70) for c in self.color)
        pygame.draw.line(screen, light, (r.x + 3, r.y + 2),
                         (r.right - 4, r.y + 2), 2)
        if self.tough:
            pygame.draw.rect(screen, WHITE, r, 2, border_radius=4)
            if self.health <= 100:  # retak setelah kena sekali
                pygame.draw.lines(screen, (60, 90, 130), False, [
                    (r.x + 4, r.y + 2), (r.centerx - 2, r.centery),
                    (r.centerx + 6, r.centery - 3), (r.right - 5, r.bottom - 2)
                ], 2)

    def hit(self):
        self.health -= self.damage

    def getRect(self):
        return self.blockRect

    def getHealth(self):
        return self.health


# ---------------------------------------------------------------
# Kelas Ball
# ---------------------------------------------------------------
class Ball:
    def __init__(self, posx, posy, radius, speed, color):
        self.posx, self.posy = posx, posy
        self.radius = radius
        self.speed = speed
        self.color = color
        self.xFac, self.yFac = 1, 1
        self.zap = 0  # sisa frame petir kuat setelah kena blok
        self.ball = pygame.Rect(0, 0, radius * 2, radius * 2)
        self._syncRect()

    def _syncRect(self):
        self.ball.center = (int(self.posx), int(self.posy))

    def display(self):
        # Petir digambar lebih dulu supaya bola tetap terlihat di atasnya
        drawLightning(self)

        # Bola api: lapisan merah -> oranye -> kuning -> inti putih panas
        pos = (int(self.posx), int(self.posy))
        flicker = random.randint(0, 2)  # sedikit berkedip seperti api
        pygame.draw.circle(screen, (220, 50, 20), pos, self.radius + 3 + flicker)
        pygame.draw.circle(screen, (255, 130, 20), pos, self.radius + 1)
        pygame.draw.circle(screen, self.color, pos, self.radius - 2)
        pygame.draw.circle(screen, (255, 250, 220), pos, max(2, self.radius // 3))

    def update(self):
        if self.zap > 0:
            self.zap -= 1

        self.posx += self.xFac * self.speed
        self.posy += self.yFac * self.speed

        if self.posx <= 0:
            self.posx = 0
            self.xFac = 1
        elif self.posx >= WIDTH:
            self.posx = WIDTH
            self.xFac = -1

        if self.posy <= 0:
            self.posy = 0
            self.yFac = 1

        self._syncRect()
        return self.posy >= HEIGHT

    def reset(self):
        self.posx = WIDTH // 2
        self.posy = HEIGHT - 150
        self.xFac, self.yFac = 1, -1
        self.zap = 0
        self._syncRect()

    def hit(self):
        self.yFac *= -1

    def getRect(self):
        return self.ball


# ---------------------------------------------------------------
# Fungsi pembantu
# ---------------------------------------------------------------
def collisionChecker(rect, ball):
    return rect.colliderect(ball)


def populateBlocks(blockWidth, blockHeight, horizontalGap, verticalGap):
    listOfBlocks = []
    row = 0
    for j in range(0, HEIGHT // 2, blockHeight + verticalGap):
        for i in range(0, WIDTH, blockWidth + horizontalGap):
            if random.random() < 0.3:
                listOfBlocks.append(
                    Block(i, j, blockWidth, blockHeight, ICE, tough=True))
            else:
                color = ROW_COLORS[row % len(ROW_COLORS)]
                listOfBlocks.append(
                    Block(i, j, blockWidth, blockHeight, color))
        row += 1
    return listOfBlocks


def gameOver(score):
    text = bigFont.render("GAME OVER", True, RED)
    textRect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20))
    info = font.render(
        "Skor: " + str(score) + "  |  Tekan SPASI untuk main lagi",
        True, WHITE)
    infoRect = info.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))

    while True:
        screen.blit(background, (0, 0))
        screen.blit(text, textRect)
        screen.blit(info, infoRect)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return True

        clock.tick(FPS)


# ---------------------------------------------------------------
# Game Manager
# ---------------------------------------------------------------
def main():
    running = True
    lives = 3
    score = 0

    striker = Striker(WIDTH // 2 - 50, HEIGHT - 50, 100, 20, 10, CYAN)
    strikerXFac = 0

    ball = Ball(WIDTH // 2, HEIGHT - 150, 8, 5, YELLOW)

    blockWidth, blockHeight = 40, 15
    horizontalGap, verticalGap = 20, 20

    listOfBlocks = populateBlocks(
        blockWidth, blockHeight, horizontalGap, verticalGap)

    while running:
        screen.blit(background, (0, 0))

        scoreText = font.render("Score : " + str(score), True, WHITE)
        livesText = font.render("Lives : " + str(lives), True, RED)
        screen.blit(scoreText, (10, HEIGHT - 25))
        screen.blit(livesText, (120, HEIGHT - 25))

        if not listOfBlocks:
            listOfBlocks = populateBlocks(
                blockWidth, blockHeight, horizontalGap, verticalGap)

        if lives <= 0:
            running = gameOver(score)
            if not running:
                break

            lives = 3
            score = 0
            strikerXFac = 0
            particles.clear()
            flames.clear()
            popups.clear()
            ball.reset()
            listOfBlocks = populateBlocks(
                blockWidth, blockHeight, horizontalGap, verticalGap)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    strikerXFac = -1
                if event.key == pygame.K_RIGHT:
                    strikerXFac = 1
            if event.type == pygame.KEYUP:
                if (event.key == pygame.K_LEFT or
                        event.key == pygame.K_RIGHT):
                    strikerXFac = 0

        # Bola kena striker (hanya saat bola turun)
        if collisionChecker(striker.getRect(), ball.getRect()) \
                and ball.yFac > 0:
            ball.hit()
            ball.posy = striker.getRect().top - ball.radius
            play(SND_THUMP)

        # Bola kena blok (maksimal 1 blok per frame)
        for block in listOfBlocks[:]:
            if collisionChecker(block.getRect(), ball.getRect()):
                ball.hit()
                block.hit()
                spawnPopup(block.getRect())
                ball.zap = 6  # petir kuat selama beberapa frame

                if block.getHealth() <= 0:
                    spawnShards(block.getRect(), block.color)
                    playBreak()
                    listOfBlocks.remove(block)
                    score += 5
                else:
                    play(SND_TINK)
                break

        striker.update(strikerXFac)
        lifeLost = ball.update()
        spawnFlames(ball)
        updateParticles()
        updateFlames()
        updatePopups()

        if lifeLost:
            lives -= 1
            ball.reset()
            flames.clear()

        for block in listOfBlocks:
            block.display()
        striker.display()
        drawFlames()
        ball.display()
        drawParticles()
        drawPopups()

        pygame.display.update()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
    pygame.quit()