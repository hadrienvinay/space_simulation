import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from OpenGL.GL.ARB.shader_objects import *
from OpenGL.GL.ARB.vertex_shader import *
from OpenGL.GL.ARB.fragment_shader import *

import math
import sys
import numpy as np

WIDTH, HEIGHT = 1200, 900 

AU = 149.6e6 * 1000
G = 6.67428e-11
SCALE = 50 / AU # 1AU = 500 pixel
TIMESTEP = 3600 *24 *2# 1 day

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

def load_image(filename):
    image = pygame.image.load(filename).convert_alpha()
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

    def __init__(self, x, y, z, radius, color, mass, type, sun):
        self.x = x
        self.y = y
        self.z = z
        self.radius = radius
        self.color = color
        self.mass = mass
        self.type = type
        self.sun = sun

        self.orbit = []

        self.x_vel = 0
        self.y_vel = 0
        self.z_vel = 0

    def infos(self):
        print(self.x,self.y,self.z)

    def draw(self):
        x = self.x * SCALE 
        y = self.y * SCALE 
        z = self.z * SCALE 
        sphere = gluNewQuadric() #Create new sphere
        glTranslatef(x, y, z) #Move to the place
        glColor4f(self.color[0]/255,self.color[1]/255,self.color[2]/255,0) #Put color
        gluSphere(sphere,self.radius,32,32) #Draw sphere

    def update_position(self,planets):
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
        distance = math.sqrt(distance_x ** 2 + distance_y ** 2)
        distance2 = math.sqrt(distance_x ** 2 + distance_y ** 2 + distance_z **2)
        force = G * self.mass * other.mass / distance ** 2
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

    def draw_orbit(self):
        if len(self.orbit) > 1:
            #glTranslatef(0, 0,0) #Move to the place
            #glTranslatef(-self.x*SCALE, -self.y*SCALE, -self.z*SCALE) #Move to the place
            #print(self.orbit)
            #print(-self.x*SCALE, -self.y*SCALE, -self.z*SCALE)
            glBegin(GL_LINES) 
            glColor3f (self.color[0]/255,self.color[1]/255,self.color[2]/255)
            i = 0
            for point in self.orbit:
                if i > 1:
                    glVertex3f(self.orbit[i-1][0]*SCALE,self.orbit[i-1][1]*SCALE,self.orbit[i-1][2]*SCALE)
                    glVertex3f(self.orbit[i][0]*SCALE,self.orbit[i][1]*SCALE,self.orbit[i][2]*SCALE)
                    #glVertex3f(x,y,z)
                i += 1

            glEnd()

def force_gravite(x,y):
    distance_x = x - 0
    distance_y = y - 0
    #distance_z = z - sun.z
    if(distance_x & distance_y != 0):
        distance = math.sqrt(distance_x ** 2 + distance_y ** 2)
    else : distance = 1
    force =  G * 1.98892 * 10**30 / distance ** 2
    print(force*SCALE)
    coef = force *SCALE*SCALE
    return coef

