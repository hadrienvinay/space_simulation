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
import numpy as np

WIDTH, HEIGHT = 1400, 1000 

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

    def draw_orbit(self,SCALE):
        if len(self.orbit) > 1:
            glBegin(GL_LINES) 
            glColor3f (self.color[0]/255,self.color[1]/255,self.color[2]/255)
            i = 0
            ii=0                
            points = len(self.orbit)
            #draw only 1000/10 points of an orbit
            for point in self.orbit:
                if points > 1000:
                    if ii > 1 and ii < 1000:
                        j = points - ii
                        #print(i)
                        glVertex3f(self.orbit[j-10][0]*SCALE,self.orbit[j-10][1]*SCALE,self.orbit[j-10][2]*SCALE)
                        glVertex3f(self.orbit[j][0]*SCALE,self.orbit[j][1]*SCALE,self.orbit[j][2]*SCALE)
                    elif ii > 1000 : 
                        break
                else :
                    if i > 1 :
                        glVertex3f(self.orbit[i-1][0]*SCALE,self.orbit[i-1][1]*SCALE,self.orbit[i-1][2]*SCALE)
                        glVertex3f(self.orbit[i][0]*SCALE,self.orbit[i][1]*SCALE,self.orbit[i][2]*SCALE)
                i += 1
                ii +=10
            glEnd()

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
    #coef = force *SCALE*SCALE
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
    #tab_planets.append(uranus)
    #tab_planets.append(neptune)

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

    while running_menu:
 
        move = 0
        run = True
        tab_planets = []
        font = pygame.font.SysFont("comicsans", 38)
        if menu == 0:   
            text_surface = font.render("MENU - Suri Space Station", False, (255, 215, 255, 1))
            text_width, text_height = text_surface.get_size()
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            button_earth = Button (pygame.Rect(WIDTH/2-600, HEIGHT/2, 350, 100),
                                font.render("TERRE - LUNE", False, (1, 1, 0, 255)),
                                WHITE_3D,
                                font)
            button_solar_system = Button (pygame.Rect(WIDTH/2-175, HEIGHT/2, 400, 100),
                                font.render("SYSTEME SOLAIRE", False, (0, 0, 0, 255)),
                                WHITE_3D,
                                font)
            button_quit = Button (pygame.Rect(WIDTH/2+300, HEIGHT/2, 300, 100),
                                font.render("QUIT", False, (0, 0, 0, 255)),
                                WHITE_3D,
                                font)
            buttons_list = [button_earth,button_solar_system,button_quit]
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
                    if (button_quit.x <= mouse_x <= button_quit.x + button_quit.width and
                    button_quit.y <= mouse_y <= button_quit.y + button_quit.height):
                            running_menu = 0      
   
            glLoadIdentity()  
            #gluLookAt(camera_x+camera.pos_x, camera_y+camera.pos_y,camera_z+camera.pos_z, camera_x+camera.angle_x, camera_y+camera.angle_y,camera_z+camera.angle_z, 0, 0, 1)

            # init the view matrix
            
            glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT) #Clear the screen

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
                glLineWidth(2)
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
            else:
                text_surface = font.render("Erreur Menu", False, (255, 215, 255, 1))

            text_width, text_height = text_surface.get_size()
            text_data = pygame.image.tostring(text_surface, "RGBA", True)

            camera = Camera_Position(150,100,50,0,0,0)
            
            button_orbit = Button (pygame.Rect(WIDTH-180, HEIGHT-70, 150, 50),
                                font.render("Orbit ON", False, (0, 0, 0, 0)),
                                RED_3D,
                                font)
            button_reset = Button (pygame.Rect(WIDTH-180, HEIGHT-150, 150, 50),
                                font.render("Reset", False, (0, 0, 0, 255)),
                                GREEN_3D,
                                font)
            button_time = Button (pygame.Rect(WIDTH-180, HEIGHT-220, 150, 50),
                                font.render("Time", False, (0, 0, 0, 255)),
                                YELLOW_3D,
                                font)
            button_speed = Button (pygame.Rect(WIDTH-180, HEIGHT-290, 150, 50),
                                font.render("Speed", False, (0, 0, 0, 255)),
                                BLUE_3D,
                                pygame.font.SysFont("comicsans", 20))
            button_plus = Button (pygame.Rect(WIDTH-176, HEIGHT-282, 30, 30),
                                font.render("+", False, (0, 0, 0, 255)),
                                WHITE_3D,
                                font)
            button_minus = Button (pygame.Rect(WIDTH-65, HEIGHT-282, 30, 30),
                                font.render("-", False, (0, 0, 0, 255)),
                                WHITE_3D,
                                font)
            button_quit = Button (pygame.Rect(WIDTH-180, 20, 150, 50),
                                font.render("QUIT", False, (0, 0, 0, 255)),
                                WHITE_3D,
                                font)
            button_earth_speed = Button (pygame.Rect(WIDTH-180, 100, 150, 50),
                                font.render("Menu", False, (0, 0, 0, 255)),
                                WHITE_3D,
                                font)
            buttons_list = [button_orbit,button_reset,button_time,button_speed,button_plus,button_minus,button_quit,button_earth_speed]

            glEnable(GL_DEPTH_TEST)
            glMatrixMode(GL_PROJECTION)
            gluPerspective(60,(display[0]/display[1]), 20,1000)
            if menu == 1 :
                # --- Paramètres de la lumière (Soleil) ---
                glLightfv(GL_LIGHT0, GL_POSITION, [-1000, 50.0, 0.0, 1.0])  # Position de la lumière : ici un soleil au loin à gauche
                glLightfv(GL_LIGHT0, GL_DIFFUSE, [255,255,200, 1])   # Lumière diffuse (jaune clair)

            glMatrixMode(GL_MODELVIEW)
            glEnable(GL_TEXTURE_2D)
            #gluLookAt(-0, 150,220, 0, 0, 0, 0, 0, 1)
            #gluLookAt(2, -20,50, 0, 0, 0, 0, 0, 1)
            viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)
            glLoadIdentity()

            if (menu == 1):
                init_earth_moon(tab_planets)
            if (menu == 2):
                init_planet(tab_planets)

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
    
                    
                handle_keys(camera)
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
                elif menu == 2:
                    gluLookAt(camera.pos_x+10, camera.pos_y+0,camera.pos_z+20, camera.angle_x, camera.angle_y,camera.angle_z, 0, 0, 1)
                    #gluLookAt(10, -50,20, 0, camera.angle_x, camera.angle_y,camera.angle_z, 0, 1)


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
                draw_grid()     
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
                    glLineWidth(2)
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
                clock.tick(SPEED)

            pygame.quit()
            clock = init_game(display)   


    pygame.quit()

main()