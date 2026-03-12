import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math

# --- Initialisation ---
pygame.init()
width, height = 800, 600
pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
pygame.display.set_caption("Une Source Lumineuse (Soleil)")
clock = pygame.time.Clock()

# --- Configuration OpenGL ---
glEnable(GL_DEPTH_TEST)
glMatrixMode(GL_PROJECTION)
gluPerspective(45, (width / height), 0.1, 100.0)

# --- Activation de l'éclairage ---
glEnable(GL_LIGHTING)
glEnable(GL_LIGHT0)  # Une seule source : le Soleil

# --- Paramètres de la lumière (Soleil) ---
glLightfv(GL_LIGHT0, GL_POSITION, [-1000.0, 0.0, 10.0, 1.0])  # Position centrale
glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])   # Lumière ambiante
glLightfv(GL_LIGHT0, GL_DIFFUSE, [1, 1.0, 1.0, 1.0])   # Lumière diffuse (blanche)
glLightfv(GL_LIGHT0, GL_SPECULAR, [0.5, 0.5, 0.8, 1.0])  # Reflets

# --- Paramètres du matériau (pour les objets) ---
def set_material(ambient, diffuse, specular, shininess):
    glMaterialfv(GL_FRONT, GL_AMBIENT, ambient)
    glMaterialfv(GL_FRONT, GL_DIFFUSE, diffuse)
    glMaterialfv(GL_FRONT, GL_SPECULAR, specular)
    glMaterialf(GL_FRONT, GL_SHININESS, shininess)


# --- Dessiner une sphère ---
def draw_sphere(x, y, z, radius, ambient, diffuse, specular, shininess=30.0):
    glPushMatrix()
    glTranslatef(x, y, z)
    set_material(ambient, diffuse, specular, shininess)
    quad = gluNewQuadric()
    gluQuadricNormals(quad, GLU_SMOOTH)  # Normales lisses pour l'éclairage
    gluSphere(quad, radius, 32, 32)
    glPopMatrix()

# --- Dessiner la source lumineuse (Soleil) ---
def draw_light_source():
    glDisable(GL_LIGHTING)  # Désactive l'éclairage pour dessiner le Soleil
    glPushMatrix()
    glColor3f(1.0, 1.0, 0.0)  # Jaune
    quad = gluNewQuadric()
    gluSphere(quad, 0.5, 32, 32)  # Soleil de rayon 0.5
    glPopMatrix()
    glEnable(GL_LIGHTING)   # Réactive l'éclairage

# --- Boucle principale ---
temps_ecoule = 0
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    temps_ecoule += 0.01

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(10, 5, 10, 0, 0, 0, 0, 1, 0)  # Position de la caméra

    # --- Dessiner le Soleil (source lumineuse) ---
    #draw_light_source()

    # --- Calculer la position de la Terre ---
    angle_terre = (2 * math.pi * temps_ecoule) / 10.0  # Période orbitale = 10s
    x_terre = 3.0 * math.cos(angle_terre)
    z_terre = 3.0 * math.sin(angle_terre)

    # --- Dessiner la Terre ---
    terre_ambient = [0.1, 0.1, 0.3, 1.0]
    terre_diffuse = [0.2, 0.2, 0.8, 1.0]
    terre_specular = [0.5, 0.5, 0.5, 1.0]
    draw_sphere(x_terre, 0, z_terre, 0.5, terre_ambient, terre_diffuse, terre_specular)

    # --- Calculer la position de la Lune ---
    angle_lune = (2 * math.pi * temps_ecoule) / 2.0  # Période orbitale = 2s
    x_lune = x_terre + 0.8 * math.cos(angle_lune)
    z_lune = z_terre + 0.8 * math.sin(angle_lune)

    # --- Dessiner la Lune ---
    lune_ambient = [1, 1, 0.2, 1.0]
    lune_diffuse = [0.5, 0.5, 0.5, 1.0]
    lune_specular = [0.3, 0.3, 0.3, 1.0]
    draw_sphere(x_lune, 0, z_lune, 0.2, lune_ambient, lune_diffuse, lune_specular)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