def init_planet(tab_planets):
    mercury  = Planet(0.39*AU,0,0,2,DARK_GREY,0.33*10**24,0,0)
    #mercury.y_vel = -170496 *1.6
    mercury.y_vel = -47.4 * 1000
    mercury.orbit.append((mercury.x, mercury.y, mercury.z))
    venus    = Planet(0.72*AU,0,0,3,GREEN,4.87*10**24,0,0)
    #venus.x_vel = 12600* 1.4
    venus.y_vel = -35.02 * 1000
    venus.orbit.append((venus.x, venus.y, venus.z))
    earth    = Planet(1*AU,0,0,4,BLUE,5.97*10**24,0,0)
    #earth.y_vel = -107206* 1.3
    earth.y_vel = -29.783 * 1000
    earth.orbit.append((earth.x, earth.y, earth.z))
    mars     = Planet(1.52*AU,0,0,3,RED,0.642*10**24,0,0)
    #mars.y_vel = -86425* 1.6
    mars.y_vel = -24.077 * 1000
    mars.orbit.append((mars.x, mars.y,mars.z))
    jupiter  = Planet(5.2*AU,0,0,8,ORANGE,1.9*10**27,0,0)
    #jupiter.y_vel = -47052* 1.5
    jupiter.y_vel = -13.06* 1000
    jupiter.orbit.append((jupiter.x, jupiter.y,jupiter.z))
    saturn   = Planet(9.55*AU,0,0,7,YELLOW,1.9*10**27,0,0)
    #saturn.y_vel = -34848* 1.5
    saturn.y_vel = -9.68 * 1000
    saturn.orbit.append((saturn.x, saturn.y, saturn.z))
    uranus   = Planet(19.22*AU,0,0,6,BLUE,568*10**24,0,0)
    #uranus.y_vel = -32480
    uranus.y_vel = -6.80 * 1000
    uranus.orbit.append((uranus.x, uranus.y, uranus.z))
    neptune  = Planet(30.11*AU,0,0,5,WHITE,0.33*10**24,0,0)
    #neptune.y_vel = -19548
    neptune.y_vel = -5.43 * 1000
    neptune.orbit.append((neptune.x, neptune.y, neptune.z))
    sun = Planet(0,0,0,8, WHITE, 1.98892 * 10**30,0,1)
    sun.z_vel = 1 * 1000

    tab_planets.append(sun)
    tab_planets.append(mercury)
    tab_planets.append(venus)
    tab_planets.append(earth)
    tab_planets.append(mars)
    tab_planets.append(jupiter)
    tab_planets.append(saturn)
    tab_planets.append(uranus)
    tab_planets.append(neptune)

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
        #for j in range(-20,20):
            #force_gravite(i*10,j)

    glEnd()

def draw_planet(Planet):
    sphere = gluNewQuadric() #Create new sphere
    #glPushMatrix()
    glColor4f(Planet.color[0],Planet.color[1],Planet.color[2],0) #Put color
    gluSphere(sphere,Planet.radius,32,32) #Draw sphere
    #Planet.draw()

def draw_text(x,y):
    glColor3f(1.0, 0.0, 0.0)
    glRasterPos2f(x, y)
    text = "QUITTER"
    for i in (0, len(text)):
        #glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, text)
        print("ok")

def handle_keys():
    keypress = pygame.key.get_pressed()
    if keypress[pygame.K_z]:
            glTranslatef(0,0,0.5)
    if keypress[pygame.K_s]:
        glTranslatef(0,0,-0.5)
    if keypress[pygame.K_d]:
        glTranslatef(-0.5,0,0)
    if keypress[pygame.K_q]:
        glTranslatef(0.5,0,0)
    if keypress[pygame.K_a]:
        glTranslatef(0,-0.5,0)
    if keypress[pygame.K_e]:
        glTranslatef(0,0.5,0)
    a = pygame.mouse.get_pressed()
    #if a[0] == 1:
        #glTranslatef(0,0,2)
    #if a[2] == 1:
        #glTranslatef(0,0,-2)

class Button:
    def __init__(self, rect, text, color,font):
        self.rect = rect
        self.text = text
        self.color = color
        self.font = font
        self.data = pygame.image.tostring(text, "RGBA", True)
        self.x = rect.x
        self.y = rect.y
        self.width = rect.width
        self.height = rect.height

    def update_button(self,text,font):
        #self.color = color
        self.text = font.render("%s"%text, False, self.color)
        self.data = pygame.image.tostring(self.text, "RGBA", True)
        
def reset(tab_planets):
    del tab_planets
    new_tab = []
    init_planet(new_tab)
    return new_tab


