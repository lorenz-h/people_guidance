"""
	PyTeapot module for drawing rotating cube using OpenGL as per
	quaternion or yaw, pitch, roll angles received over serial port.
	https://github.com/thecountoftuscany/PyTeapot-Quaternion-Euler-cube-rotation/blob/master/pyteapot.py
	"""

import pygame
import math
from OpenGL.GL import *
from OpenGL.GLU import *
from pygame.locals import *

def cam(q):
    useQuat = True  # set true for using quaternions, false for using y,p,r angles

    video_flags = OPENGL | DOUBLEBUF
    pygame.init()
    screen = pygame.display.set_mode((640, 480), video_flags)
    pygame.display.set_caption("PyTeapot IMU orientation visualization")
    resizewin(640, 480)
    init()
    frames = 0
    ticks = pygame.time.get_ticks()

    event = pygame.event.poll()
    # if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
    #     break
    if useQuat:
        [w, nx, ny, nz] = q
        draw(w, nx, ny, nz, useQuat = True)
    else:
        [yaw, pitch, roll] = q
        draw(1, yaw, pitch, roll, useQuat = False)
    pygame.display.flip()
    frames += 1
    print("fps: %d" % ((frames * 1000) / (pygame.time.get_ticks() - ticks)))


def resizewin(width, height):
    """
    For resizing window
    """
    if height == 0:
        height = 1
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, 1.0 * width / height, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


def init():
    glShadeModel(GL_SMOOTH)
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glClearDepth(1.0)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)



def draw(w, nx, ny, nz, useQuat = True):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0, 0.0, -7.0)

    drawText((-2.6, 1.8, 2), "PyTeapot", 18)
    drawText((-2.6, 1.6, 2), "Module to visualize quaternion or Euler angles data", 16)
    drawText((-2.6, -2, 2), "Press Escape to exit.", 16)

    if (useQuat):
        [yaw, pitch, roll] = quat_to_ypr([w, nx, ny, nz])
        drawText((-2.6, -1.8, 2), "Yaw: %f, Pitch: %f, Roll: %f" % (yaw, pitch, roll), 16)
        glRotatef(2 * math.acos(w) * 180.00 / math.pi, -1 * nx, nz, ny)
    else:
        yaw = nx
        pitch = ny
        roll = nz
        drawText((-2.6, -1.8, 2), "Yaw: %f, Pitch: %f, Roll: %f" % (yaw, pitch, roll), 16)
        glRotatef(-roll, 0.00, 0.00, 1.00)
        glRotatef(pitch, 1.00, 0.00, 0.00)
        glRotatef(yaw, 0.00, 1.00, 0.00)

    glBegin(GL_QUADS)
    glColor3f(0.0, 1.0, 0.0)
    glVertex3f(1.0, 0.2, -1.0)
    glVertex3f(-1.0, 0.2, -1.0)
    glVertex3f(-1.0, 0.2, 1.0)
    glVertex3f(1.0, 0.2, 1.0)

    glColor3f(1.0, 0.5, 0.0)
    glVertex3f(1.0, -0.2, 1.0)
    glVertex3f(-1.0, -0.2, 1.0)
    glVertex3f(-1.0, -0.2, -1.0)
    glVertex3f(1.0, -0.2, -1.0)

    glColor3f(1.0, 0.0, 0.0)
    glVertex3f(1.0, 0.2, 1.0)
    glVertex3f(-1.0, 0.2, 1.0)
    glVertex3f(-1.0, -0.2, 1.0)
    glVertex3f(1.0, -0.2, 1.0)

    glColor3f(1.0, 1.0, 0.0)
    glVertex3f(1.0, -0.2, -1.0)
    glVertex3f(-1.0, -0.2, -1.0)
    glVertex3f(-1.0, 0.2, -1.0)
    glVertex3f(1.0, 0.2, -1.0)

    glColor3f(0.0, 0.0, 1.0)
    glVertex3f(-1.0, 0.2, 1.0)
    glVertex3f(-1.0, 0.2, -1.0)
    glVertex3f(-1.0, -0.2, -1.0)
    glVertex3f(-1.0, -0.2, 1.0)

    glColor3f(1.0, 0.0, 1.0)
    glVertex3f(1.0, 0.2, -1.0)
    glVertex3f(1.0, 0.2, 1.0)
    glVertex3f(1.0, -0.2, 1.0)
    glVertex3f(1.0, -0.2, -1.0)
    glEnd()


def drawText(position, textString, size):
    font = pygame.font.SysFont("Courier", size, True)
    textSurface = font.render(textString, True, (255, 255, 255, 255), (0, 0, 0, 255))
    textData = pygame.image.tostring(textSurface, "RGBA", True)
    glRasterPos3d(*position)
    glDrawPixels(textSurface.get_width(), textSurface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, textData)


def quat_to_ypr(q):
    yaw = math.atan2(2.0 * (q[1] * q[2] + q[0] * q[3]), q[0] * q[0] + q[1] * q[1] - q[2] * q[2] - q[3] * q[3])
    pitch = -math.sin(2.0 * (q[1] * q[3] - q[0] * q[2]))
    roll = math.atan2(2.0 * (q[0] * q[1] + q[2] * q[3]), q[0] * q[0] - q[1] * q[1] - q[2] * q[2] + q[3] * q[3])
    pitch *= 180.0 / math.pi
    yaw *= 180.0 / math.pi
    yaw -= -0.13  # Declination at Chandrapur, Maharashtra is - 0 degress 13 min
    roll *= 180.0 / math.pi
    return [yaw, pitch, roll]
