import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from OpenGL.GL.ARB.shader_objects import *
from OpenGL.GL.ARB.vertex_shader import *
from OpenGL.GL.ARB.fragment_shader import *

import math
import sys
import time
import json
import random
import numpy as np

WIDTH, HEIGHT = 1100, 800 

AU = 149.6e6 * 1000
G = 6.67428e-11
SCALE_1 = 15000 / AU # 1AU = 500 pixel
SCALE_2 = 150 / AU # 1AU = 500 pixel
TIMESTEP_1 = 3600  # 1 day = *24 , here 1hour
TIMESTEP_2 = 3600 * 24 # 1 day = *24 , here 1 day

WHITE = (255,255,255)
YELLOW = (255,255,0)
BLUE = (0,0,255)
BLACK = (0,0,0)
ORANGE = (255,128,0)
GREEN = (0,240,0)
DARK_GREY = (80,78,81)
RED = (255,20,0)

WHITE_3D = (1,1,1,1)
YELLOW_3D = (1,1,0,1)
BLUE_3D = (0,0,1,1)
BLACK_3D = (0,0,0,1)
ORANGE_3D = (1,0.5,0,1)
GREEN_3D = (0,0.92,0,1)
DARK_GREY_3D = (0.3,0.29,0.3,1)
RED_3D = (1,0.1,0,1)

# Fonction pour dessiner un rectangle 2D (bouton)
def draw_2d_rect(x, y, width, height, color):
    glColor4f(*color)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + width, y)
    glVertex2f(x + width, y + height)
    glVertex2f(x, y + height)
    glEnd()

# Dégradé vertical : color_top en haut, color_bottom en bas
def draw_gradient_rect(x, y, width, height, color_top, color_bottom):
    glBegin(GL_QUADS)
    glColor4f(*color_bottom)
    glVertex2f(x, y)
    glVertex2f(x + width, y)
    glColor4f(*color_top)
    glVertex2f(x + width, y + height)
    glVertex2f(x, y + height)
    glEnd()

# Bordure stylisée : highlight en haut/gauche, ombre en bas/droite
def draw_button_border(x, y, width, height):
    glLineWidth(1.5)
    glColor4f(1, 1, 1, 0.7)
    glBegin(GL_LINES)
    glVertex2f(x, y); glVertex2f(x, y + height)
    glVertex2f(x, y + height); glVertex2f(x + width, y + height)
    glEnd()
    glColor4f(0, 0, 0, 0.5)
    glBegin(GL_LINES)
    glVertex2f(x + width, y + height); glVertex2f(x + width, y)
    glVertex2f(x + width, y); glVertex2f(x, y)
    glEnd()

def darken(color, factor=0.5):
    return (color[0]*factor, color[1]*factor, color[2]*factor, color[3])

# Fonction pour charger une image
def load_image(filename):
    try :
        image = pygame.image.load(filename).convert_alpha()
    except IOError:
        print("can't load file %s"%filename)
        return(0)

    width, height = image.get_rect().size
    data = pygame.image.tobytes(image,"RGBA")
    # Génération d'un identifiant de texture
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)

    # Spécification de la texture avec glTexImage2D
    glTexImage2D(
        GL_TEXTURE_2D,  # Cible : texture 2D
        0,             # Niveau de détail (mipmap)
        GL_RGBA,       # Format interne (à adapter selon l'image)
        width,   # Largeur
        height,  # Hauteur
        0,             # Bordure (toujours 0)
        GL_RGBA,       # Format des données (à adapter selon l'image)
        GL_UNSIGNED_BYTE, # Type des données
        data       # Données de la texture
    )
    # Paramètres de filtrage
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    return(texture)

# Fonction pour dessiner une image (mode rectangle)
def draw_image(texture):
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)

    # Dessiner un rectangle texturé
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex3f(-100, -100, -40)
    glTexCoord2f(1, 0)
    glVertex3f(100, -100, -40)
    glTexCoord2f(1, 1)
    glVertex3f(100, 100, -40)
    glTexCoord2f(0, 1)
    glVertex3f(-100, 100, -40)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_DEPTH_TEST)

class Planet:
    def __init__(self, x, y, z, radius, color, mass, type, sun, texture, rotation):
        self.x = x
        self.y = y
        self.z = z
        self.radius = radius
        self.color = color
        self.mass = mass
        self.type = type
        self.sun = sun
        self.texture = texture
        self.rotation = rotation
        self.texture_name = ""
        self.angle = 0

        self.orbit = []

        self.x_vel = 0
        self.y_vel = 0
        self.z_vel = 0

    def infos(self):
        print(self.x,self.y,self.z)

    def draw(self,SCALE):
        x = self.x * SCALE 
        y = self.y * SCALE 
        z = self.z * SCALE 
        glPushMatrix()
        sphere = gluNewQuadric() #Create new sphere
        glTranslatef(x, y, z) #Move to the placegluSphere(sphere,self.radius,32,32) #Draw sphere
        glRotatef(self.angle,0,0,1)
        self.angle += self.rotation
        if self.texture == 0:
            glColor4f(self.color[0]/255,self.color[1]/255,self.color[2]/255,0) #Put default color
        else :
            glColor4f(1,1,1,0) #Put default color
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.texture)
        gluQuadricTexture(sphere, GL_TRUE)  # Active le mappage de texture si l'image est chargée
        #gluQuadricNormals(sphere, GLU_SMOOTH)
        gluSphere(sphere,self.radius,32,32) #Draw sphere
        gluDeleteQuadric(sphere)
        if self.texture != 0:
            glDisable(GL_TEXTURE_2D)
        glPopMatrix()

    def update_position(self,planets,TIMESTEP):
        total_fx = total_fy = total_fz = 0
        for planet in planets:
            if self == planet:
                continue
            fx, fy, fz = self.attraction(planet)
            total_fx += fx
            total_fy += fy
            total_fz += fz

        self.x_vel += total_fx / self.mass * TIMESTEP  # a = f / m * timestep (here 1 day)
        self.y_vel += total_fy / self.mass * TIMESTEP
        self.z_vel += total_fz / self.mass * TIMESTEP

        self.x += self.x_vel * TIMESTEP
        self.y += self.y_vel * TIMESTEP
        self.z += self.z_vel * TIMESTEP
        self.orbit.append((self.x, self.y,self.z))
    
    def attraction(self, other):
        other_x, other_y, other_z = other.x, other.y, other.z
        distance_x = other_x - self.x
        distance_y = other_y - self.y
        distance_z = other_z - self.z
        distance2 = math.sqrt(distance_x ** 2 + distance_y ** 2 + distance_z **2)
        force2 =  G * self.mass * other.mass / distance2 ** 2
        theta = math.atan2(distance_y, distance_x)
        beta = math.atan2(distance_z, distance_y)
        force_x = math.cos(theta) * force2
        force_y = math.sin(theta) * force2
        force_z = math.sin(beta) * force2

        #force_x = -G * self.mass * distance_x / distance2**3        
        #force_y = -G * self.mass * distance_y / distance2**3
        #force_z = -G * self.mass * distance_z / distance2**3
        #print(force_x,force_y,force_z)
        return force_x, force_y, force_z

    def draw_orbit(self, SCALE):
        points = len(self.orbit)
        if points < 2:
            return
        glBegin(GL_LINES)
        glColor3f(self.color[0]/255, self.color[1]/255, self.color[2]/255)
        if points > 1000:
            # Draw last ~1000 points with step of 10
            for ii in range(10, 1000, 10):
                j = points - ii
                glVertex3f(self.orbit[j-10][0]*SCALE, self.orbit[j-10][1]*SCALE, self.orbit[j-10][2]*SCALE)
                glVertex3f(self.orbit[j][0]*SCALE, self.orbit[j][1]*SCALE, self.orbit[j][2]*SCALE)
        else:
            for i in range(1, points):
                glVertex3f(self.orbit[i-1][0]*SCALE, self.orbit[i-1][1]*SCALE, self.orbit[i-1][2]*SCALE)
                glVertex3f(self.orbit[i][0]*SCALE, self.orbit[i][1]*SCALE, self.orbit[i][2]*SCALE)
        glEnd()

