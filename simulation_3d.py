import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import sys

WIDTH, HEIGHT = 1000, 800 

AU = 149.6e6 * 1000
G = 6.67428e-11
SCALE = 50 / AU # 1AU = 500 pixel
TIMESTEP = 3600 *24 # 1 day

WHITE = (255,255,255)
YELLOW = (255,255,0)
BLUE = (0,0,255)
BLACK = (0,0,0)
ORANGE = (255,128,0)
GREEN = (0,240,0)
DARK_GREY = (80,78,81)
RED = (255,20,0)

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
        force2 =  G * self.mass * other.mass / distance2 ** 3
        theta = math.atan2(distance_y, distance_x)
        force_x = math.cos(theta) * force
        force_y = math.sin(theta) * force
        force_z = math.cos(180-theta) * force2
        #force_z = math.cos(theta) * force
        force_z = 0
        return force_x, force_y, force_z

    def draw_orbit(self):
        if len(self.orbit) > 1:
            updated_points = []
            #glTranslatef(0, 0,0) #Move to the place
            glTranslatef(-self.x*SCALE, -self.y*SCALE, -self.z*SCALE) #Move to the place
            print(-self.x*SCALE, -self.y*SCALE, -self.z*SCALE)
            glBegin(GL_LINES) 
            glColor3f (self.color[0]/255,self.color[1]/255,self.color[2]/255)
            i = 0
            for point in self.orbit:
                x, y, z = point
                x = self.x * SCALE 
                y = self.y * SCALE
                z = self.z * SCALE 
                #updated_points.append((x, y, z))
                if i > 1:
                    glVertex3f(self.orbit[i-1][0]*SCALE,self.orbit[i-1][1]*SCALE,self.orbit[i-1][2]*SCALE)
                    glVertex3f(self.orbit[i][0]*SCALE,self.orbit[i][1]*SCALE,self.orbit[i][2]*SCALE)
                    #glVertex3f(x,y,z)
                i += 1

            glEnd()


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
    #glPushMatrix()
    #glLoadIdentity()

    glBegin(GL_LINES)
    glColor3f (1.0, 1.0, 1.0)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(100, 0.0, 0.0)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0, 100, 0.0)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0, 0.0, 100)

    glEnd()

def draw_planet(Planet):
    sphere = gluNewQuadric() #Create new sphere
    #glPushMatrix()
    glColor4f(Planet.color[0],Planet.color[1],Planet.color[2],0) #Put color
    gluSphere(sphere,Planet.radius,32,32) #Draw sphere
    #Planet.draw()

def main():
    pygame.init()
    display = (WIDTH, HEIGHT)
    screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)

    glEnable(GL_DEPTH_TEST)

    sphere = gluNewQuadric() #Create new sphere
    #sphere2 = gluNewQuadric() #Create new sphere

    glMatrixMode(GL_PROJECTION)
    gluPerspective(100, (display[0]/display[1]), 1,500.0)

    glMatrixMode(GL_MODELVIEW)
    gluLookAt(-50, 150,220, 0, 0, 0, 0, 0, 1)
    viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)
    glLoadIdentity()
    move = 0
    run = True
    tab_planets = []
    init_planet(tab_planets)
    
    while run:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                    run = False  

        keypress = pygame.key.get_pressed()
        move += 1
        # init model view matrix
        glLoadIdentity()
        # init the view matrix
        glPushMatrix()
        glLoadIdentity()

        # apply the movement 
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

        # multiply the current matrix by the get the new view matrix and store the final vie matrix 
        glMultMatrixf(viewMatrix)
        viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)

        # apply view matrix
        glPopMatrix()
        glMultMatrixf(viewMatrix)

        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT) #Clear the screen

        glPushMatrix()

        #glTranslatef(10, 0, 0) #Move to the place
        #glColor4f(0.5, 0.2, 0.2, 1) #Put color
        #gluSphere(sphere,1,16,32) #Draw sphere
        #glTranslatef(0, 0,0) #Move to the place
        #glColor4f(0.5, 1, 0.4, 1) #Put color
        #gluSphere(sphere,2,16,32) #Draw sphere
        draw_axys()

        for planet in tab_planets:
            planet.update_position(tab_planets)
            planet.draw()
            if  planet.sun ==0:
                planet.draw_orbit()
            

        #glFlush()
        glPopMatrix()
        pygame.display.flip() #Update the screen
        pygame.time.wait(20)

    pygame.quit()

main()