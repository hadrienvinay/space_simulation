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
import datetime
import json
import random
from collections import deque
import numpy as np

MAX_ORBIT_POINTS = 2000

WIDTH, HEIGHT = 1100, 800 

AU = 149.6e6 * 1000
G = 6.67428e-11
SCALE_1 = 15000 / AU # 1AU = 500 pixel
SCALE_2 = 150 / AU # 1AU = 500 pixel
TIMESTEP_1 = 3600  # 1 day = *24 , here 1hour
TIMESTEP_2 = 3600 * 24 # 1 day = *24 , here 1 day
SCALE_THREE  = 5e-8      # L=1e9 m → 50 visual units (figure-8 orbit)
TIMESTEP_THREE = 3600    # 1 hour/step for numerical stability
SOFTENING    = 1e7       # Plummer softening length in metres (10 000 km)
SUBSTEP_MAX  = 64        # maximum adaptive sub-steps per rendered frame

# Earth 3D mode constants
SCALE_EARTH = 10.0 / 6.371e6          # Earth radius = 10 visual units
TIMESTEP_EARTH = 10                    # 10 sec/frame -> 600x real-time at 60fps
EARTH_RADIUS_M = 6.371e6              # meters
EARTH_MASS = 5.972e24                  # kg
EARTH_ROT_PER_FRAME = 360.0 * TIMESTEP_EARTH / 86400.0  # ~0.04167 deg/frame
V_CIRC_SURFACE = 7910.0               # m/s circular orbit at surface
LAUNCH_V_FACTOR = 1.15                # elliptical orbit factor
V_TLI = 10900.0                       # m/s trans-lunar injection velocity

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

        self.orbit = deque(maxlen=MAX_ORBIT_POINTS)

        self.x_vel = 0
        self.y_vel = 0
        self.z_vel = 0

    def infos(self):
        print(self.x,self.y,self.z)

    _shared_quadric = None

    @classmethod
    def _get_quadric(cls):
        if cls._shared_quadric is None:
            cls._shared_quadric = gluNewQuadric()
        return cls._shared_quadric

    def draw(self,SCALE):
        x = self.x * SCALE
        y = self.y * SCALE
        z = self.z * SCALE
        sphere = self._get_quadric()
        glPushMatrix()
        glTranslatef(x, y, z)
        glRotatef(self.angle, 0, 0, 1)
        self.angle += self.rotation
        if self.texture == 0:
            glColor4f(self.color[0]/255, self.color[1]/255, self.color[2]/255, 0)
        else:
            glColor4f(1, 1, 1, 0)
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.texture)
        gluQuadricTexture(sphere, GL_TRUE)
        gluSphere(sphere, self.radius, 32, 32)
        if self.texture != 0:
            glDisable(GL_TEXTURE_2D)
        glPopMatrix()

    def update_position(self, planets, TIMESTEP, substeps=1):
        dt = TIMESTEP / substeps
        for _ in range(substeps):
            total_fx = total_fy = total_fz = 0
            for planet in planets:
                if self == planet:
                    continue
                # Skip negligible satellite-satellite gravity
                if self.mass < 1e10 and planet.mass < 1e10:
                    continue
                fx, fy, fz = self.attraction(planet)
                total_fx += fx
                total_fy += fy
                total_fz += fz
            self.x_vel += total_fx / self.mass * dt
            self.y_vel += total_fy / self.mass * dt
            self.z_vel += total_fz / self.mass * dt
            self.x += self.x_vel * dt
            self.y += self.y_vel * dt
            self.z += self.z_vel * dt
        self.orbit.append((self.x, self.y, self.z))

    def attraction(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        dz = other.z - self.z
        r2 = dx*dx + dy*dy + dz*dz
        # Plummer softening: replaces 1/r² with 1/(r²+ε²), caps force at close range
        soft_r = math.sqrt(r2 + SOFTENING * SOFTENING)
        f = G * self.mass * other.mass / (soft_r * soft_r)
        inv = 1.0 / soft_r
        return f * dx * inv, f * dy * inv, f * dz * inv

    def draw_orbit(self, SCALE):
        points = len(self.orbit)
        if points < 2:
            return
        MAX_SEGMENTS = 200
        step = max(1, points // MAX_SEGMENTS)
        glBegin(GL_LINE_STRIP)
        glColor3f(self.color[0]/255, self.color[1]/255, self.color[2]/255)
        for i in range(0, points, step):
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

    def hit_test(self, mx, my):
        return (self.x <= mx <= self.x + self.width and
                self.y <= my <= self.y + self.height)

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

def draw_text_overlay(font, text, color, x, y):
    """Render text as a 2D overlay using glDrawPixels."""
    surf = font.render(text, False, color)
    data = pygame.image.tobytes(surf, "RGBA", True)
    glRasterPos2f(x, y)
    glDrawPixels(surf.get_width(), surf.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, data)

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
    near, d = screen_to_ray(mouse_x, mouse_y, modelview, projection, viewport)
    if abs(d[2]) < 1e-10:
        return near[0], near[1]
    t = -near[2] / d[2]
    return near[0] + t * d[0], near[1] + t * d[1]

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

def screen_to_ray(mouse_x, mouse_y, modelview, projection, viewport):
    """Returns (origin, direction) ray in world space from a screen click."""
    near = gluUnProject(mouse_x, mouse_y, 0.0, modelview, projection, viewport)
    far  = gluUnProject(mouse_x, mouse_y, 1.0, modelview, projection, viewport)
    d = (far[0] - near[0], far[1] - near[1], far[2] - near[2])
    return near, d

def ray_sphere_intersect(ray_origin, ray_dir, center, radius):
    """Returns intersection point (x,y,z) or None."""
    ox = ray_origin[0] - center[0]
    oy = ray_origin[1] - center[1]
    oz = ray_origin[2] - center[2]
    a = ray_dir[0]**2 + ray_dir[1]**2 + ray_dir[2]**2
    b = 2 * (ox * ray_dir[0] + oy * ray_dir[1] + oz * ray_dir[2])
    c = ox**2 + oy**2 + oz**2 - radius**2
    disc = b*b - 4*a*c
    if disc < 0:
        return None
    sq = math.sqrt(disc)
    t1 = (-b - sq) / (2*a)
    t2 = (-b + sq) / (2*a)
    t = t1 if t1 > 0 else t2
    if t < 0:
        return None
    return (ray_origin[0] + t*ray_dir[0],
            ray_origin[1] + t*ray_dir[1],
            ray_origin[2] + t*ray_dir[2])

def launch_satellite(hit_visual, SCALE):
    """Create a satellite at the hit point on Earth's surface with tangent velocity."""
    # Convert visual coords to real-world meters
    pos_x = hit_visual[0] / SCALE
    pos_y = hit_visual[1] / SCALE
    pos_z = hit_visual[2] / SCALE
    # Normal (radial direction from Earth center)
    r = math.sqrt(pos_x**2 + pos_y**2 + pos_z**2)
    if r < 1e-6:
        r = 1.0
    nx, ny, nz = pos_x/r, pos_y/r, pos_z/r
    # Tangent direction: cross((0,0,1), normal) → eastward
    tx = -ny
    ty = nx
    tz = 0.0
    tlen = math.sqrt(tx**2 + ty**2 + tz**2)
    if tlen < 1e-6:
        # Near pole: use cross((1,0,0), normal)
        tx, ty, tz = 0.0, nz, -ny
        tlen = math.sqrt(tx**2 + ty**2 + tz**2)
    tx /= tlen; ty /= tlen; tz /= tlen
    v = LAUNCH_V_FACTOR * V_CIRC_SURFACE
    color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
    sat = Planet(pos_x, pos_y, pos_z, 0.3, color, 1000, 0, 0, 0, 0)
    sat.x_vel = tx * v
    sat.y_vel = ty * v
    sat.z_vel = tz * v
    sat.orbit.append((sat.x, sat.y, sat.z))
    return sat

def init_earth_3d(tab_planets):
    """Initialize Earth + Moon for 3D satellite mode."""
    texture_earth = load_image("textures/earth_test.jpg")
    earth = Planet(0, 0, 0, 10, BLUE, EARTH_MASS, 0, 0, texture_earth, EARTH_ROT_PER_FRAME)
    earth.orbit.append((earth.x, earth.y, earth.z))
    tab_planets.append(earth)
    texture_moon = load_image("textures/moon_test.jpg")
    moon = Planet(-3.844e8, 0, 0, 2.7, DARK_GREY, 7.347e22, 0, 0, texture_moon, 0)
    moon.y_vel = 1.022 * 1000  # orbital velocity ~1.022 km/s
    moon.orbit.append((moon.x, moon.y, moon.z))
    tab_planets.append(moon)

def launch_rocket_to_moon(tab_planets, SCALE):
    """Launch a rocket from Earth surface towards the Moon."""
    earth = tab_planets[0]
    moon = None
    for p in tab_planets:
        if 1e21 < p.mass < 1e24:
            moon = p
            break
    if moon is None:
        return None
    dx = moon.x - earth.x
    dy = moon.y - earth.y
    dz = moon.z - earth.z
    dist = math.sqrt(dx**2 + dy**2 + dz**2)
    nx, ny, nz = dx/dist, dy/dist, dz/dist
    # Launch from Earth surface facing the Moon
    launch_x = earth.x + EARTH_RADIUS_M * nx
    launch_y = earth.y + EARTH_RADIUS_M * ny
    launch_z = earth.z + EARTH_RADIUS_M * nz
    v = V_TLI
    rocket = Planet(launch_x, launch_y, launch_z, 0.5, (255, 50, 50), 1000, 0, 0, 0, 0)
    rocket.x_vel = v * nx
    rocket.y_vel = v * ny
    rocket.z_vel = v * nz
    rocket.orbit.append((rocket.x, rocket.y, rocket.z))
    return rocket

def init_earth_moon(tab_planets):
    M_EARTH = 5.972e24
    M_MOON  = 7.347e22
    V_MOON  = 1.022e3   # m/s orbital speed relative to Earth

    texture_earth = load_image("textures/earth_test.jpg")
    earth = Planet(0, 0, 0, 10, BLUE, M_EARTH, 0, 0, texture_earth, 5)
    # Conservation of momentum: Earth recoils opposite to Moon's orbital velocity
    earth.y_vel = -(M_MOON / M_EARTH) * V_MOON   # ≈ -12.6 m/s
    earth.orbit.append((earth.x, earth.y, earth.z))

    # Moon distance ~384 400 km; 5.1° orbital inclination gives z ≈ 3.4e7 m
    texture_moon = load_image("textures/moon_test.jpg")
    moon = Planet(-3.844e8, 0, 3.4e7, 5, DARK_GREY, M_MOON, 0, 0, texture_moon, 0)
    # Orbital velocity is perpendicular to the radius vector (-3.844e8, 0, 3.4e7)
    # y-component only → dot product with radius = 0  ✓
    moon.y_vel = earth.y_vel + V_MOON
    moon.orbit.append((moon.x, moon.y, moon.z))

    tab_planets.append(earth)
    tab_planets.append(moon)

# Keplerian elements at epoch J2000.0 and their rates per Julian century.
# Standard JPL/Standish low-precision set, valid ~1800-2050 AD.
# a: semi-major axis (AU), e: eccentricity, I: inclination (deg),
# L: mean longitude (deg), peri: longitude of perihelion (deg), node: longitude of ascending node (deg)
PLANET_ORBITAL_ELEMENTS = {
    "mercury": dict(a=0.38709927, a_dot=0.00000037, e=0.20563593, e_dot=0.00001906,
                     I=7.00497902, I_dot=-0.00594749, L=252.25032350, L_dot=149472.67411175,
                     peri=77.45779628, peri_dot=0.16047689, node=48.33076593, node_dot=-0.12534081),
    "venus": dict(a=0.72333566, a_dot=0.00000390, e=0.00677672, e_dot=-0.00004107,
                   I=3.39467605, I_dot=-0.00078890, L=181.97909950, L_dot=58517.81538729,
                   peri=131.60246718, peri_dot=0.00268329, node=76.67984255, node_dot=-0.27769418),
    "earth": dict(a=1.00000261, a_dot=0.00000562, e=0.01671123, e_dot=-0.00004392,
                   I=-0.00001531, I_dot=-0.01294668, L=100.46457166, L_dot=35999.37244981,
                   peri=102.93768193, peri_dot=0.32327364, node=0.0, node_dot=0.0),
    "mars": dict(a=1.52371034, a_dot=0.00001847, e=0.09339410, e_dot=0.00007882,
                  I=1.84969142, I_dot=-0.00813131, L=-4.55343205, L_dot=19140.30268499,
                  peri=-23.94362959, peri_dot=0.44441088, node=49.55953891, node_dot=-0.29257343),
    "jupiter": dict(a=5.20288700, a_dot=-0.00011607, e=0.04838624, e_dot=-0.00013253,
                     I=1.30439695, I_dot=-0.00183714, L=34.39644051, L_dot=3034.74612775,
                     peri=14.72847983, peri_dot=0.21252668, node=100.47390909, node_dot=0.20469106),
    "saturn": dict(a=9.53667594, a_dot=-0.00125060, e=0.05386179, e_dot=-0.00050991,
                    I=2.48599187, I_dot=0.00193609, L=49.95424423, L_dot=1222.49362201,
                    peri=92.59887831, peri_dot=-0.41897216, node=113.66242448, node_dot=-0.28867794),
    "uranus": dict(a=19.18916464, a_dot=-0.00196176, e=0.04725744, e_dot=-0.00004397,
                    I=0.77263783, I_dot=-0.00242939, L=313.23810451, L_dot=428.48202785,
                    peri=170.95427630, peri_dot=0.40805281, node=74.01692503, node_dot=0.04240589),
    "neptune": dict(a=30.06992276, a_dot=0.00026291, e=0.00859048, e_dot=0.00005105,
                     I=1.77004347, I_dot=0.00035372, L=-55.12002969, L_dot=218.45945325,
                     peri=44.96476227, peri_dot=-0.32241464, node=131.78422574, node_dot=-0.00508664),
}

J2000_EPOCH = datetime.datetime(2000, 1, 1, 12, 0, 0)

def days_since_j2000(date):
    if isinstance(date, datetime.datetime):
        dt = date
    else:
        dt = datetime.datetime.combine(date, datetime.time())
    return (dt - J2000_EPOCH).total_seconds() / 86400.0

def solve_kepler(M, e):
    E = M
    for _ in range(50):
        dE = (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
        E -= dE
        if abs(dE) < 1e-12:
            break
    return E

def heliocentric_state(elements, days, GM):
    T = days / 36525.0
    a = (elements["a"] + elements["a_dot"] * T) * AU
    e = elements["e"] + elements["e_dot"] * T
    I = math.radians(elements["I"] + elements["I_dot"] * T)
    L = elements["L"] + elements["L_dot"] * T
    peri = elements["peri"] + elements["peri_dot"] * T
    node = elements["node"] + elements["node_dot"] * T
    omega = math.radians(peri - node)
    node = math.radians(node)

    M = math.radians((L - peri + 180) % 360 - 180)
    E = solve_kepler(M, e)

    x_orb = a * (math.cos(E) - e)
    y_orb = a * math.sqrt(1 - e * e) * math.sin(E)
    r = a * (1 - e * math.cos(E))
    n = math.sqrt(GM / (a ** 3))
    vx_orb = -n * a * a / r * math.sin(E)
    vy_orb = n * a * a / r * math.sqrt(1 - e * e) * math.cos(E)

    cos_o, sin_o = math.cos(omega), math.sin(omega)
    cos_n, sin_n = math.cos(node), math.sin(node)
    cos_i, sin_i = math.cos(I), math.sin(I)

    def rotate(px, py):
        x = (cos_n * cos_o - sin_n * sin_o * cos_i) * px + (-cos_n * sin_o - sin_n * cos_o * cos_i) * py
        y = (sin_n * cos_o + cos_n * sin_o * cos_i) * px + (-sin_n * sin_o + cos_n * cos_o * cos_i) * py
        z = (sin_o * sin_i) * px + (cos_o * sin_i) * py
        return x, y, z

    x, y, z = rotate(x_orb, y_orb)
    vx, vy, vz = rotate(vx_orb, vy_orb)
    return x, y, z, vx, vy, vz

def init_planet(tab_planets, date=None):
    if date is None:
        date = datetime.date.today()
    days = days_since_j2000(date)
    SUN_MASS = 1.98892 * 10**30
    GM = G * SUN_MASS

    x,y,z,vx,vy,vz = heliocentric_state(PLANET_ORBITAL_ELEMENTS["mercury"], days, GM)
    texture_mercury = load_image("textures/mercury.jpg")
    mercury  = Planet(x,y,z,2,DARK_GREY,0.33*10**24,0,0,texture_mercury,8)
    mercury.x_vel, mercury.y_vel, mercury.z_vel = vx, vy, vz
    mercury.orbit.append((mercury.x, mercury.y, mercury.z))

    x,y,z,vx,vy,vz = heliocentric_state(PLANET_ORBITAL_ELEMENTS["venus"], days, GM)
    texture_venus = load_image("textures/venus.jpg")
    venus    = Planet(x,y,z,3,GREEN,4.87*10**24,0,0,texture_venus,0.01)
    venus.x_vel, venus.y_vel, venus.z_vel = vx, vy, vz
    venus.orbit.append((venus.x, venus.y, venus.z))

    x,y,z,vx,vy,vz = heliocentric_state(PLANET_ORBITAL_ELEMENTS["earth"], days, GM)
    texture_earth = load_image("textures/earth.jpg")
    earth    = Planet(x,y,z,4,BLUE,5.97*10**24,0,0,texture_earth,10)
    earth.x_vel, earth.y_vel, earth.z_vel = vx, vy, vz
    earth.orbit.append((earth.x, earth.y, earth.z))

    x,y,z,vx,vy,vz = heliocentric_state(PLANET_ORBITAL_ELEMENTS["mars"], days, GM)
    texture_mars = load_image("textures/mars.jpg")
    mars     = Planet(x,y,z,3,RED,0.642*10**24,0,0,texture_mars,0)
    mars.x_vel, mars.y_vel, mars.z_vel = vx, vy, vz
    mars.orbit.append((mars.x, mars.y,mars.z))

    x,y,z,vx,vy,vz = heliocentric_state(PLANET_ORBITAL_ELEMENTS["jupiter"], days, GM)
    texture_jupiter = load_image("textures/jupiter.jpg")
    jupiter  = Planet(x,y,z,8,ORANGE,1.9*10**27,0,0,texture_jupiter,0)
    jupiter.x_vel, jupiter.y_vel, jupiter.z_vel = vx, vy, vz
    jupiter.orbit.append((jupiter.x, jupiter.y,jupiter.z))

    x,y,z,vx,vy,vz = heliocentric_state(PLANET_ORBITAL_ELEMENTS["saturn"], days, GM)
    texture_saturn = load_image("textures/saturn.jpg")
    saturn   = Planet(x,y,z,7,YELLOW,5.683e26,0,0,texture_saturn,0)
    saturn.x_vel, saturn.y_vel, saturn.z_vel = vx, vy, vz
    saturn.orbit.append((saturn.x, saturn.y, saturn.z))

    x,y,z,vx,vy,vz = heliocentric_state(PLANET_ORBITAL_ELEMENTS["uranus"], days, GM)
    uranus   = Planet(x,y,z,6,BLUE,8.681e25,0,0,0,0)
    uranus.x_vel, uranus.y_vel, uranus.z_vel = vx, vy, vz
    uranus.orbit.append((uranus.x, uranus.y, uranus.z))

    x,y,z,vx,vy,vz = heliocentric_state(PLANET_ORBITAL_ELEMENTS["neptune"], days, GM)
    neptune  = Planet(x,y,z,5,(63,84,186),1.024e26,0,0,0,0)
    neptune.x_vel, neptune.y_vel, neptune.z_vel = vx, vy, vz
    neptune.orbit.append((neptune.x, neptune.y, neptune.z))

    texture_sun = load_image("textures/sun2.jpg")
    sun = Planet(0,0,0,8, WHITE, SUN_MASS,0,1,texture_sun,1)
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

def init_three_body(tab_planets, mode=1):
    """Known periodic three-body solutions, all scaled to Earth masses.
    Normalised units: G=m=1, L=1e9 m, v_scale = sqrt(G*M_earth/L) ≈ 631 m/s.
    mode 1 – Figure-8            Chenciner & Montgomery (2000)
    mode 2 – Triangle de Lagrange Lagrange (1772)
    mode 3 – Papillon            Šuvakov & Dmitrašinović (2013)
    mode 4 – Euler Collinéaire   Euler (1767) – analytically exact, unstable
    mode 5 – Binaire + Planète   hierarchical triple (binary + outer planet)"""
    L = 1e9
    v = math.sqrt(G * EARTH_MASS / L)   # ~631 m/s

    if mode == 1:
        # ── Figure-8 choreography ─────────────────────────────────────────
        x0, y0   = 0.97000436, 0.24308753
        vx0, vy0 = 0.93240737, 0.86473146
        bodies = [
            ((-x0,  y0), (vx0/2,  vy0/2), BLUE),
            (( x0, -y0), (vx0/2,  vy0/2), RED),
            (( 0.0, 0.0), (-vx0,   -vy0), GREEN),
        ]

    elif mode == 2:
        # ── Lagrange equilateral triangle, side a=2 ───────────────────────
        # ω = √(3/a³) = √(3/8); v = √(Gm/a) = 1/√2; R = a/√3
        R   = 2 / math.sqrt(3)   # centroid-to-vertex ≈ 1.1547
        spd = math.sqrt(0.5)     # orbital speed = 1/√2 ≈ 0.7071
        s3  = math.sqrt(3) / 2   # sin 60° — note y = R·s3 = 1.0 exactly
        bodies = [
            (( R,    0.0), (0.0,       spd),   BLUE),
            ((-R/2,  1.0), (-s3*spd,  -spd/2), RED),
            ((-R/2, -1.0), ( s3*spd,  -spd/2), GREEN),
        ]

    elif mode == 3:
        # ── Butterfly I choreography ──────────────────────────────────────
        # Šuvakov & Dmitrašinović (2013), Table 1; T ≈ 6.2356
        bodies = [
            (( 1.0, 0.0), ( 0.30674,  0.12540), BLUE),
            ((-1.0, 0.0), ( 0.30674,  0.12540), RED),
            (( 0.0, 0.0), (-0.61348, -0.25080), GREEN),
        ]

    elif mode == 4:
        # ── Euler's collinear rotating solution (1767) ────────────────────
        # Three equal masses at −1, 0, +1; outer bodies orbit the stationary centre.
        # Force on outer body: F = Gm²/1² + Gm²/4 = 5Gm²/4
        # Centripetal: mω²·1 = 5Gm/4  →  ω = √(5/4) (normalised G=m=1)
        # Centre body stays at rest (forces cancel by symmetry).
        # NOTE: this equilibrium is UNSTABLE — numerical errors will
        # eventually trigger chaotic divergence (demonstrating Euler instability).
        om = math.sqrt(5.0 / 4.0)   # ≈ 1.11803
        bodies = [
            ((-1.0, 0.0), (0.0, -om),  RED),
            (( 0.0, 0.0), (0.0,  0.0), WHITE),
            (( 1.0, 0.0), (0.0, +om),  BLUE),
        ]

    else:
        # ── Hierarchical triple: tight binary + distant planet ─────────────
        # Binary semi-separation d=0.04, planet radius R=0.8 (both × L).
        # d << R  →  T_inner/T_outer ≈ 1/32  (binary spins ~32× per planet orbit).
        # Binary orbital speed: v_b = 1/(2√d) = 2.5 (normalised)
        # Planet orbital speed: v_p = √(2/R) = √2.5 ≈ 1.5811 (normalised)
        # Binary CM gets recoil −v_p/2 so total linear momentum = 0.
        d   = 0.04
        R   = 0.80
        v_b = 1.0 / (2.0 * math.sqrt(d))          # = 2.5
        v_p = math.sqrt(2.0 / R)                   # ≈ 1.5811
        bodies = [
            ((-d,  0.0), (0.0, -(v_b + v_p / 2.0)), YELLOW),   # étoile A
            (( d,  0.0), (0.0,  (v_b - v_p / 2.0)), ORANGE),   # étoile B
            (( R,  0.0), (0.0,   v_p),               BLUE),     # planète
        ]

    for (px, py), (pvx, pvy), color in bodies:
        p = Planet(px * L, py * L, 0, 4, color, EARTH_MASS, 0, 0, 0, 0)
        p.x_vel = pvx * v
        p.y_vel = pvy * v
        p.orbit.append((p.x, p.y, p.z))
        tab_planets.append(p)

def step_all_synchronized(planets, dt):
    """One symplectic-Euler step where ALL forces are computed from the current
    position snapshot before ANY body is moved.
    Each pair is evaluated once and Newton's 3rd law is enforced exactly."""
    n = len(planets)
    forces = [[0.0, 0.0, 0.0] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            pi, pj = planets[i], planets[j]
            if pi.mass < 1e10 and pj.mass < 1e10:
                continue
            fx, fy, fz = pi.attraction(pj)
            forces[i][0] += fx;  forces[i][1] += fy;  forces[i][2] += fz
            forces[j][0] -= fx;  forces[j][1] -= fy;  forces[j][2] -= fz
    for p, f in zip(planets, forces):
        inv_m = 1.0 / p.mass
        p.x_vel += f[0] * inv_m * dt
        p.y_vel += f[1] * inv_m * dt
        p.z_vel += f[2] * inv_m * dt
        p.x += p.x_vel * dt
        p.y += p.y_vel * dt
        p.z += p.z_vel * dt

def adaptive_substeps(tab_planets, dt_frame):
    """Physics-derived sub-step count: keep Δv/v_orbital < 1% per sub-step.
    Condition: dt_sub < ε × v_orb/a = ε × r^1.5 / √(GM)
    → n = dt_frame × √(GM) / (ε × r^1.5),  ε = 0.01."""
    if len(tab_planets) < 2:
        return 1
    min_d2 = float('inf')
    for i in range(len(tab_planets)):
        for j in range(i + 1, len(tab_planets)):
            p, q = tab_planets[i], tab_planets[j]
            d2 = (p.x-q.x)**2 + (p.y-q.y)**2 + (p.z-q.z)**2
            if d2 < min_d2:
                min_d2 = d2
    min_d = max(math.sqrt(min_d2), 1.0)          # avoid division by zero
    GM    = G * max(p.mass for p in tab_planets)  # dominant mass term
    n     = int(dt_frame * math.sqrt(GM) / (0.01 * min_d ** 1.5))
    return max(1, min(SUBSTEP_MAX, n))

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

def reset(tab_planets, menu, three_corps_mode=1, date=None):
    new_tab = []
    if menu == 1:
        init_earth_moon(new_tab)
    elif menu == 2:
        init_planet(new_tab, date)
    elif menu == 3:
        pass  # Sandbox starts empty
    elif menu == 4:
        init_earth_3d(new_tab)
    elif menu == 5:
        init_three_body(new_tab, three_corps_mode)
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
    _total_btn_h = 6 * BTN_H + 5 * GAP
    menu_start_x = WIDTH // 2 - BTN_W // 2      # centered
    menu_start_y = HEIGHT // 2 - _total_btn_h // 2 - 40  # shifted down to leave room for title

    COL_BLUE   = (0.20, 0.45, 0.85, 1)
    COL_GOLD   = (0.85, 0.55, 0.05, 1)
    COL_PURPLE = (0.55, 0.20, 0.75, 1)
    COL_TEAL   = (0.10, 0.60, 0.60, 1)
    COL_RED    = (0.72, 0.10, 0.10, 1)
    COL_CYAN   = (0.10, 0.72, 0.78, 1)

    button_three_corps = Button(pygame.Rect(menu_start_x, menu_start_y + 5*(BTN_H + GAP), BTN_W, BTN_H),
                        font_menu.render("3 CORPS", False, (255, 255, 255)),
                        COL_CYAN, font_menu, text_color=(255, 255, 255))
    button_earth = Button(pygame.Rect(menu_start_x, menu_start_y + 4*(BTN_H + GAP), BTN_W, BTN_H),
                        font_menu.render("TERRE - LUNE", False, (255, 255, 255)),
                        COL_BLUE, font_menu, text_color=(255, 255, 255))
    button_solar_system = Button(pygame.Rect(menu_start_x, menu_start_y + 3*(BTN_H + GAP), BTN_W, BTN_H),
                        font_menu.render("SYSTEME SOLAIRE", False, (255, 255, 255)),
                        COL_GOLD, font_menu, text_color=(255, 255, 255))
    button_sandbox = Button(pygame.Rect(menu_start_x, menu_start_y + 2*(BTN_H + GAP), BTN_W, BTN_H),
                        font_menu.render("SANDBOX", False, (255, 255, 255)),
                        COL_PURPLE, font_menu, text_color=(255, 255, 255))
    button_earth_3d = Button(pygame.Rect(menu_start_x, menu_start_y + 1*(BTN_H + GAP), BTN_W, BTN_H),
                        font_menu.render("TERRE 3D", False, (255, 255, 255)),
                        COL_TEAL, font_menu, text_color=(255, 255, 255))
    button_quit_menu = Button(pygame.Rect(menu_start_x, menu_start_y, BTN_W, BTN_H),
                        font_menu.render("QUITTER", False, (255, 255, 255)),
                        COL_RED, font_menu, text_color=(255, 255, 255))
    buttons_menu = [button_three_corps, button_earth, button_solar_system, button_sandbox, button_earth_3d, button_quit_menu]

    texture_menu_bg = 0  # loaded lazily (reloaded after context recreation)

    # ── 3-corps sub-menu state ─────────────────────────────────────────────
    three_corps_mode    = 1     # 1=figure-8  2=Lagrange  3=Butterfly  4=Euler  5=Binary
    three_corps_submenu = False

    _sub_total_h = 6 * BTN_H + 5 * GAP   # 5 modes + back button
    sub_start_x  = menu_start_x
    sub_start_y  = HEIGHT // 2 - _sub_total_h // 2

    sub_title_surf = font_title.render("3 Corps  —  Choisissez la configuration",
                                       False, (160, 220, 255))
    sub_tw, sub_th = sub_title_surf.get_size()
    sub_title_data = pygame.image.tobytes(sub_title_surf, "RGBA", True)

    COL_FIG8  = (0.10, 0.72, 0.78, 1)
    COL_LAG   = (0.20, 0.68, 0.28, 1)
    COL_BUTT  = (0.72, 0.28, 0.60, 1)
    COL_EULER = (0.78, 0.40, 0.08, 1)
    COL_BIN   = (0.22, 0.20, 0.70, 1)
    COL_BACK  = (0.40, 0.40, 0.46, 1)

    button_binary = Button(
        pygame.Rect(sub_start_x, sub_start_y + 5*(BTN_H+GAP), BTN_W, BTN_H),
        font_menu.render("Binaire + Planete", False, (255,255,255)),
        COL_BIN, font_menu, text_color=(255,255,255))
    button_euler = Button(
        pygame.Rect(sub_start_x, sub_start_y + 4*(BTN_H+GAP), BTN_W, BTN_H),
        font_menu.render("Euler Colineaire", False, (255,255,255)),
        COL_EULER, font_menu, text_color=(255,255,255))
    button_fig8 = Button(
        pygame.Rect(sub_start_x, sub_start_y + 3*(BTN_H+GAP), BTN_W, BTN_H),
        font_menu.render("Orbite en 8", False, (255,255,255)),
        COL_FIG8, font_menu, text_color=(255,255,255))
    button_lagrange = Button(
        pygame.Rect(sub_start_x, sub_start_y + 2*(BTN_H+GAP), BTN_W, BTN_H),
        font_menu.render("Triangle de Lagrange", False, (255,255,255)),
        COL_LAG, font_menu, text_color=(255,255,255))
    button_butterfly = Button(
        pygame.Rect(sub_start_x, sub_start_y + 1*(BTN_H+GAP), BTN_W, BTN_H),
        font_menu.render("Papillon", False, (255,255,255)),
        COL_BUTT, font_menu, text_color=(255,255,255))
    button_back = Button(
        pygame.Rect(sub_start_x, sub_start_y, BTN_W, BTN_H),
        font_menu.render("< Retour", False, (255,255,255)),
        COL_BACK, font_menu, text_color=(255,255,255))
    buttons_submenu = [button_binary, button_euler, button_fig8,
                       button_lagrange, button_butterfly, button_back]

    while running_menu:

        move = 0
        run = True
        tab_planets = []
        sim_date = None
        sim_paused = False
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
                        if three_corps_submenu:
                            if button_binary.hit_test(mouse_x, mouse_y):
                                three_corps_mode = 5
                                menu = 5
                                three_corps_submenu = False
                            elif button_euler.hit_test(mouse_x, mouse_y):
                                three_corps_mode = 4
                                menu = 5
                                three_corps_submenu = False
                            elif button_fig8.hit_test(mouse_x, mouse_y):
                                three_corps_mode = 1
                                menu = 5
                                three_corps_submenu = False
                            elif button_lagrange.hit_test(mouse_x, mouse_y):
                                three_corps_mode = 2
                                menu = 5
                                three_corps_submenu = False
                            elif button_butterfly.hit_test(mouse_x, mouse_y):
                                three_corps_mode = 3
                                menu = 5
                                three_corps_submenu = False
                            elif button_back.hit_test(mouse_x, mouse_y):
                                three_corps_submenu = False
                        else:
                            if button_three_corps.hit_test(mouse_x, mouse_y):
                                three_corps_submenu = True
                            elif button_earth.hit_test(mouse_x, mouse_y):
                                menu = 1
                            elif button_solar_system.hit_test(mouse_x, mouse_y):
                                menu = 2
                            elif button_sandbox.hit_test(mouse_x, mouse_y):
                                menu = 3
                            elif button_earth_3d.hit_test(mouse_x, mouse_y):
                                menu = 4
                            elif button_quit_menu.hit_test(mouse_x, mouse_y):
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

            if three_corps_submenu:
                # ── Sub-menu panel ─────────────────────────────────────────
                _px = sub_start_x - 52
                _pw = BTN_W + 104
                _py = sub_start_y - 36
                _ph = _sub_total_h + sub_th + 60
                draw_gradient_rect(_px, _py, _pw, _ph,
                                   (0.05, 0.12, 0.22, 0.88), (0.02, 0.06, 0.14, 0.95))
                glColor4f(0.20, 0.70, 0.90, 0.40)
                glLineWidth(1.0)
                glBegin(GL_LINE_LOOP)
                glVertex2f(_px, _py); glVertex2f(_px + _pw, _py)
                glVertex2f(_px + _pw, _py + _ph); glVertex2f(_px, _py + _ph)
                glEnd()

                # Sub-menu title
                title_y = sub_start_y + _sub_total_h + 20
                glRasterPos2f(WIDTH // 2 - sub_tw // 2, title_y)
                glDrawPixels(sub_tw, sub_th, GL_RGBA, GL_UNSIGNED_BYTE, sub_title_data)

                sep_y = title_y - 8
                glColor4f(0.20, 0.70, 0.90, 0.50)
                glLineWidth(1.5)
                glBegin(GL_LINES)
                glVertex2f(_px + 24, sep_y); glVertex2f(_px + _pw - 24, sep_y)
                glEnd()
                glLineWidth(1.0)

                # Sub-menu buttons
                for button in buttons_submenu:
                    draw_gradient_rect(button.x, button.y, button.width, button.height,
                                       button.color, darken(button.color, 0.6))
                    draw_button_border(button.x, button.y, button.width, button.height)
                    glRasterPos2f(button.x + (button.width - button.text.get_width()) // 2,
                                  button.y + (button.height - button.text.get_height()) // 2)
                    glDrawPixels(button.text.get_width(), button.text.get_height(),
                                 GL_RGBA, GL_UNSIGNED_BYTE, button.data)
            else:
                # ── Main menu panel ────────────────────────────────────────
                _px = menu_start_x - 52
                _pw = BTN_W + 104
                _py = menu_start_y - 36
                _ph = _total_btn_h + text_height_menu + sub_h + 90
                draw_gradient_rect(_px, _py, _pw, _ph,
                                   (0.10, 0.05, 0.22, 0.82), (0.05, 0.02, 0.14, 0.92))
                glColor4f(0.65, 0.40, 1.0, 0.35)
                glLineWidth(1.0)
                glBegin(GL_LINE_LOOP)
                glVertex2f(_px, _py); glVertex2f(_px + _pw, _py)
                glVertex2f(_px + _pw, _py + _ph); glVertex2f(_px, _py + _ph)
                glEnd()

                # ── Title ──────────────────────────────────────────────────
                title_x = WIDTH // 2 - text_width_menu // 2
                title_y = menu_start_y + _total_btn_h + 38
                glRasterPos2f(title_x, title_y)
                glDrawPixels(text_width_menu, text_height_menu, GL_RGBA, GL_UNSIGNED_BYTE, text_data_menu)

                sep_y = title_y - 8
                glColor4f(0.75, 0.45, 1.0, 0.5)
                glLineWidth(1.5)
                glBegin(GL_LINES)
                glVertex2f(_px + 24, sep_y); glVertex2f(_px + _pw - 24, sep_y)
                glEnd()
                glLineWidth(1.0)

                glRasterPos2f(WIDTH // 2 - sub_w // 2, title_y + text_height_menu + 6)
                glDrawPixels(sub_w, sub_h, GL_RGBA, GL_UNSIGNED_BYTE, sub_data)

                # ── Main menu buttons ──────────────────────────────────────
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
            elif menu == 4:
                text_surface = font.render("Terre 3D - Lanceur de Satellites", False, (255, 215, 255, 1))
                SCALE = SCALE_EARTH
                TIMESTEP = TIMESTEP_EARTH
            elif menu == 5:
                text_surface = font.render("3 Corps - Orbite en 8 (Chenciner & Montgomery)", False, (255, 215, 255, 1))
                SCALE = SCALE_THREE
                TIMESTEP = TIMESTEP_THREE
            else:
                text_surface = font.render("Erreur Menu", False, (255, 215, 255, 1))

            text_width, text_height = text_surface.get_size()
            text_data = pygame.image.tobytes(text_surface, "RGBA", True)

            if menu == 4:
                camera = Camera_Position(0, -35, 15, 0, 0, 0)
            elif menu == 5:
                camera = Camera_Position(50, 80, 80, 0, 0, 0)
            else:
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
            SIM_TEAL_G = (0.15, 0.55, 0.50, 1)
            GRID_ON = True
            button_grid = Button(pygame.Rect(WIDTH-180, HEIGHT-360, 150, 50),
                                font.render("Grille ON", False, (255, 255, 255)),
                                SIM_TEAL_G, font, text_color=(255, 255, 255))
            SIM_ORANGE_M = (0.85, 0.50, 0.10, 1)
            button_pause = Button(pygame.Rect(WIDTH-180, HEIGHT-430, 150, 50),
                                font.render("Pause", False, (255, 255, 255)),
                                SIM_ORANGE_M, font, text_color=(255, 255, 255))
            buttons_list = [button_orbit,button_reset,button_time,button_speed,button_plus,button_minus,button_grid,button_pause,button_quit,button_earth_speed]

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

            if menu == 4:
                SIM_TEAL_E = (0.10, 0.55, 0.55, 1)
                SIM_ORANGE_E = (0.85, 0.50, 0.10, 1)
                button_launch = Button(pygame.Rect(WIDTH-180, HEIGHT-70, 150, 50),
                                    font.render("Lancer Sat.", False, (255, 255, 255)),
                                    SIM_TEAL_E, font, text_color=(255, 255, 255))
                button_e3d_orbit = Button(pygame.Rect(WIDTH-180, HEIGHT-140, 150, 50),
                                    font.render("Orbits ON", False, (255, 255, 255)),
                                    SIM_RED, font, text_color=(255, 255, 255))
                button_e3d_speed = Button(pygame.Rect(WIDTH-180, HEIGHT-210, 150, 50),
                                    font.render("Speed", False, (255, 255, 255)),
                                    SIM_NAVY, font, text_color=(255, 255, 255))
                button_e3d_plus = Button(pygame.Rect(WIDTH-176, HEIGHT-202, 30, 30),
                                    font.render("+", False, (255, 255, 255)),
                                    SIM_LGRAY, font, text_color=(255, 255, 255))
                button_e3d_minus = Button(pygame.Rect(WIDTH-65, HEIGHT-202, 30, 30),
                                    font.render("-", False, (255, 255, 255)),
                                    SIM_LGRAY, font, text_color=(255, 255, 255))
                SIM_ROCKET = (0.75, 0.20, 0.20, 1)
                button_rocket = Button(pygame.Rect(WIDTH-180, HEIGHT-280, 150, 50),
                                    font.render("Fusee Lune", False, (255, 255, 255)),
                                    SIM_ROCKET, font, text_color=(255, 255, 255))
                button_e3d_reset = Button(pygame.Rect(WIDTH-180, HEIGHT-350, 150, 50),
                                    font.render("Reset", False, (255, 255, 255)),
                                    SIM_GREEN, font, text_color=(255, 255, 255))
                button_e3d_menu = Button(pygame.Rect(WIDTH-180, 20, 150, 50),
                                    font.render("Menu", False, (255, 255, 255)),
                                    SIM_GRAY, font, text_color=(255, 255, 255))
                button_e3d_quit = Button(pygame.Rect(WIDTH-180, 80, 150, 50),
                                    font.render("QUIT", False, (255, 255, 255)),
                                    SIM_RED, font, text_color=(255, 255, 255))
                button_e3d_pause = Button(pygame.Rect(WIDTH-180, HEIGHT-420, 150, 50),
                                    font.render("Pause", False, (255, 255, 255)),
                                    SIM_ORANGE_E, font, text_color=(255, 255, 255))
                buttons_list = [button_launch, button_rocket, button_e3d_orbit, button_e3d_speed,
                                button_e3d_plus, button_e3d_minus, button_e3d_pause,
                                button_e3d_reset, button_e3d_menu, button_e3d_quit]
                e3d_launch_mode = False
                e3d_orbit_on = True
                satellites = []

            glEnable(GL_DEPTH_TEST)
            glMatrixMode(GL_PROJECTION)
            if menu == 4:
                gluPerspective(60, (display[0]/display[1]), 0.1, 2000)
            else:
                gluPerspective(60, (display[0]/display[1]), 20, 1000)
            if menu == 1:
                glLightfv(GL_LIGHT0, GL_POSITION, [-1000, 50.0, 0.0, 1.0])
                glLightfv(GL_LIGHT0, GL_DIFFUSE, [255, 255, 200, 1])
            # menu == 4: no lighting setup needed

            glMatrixMode(GL_MODELVIEW)
            glEnable(GL_TEXTURE_2D)
            viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)
            glLoadIdentity()

            if (menu == 1):
                init_earth_moon(tab_planets)
            if (menu == 2):
                today = datetime.date.today()
                init_planet(tab_planets, today)
                sim_date = datetime.datetime.combine(today, datetime.time())
            if (menu == 4):
                init_earth_3d(tab_planets)
            if (menu == 5):
                init_three_body(tab_planets, three_corps_mode)
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
                                if button_add_sun.hit_test(mouse_x, mouse_y):
                                    sandbox_mode = SANDBOX_PLACING_SUN
                                    sandbox_pending_planet = None
                                    sandbox_pending_pos = None
                                elif button_add_planet.hit_test(mouse_x, mouse_y):
                                    sandbox_mode = SANDBOX_PLACING_PLANET_POS
                                    sandbox_pending_planet = None
                                    sandbox_pending_pos = None
                                elif button_play_pause.hit_test(mouse_x, mouse_y):
                                    sandbox_paused = not sandbox_paused
                                    button_play_pause.update_button("Play" if sandbox_paused else "Pause", font)
                                    button_play_pause.color = SIM_GREEN if sandbox_paused else SIM_ORANGE
                                elif button_save.hit_test(mouse_x, mouse_y):
                                    save_sandbox(tab_planets)
                                elif button_load.hit_test(mouse_x, mouse_y):
                                    tab_planets = load_sandbox()
                                    move = 0
                                elif button_sb_reset.hit_test(mouse_x, mouse_y):
                                    tab_planets = []
                                    sandbox_mode = SANDBOX_IDLE
                                    sandbox_pending_planet = None
                                    sandbox_pending_pos = None
                                    move = 0
                                elif button_sb_menu.hit_test(mouse_x, mouse_y):
                                    tab_planets = []
                                    menu = 0
                                    run = 0
                                elif button_sb_quit.hit_test(mouse_x, mouse_y):
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

                            elif menu == 4:
                                # --- Earth 3D button clicks ---
                                if button_launch.hit_test(mouse_x, mouse_y):
                                    e3d_launch_mode = not e3d_launch_mode
                                    button_launch.update_button("Annuler" if e3d_launch_mode else "Lancer Sat.", font)
                                    button_launch.color = SIM_ORANGE_E if e3d_launch_mode else SIM_TEAL_E
                                elif button_rocket.hit_test(mouse_x, mouse_y):
                                    rocket = launch_rocket_to_moon(tab_planets, SCALE)
                                    if rocket is not None:
                                        tab_planets.append(rocket)
                                        satellites.append(rocket)
                                elif button_e3d_orbit.hit_test(mouse_x, mouse_y):
                                    e3d_orbit_on = not e3d_orbit_on
                                    button_e3d_orbit.update_button("Orbits ON" if e3d_orbit_on else "Orbits OFF", font)
                                    button_e3d_orbit.color = SIM_RED if e3d_orbit_on else SIM_GRAY
                                elif button_e3d_plus.hit_test(mouse_x, mouse_y):
                                    if SPEED < 500:
                                        SPEED *= 2
                                        button_e3d_speed.update_button("x %.2f" % (SPEED/60), font)
                                elif button_e3d_minus.hit_test(mouse_x, mouse_y):
                                    if SPEED > 9:
                                        SPEED /= 2
                                        button_e3d_speed.update_button("x %.2f" % (SPEED/60), font)
                                elif button_e3d_pause.hit_test(mouse_x, mouse_y):
                                    sim_paused = not sim_paused
                                    button_e3d_pause.update_button("Play" if sim_paused else "Pause", font)
                                    button_e3d_pause.color = SIM_GREEN if sim_paused else SIM_ORANGE_E
                                elif button_e3d_reset.hit_test(mouse_x, mouse_y):
                                    tab_planets = reset(tab_planets, menu)
                                    satellites = []
                                    move = 0
                                elif button_e3d_menu.hit_test(mouse_x, mouse_y):
                                    tab_planets = []
                                    menu = 0
                                    run = 0
                                elif button_e3d_quit.hit_test(mouse_x, mouse_y):
                                    run = False
                                    running_menu = False
                                elif e3d_launch_mode and mouse_x < WIDTH - 190 and last_modelview is not None:
                                    ray_o, ray_d = screen_to_ray(mouse_x, mouse_y,
                                                                  last_modelview, last_projection, last_viewport)
                                    hit = ray_sphere_intersect(ray_o, ray_d, (0, 0, 0), 10)
                                    if hit is not None:
                                        sat = launch_satellite(hit, SCALE)
                                        tab_planets.append(sat)
                                        satellites.append(sat)
                                        e3d_launch_mode = False
                                        button_launch.update_button("Lancer Sat.", font)
                                        button_launch.color = SIM_TEAL_E

                            else:
                                # --- Menu 1/2 button clicks ---
                                if button_orbit.hit_test(mouse_x, mouse_y):
                                    if ORBIT_ON:
                                        button_orbit.color = (0.38, 0.38, 0.44, 1)
                                        button_orbit.update_button("ORBIT OFF", font)
                                        ORBIT_ON = 0
                                    else:
                                        button_orbit.color = (0.80, 0.15, 0.15, 1)
                                        button_orbit.update_button("ORBIT ON", font)
                                        ORBIT_ON = 1
                                if button_reset.hit_test(mouse_x, mouse_y):
                                    if menu == 2:
                                        today = datetime.date.today()
                                        tab_planets = reset(tab_planets, menu, three_corps_mode, today)
                                        sim_date = datetime.datetime.combine(today, datetime.time())
                                    else:
                                        tab_planets = reset(tab_planets, menu, three_corps_mode)
                                    move = 0
                                    incremented_speed = 1
                                    camera = Camera_Position(50, 80, 80, 0, 0, 0) if menu == 5 else Camera_Position(150, 100, 50, 0, 0, 0)
                                if button_plus.hit_test(mouse_x, mouse_y):
                                    if SPEED < 500:
                                        SPEED *= 2
                                        button_speed.update_button("x %.2f" % (SPEED/60), font)
                                if button_minus.hit_test(mouse_x, mouse_y):
                                    if SPEED > 9:
                                        SPEED /= 2
                                        button_speed.update_button("x %.2f" % (SPEED/60), font)
                                if button_pause.hit_test(mouse_x, mouse_y):
                                    sim_paused = not sim_paused
                                    button_pause.update_button("Play" if sim_paused else "Pause", font)
                                    button_pause.color = SIM_GREEN if sim_paused else SIM_ORANGE_M
                                if button_grid.hit_test(mouse_x, mouse_y):
                                    GRID_ON = not GRID_ON
                                    button_grid.update_button("Grille ON" if GRID_ON else "Grille OFF", font)
                                    button_grid.color = SIM_TEAL_G if GRID_ON else SIM_GRAY
                                if button_quit.hit_test(mouse_x, mouse_y):
                                    run = False
                                    running_menu = False
                                if button_earth_speed.hit_test(mouse_x, mouse_y):
                                    tab_planets = reset(tab_planets, menu, three_corps_mode)
                                    menu = 0
                                    run = 0

                        # Right click to cancel placement in sandbox
                        if event.button == 3 and menu == 3:
                            sandbox_mode = SANDBOX_IDLE
                            sandbox_pending_planet = None
                            sandbox_pending_pos = None
                        if event.button == 3 and menu == 4:
                            e3d_launch_mode = False
                            button_launch.update_button("Lancer Sat.", font)
                            button_launch.color = SIM_TEAL_E

                handle_keys(camera)
                paused_now = sandbox_paused if menu == 3 else sim_paused
                if not paused_now:
                    move += 1
                    if menu == 2:
                        sim_date += datetime.timedelta(seconds=TIMESTEP)

                #display info about the simulation elapsed_time since the start of simulation
                if menu == 1:
                    elapsed_time = move / 3600 * 24 *6
                    button_time.update_button("time : %.1f jours" % elapsed_time,font)
                    # init model view matrix and center it to the earth (center object)
                elif menu == 2 :
                    button_time.update_button(sim_date.strftime("%d/%m/%Y"), font)
                    # init model view matrix and center it to the earth (center object)
                elif menu == 5:
                    elapsed_days = move * TIMESTEP_THREE / 86400
                    button_time.update_button("temps : %.1f j" % elapsed_days, font)
                glLoadIdentity()  
                if menu == 1 :
                    camera_x = tab_planets[0].x  * SCALE
                    camera_y = tab_planets[0].y  * SCALE
                    camera_z = tab_planets[0].z  * SCALE        
                    camera.reset_angles()          
                    gluLookAt(camera_x+camera.pos_x, camera_y+camera.pos_y,camera_z+camera.pos_z, camera_x+camera.angle_x, camera_y+camera.angle_y,camera_z+camera.angle_z, 0, 0, 1)
                elif menu == 2 or menu == 3 or menu == 5:
                    gluLookAt(camera.pos_x+10, camera.pos_y+0,camera.pos_z+20, camera.angle_x, camera.angle_y,camera.angle_z, 0, 0, 1)
                elif menu == 4:
                    camera.reset_angles()
                    gluLookAt(camera.pos_x, camera.pos_y, camera.pos_z,
                              camera.angle_x, camera.angle_y, camera.angle_z, 0, 0, 1)


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
                if menu != 4:
                    draw_axys()
                if GRID_ON:
                    if menu == 1:
                        draw_gravity_grid(tab_planets, SCALE, grid_range=120, grid_steps=22, z_scale=80, z_offset=-10)
                    elif menu == 2 or menu == 3:
                        if tab_planets:
                            draw_gravity_grid(tab_planets, SCALE, grid_range=300, grid_steps=22, z_scale=200, z_offset=-15)
                    elif menu == 5:
                        if tab_planets:
                            draw_gravity_grid(tab_planets, SCALE, grid_range=80, grid_steps=22, z_scale=120, z_offset=-12)
                # ── Physics update (synchronized: all forces from snapshot) ──────
                _n  = adaptive_substeps(tab_planets, TIMESTEP)
                _dt = TIMESTEP / _n

                if menu == 3:
                    if not sandbox_paused:
                        for _ in range(_n):
                            step_all_synchronized(tab_planets, _dt)
                        for p in tab_planets:
                            p.orbit.append((p.x, p.y, p.z))
                elif menu != 4:
                    if not sim_paused:
                        for _ in range(_n):
                            step_all_synchronized(tab_planets, _dt)
                        for p in tab_planets:
                            p.orbit.append((p.x, p.y, p.z))
                else:
                    # menu 4: Earth 3D — individual update keeps satellite-mass guard
                    if not sim_paused:
                        for planet in tab_planets:
                            planet.update_position(tab_planets, TIMESTEP)

                # ── Drawing ───────────────────────────────────────────────────────
                if menu == 1:
                    glEnable(GL_LIGHTING)
                    glEnable(GL_LIGHT0)
                    for planet in tab_planets:
                        planet.draw(SCALE)
                        if ORBIT_ON:
                            glDisable(GL_LIGHTING)
                            glDisable(GL_LIGHT0)
                            planet.draw_orbit(SCALE)
                            glEnable(GL_LIGHTING)
                            glEnable(GL_LIGHT0)
                    glDisable(GL_LIGHTING)
                    glDisable(GL_LIGHT0)

                elif menu == 2:
                    for planet in tab_planets:
                        planet.draw(SCALE)
                        if ORBIT_ON:
                            planet.draw_orbit(SCALE)

                elif menu == 3:
                    for planet in tab_planets:
                        planet.draw(SCALE)
                        planet.draw_orbit(SCALE)
                    if sandbox_pending_planet is not None:
                        sandbox_pending_planet.draw(SCALE)
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

                elif menu == 4:
                    for planet in tab_planets:
                        planet.draw(SCALE)
                    if e3d_orbit_on:
                        for sat in satellites:
                            sat.draw_orbit(SCALE)

                elif menu == 5:
                    for planet in tab_planets:
                        planet.draw(SCALE)
                        if ORBIT_ON:
                            planet.draw_orbit(SCALE)

                # Store matrices for gluUnProject (needed by menu 3 and 4)
                if menu in (3, 4):
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
                    draw_text_overlay(font, status_text, (255, 200, 100), 50, display[1] - 80)
                    mode_names = {SANDBOX_IDLE: "", SANDBOX_PLACING_SUN: "Cliquez pour placer un Soleil",
                                  SANDBOX_PLACING_PLANET_POS: "Cliquez pour placer une Planete",
                                  SANDBOX_PLACING_PLANET_VEL: "Cliquez pour definir la vitesse"}
                    mode_txt = mode_names.get(sandbox_mode, "")
                    if mode_txt:
                        draw_text_overlay(font, mode_txt, (100, 255, 100), 50, display[1] - 110)

                # Earth 3D status text
                if menu == 4:
                    elapsed_min = move * TIMESTEP_EARTH / 60.0
                    if elapsed_min < 120:
                        time_str = "Temps: %.0f min" % elapsed_min
                    else:
                        time_str = "Temps: %.1f h" % (elapsed_min / 60)
                    draw_text_overlay(font, time_str, (255, 200, 100), 50, display[1] - 80)
                    draw_text_overlay(font, "Satellites: %d" % len(satellites), (100, 200, 255), 50, display[1] - 110)
                    if e3d_launch_mode:
                        draw_text_overlay(font, "Cliquez sur la Terre pour lancer", (100, 255, 100), 50, display[1] - 140)

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