class Button:
    def __init__(self, rect, text, color, font, text_color=(0, 0, 0)):
        self.rect = rect
        self.text = text
        self.color = color
        self.font = font
        self.text_color = text_color
        self.data = pygame.image.tobytes(text, "RGBA", True)
        self.x = rect.x
        self.y = rect.y
        self.width = rect.width
        self.height = rect.height

    def update_button(self, text, font):
        self.text = font.render("%s" % text, False, self.text_color)
        self.data = pygame.image.tobytes(self.text, "RGBA", True)

class Camera_Position:
    def __init__(self, pos_x,pos_y,pos_z,angle_x,angle_y,angle_z):
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.angle_x = angle_x
        self.angle_y = angle_y
        self.angle_z = angle_z
    
    def infos(self):
        print(self.angle_x,self.angle_y,self.angle_z)

    def reset_angles(self):
        if self.angle_x>720 or self.angle_x<-720:
            self.angle_x = 0
        if self.angle_y>720 or self.angle_y<-720:
            self.angle_y = 0
        if self.angle_z>720 or self.angle_z<-720:
            self.angle_z = 0

def force_gravite(x,y):
    distance_x = x - 0
    distance_y = y - 0
    #distance_z = z - sun.z
    if(distance_x & distance_y != 0):
        distance = math.sqrt(distance_x ** 2 + distance_y ** 2)
    else : distance = 1
    force =  G * 1.98892 * 10**30 / distance ** 2
    #print(force*SCALE)
    coef = force *SCALE_1*SCALE_1
    return coef

def draw_axys():
    glBegin(GL_LINES)
    glColor3f (1.0, 1.0, 1.0)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(100, 0.0, 0.0)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0, 100, 0.0)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0, 0.0, 100)
    glEnd()

def draw_grid():
    glBegin(GL_LINES)
    glColor3f (0.2, 0.2, 0.1)
    for i in range(-100,100):
        glVertex3f(-500, i*5, -10)
        glVertex3f(500, i*5, -10)
        glVertex3f(i*5, -500, -10)
        glVertex3f(i*5, 500, -10)
    glEnd()

def draw_gravity_grid(tab_planets, SCALE, grid_range=200, grid_steps=22, z_scale=100, z_offset=-12):
    """Grille espace-temps 2D déformée par le potentiel gravitationnel des corps."""
    if not tab_planets:
        return

    ref_mass = max(p.mass for p in tab_planets)
    min_dist = 6.0
    bodies = [(p.x * SCALE, p.y * SCALE, p.mass / ref_mass) for p in tab_planets]

    n = grid_steps + 1
    step = grid_range * 2 / grid_steps

    # Précalcul du z déformé pour chaque vertex de la grille
    grid_z = [[0.0] * n for _ in range(n)]
    for i in range(n):
        gx = -grid_range + i * step
        for j in range(n):
            gy = -grid_range + j * step
            potential = sum(
                m / max(math.sqrt((gx - px)**2 + (gy - py)**2), min_dist)
                for px, py, m in bodies
            )
            grid_z[i][j] = z_offset - z_scale * potential

    glColor3f(0.08, 0.35, 0.55)
    glBegin(GL_LINES)

    # Lignes parallèles à Y (x fixe)
    for i in range(n):
        gx = -grid_range + i * step
        for j in range(grid_steps):
            gy1 = -grid_range + j * step
            gy2 = gy1 + step
            glVertex3f(gx, gy1, grid_z[i][j])
            glVertex3f(gx, gy2, grid_z[i][j + 1])

    # Lignes parallèles à X (y fixe)
    for j in range(n):
        gy = -grid_range + j * step
        for i in range(grid_steps):
            gx1 = -grid_range + i * step
            gx2 = gx1 + step
            glVertex3f(gx1, gy, grid_z[i][j])
            glVertex3f(gx2, gy, grid_z[i + 1][j])

    glEnd()
    
def screen_to_world_z0(mouse_x, mouse_y, modelview, projection, viewport):
    """Convert screen coordinates to world coordinates on the z=0 plane."""
    near = gluUnProject(mouse_x, mouse_y, 0.0, modelview, projection, viewport)
    far = gluUnProject(mouse_x, mouse_y, 1.0, modelview, projection, viewport)
    # Ray direction
    dx = far[0] - near[0]
    dy = far[1] - near[1]
    dz = far[2] - near[2]
    if abs(dz) < 1e-10:
        return near[0], near[1]
    t = -near[2] / dz
    world_x = near[0] + t * dx
    world_y = near[1] + t * dy
    return world_x, world_y

