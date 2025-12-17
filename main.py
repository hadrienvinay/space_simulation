import random

import pygame
import math
import sys

pygame.init()

WHITE = (255,255,255)
YELLOW = (255,255,0)
BLUE = (0,0,255)
BLACK = (0,0,0)
ORANGE = (255,128,0)
GREEN = (0,240,0)
DARK_GREY = (80,78,81)
RED = (255,20,0)

WIDTH, HEIGHT = 1600, 1000
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("BIG BANG Simulation")

FONT = pygame.font.SysFont("comicsans", 16)
text_quit = FONT.render('QUITTER', True, BLACK)
text_refresh = FONT.render('REFRESH', True, RED)
text_reset = FONT.render('RESET', True, BLACK)
text_orbit_on = FONT.render('orbit : ON', True, BLACK)
text_orbit_off = FONT.render('orbit : OFF', True, BLACK)
text_border = FONT.render('Bordure', True, BLACK)
text_on = FONT.render('ON', True, BLACK)
text_off = FONT.render('OFF', True, BLACK)
text_duree = FONT.render('Temps écoulé', True, WHITE)
FONT = pygame.font.SysFont("comicsans", 30)
text_plus = FONT.render('+', True, BLACK)
text_moins = FONT.render('-', True, BLACK)

#AU = 149597871*1000
AU = 149.6e6 * 1000
G = 6.67428e-11
SCALE = 10 / AU # 1AU = 500 pixel
TIMESTEP = 3600 *24 # 1 day

class Particule:

    def __init__(self, x, y, radius, color, mass, type):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.mass = mass
        self.type = type

        self.orbit = []

        self.x_vel = 0
        self.y_vel = 0


    def infos(self):
        print(self.x,self.y)

    def draw(self, screen):
        #print(f"draw {self.x}")
        x = self.x * SCALE + WIDTH / 2
        y = self.y * SCALE + HEIGHT / 2

        pygame.draw.circle(screen, self.color, (x, y), self.radius)

    def draw_orbit(self, screen):
        if len(self.orbit) > 1:
            updated_points = []
            for point in self.orbit:
                x, y = point
                x = x * SCALE + WIDTH / 2
                y = y * SCALE + HEIGHT / 2
                updated_points.append((x, y))

            pygame.draw.lines(screen, self.color, False, updated_points, 2)

    def attraction(self, other):
        other_x, other_y = other.x, other.y
        distance_x = other_x - self.x
        distance_y = other_y - self.y
        distance = math.sqrt(distance_x ** 2 + distance_y ** 2)
        force = G * self.mass * other.mass / distance ** 2
        theta = math.atan2(distance_y, distance_x)
        force_x = math.cos(theta) * force
        force_y = math.sin(theta) * force
        #print(distance)
        return force_x, force_y

    def border(self):
        if self.x < WIDTH:
            if self.x_vel < 0:
                self.x_vel = -self.x_vel
                self.x_vel = self.x_vel / 1.5
                self.y_vel = self.y_vel / 1.5
        if self.x > WIDTH:
            if self.x_vel > 0:
                self.x_vel = -self.x_vel
                self.x_vel = self.x_vel / 1.5
                self.y_vel = self.y_vel / 1.5
        if self.y < HEIGHT:
            if self.y_vel < 0:
                self.y_vel = -self.y_vel
                self.x_vel = self.x_vel / 1.5
                self.y_vel = self.y_vel / 1.5
        if self.y > HEIGHT:
            if self.y_vel > 0:
                self.y_vel = -self.y_vel
                self.x_vel = self.x_vel / 1.5
                self.y_vel = self.y_vel / 1.5

    def update_position(self, particules, border):
        total_fx = total_fy = 0
        for particule in particules:
            if self == particule:
                continue
            fx, fy = self.attraction(particule)
            total_fx += fx
            total_fy += fy

        self.x_vel += total_fx / self.mass * TIMESTEP  # a = f / m * timestep (here 1 day)
        self.y_vel += total_fy / self.mass * TIMESTEP

        if border:
            self.border()
        self.x += self.x_vel * TIMESTEP
        self.y += self.y_vel * TIMESTEP

        self.orbit.append((self.x, self.y))


def init_screen(SHOW_ORBIT, BORDER):
    #init pygame screen
    SCREEN.fill(BLACK)
    # print button refresh and quit
    pygame.draw.rect(SCREEN, YELLOW, [880, 10, 100, 50])
    pygame.draw.rect(SCREEN, ORANGE, [695, 10, 100, 50])
    pygame.draw.rect(SCREEN, ORANGE, [425, 10, 50, 50])
    pygame.draw.rect(SCREEN, ORANGE, [525, 10, 50, 50])
    if BORDER == 1:
        pygame.draw.rect(SCREEN, DARK_GREY, [225, 10, 100, 50])
        SCREEN.blit(text_on, (252, 35))
    else:
        pygame.draw.rect(SCREEN, WHITE, [225, 10, 100, 50])
        SCREEN.blit(text_off, (252, 35))
    if SHOW_ORBIT == 1:
        pygame.draw.rect(SCREEN, GREEN, [10, 10, 100, 50])
        SCREEN.blit(text_orbit_on, (25, 25))
    else:
        pygame.draw.rect(SCREEN, RED, [10, 10, 100, 50])
        SCREEN.blit(text_orbit_off, (25, 25))
    SCREEN.blit(text_border, (240, 10))
    SCREEN.blit(text_plus, (440, 10))
    SCREEN.blit(text_moins, (540, 10))
    SCREEN.blit(text_reset, (705, 25))
    SCREEN.blit(text_quit, (895, 25))
    SCREEN.blit(text_duree, (WIDTH-300, 50))
    
