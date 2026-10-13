import math, random, sys, pygame
from pygame.math import Vector2

pygame.init()

W, H = 800, 700
margin_val = 50
lanes_per_side = 3
laneW = 70
roadw = laneW*lanes_per_side*2
road_l = (W - roadw)/2
ply_y = H*0.78
max_hp = 100
kmh_rate = 0.3
dashL, dashG = 30, 30
score = 0

accl = 180
brakeSpd = 450
dragVal = 0.4
steerRate = 3.0
rtRate = 1.0
maxAng = 0.4
pullAng = 0.3
pushSpd = 80
dmgSpd = 0.1
restitVal = 0.3
jmpT = 1.1
jmpL = 110

spwnRate = 2.0
maxCars = 18
laneSpd = 80
rcvrVal = 0.8

# 4 TYPES i labelled them in a dictionary fancy ik
# that's aura bro^
car_types = {
    "car": (36, 64, 60),
    "truck": (46, 84, 15),
    "bus": (36, 130, 12),
    "ramp": (30, 52, 13),
}

upgrades_dict = { # upgrade dictionary 
    "Repair": "-30 front & side",
    "Engine": "+25%",
    "Brakes": "+40%",
    "Handling": "+30%",
    "Armor": "-20%",
    "Reroll": "Try again",
}

scrn = pygame.display.set_mode((W, H))
pygame.display.set_caption("Highway")
clk = pygame.time.Clock()
fnt = pygame.font.SysFont(None, 26)
bigFont = pygame.font.SysFont(None, 72)


def main(): # game loop
    ply, cList, scrll = MainPlayer(), [], 0.0
    global score
    while True:
        dt = min(clk.tick(60)/1000, 0.05)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_u and ply.upgrades > 0 and ply.health > 0:
                apply_upgrade(ply, choose_upgrade())
                ply.upgrades -= 1
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r and ply.health <= 0:
                ply, cList, scrll = MainPlayer(), [], 0.0

        if ply.health > 0:
            update_player(ply, pygame.key.get_pressed(), dt)
            scrll += ply.forward*dt
            update_cars(cList, ply, dt)
            spawn_cars(cList, ply, dt)
            collide_cars(cList)
            collide_player(ply, cList)
            score+=1

        draw(ply, cList, scrll)



def lane_x(lane): # lane centers. 0,1,2 are coming down, 3,4,5 are going up
    return road_l + laneW*(lane + 0.5)


#movement (acceleration) and damage (steering or speed)
def update_player(player, keys, dt):
    front_ok = 1 - 0.8*player.front_damage/max_hp
    side_ok = 1 - 0.8*player.side_damage/max_hp

    if keys[pygame.K_w]:
        thrust = accl*player.engine*front_ok
    elif keys[pygame.K_s]:
        thrust = -brakeSpd*player.brakes*front_ok
    else:
        thrust = 0
    player.speed = max(0, player.speed + (thrust - dragVal*player.speed)*dt)

    neutral = player.pull*pullAng*player.side_damage/max_hp
    player.angle += (keys[pygame.K_d] - keys[pygame.K_a])*steerRate*player.handling*side_ok*dt
    player.angle += max(-rtRate*dt, min(rtRate*dt, neutral - player.angle))
    player.angle = max(-maxAng, min(maxAng, player.angle))

    player.pos.x += player.vel.x*dt
    player.pos.x = max(road_l + player.size.x/2, min(road_l + roadw - player.size.x/2, player.pos.x))

    update_jump(player, dt)
    player.notice_timer = max(0, player.notice_timer - dt)


def update_jump(player, dt): #z direction  
    if player.air > 0:
        player.air = max(0, player.air - dt)
        player.pos.y = ply_y - jmpL*math.sin(math.pi*(1 - player.air/jmpT))
        if player.air == 0:
            player.pos.y = ply_y


def update_cars(cars, player, dt): # relative motion
    for car in cars:
        target_x = lane_x(car.lane)
        car.bump_timer -= dt
        if abs(car.pos.x - target_x) < 2:
            car.pos.x, car.vel.x, car.prev_lane = target_x, 0, car.lane
            if random.random() < car.lane_chance*dt:
                new_lane = car.lane + random.choice((-1, 1))
                if new_lane // lanes_per_side == car.lane // lanes_per_side:
                    car.lane = new_lane
        else:
            car.vel.x = max(-laneSpd, min(laneSpd, (target_x - car.pos.x)*3))

        car.vel.y += (car.dir*car.base_speed - car.vel.y)*rcvrVal*dt
        car.pos += (car.vel + Vector2(0, player.forward))*dt

    cars[:] = [c for c in cars if abs(c.pos.y - H/2) <= H/2 + margin_val + c.size.y/2]