def compute_orbital_velocity(planet_x, planet_y, click_wx, click_wy, tab_planets, SCALE):
    """Compute orbital velocity for a planet based on nearest sun and click direction."""
    # Find nearest sun
    nearest_sun = None
    min_dist = float('inf')
    for p in tab_planets:
        if p.sun == 1:
            dist = math.sqrt((planet_x - p.x)**2 + (planet_y - p.y)**2)
            if dist < min_dist:
                min_dist = dist
                nearest_sun = p
    if nearest_sun is None or min_dist < 1e5:
        return 0, 0
    # Circular orbital speed: v = sqrt(G * M / r)
    v = math.sqrt(G * nearest_sun.mass / min_dist)
    # Direction from click vector (planet pos -> click pos in world)
    dir_x = click_wx - planet_x * SCALE
    dir_y = click_wy - planet_y * SCALE
    dir_len = math.sqrt(dir_x**2 + dir_y**2)
    if dir_len < 1e-10:
        # Default: perpendicular to radius (counter-clockwise)
        rx = planet_x - nearest_sun.x
        ry = planet_y - nearest_sun.y
        rlen = math.sqrt(rx**2 + ry**2)
        if rlen < 1e-10:
            return 0, v
        return -ry / rlen * v, rx / rlen * v
    return dir_x / dir_len * v, dir_y / dir_len * v