def main():
    pygame.init()
    display = (WIDTH, HEIGHT)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("BIG BANG Simulation")

    font = pygame.font.SysFont("comicsans", 20)
    text_surface = font.render("Système solaire 2025", False, (255, 215, 255, 1))
    text_width, text_height = text_surface.get_size()
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    
    button_orbit = Button (pygame.Rect(WIDTH-180, HEIGHT-70, 150, 50),
                           font.render("Orbit ON", False, (0, 0, 0, 0)),
                           RED_3D,
                           pygame.font.SysFont("comicsans", 20))
    button_reset = Button (pygame.Rect(WIDTH-180, HEIGHT-150, 150, 50),
                           font.render("Reset", False, (0, 0, 0, 255)),
                           GREEN_3D,
                           pygame.font.SysFont("comicsans", 20))
    
    buttons_list = [button_orbit,button_reset]

    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    gluPerspective(100, (display[0]/display[1]), 1,1000)
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_TEXTURE_2D)
    #gluLookAt(-0, 150,220, 0, 0, 0, 0, 0, 1)
    gluLookAt(-0, 50,20, 0, 0, 0, 0, 0, 1)
    viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)
    glLoadIdentity()

    #Default Variables, Orbit ON
    ORBIT_ON = 1
    #move = 0
    run = True
    tab_planets = []
    init_planet(tab_planets)
    texture = load_image('milky.jpg')
    
    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                    run = False  
                if event.type == pygame.MOUSEWHEEL:
                    print("down")
                    glTranslatef(0,0,0.5)
                if event.type == pygame.MOUSEBUTTONUP:
                    print("UP")
                    glTranslatef(0,0,-0.5)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Clic gauche
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    # Conversion des coordonnées OpenGL (viewport)
                    viewport = glGetIntegerv(GL_VIEWPORT)
                    mouse_y = viewport[3] - mouse_y  # Inversion Y
                    if (button_orbit.x <= mouse_x <= button_orbit.x + button_orbit.width and
                        button_orbit.y <= mouse_y <= button_orbit.y + button_orbit.height):
                        if ORBIT_ON:
                            button_orbit.color = WHITE_3D
                            button_orbit.update_button("ORBIT OFF",font)
                            ORBIT_ON = 0
                        else: 
                            button_orbit.color = RED_3D
                            button_orbit.update_button("ORBIT ON",font)
                            ORBIT_ON = 1
                    if (button_reset.x <= mouse_x <= button_reset.x + button_reset.width and
                    button_reset.y <= mouse_y <= button_reset.y + button_reset.height):
                        tab_planets = reset(tab_planets)


        #move += 1
        # init model view matrix
        glLoadIdentity()
        # init the view matrix
        glPushMatrix()
        glLoadIdentity()
        
        # apply the movement of the camera with keyboard input
        handle_keys()
        
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
        draw_grid()

        for planet in tab_planets:  
            planet.update_position(tab_planets)
            #glTranslatef(-planet.x*SCALE, -planet.y*SCALE, -planet.z*SCALE) #Move to the place
            planet.draw()
            glTranslatef(-planet.x*SCALE, -planet.y*SCALE, -planet.z*SCALE)
            if(ORBIT_ON):
            #if  planet.sun == 0:
                planet.draw_orbit()

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
        glRasterPos2f(0, 0)  # Important pour glDrawPixels

        # Afficher le texte
        glRasterPos2f(50, display[1] - 50)
        glDrawPixels(text_width, text_height, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        # Afficher les boutons
        for button in buttons_list:
            draw_2d_rect(button.x, button.y, button.width, button.height, button.color)
            glColor3f(*WHITE)
            glLineWidth(4)
            glBegin(GL_LINE_LOOP)
            glVertex2f(button.x, button.y)
            glVertex2f(button.x + button.width, button.y)
            glVertex2f(button.x + button.width, button.y + button.height)
            glVertex2f(button.x, button.y + button.height)
            glEnd()

            glRasterPos2f(button.x + (button.width - button.text.get_width()) // 2,button.y + (button.height - button.text.get_height()) // 2)
            glDrawPixels(button.text.get_width(), button.text.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, button.data)
        

        glEnable(GL_DEPTH_TEST)

        # On restaure les matrices
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

        pygame.display.flip() #Update the screen
        pygame.time.wait(10)

    pygame.quit()

main()