def spawn_cars(cars, player, dt): #spawns on correct side
    if len(cars) >= maxCars or random.random() > spwnRate*dt:
        return
    kind = random.choices(list(car_types), weights=[t[2] for t in car_types.values()])[0]
    car = TrafficCar(kind, random.randrange(2*lanes_per_side), random.uniform(120, 320))
    screen_vy = car.vel.y + player.forward
    car.pos.y = H/2 - math.copysign(H/2 + margin_val + car.size.y/2 - 1, screen_vy)
    if not any(car.rect.inflate(20, 80).colliderect(other.rect) for other in cars):
        cars.append(car)


#collisions:

def contact(a, b):
    overlap = a.rect.clip(b.rect)
    if overlap.w < overlap.h:
        return Vector2(math.copysign(1, b.pos.x - a.pos.x), 0), overlap.w + 1
    return Vector2(0, math.copysign(1, b.pos.y - a.pos.y)), overlap.h + 1


def collide_cars(cars): #speed transfer
    for i, a in enumerate(cars):
        for b in cars[i + 1:]:
            if not a.rect.colliderect(b.rect):
                continue
            n, depth = contact(a, b)
            a.pos -= n*depth/2
            b.pos += n*depth/2
            a.base_speed, b.base_speed = b.base_speed, a.base_speed
            a.vel.y, b.vel.y = a.dir*a.base_speed, b.dir*b.base_speed
            a.reverse_lane()
            b.reverse_lane()


def collide_player(player, cars): #ramps too
    if player.air > 0:
        return
    for car in cars:
        if not player.rect.colliderect(car.rect):
            continue
        if car.kind == "ramp" and not car.used:
            car.used = True
            player.air = jmpT
            player.upgrades += 1
            player.notice, player.notice_timer = "Ramp truck! Press U for upgrade", 3
            return

        n, depth = contact(player, car)
        side_hit = n.x != 0
        if side_hit:
            player.pos -= n*depth/2
            car.pos += n*depth/2
        else:
            car.pos += n*depth

        approach = (player.vel - car.vel).dot(n)
        if approach > 0:
            j = (1 + restitVal)*approach/(1/player.mass + 1/car.mass)
            player.set_vel(player.vel - n*j/player.mass)
            car.vel += n*j/car.mass
            car.reverse_lane()
            if approach > pushSpd:
                damage = (approach - pushSpd)*dmgSpd*player.armor
                if side_hit:
                    player.side_damage += damage
                else:
                    player.front_damage += damage



def choose_upgrade(): #upgrade menu
    boxes = [pygame.Rect(50 + i*235, 200, 220, 300) for i in range(3)]
    names = random.sample(list(upgrades_dict), 3)
    while True:
        pygame.draw.rect(scrn, (10, 25, 110), (30, 120, W - 60, H - 240))
        draw_text("Choose an upgrade (click or press 1-3)", (W/2, 160))
        for box, name in zip(boxes, names):
            pygame.draw.rect(scrn, (85, 25, 100), box)
            draw_text(name, (box.centerx, box.y + 60))
            draw_text(upgrades_dict[name], (box.centerx, box.y + 110))
        pygame.display.flip()

        for ev in pygame.event.get():
            picked = None
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                picked = next((n for box, n in zip(boxes, names) if box.collidepoint(ev.pos)), None)
            elif ev.type == pygame.KEYDOWN and pygame.K_1 <= ev.key <= pygame.K_3:
                picked = names[ev.key - pygame.K_1]
            if picked == "Reroll":
                names = random.sample(list(upgrades_dict), 3)
            elif picked:
                return picked
        clk.tick(30)


def apply_upgrade(player, name):
    if name == "Repair":
        player.front_damage = max(0, player.front_damage - 30)
        player.side_damage = max(0, player.side_damage - 30)
    elif name == "Engine":
        player.engine *= 1.25
    elif name == "Brakes":
        player.brakes *= 1.4
    elif name == "Handling":
        player.handling *= 1.3
    elif name == "Armor":
        player.armor *= 0.8
    player.notice, player.notice_timer = f"Upgrade: {name} ({upgrades_dict[name]})", 3


#render:
def draw(player, cars, scroll):
    draw_road(scroll)
    for car in cars:
        draw_car(car)
    draw_player(player)
    draw_hud(player)
    pygame.display.flip()