def save_sandbox(tab_planets, filename="sandbox_save.json"):
    """Save sandbox planets to JSON."""
    data = []
    for p in tab_planets:
        data.append({
            "x": p.x, "y": p.y, "z": p.z,
            "x_vel": p.x_vel, "y_vel": p.y_vel, "z_vel": p.z_vel,
            "radius": p.radius, "color": list(p.color),
            "mass": p.mass, "sun": p.sun, "rotation": p.rotation,
            "texture_name": p.texture_name
        })
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def load_sandbox(filename="sandbox_save.json"):
    """Load sandbox planets from JSON."""
    try:
        with open(filename, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    tab_planets = []
    for d in data:
        tex = 0
        tex_name = d.get("texture_name", "")
        if tex_name:
            tex = load_image(tex_name)
        p = Planet(d["x"], d["y"], d["z"], d["radius"], tuple(d["color"]),
                   d["mass"], 0, d["sun"], tex, d["rotation"])
        p.texture_name = tex_name
        p.x_vel = d["x_vel"]
        p.y_vel = d["y_vel"]
        p.z_vel = d["z_vel"]
        p.orbit.append((p.x, p.y, p.z))
        tab_planets.append(p)
    return tab_planets

def init_earth_moon(tab_planets):
    texture_earth = load_image("textures/earth_test.jpg")
    earth = Planet(0,0,0,10,BLUE,5.97*10**24,0,0,texture_earth,5)
    earth.y_vel = -29.786 * 10 #vitesse rotation autour soleil : 30km/s
    earth.orbit.append((earth.x, earth.y, earth.z))
    texture_moon = load_image("textures/moon_test.jpg")
    moon  = Planet(earth.x - 0.0026*AU, 0,0.0002*AU,5,DARK_GREY,7.347*10**22,0,0,texture_moon,0)
    moon.y_vel = earth.y_vel
    moon.y_vel += 1.02 * 1000 #v orbitale : 1.02km/s
    moon.orbit.append((moon.x, moon.y, moon.z))
    tab_planets.append(earth)
    tab_planets.append(moon)

def init_planet(tab_planets):
    texture_mercury = load_image("textures/mercury.jpg")
    mercury  = Planet(0.39*AU,0,0,2,DARK_GREY,0.33*10**24,0,0,texture_mercury,8)
    #mercury.y_vel = -170496 *1.6
    mercury.y_vel = 47.4 * 1000
    mercury.orbit.append((mercury.x, mercury.y, mercury.z))
    texture_venus = load_image("textures/venus.jpg")
    venus    = Planet(0.72*AU,0,0,3,GREEN,4.87*10**24,0,0,texture_venus,0.01)
    #venus.x_vel = 12600* 1.4
    venus.y_vel = 35.02 * 1000
    venus.orbit.append((venus.x, venus.y, venus.z))
    texture_earth = load_image("textures/earth.jpg")
    earth    = Planet(1*AU,0,0,4,BLUE,5.97*10**24,0,0,texture_earth,10)
    #earth.y_vel = -107206* 1.3
    earth.y_vel = 29.783 * 1000 #vitesse rotation autour soleil : 30km/s
    earth.orbit.append((earth.x, earth.y, earth.z))
    #texture_moon = load_image("textures/moon.jpg")
    #moon    = Planet(earth.x - 0.0026*AU, 0,0,0.1,DARK_GREY,7.347*10**22,0,0,texture_moon,8)
    #moon.y_vel = earth.y_vel + 1.02 * 1000 #v orbitale : 1.02km/s
    #moon.orbit.append((moon.x, moon.y, moon.z))
    texture_mars = load_image("textures/mars.jpg")
    mars     = Planet(1.52*AU,0,0,3,RED,0.642*10**24,0,0,texture_mars,0)
    #mars.y_vel = -86425* 1.6
    mars.y_vel = 24.077 * 1000
    mars.orbit.append((mars.x, mars.y,mars.z))
    texture_jupiter = load_image("textures/jupiter.jpg")
    jupiter  = Planet(-5.2*AU,0,0,8,ORANGE,1.9*10**27,0,0,texture_jupiter,0)
    #jupiter.y_vel = -47052* 1.5
    jupiter.y_vel = -13.06* 1000
    jupiter.orbit.append((jupiter.x, jupiter.y,jupiter.z))
    texture_saturn = load_image("textures/saturn.jpg")
    saturn   = Planet(-9.55*AU,0,0,7,YELLOW,1.9*10**27,0,0,texture_saturn,0)
    #saturn.y_vel = -34848* 1.5
    saturn.y_vel = -9.68 * 1000
    saturn.orbit.append((saturn.x, saturn.y, saturn.z))
    uranus   = Planet(19.22*AU,0,0,6,BLUE,568*10**24,0,0,0,0)
    #uranus.y_vel = -32480
    uranus.y_vel = 6.80 * 1000
    uranus.orbit.append((uranus.x, uranus.y, uranus.z))
    neptune  = Planet(30.11*AU,0,0,5,WHITE,0.33*10**24,0,0,0,0)
    #neptune.y_vel = -19548
    neptune.y_vel = 5.43 * 1000
    neptune.orbit.append((neptune.x, neptune.y, neptune.z))
    texture_sun = load_image("textures/sun2.jpg")
    sun = Planet(0,0,0,8, WHITE, 1.98892 * 10**30,0,1,texture_sun,1)
    #sun2 = Planet(5*AU,0.5*AU,0,8, WHITE, 1.98892 * 10**30,0,1)
    #sun2.y_vel = -10 * 1000
    #sun.z_vel = 1 * 1000

    tab_planets.append(sun)
    #tab_planets.append(sun2)
    tab_planets.append(mercury)
    tab_planets.append(venus)
    tab_planets.append(earth)
    tab_planets.append(mars)
    tab_planets.append(jupiter)
    tab_planets.append(saturn)
    tab_planets.append(uranus)
    tab_planets.append(neptune)

def handle_keys(camera):
    keypress = pygame.key.get_pressed()
    if keypress[pygame.K_z]:
        camera.pos_x -= 0.5
    if keypress[pygame.K_s]:
        camera.pos_x += 0.5
    if keypress[pygame.K_d]:
        camera.pos_y += 0.5
    if keypress[pygame.K_q]:
        camera.pos_y -= 0.5
    if keypress[pygame.K_a]:
        camera.pos_z += 0.5
    if keypress[pygame.K_e]:
        camera.pos_z -= 0.5
    if keypress[pygame.K_RIGHT]:
        camera.angle_x -=0.5
    if keypress[pygame.K_LEFT]:
        camera.angle_x +=0.5
    if keypress[pygame.K_UP]:
        camera.angle_z +=0.5
    if keypress[pygame.K_DOWN]:
        camera.angle_z -=0.5
    if keypress[pygame.K_t]:
        camera.angle_y +=0.5
    if keypress[pygame.K_y]:
        camera.angle_y -=0.5

def reset(tab_planets,menu):
    del tab_planets
    new_tab = []
    if menu == 1 :
        init_earth_moon(new_tab)
    elif menu ==2 :
        init_planet(new_tab)
    elif menu == 3:
        pass  # Sandbox starts empty
    return new_tab

def init_game(display):
    pygame.init()
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Solar System")
    return pygame.time.Clock()

def main():
    #Default Variables, Orbit ON, SPEED, pov, time, planets
    display = (WIDTH, HEIGHT)
    clock = init_game(display)
    running_menu = 1
    ORBIT_ON = 1
    SPEED = 60
    menu = 0

    # Menu buttons created once
    font_title    = pygame.font.SysFont("comicsans", 30)
    font_subtitle = pygame.font.SysFont("comicsans", 15)
    font_menu     = pygame.font.SysFont("comicsans", 30)

    text_surface_menu = font_title.render("✦  SURI SPACE STATION  ✦", False, (220, 180, 255))
    text_width_menu, text_height_menu = text_surface_menu.get_size()
    text_data_menu = pygame.image.tobytes(text_surface_menu, "RGBA", True)

    sub_surface = font_subtitle.render("Explorez, créez et simulez l'univers", False, (170, 150, 210))
    sub_w, sub_h = sub_surface.get_size()
    sub_data = pygame.image.tobytes(sub_surface, "RGBA", True)

    BTN_W, BTN_H, GAP = 340, 62, 16
    _total_btn_h = 4 * BTN_H + 3 * GAP          # 248 + 48 = 296
    menu_start_x = WIDTH // 2 - BTN_W // 2      # centered
    menu_start_y = HEIGHT // 2 - _total_btn_h // 2 - 40  # shifted down to leave room for title

    COL_BLUE   = (0.20, 0.45, 0.85, 1)
    COL_GOLD   = (0.85, 0.55, 0.05, 1)
    COL_PURPLE = (0.55, 0.20, 0.75, 1)
    COL_RED    = (0.72, 0.10, 0.10, 1)

    button_earth = Button(pygame.Rect(menu_start_x, menu_start_y + 3*(BTN_H + GAP), BTN_W, BTN_H),
                        font_menu.render("TERRE - LUNE", False, (255, 255, 255)),
                        COL_BLUE, font_menu, text_color=(255, 255, 255))
    button_solar_system = Button(pygame.Rect(menu_start_x, menu_start_y + 2*(BTN_H + GAP), BTN_W, BTN_H),
                        font_menu.render("SYSTEME SOLAIRE", False, (255, 255, 255)),
                        COL_GOLD, font_menu, text_color=(255, 255, 255))
    button_sandbox = Button(pygame.Rect(menu_start_x, menu_start_y + 1*(BTN_H + GAP), BTN_W, BTN_H),
                        font_menu.render("SANDBOX", False, (255, 255, 255)),
                        COL_PURPLE, font_menu, text_color=(255, 255, 255))
    button_quit_menu = Button(pygame.Rect(menu_start_x, menu_start_y, BTN_W, BTN_H),
                        font_menu.render("QUITTER", False, (255, 255, 255)),
                        COL_RED, font_menu, text_color=(255, 255, 255))
    buttons_menu = [button_earth, button_solar_system, button_sandbox, button_quit_menu]

    texture_menu_bg = 0  # loaded lazily (reloaded after context recreation)

    while running_menu:

        move = 0
        run = True
        tab_planets = []
        if menu == 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running_menu = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                        running_menu = False  
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Clic gauche
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        # Conversion des coordonnées OpenGL (viewport)
                        viewport = glGetIntegerv(GL_VIEWPORT)
                        mouse_y = viewport[3] - mouse_y  # Inversion Y
                        if (button_earth.x <= mouse_x <= button_earth.x + button_earth.width and
                            button_earth.y <= mouse_y <= button_earth.y + button_earth.height):
                            menu = 1
                        if (button_solar_system.x <= mouse_x <= button_solar_system.x + button_solar_system.width and
                                button_solar_system.y <= mouse_y <= button_solar_system.y + button_solar_system.height):
                            menu = 2
                        if (button_sandbox.x <= mouse_x <= button_sandbox.x + button_sandbox.width and
                                button_sandbox.y <= mouse_y <= button_sandbox.y + button_sandbox.height):
                            menu = 3
                        if (button_quit_menu.x <= mouse_x <= button_quit_menu.x + button_quit_menu.width and
                                button_quit_menu.y <= mouse_y <= button_quit_menu.y + button_quit_menu.height):
                            running_menu = 0
   
            # Load background texture (lazy, re-loaded after context recreation)
            if texture_menu_bg == 0:
                texture_menu_bg = load_image('textures/milky.jpg')

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            gluOrtho2D(0, display[0], 0, display[1])
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()
            glDisable(GL_DEPTH_TEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            # ── Background galaxy texture ──────────────────────────────────
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, texture_menu_bg)
            glColor4f(1, 1, 1, 1)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(0, 0)
            glTexCoord2f(1, 0); glVertex2f(display[0], 0)
            glTexCoord2f(1, 1); glVertex2f(display[0], display[1])
            glTexCoord2f(0, 1); glVertex2f(0, display[1])
            glEnd()
            glDisable(GL_TEXTURE_2D)

            # ── Full-screen dark overlay ───────────────────────────────────
            glColor4f(0.02, 0.00, 0.08, 0.62)
            glBegin(GL_QUADS)
            glVertex2f(0, 0); glVertex2f(display[0], 0)
            glVertex2f(display[0], display[1]); glVertex2f(0, display[1])
            glEnd()

            # ── Center panel (frosted dark) ────────────────────────────────
            _px = menu_start_x - 52
            _pw = BTN_W + 104
            _py = menu_start_y - 36
            _ph = _total_btn_h + text_height_menu + sub_h + 90
            draw_gradient_rect(_px, _py, _pw, _ph,
                               (0.10, 0.05, 0.22, 0.82), (0.05, 0.02, 0.14, 0.92))
            # panel border
            glColor4f(0.65, 0.40, 1.0, 0.35)
            glLineWidth(1.0)
            glBegin(GL_LINE_LOOP)
            glVertex2f(_px, _py); glVertex2f(_px + _pw, _py)
            glVertex2f(_px + _pw, _py + _ph); glVertex2f(_px, _py + _ph)
            glEnd()

            # ── Title ──────────────────────────────────────────────────────
            title_x = WIDTH // 2 - text_width_menu // 2
            title_y = menu_start_y + _total_btn_h + 38
            glRasterPos2f(title_x, title_y)
            glDrawPixels(text_width_menu, text_height_menu, GL_RGBA, GL_UNSIGNED_BYTE, text_data_menu)

            # Separator line under title
            sep_y = title_y - 8
            glColor4f(0.75, 0.45, 1.0, 0.5)
            glLineWidth(1.5)
            glBegin(GL_LINES)
            glVertex2f(_px + 24, sep_y); glVertex2f(_px + _pw - 24, sep_y)
            glEnd()
            glLineWidth(1.0)

            # Subtitle
            glRasterPos2f(WIDTH // 2 - sub_w // 2, title_y + text_height_menu + 6)
            glDrawPixels(sub_w, sub_h, GL_RGBA, GL_UNSIGNED_BYTE, sub_data)

            # ── Buttons ────────────────────────────────────────────────────
            for button in buttons_menu:
                draw_gradient_rect(button.x, button.y, button.width, button.height,
                                   button.color, darken(button.color, 0.6))
                draw_button_border(button.x, button.y, button.width, button.height)
                glRasterPos2f(button.x + (button.width - button.text.get_width()) // 2,
                              button.y + (button.height - button.text.get_height()) // 2)
                glDrawPixels(button.text.get_width(), button.text.get_height(),
                             GL_RGBA, GL_UNSIGNED_BYTE, button.data)

            glDisable(GL_BLEND)
            glEnable(GL_DEPTH_TEST)
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()

            pygame.display.flip()
            clock.tick(SPEED)
        else:
            font = pygame.font.SysFont("comicsans", 20)
            if menu == 1 :
                text_surface = font.render("Système Terre - Lune", False, (255, 215, 255, 1))
                SCALE = SCALE_1
                TIMESTEP = TIMESTEP_1
            elif menu == 2 :
                text_surface = font.render("Système Solaire Proche", False, (255, 215, 255, 1))
                SCALE = SCALE_2
                TIMESTEP = TIMESTEP_2
            elif menu == 3:
                text_surface = font.render("Sandbox Mode", False, (255, 215, 255, 1))
                SCALE = SCALE_2
                TIMESTEP = TIMESTEP_2
            else:
                text_surface = font.render("Erreur Menu", False, (255, 215, 255, 1))

            text_width, text_height = text_surface.get_size()
            text_data = pygame.image.tobytes(text_surface, "RGBA", True)

            camera = Camera_Position(150,100,50,0,0,0)
            
            SIM_RED   = (0.80, 0.15, 0.15, 1)
            SIM_GREEN = (0.15, 0.68, 0.25, 1)
            SIM_BLUE  = (0.15, 0.40, 0.75, 1)
            SIM_NAVY  = (0.12, 0.18, 0.52, 1)
            SIM_GRAY  = (0.38, 0.38, 0.44, 1)
            SIM_LGRAY = (0.60, 0.60, 0.65, 1)
            button_orbit = Button(pygame.Rect(WIDTH-180, HEIGHT-70, 150, 50),
                                font.render("Orbit ON", False, (255, 255, 255)),
                                SIM_RED, font, text_color=(255, 255, 255))
            button_reset = Button(pygame.Rect(WIDTH-180, HEIGHT-150, 150, 50),
                                font.render("Reset", False, (255, 255, 255)),
                                SIM_GREEN, font, text_color=(255, 255, 255))
            button_time = Button(pygame.Rect(WIDTH-180, HEIGHT-220, 150, 50),
                                font.render("Time", False, (255, 255, 255)),
                                SIM_BLUE, font, text_color=(255, 255, 255))
            button_speed = Button(pygame.Rect(WIDTH-180, HEIGHT-290, 150, 50),
                                font.render("Speed", False, (255, 255, 255)),
                                SIM_NAVY, font, text_color=(255, 255, 255))
            button_plus = Button(pygame.Rect(WIDTH-176, HEIGHT-282, 30, 30),
                                font.render("+", False, (255, 255, 255)),
                                SIM_LGRAY, font, text_color=(255, 255, 255))
            button_minus = Button(pygame.Rect(WIDTH-65, HEIGHT-282, 30, 30),
                                font.render("-", False, (255, 255, 255)),
                                SIM_LGRAY, font, text_color=(255, 255, 255))
            button_quit = Button(pygame.Rect(WIDTH-180, 20, 150, 50),
                                font.render("QUIT", False, (255, 255, 255)),
                                SIM_RED, font, text_color=(255, 255, 255))
            button_earth_speed = Button(pygame.Rect(WIDTH-180, 100, 150, 50),
                                font.render("Menu", False, (255, 255, 255)),
                                SIM_GRAY, font, text_color=(255, 255, 255))
            buttons_list = [button_orbit,button_reset,button_time,button_speed,button_plus,button_minus,button_quit,button_earth_speed]

            # Sandbox-specific state and buttons
            SANDBOX_IDLE = 0
            SANDBOX_PLACING_SUN = 1
            SANDBOX_PLACING_PLANET_POS = 2
            SANDBOX_PLACING_PLANET_VEL = 3
            sandbox_mode = SANDBOX_IDLE
            sandbox_paused = True
            sandbox_pending_pos = None  # (world_x, world_y) of planet being placed
            sandbox_pending_planet = None  # temp Planet object
            last_modelview = None
            last_projection = None
            last_viewport = None

            if menu == 3:
                SIM_ORANGE = (0.85, 0.50, 0.10, 1)
                SIM_PURPLE = (0.55, 0.20, 0.75, 1)
                SIM_TEAL   = (0.10, 0.55, 0.55, 1)
                button_add_sun = Button(pygame.Rect(WIDTH-180, HEIGHT-70, 150, 50),
                                    font.render("Soleil", False, (255, 255, 255)),
                                    SIM_ORANGE, font, text_color=(255, 255, 255))
                button_add_planet = Button(pygame.Rect(WIDTH-180, HEIGHT-140, 150, 50),
                                    font.render("Planete", False, (255, 255, 255)),
                                    SIM_BLUE, font, text_color=(255, 255, 255))
                button_play_pause = Button(pygame.Rect(WIDTH-180, HEIGHT-210, 150, 50),
                                    font.render("Play", False, (255, 255, 255)),
                                    SIM_GREEN, font, text_color=(255, 255, 255))
                button_save = Button(pygame.Rect(WIDTH-180, HEIGHT-280, 150, 50),
                                    font.render("Save", False, (255, 255, 255)),
                                    SIM_TEAL, font, text_color=(255, 255, 255))
                button_load = Button(pygame.Rect(WIDTH-180, HEIGHT-350, 150, 50),
                                    font.render("Load", False, (255, 255, 255)),
                                    SIM_PURPLE, font, text_color=(255, 255, 255))
                button_sb_reset = Button(pygame.Rect(WIDTH-180, HEIGHT-420, 150, 50),
                                    font.render("Reset", False, (255, 255, 255)),
                                    SIM_RED, font, text_color=(255, 255, 255))
                button_sb_menu = Button(pygame.Rect(WIDTH-180, 20, 150, 50),
                                    font.render("Menu", False, (255, 255, 255)),
                                    SIM_GRAY, font, text_color=(255, 255, 255))
                button_sb_quit = Button(pygame.Rect(WIDTH-180, 80, 150, 50),
                                    font.render("QUIT", False, (255, 255, 255)),
                                    SIM_RED, font, text_color=(255, 255, 255))
                buttons_list = [button_add_sun, button_add_planet, button_play_pause,
                                button_save, button_load, button_sb_reset, button_sb_menu, button_sb_quit]

            glEnable(GL_DEPTH_TEST)
            glMatrixMode(GL_PROJECTION)
            gluPerspective(60,(display[0]/display[1]), 20,1000)
            if menu == 1 :
                # --- Paramètres de la lumière (Soleil) ---
                glLightfv(GL_LIGHT0, GL_POSITION, [-1000, 50.0, 0.0, 1.0])
                glLightfv(GL_LIGHT0, GL_DIFFUSE, [255,255,200, 1])

            glMatrixMode(GL_MODELVIEW)
            glEnable(GL_TEXTURE_2D)
            viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)
            glLoadIdentity()

            if (menu == 1):
                init_earth_moon(tab_planets)
            if (menu == 2):
                init_planet(tab_planets)
            # menu == 3: start with empty tab_planets

            texture = load_image('textures/milky.jpg')
            camera_x = 0
            camera_y = 0
            incremented_speed = 1
            while run:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        run = False
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                            run = False  
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:  # Clic gauche
                            mouse_x, mouse_y = pygame.mouse.get_pos()
                            # Conversion des coordonnées OpenGL (viewport)
                            viewport = glGetIntegerv(GL_VIEWPORT)
                            mouse_y = viewport[3] - mouse_y  # Inversion Y

                            if menu == 3:
                                # --- Sandbox button clicks ---
                                def btn_hit(b):
                                    return (b.x <= mouse_x <= b.x + b.width and
                                            b.y <= mouse_y <= b.y + b.height)
                                if btn_hit(button_add_sun):
                                    sandbox_mode = SANDBOX_PLACING_SUN
                                    sandbox_pending_planet = None
                                    sandbox_pending_pos = None
                                elif btn_hit(button_add_planet):
                                    sandbox_mode = SANDBOX_PLACING_PLANET_POS
                                    sandbox_pending_planet = None
                                    sandbox_pending_pos = None
                                elif btn_hit(button_play_pause):
                                    sandbox_paused = not sandbox_paused
                                    button_play_pause.update_button("Play" if sandbox_paused else "Pause", font)
                                    button_play_pause.color = SIM_GREEN if sandbox_paused else SIM_ORANGE
                                elif btn_hit(button_save):
                                    save_sandbox(tab_planets)
                                elif btn_hit(button_load):
                                    tab_planets = load_sandbox()
                                    move = 0
                                elif btn_hit(button_sb_reset):
                                    tab_planets = []
                                    sandbox_mode = SANDBOX_IDLE
                                    sandbox_pending_planet = None
                                    sandbox_pending_pos = None
                                    move = 0
                                elif btn_hit(button_sb_menu):
                                    tab_planets = []
                                    menu = 0
                                    run = 0
                                elif btn_hit(button_sb_quit):
                                    run = False
                                    running_menu = False
                                elif mouse_x < WIDTH - 190 and last_modelview is not None:
                                    # Click on the map area
                                    wx, wy = screen_to_world_z0(mouse_x, mouse_y, last_modelview, last_projection, last_viewport)
                                    if sandbox_mode == SANDBOX_PLACING_SUN:
                                        texture_sun = load_image("textures/sun2.jpg")
                                        new_sun = Planet(wx / SCALE, wy / SCALE, 0, 8, WHITE, 1.98892 * 10**30, 0, 1, texture_sun, 1)
                                        new_sun.texture_name = "textures/sun2.jpg"
                                        # If another sun exists, give circular orbital velocity around nearest sun
                                        existing_suns = [p for p in tab_planets if p.sun == 1]
                                        if existing_suns:
                                            nearest = min(existing_suns, key=lambda p: math.sqrt((new_sun.x - p.x)**2 + (new_sun.y - p.y)**2))
                                            dist = math.sqrt((new_sun.x - nearest.x)**2 + (new_sun.y - nearest.y)**2)
                                            if dist > 1e5:
                                                v = math.sqrt(G * nearest.mass / dist)
                                                rx = new_sun.x - nearest.x
                                                ry = new_sun.y - nearest.y
                                                rlen = math.sqrt(rx**2 + ry**2)
                                                new_sun.x_vel = -ry / rlen * v
                                                new_sun.y_vel = rx / rlen * v
                                        new_sun.orbit.append((new_sun.x, new_sun.y, new_sun.z))
                                        tab_planets.append(new_sun)
                                        sandbox_mode = SANDBOX_IDLE
                                    elif sandbox_mode == SANDBOX_PLACING_PLANET_POS:
                                        sandbox_pending_pos = (wx, wy)
                                        # Create temp planet at this position
                                        rand_color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
                                        sandbox_pending_planet = Planet(wx / SCALE, wy / SCALE, 0, 3, rand_color, 5.97 * 10**24, 0, 0, 0, 5)
                                        sandbox_mode = SANDBOX_PLACING_PLANET_VEL
                                    elif sandbox_mode == SANDBOX_PLACING_PLANET_VEL:
                                        if sandbox_pending_planet is not None:
                                            vx, vy = compute_orbital_velocity(
                                                sandbox_pending_planet.x, sandbox_pending_planet.y,
                                                wx, wy, tab_planets, SCALE)
                                            sandbox_pending_planet.x_vel = vx
                                            sandbox_pending_planet.y_vel = vy
                                            sandbox_pending_planet.orbit.append((sandbox_pending_planet.x, sandbox_pending_planet.y, sandbox_pending_planet.z))
                                            tab_planets.append(sandbox_pending_planet)
                                            sandbox_pending_planet = None
                                            sandbox_pending_pos = None
                                            sandbox_mode = SANDBOX_IDLE

                            else:
                                # --- Menu 1/2 button clicks ---
                                if (button_orbit.x <= mouse_x <= button_orbit.x + button_orbit.width and
                                    button_orbit.y <= mouse_y <= button_orbit.y + button_orbit.height):
                                    if ORBIT_ON:
                                        button_orbit.color = (0.38, 0.38, 0.44, 1)
                                        button_orbit.update_button("ORBIT OFF", font)
                                        ORBIT_ON = 0
                                    else:
                                        button_orbit.color = (0.80, 0.15, 0.15, 1)
                                        button_orbit.update_button("ORBIT ON", font)
                                        ORBIT_ON = 1
                                if (button_reset.x <= mouse_x <= button_reset.x + button_reset.width and
                                button_reset.y <= mouse_y <= button_reset.y + button_reset.height):
                                    tab_planets = reset(tab_planets,menu)
                                    move = 0
                                    incremented_speed = 1
                                    del camera
                                    camera = Camera_Position(150,100,50,0,0,0)
                                if (button_plus.x <= mouse_x <= button_plus.x + button_plus.width and
                                button_plus.y <= mouse_y <= button_plus.y + button_plus.height):
                                        if (SPEED<500):
                                            SPEED *= 2
                                            button_speed.update_button("x %.2f"%(SPEED/60),font)
                                if (button_minus.x <= mouse_x <= button_minus.x + button_minus.width and
                                button_minus.y <= mouse_y <= button_minus.y + button_minus.height):
                                        if (SPEED>9):
                                            SPEED /=2
                                            button_speed.update_button("x %.2f"%(SPEED/60),font)
                                if (button_quit.x <= mouse_x <= button_quit.x + button_quit.width and
                                button_quit.y <= mouse_y <= button_quit.y + button_quit.height):
                                        run = False
                                        running_menu = False
                                if (button_earth_speed.x <= mouse_x <= button_earth_speed.x + button_earth_speed.width and
                                button_earth_speed.y <= mouse_y <= button_earth_speed.y + button_earth_speed.height):
                                        tab_planets = reset(tab_planets,menu)
                                        menu = 0
                                        run = 0

                        # Right click to cancel placement in sandbox
                        if event.button == 3 and menu == 3:
                            sandbox_mode = SANDBOX_IDLE
                            sandbox_pending_planet = None
                            sandbox_pending_pos = None

                handle_keys(camera)
                if menu != 3 or not sandbox_paused:
                    move += 1

                #display info about the simulation elapsed_time since the start of simulation
                if menu == 1:  
                    elapsed_time = move / 3600 * 24 *6 
                    button_time.update_button("time : %.1f jours" % elapsed_time,font)
                    # init model view matrix and center it to the earth (center object)
                elif menu == 2 :
                    elapsed_time = move / 360 
                    button_time.update_button("time : %.2f ans" % elapsed_time,font)
                    # init model view matrix and center it to the earth (center object)
                glLoadIdentity()  
                if menu == 1 :
                    camera_x = tab_planets[0].x  * SCALE
                    camera_y = tab_planets[0].y  * SCALE
                    camera_z = tab_planets[0].z  * SCALE        
                    camera.reset_angles()          
                    gluLookAt(camera_x+camera.pos_x, camera_y+camera.pos_y,camera_z+camera.pos_z, camera_x+camera.angle_x, camera_y+camera.angle_y,camera_z+camera.angle_z, 0, 0, 1)
                elif menu == 2 or menu == 3:
                    gluLookAt(camera.pos_x+10, camera.pos_y+0,camera.pos_z+20, camera.angle_x, camera.angle_y,camera.angle_z, 0, 0, 1)


                # init the view matrix
                glPushMatrix()
                glLoadIdentity()
                        
                # multiply the current matrix by the get the new view matrix and store the final vie matrix 
                glMultMatrixf(viewMatrix)
                viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)

                # apply view matrix
                glPopMatrix()
                glMultMatrixf(viewMatrix)
                glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT) #Clear the screen
                glPushMatrix()

                #draw images, axys and grid
                draw_image(texture)
                draw_axys()
                if menu == 1:
                    draw_gravity_grid(tab_planets, SCALE, grid_range=120, grid_steps=22, z_scale=80, z_offset=-10)
                elif menu == 2 or menu == 3:
                    if tab_planets:
                        draw_gravity_grid(tab_planets, SCALE, grid_range=300, grid_steps=22, z_scale=200, z_offset=-15)
                if menu == 1:
                    glEnable(GL_LIGHTING)
                    glEnable(GL_LIGHT0)

                    for planet in tab_planets:  
                        planet.update_position(tab_planets,TIMESTEP)
                        planet.draw(SCALE)

                        if(ORBIT_ON):
                        #if  planet.sun == 0:
                            glDisable(GL_LIGHTING)
                            glDisable(GL_LIGHT0)
                            planet.draw_orbit(SCALE)
                            glEnable(GL_LIGHTING)
                            glEnable(GL_LIGHT0)
                    glDisable(GL_LIGHTING)
                    glDisable(GL_LIGHT0)
                
                elif menu == 2:
                    for planet in tab_planets:
                        planet.update_position(tab_planets,TIMESTEP)
                        planet.draw(SCALE)
                        if(ORBIT_ON):
                            planet.draw_orbit(SCALE)

                elif menu == 3:
                    for planet in tab_planets:
                        if not sandbox_paused:
                            planet.update_position(tab_planets, TIMESTEP)
                        planet.draw(SCALE)
                        planet.draw_orbit(SCALE)
                    # Draw pending planet
                    if sandbox_pending_planet is not None:
                        sandbox_pending_planet.draw(SCALE)
                    # Draw velocity preview line
                    if sandbox_mode == SANDBOX_PLACING_PLANET_VEL and sandbox_pending_pos is not None and last_modelview is not None:
                        mx, my = pygame.mouse.get_pos()
                        vp = glGetIntegerv(GL_VIEWPORT)
                        my_gl = vp[3] - my
                        try:
                            mwx, mwy = screen_to_world_z0(mx, my_gl, last_modelview, last_projection, last_viewport)
                            glColor3f(0, 1, 0)
                            glLineWidth(2.0)
                            glBegin(GL_LINES)
                            glVertex3f(sandbox_pending_pos[0], sandbox_pending_pos[1], 0)
                            glVertex3f(mwx, mwy, 0)
                            glEnd()
                            glLineWidth(1.0)
                        except Exception:
                            pass

                    # Store matrices for gluUnProject
                    last_modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
                    last_projection = glGetDoublev(GL_PROJECTION_MATRIX)
                    last_viewport = glGetIntegerv(GL_VIEWPORT)

                glPopMatrix()

                # 3. Afficher le texte en 2D par-dessus la scène OpenGL
                # On sauvegarde la matrice de projection OpenGL
                glMatrixMode(GL_PROJECTION)
                glPushMatrix()
                glLoadIdentity()
                gluOrtho2D(0, display[0], 0, display[1])  # Passe en mode 2D
                glMatrixMode(GL_MODELVIEW)
                glPushMatrix()
                glLoadIdentity()
                glDisable(GL_DEPTH_TEST)
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                # Afficher le texte
                glRasterPos2f(50, display[1] - 50)
                glDrawPixels(text_width, text_height, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

                # Afficher les boutons avec dégradé et bordure
                for button in buttons_list:
                    draw_gradient_rect(button.x, button.y, button.width, button.height,
                                       button.color, darken(button.color))
                    draw_button_border(button.x, button.y, button.width, button.height)
                    glRasterPos2f(button.x + (button.width - button.text.get_width()) // 2,
                                  button.y + (button.height - button.text.get_height()) // 2)
                    glDrawPixels(button.text.get_width(), button.text.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, button.data)

                # Sandbox status text
                if menu == 3:
                    if sandbox_paused:
                        status_text = "PAUSED"
                    else:
                        elapsed_time = move / 360
                        status_text = "%.2f ans" % elapsed_time
                    status_surface = font.render(status_text, False, (255, 200, 100))
                    status_data = pygame.image.tobytes(status_surface, "RGBA", True)
                    glRasterPos2f(50, display[1] - 80)
                    glDrawPixels(status_surface.get_width(), status_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, status_data)

                    # Mode indicator
                    mode_names = {SANDBOX_IDLE: "", SANDBOX_PLACING_SUN: "Cliquez pour placer un Soleil",
                                  SANDBOX_PLACING_PLANET_POS: "Cliquez pour placer une Planete",
                                  SANDBOX_PLACING_PLANET_VEL: "Cliquez pour definir la vitesse"}
                    mode_txt = mode_names.get(sandbox_mode, "")
                    if mode_txt:
                        mode_surface = font.render(mode_txt, False, (100, 255, 100))
                        mode_data = pygame.image.tobytes(mode_surface, "RGBA", True)
                        glRasterPos2f(50, display[1] - 110)
                        glDrawPixels(mode_surface.get_width(), mode_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, mode_data)

                glDisable(GL_BLEND)
                glEnable(GL_DEPTH_TEST)
                # On restaure les matrices
                glMatrixMode(GL_PROJECTION)
                glPopMatrix()
                glMatrixMode(GL_MODELVIEW)
                glPopMatrix()

                pygame.display.flip() #Update the screen
                clock.tick(SPEED)

            pygame.quit()
            clock = init_game(display)
            texture_menu_bg = 0  # invalidate: new OpenGL context after reinit


    pygame.quit()

main()