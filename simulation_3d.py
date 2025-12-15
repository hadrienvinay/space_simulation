import random

import pygame
import math
import sys

from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

#init pygame
pygame.init()



WHITE = (255,255,255)
YELLOW = (255,255,0)
BLUE = (0,0,255)
BLACK = (0,0,0)
ORANGE = (255,128,0)
GREEN = (0,240,0)
DARK_GREY = (80,78,81)
RED = (255,20,0)

# Créer une fenêtre Pygame avec un contexte OpenGL
WIDTH, HEIGHT = 1600, 1000
#SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
# Paramétrer la perspective 3D
gluPerspective(45, (800 / 600), 0.1, 50.0)
glTranslatef(0.0, 0.0, -5)  # Position de la caméra

pygame.display.set_caption("BIG BANG Simulation")

FONT = pygame.font.SysFont("comicsans", 16)

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

        #pygame.draw.circle(screen, self.color, (x, y), self.radius)

    def draw_orbit(self, screen):
        if len(self.orbit) > 1:
            updated_points = []
            for point in self.orbit:
                x, y = point
                x = x * SCALE + WIDTH / 2
                y = y * SCALE + HEIGHT / 2
                updated_points.append((x, y))

            #pygame.draw.lines(screen, self.color, False, updated_points, 2)

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

def draw_cube():
    glBegin(GL_QUADS)
    # Face avant
    glColor3f(1, 0, 0)  # Rouge
    glVertex3f(-1, -1, 1)
    glVertex3f(1, -1, 1)
    glVertex3f(1, 1, 1)
    glVertex3f(-1, 1, 1)
     
    # Face arrière
    glColor3f(0, 1, 0)  # Vert
    glVertex3f(-1, -1, -1)
    glVertex3f(1, -1, -1)
    glVertex3f(1, 1, -1)
    glVertex3f(-1, 1, -1)
     
    # Face gauche
    glColor3f(0, 0, 1)  # Bleu
    glVertex3f(-1, -1, -1)
    glVertex3f(-1, -1, 1)
    glVertex3f(-1, 1, 1)
    glVertex3f(-1, 1, -1)
     
    # Face droite
    glColor3f(1, 1, 0)  # Jaune
    glVertex3f(1, -1, -1)
    glVertex3f(1, -1, 1)
    glVertex3f(1, 1, 1)
    glVertex3f(1, 1, -1)
     
    # Face supérieure
    glColor3f(1, 0, 1)  # Magenta
    glVertex3f(-1, 1, -1)
    glVertex3f(1, 1, -1)
    glVertex3f(1, 1, 1)
    glVertex3f(-1, 1, 1)
     
    # Face inférieure
    glColor3f(0, 1, 1)  # Cyan
    glVertex3f(-1, -1, -1)
    glVertex3f(1, -1, -1)
    glVertex3f(1, -1, 1)
    glVertex3f(-1, -1, 1)

    glEnd()

def draw_circle(radius):
    glClear(GL_COLOR_BUFFER_BIT)
    glBegin(GL_TRIANGLE_FAN)


    
def handle_keys():
    keys = pygame.key.get_pressed()
 
    if keys[pygame.K_z]:
        glTranslatef(0, 0, 0.1)  # Avancer
    if keys[pygame.K_s]:
        glTranslatef(0, 0, -0.1)  # Reculer
    if keys[pygame.K_q]:
        glTranslatef(0.1, 0, 0)  # Gauche
    if keys[pygame.K_d]:
        glTranslatef(-0.1, 0, 0)  # Droite
    

def main():
    SHOW_ORBIT = 1
    BORDER = 0
    SPEED = 50
    run = True
    clock = pygame.time.Clock()


    timer = 0
    elapsed_time = 0
    angle = 0
    
    while run:
        clock.tick(SPEED)
        timer += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        mouse = pygame.mouse.get_pos()
        print (mouse)
        handle_keys()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # Dans la boucle principale
        glPushMatrix()  # Sauvegarder la matrice actuelle
        glRotatef(angle, 0, 1, 0)  # Rotation autour de l'axe Y
        draw_cube()
        glPopMatrix()  # Restaurer la matrice
        
        angle += 1  # Incrémenter l'angle pour la rotation continue


        #display info about the simulation elapsed_time since the start of simulation  
        elapsed_time = timer  / 360
        FONT = pygame.font.SysFont("comicsans", 20)
        text_time = FONT.render(("%.2f ans " % elapsed_time), True, WHITE)
        SCREEN.blit(text_time, (WIDTH-192, 46))
        speed_value = SPEED / 50
        speed_time = FONT.render(("Vitesse : x%.2f " % speed_value), True, WHITE)
        SCREEN.blit(speed_time, (WIDTH-280, 80))

        pygame.display.flip()
        pygame.time.wait(10)

    pygame.quit()


main()