def draw_road(scroll):
    scrn.fill((25, 70, 25))
    pygame.draw.rect(scrn, (0, 0, 0), (road_l, 0, roadw, H))
    offset = scroll % (dashL + dashG)
    for lane in range(1, 2*lanes_per_side):
        x = road_l + lane*laneW
        if lane == lanes_per_side:
            pygame.draw.line(scrn, (255, 255, 255), (x, 0), (x, H), 4)
            continue
        for y in range(-dashL - dashG, H + margin_val, dashL + dashG):
            pygame.draw.line(scrn, (255, 255, 255), (x, y + offset), (x, y + offset + dashL), 3)


def draw_car(car):
    pygame.draw.rect(scrn, car.color, car.rect)
    if car.kind == "ramp":
        inverse = tuple(255 - c for c in car.color)
        x, y = car.pos
        pygame.draw.lines(scrn, inverse, False,
                          [(x - 10, y - 7*car.dir), (x, y + 7*car.dir), (x + 10, y - 7*car.dir)], 4)


def draw_player(player):
    scale = 1 + (ply_y - player.pos.y)/150
    corners = [player.pos + Vector2(sx*player.size.x/2, sy*player.size.y/2).rotate(math.degrees(player.angle))*scale
               for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    pygame.draw.polygon(scrn, (255, 255, 255), corners)


def draw_hud(player):
    draw_bar(pygame.Rect(10, 10, 200, 28), player.health/max_hp, (190, 40, 40), f"Health: {int(player.health)}")
    draw_bar(pygame.Rect(10, 46, 200, 28), player.speed/500, (40, 110, 190), f"{int(player.speed*kmh_rate)} km/h")
    draw_text(f"Upgrades: {player.upgrades}  [U to choose]", (150, H - 20))
    draw_text(f"Score: {score}", (50, 300)) #temp location ofc
    if player.notice_timer > 0:
        draw_text(player.notice, (W/2, 30), (255, 220, 80))
    if player.health <= 0:
        draw_text("GAME OVER :((((((((((", (W/2, H/2), (255, 60, 60), big=True)
        draw_text("Press R to try again", (W/2, H/2 + 50))


def draw_bar(rect, fraction, color, label):
    pygame.draw.rect(scrn, (40, 40, 40), rect)
    pygame.draw.rect(scrn, color, (rect.x, rect.y, rect.w*max(0, min(1, fraction)), rect.h))
    pygame.draw.rect(scrn, (255, 255, 255), rect, 2)
    draw_text(label, rect.center)


def draw_text(text, center, color=(255, 255, 255), big=False):
    surface = (bigFont if big else fnt).render(text, True, color)
    scrn.blit(surface, surface.get_rect(center=center))



class BodyObj:
    def __init__(self, pos, size):
        self.pos = Vector2(pos)
        self.size = Vector2(size)
        self.mass = self.size.x*self.size.y/2304

    @property
    def rect(self):
        return pygame.Rect(self.pos.x - self.size.x/2, self.pos.y - self.size.y/2, self.size.x, self.size.y)


class MainPlayer(BodyObj):
    def __init__(self):
        super().__init__((lane_x(lanes_per_side + 1), ply_y), (36, 64))
        self.speed = 200
        self.angle = 0.0
        self.front_damage = 0
        self.side_damage = 0
        self.pull = random.choice((-1, 1))
        self.engine = 1.0
        self.brakes = 1.0
        self.handling = 1.0
        self.armor = 1.0
        self.air = 0.0
        self.upgrades = 0
        self.notice = ""
        self.notice_timer = 0.0

    @property
    def health(self):
        return max(0, max_hp - self.front_damage - self.side_damage)

    @property
    def vel(self):
        return Vector2(math.sin(self.angle), -math.cos(self.angle))*self.speed

    @property
    def forward(self):
        return -self.vel.y

    def set_vel(self, v):
        if v.y >= 0:
            self.speed = 0
            return
        self.speed = v.length()
        self.angle = max(-maxAng, min(maxAng, math.atan2(v.x, -v.y)))


class TrafficCar(BodyObj):
    def __init__(self, kind, lane, speed):
        super().__init__((lane_x(lane), 0), car_types[kind][:2])
        self.kind = kind
        self.color = tuple(random.randint(50, 220) for _ in range(3))
        self.lane = lane
        self.prev_lane = lane
        self.dir = 1 if lane < lanes_per_side else -1
        self.base_speed = speed
        self.vel = Vector2(0, self.dir*speed)
        self.lane_chance = random.uniform(0, 0.2)
        self.bump_timer = 0.0
        self.used = False

    def reverse_lane(self): #returning to lane upon collision
        if self.bump_timer <= 0:
            self.lane, self.prev_lane = self.prev_lane, self.lane
            self.bump_timer = 0.5


if __name__ == "__main__":
    main()
