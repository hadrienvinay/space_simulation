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
SCALE = 15000 / AU # 1AU = 500 pixel
TIMESTEP = 3600  # 1 day = *24 , here 1hour

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
angle_vue = 30

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

# --- Paramètres du matériau (pour les objets) ---
def set_material(ambient, diffuse, specular, shininess=30.0):
    glMaterialfv(GL_FRONT, GL_AMBIENT, ambient)
    glMaterialfv(GL_FRONT, GL_DIFFUSE, diffuse)
    glMaterialfv(GL_FRONT, GL_SPECULAR, specular)
    glMaterialf(GL_FRONT, GL_SHININESS, shininess)

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

    def draw(self):
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
        gluQuadricNormals(sphere, GLU_SMOOTH)
        gluSphere(sphere,self.radius,32,32) #Draw sphere
        gluDeleteQuadric(sphere)
        if self.texture != 0:
            glDisable(GL_TEXTURE_2D)
        glPopMatrix()

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

    def draw_orbit(self):
        if len(self.orbit) > 1:
            #glTranslatef(0, 0,0) #Move to the place
            #glTranslatef(-self.x*SCALE, -self.y*SCALE, -self.z*SCALE) #Move to the place
            #print(self.orbit)
            #print(-self.x*SCALE, -self.y*SCALE, -self.z*SCALE)
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

    texture_earth = load_image("textures/earth_test.jpg")
    earth = Planet(0,0,0,10,BLUE,5.97*10**24,0,0,texture_earth,5)
    #earth.x_vel = -1 *100
    earth.y_vel = 29.786 * 10 #vitesse rotation autour soleil : 30km/s
    earth.orbit.append((earth.x, earth.y, earth.z))
    texture_moon = load_image("textures/moon_test.jpg")
    moon  = Planet(earth.x - 0.0026*AU, 0,0.0002*AU,5,DARK_GREY,7.347*10**22,0,0,texture_moon,0)
    moon.y_vel = earth.y_vel
    moon.y_vel += 1.02 * 1000 #v orbitale : 1.02km/s

    moon.orbit.append((moon.x, moon.y, moon.z))

    #texture_sun = load_image("textures/sun.jpg")
    #sun = Planet(0,0,0,8, WHITE, 1.98892 * 10**30,0,1,texture_sun,1)
    #sun.z_vel = 1 * 1000
    #tab_planets.append(sun)
    tab_planets.append(earth)
    tab_planets.append(moon)

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

def handle_keys(angle_vue):
    keypress = pygame.key.get_pressed()
    if keypress[pygame.K_z]:
        glTranslatef(0,0.5,0)
    if keypress[pygame.K_s]:
        glTranslatef(0,-0.5,0)
    if keypress[pygame.K_d]:
        glTranslatef(0.5,0,0)
    if keypress[pygame.K_q]:
        glTranslatef(-0.5,0,0)
    if keypress[pygame.K_a]:
        glTranslatef(0,0,0.5)
    if keypress[pygame.K_e]:
        glTranslatef(0,0,-0.5)
    if keypress[pygame.K_t]:
        angle_vue +=2
    if keypress[pygame.K_y]:
        angle_vue -=2

def draw_light_source():
    glDisable(GL_LIGHTING)  # Désactive l'éclairage pour dessiner le Soleil
    glPushMatrix()
    glColor3f(1.0, 1.0, 0.0)  # Jaune
    quad = gluNewQuadric()
    gluSphere(quad, 0.5, 32, 32)  # Soleil de rayon 0.5
    glPopMatrix()
    glEnable(GL_LIGHTING)   # Réactive l'éclairage

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
    pygame.display.set_caption("Solar System")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("comicsans", 20)
    text_surface = font.render("Système Terre - Lune", False, (255, 215, 255, 1))
    text_width, text_height = text_surface.get_size()
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    
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
                           font.render("No Speed", False, (0, 0, 0, 255)),
                           WHITE_3D,
                           font)
    buttons_list = [button_orbit,button_reset,button_time,button_speed,button_plus,button_minus,button_quit,button_earth_speed]

    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    gluPerspective(40,(display[0]/display[1]), 10,1000)
    # --- Activation de l'éclairage ---
    #glEnable(GL_LIGHTING)
    #glEnable(GL_LIGHT0)  # Une seule source : le Soleil

    # --- Paramètres de la lumière (Soleil) ---
    glLightfv(GL_LIGHT0, GL_POSITION, [-1000, 50.0, 0.0, 1.0])  # Position de la lumière : ici un soleil au loin à gauche
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [255,255,200, 1])   # Lumière diffuse (jaune clair)


    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_TEXTURE_2D)
    #gluLookAt(-0, 150,220, 0, 0, 0, 0, 0, 1)
    #gluLookAt(2, -20,50, 0, 0, 0, 0, 0, 1)
    viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)
    glLoadIdentity()

    #Default Variables, Orbit ON
    ORBIT_ON = 1
    SPEED = 60
    move = 0
    angle_vue = 30
    run = True
    tab_planets = []
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
                        move = 0
                        camera_x = 0
                        camera_y = 0
                        incremented_speed = 1
                        #glLoadIdentity()
                        #glPushMatrix()
                        #gluLookAt(10, -50,20, 0, 0, 0, 0, 0, 1)
                    if (button_plus.x <= mouse_x <= button_plus.x + button_plus.width and
                    button_plus.y <= mouse_y <= button_plus.y + button_plus.height):
                            print("PLUS")
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
                    if (button_earth_speed.x <= mouse_x <= button_earth_speed.x + button_earth_speed.width and
                    button_earth_speed.y <= mouse_y <= button_earth_speed.y + button_earth_speed.height):
                            tab_planets = reset(tab_planets)
                            move = 0
                            camera_x = 0
                            camera_y = 0
                            tab_planets[0].y_vel = incremented_speed * 10
                            incremented_speed=0
                            tab_planets[1].y_vel = tab_planets[0].y_vel + 1.02 * 1000

        #display info about the simulation elapsed_time since the start of simulation  
        elapsed_time = move / 3600 * 24 *6 
        move += 1
        button_time.update_button("time : %.1f jours" % elapsed_time,font)
        # init model view matrix and center it to the earth (center object)
        camera_x = tab_planets[0].x  * SCALE
        camera_y = tab_planets[0].y  * SCALE
        camera_z = tab_planets[0].z  * SCALE
        glLoadIdentity()  
        gluLookAt(camera_x+100, camera_y+150,camera_z+50, -30, 0, 0, 0, 0, 1)
        draw_light_source()
        # init the view matrix
        glPushMatrix()
        glLoadIdentity()
        
        # apply the movement of the camera with keyboard input
        handle_keys(angle_vue)
        
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
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        timer = time.time()
        for planet in tab_planets:  
            if(planet.sun == 0):
                planet.update_position(tab_planets)
            #glTranslatef(-planet.x*SCALE, -planet.y*SCALE, -planet.z*SCALE) #Move to the place
            planet.draw()

            #glTranslatef(-planet.x*SCALE, -planet.y*SCALE, -planet.z*SCALE)
            if(ORBIT_ON):
            #if  planet.sun == 0:
                glDisable(GL_LIGHTING)
                glDisable(GL_LIGHT0)
                planet.draw_orbit()
                glEnable(GL_LIGHTING)
                glEnable(GL_LIGHT0)
   
        glDisable(GL_LIGHTING)
        glDisable(GL_LIGHT0)   

        glPopMatrix()

        timer_end = time.time()
        print(timer_end - timer)

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

main()