def refresh_screen(SHOW_ORBIT,BORDER):
    init_screen(SHOW_ORBIT,BORDER)

def init_planet(tab_part):

    mercury  = Particule(0.39*AU,0,6,DARK_GREY,0.33*10**24,0)
    #mercury.y_vel = -170496 *1.6
    mercury.y_vel = -47.4 * 1000
    mercury.orbit.append((mercury.x, mercury.y))
    venus    = Particule(0.72*AU,0,12,GREEN,4.87*10**24,0)
    #venus.y_vel = -126072* 1.4
    venus.y_vel = -35.02 * 1000
    venus.orbit.append((venus.x, venus.y))
    earth    = Particule(1*AU,0,13,BLUE,5.97*10**24,0)
    #earth.y_vel = -107206* 1.3
    earth.y_vel = -29.783 * 1000
    earth.orbit.append((earth.x, earth.y))
    mars     = Particule(1.52*AU,0,7,RED,0.642*10**24,0)
    #mars.y_vel = -86425* 1.6
    mars.y_vel = -24.077 * 1000
    mars.orbit.append((mars.x, mars.y))
    jupiter  = Particule(5.2*AU,0,14,ORANGE,1.9*10**27,0)
    #jupiter.y_vel = -47052* 1.5
    jupiter.y_vel = -13.06* 1000
    jupiter.orbit.append((jupiter.x, jupiter.y))
    saturn   = Particule(9.55*AU,0,10,YELLOW,1.9*10**27,0)
    #saturn.y_vel = -34848* 1.5
    saturn.y_vel = -9.68 * 1000
    saturn.orbit.append((saturn.x, saturn.y))
    uranus   = Particule(19.22*AU,0,5,BLUE,568*10**24,0)
    #uranus.y_vel = -32480
    uranus.y_vel = -6.80 * 1000
    uranus.orbit.append((uranus.x, uranus.y))
    neptune  = Particule(30.11*AU,0,4,WHITE,0.33*10**24,0)
    #neptune.y_vel = -19548
    neptune.y_vel = -5.43 * 1000
    neptune.orbit.append((neptune.x, neptune.y))
    sun = Particule(0,0, 20, YELLOW, 1.98892 * 10**30,0)

    tab_part.append(sun)
    tab_part.append(mercury)
    tab_part.append(venus)
    tab_part.append(earth)
    tab_part.append(mars)
    tab_part.append(jupiter)
    tab_part.append(saturn)
    tab_part.append(neptune)
    tab_part.append(uranus)

def main():
    SHOW_ORBIT = 1
    BORDER = 0
    SPEED = 50
    run = True
    clock = pygame.time.Clock()
    init_screen(SHOW_ORBIT,BORDER)

    NUMBER_PARTICULES_POSITIVE = 0
    #NUMBER_PARTICULES_NEGATIVE = 50

    tab_particules = []

    init_planet(tab_particules)

    for i in range(1, NUMBER_PARTICULES_POSITIVE+1):
        new = Particule(random.randint(int(-20*AU), int(20*AU)), random.randint(int(-20*AU), int(20*AU)), 5, RED, 10*10**28, 1)
        new.x_vel = 40000 * random.randint(-3, 3)
        new.y_vel = 40000 * random.randint(-2, 2)
        tab_particules.append(new)

    pygame.display.update()
    timer = 0
    elapsed_time = 0

    while run:
        clock.tick(SPEED)
        timer += 1
        print(timer)
        init_screen(SHOW_ORBIT,BORDER)
        mouse = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                print(mouse)
            # if the mouse is clicked on the button refesh, clean screen
                if 10 <= mouse[0] <= 110 and 10 <= mouse[1] <= 60:
                    if SHOW_ORBIT == 1:
                        SHOW_ORBIT = 0
                    else:
                        SHOW_ORBIT = 1
                    refresh_screen(SHOW_ORBIT,BORDER)
                    for particule in tab_particules:
                        particule.orbit = []
                if 225 <= mouse[0] <= 325 and 10 <= mouse[1] <= 60:
                    if BORDER == 1:
                        BORDER = 0
                    else:
                        BORDER = 1
                if 425 <= mouse[0] <= 475 and 10 <= mouse[1] <= 60:
                    if SPEED < 10000 :
                        SPEED = SPEED * 2
                if 525 <= mouse[0] <= 575 and 10 <= mouse[1] <= 60:
                    if SPEED > 4:
                        SPEED = SPEED / 2
                if 680 <= mouse[0] <= 780 and 10 <= mouse[1] <= 60:
                    main()
                if 880 <= mouse[0] <= 980 and 10 <= mouse[1] <= 60:
                    pygame.quit()

        for particule in tab_particules:
            #if particule.type != 0:
            particule.draw(SCREEN)
            if SHOW_ORBIT == 1:
                particule.draw_orbit(SCREEN)
            particule.update_position(tab_particules, BORDER)
        #display info about the simulation elapsed_time since the start of simulation  
        elapsed_time = timer  / 360
        FONT = pygame.font.SysFont("comicsans", 20)
        text_time = FONT.render(("%.2f ans " % elapsed_time), True, WHITE)
        SCREEN.blit(text_time, (WIDTH-192, 46))
        speed_value = SPEED / 50
        speed_time = FONT.render(("Vitesse : x%.2f " % speed_value), True, WHITE)
        SCREEN.blit(speed_time, (WIDTH-280, 80))

        pygame.display.update()

    pygame.quit()


main()
