import math
import random
import os
import sys
import pygame
from pygame.locals import *
from pygame import mixer

import pandas as pd
import openpyxl

mixer.init()
pygame.init()
vec = pygame.math.Vector2  # 2 for two dimensional
WIDTH, HEIGHT = 800, 600
FPS = 60
TILE = 64
ACC = 2
FRIC = -0.12
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

isplaying = False
ispaused = False

class SpriteSheet(object):
    def __init__(self, file_name):
        self.sprite_sheet = pygame.image.load(file_name).convert_alpha()

    def get_image(self, x, y, width, height, newW=TILE, newH=TILE):
        image = pygame.Surface([width, height], pygame.SRCALPHA)
        image.blit(self.sprite_sheet, (0, 0), (x, y, width, height))
        image = pygame.transform.scale(image, (newW, newH))
        return image


class SmartSpriteSheet(object):
    def __init__(self, file_name, sprite_width, sprite_height):
        self.sprite_sheet = pygame.image.load(file_name).convert_alpha()
        self.sprite_width = sprite_width
        self.sprite_height = sprite_height

    def get_image(self, col, row, newW=TILE, newH=TILE):
        image = pygame.Surface([self.sprite_width, self.sprite_height], pygame.SRCALPHA)
        image.blit(self.sprite_sheet, (0, 0),
                   (col * self.sprite_width, row * self.sprite_height, self.sprite_width, self.sprite_height))
        image = pygame.transform.scale(image, (newW, newH))
        return image

class Animation():
    def __init__(self, imglist, framelength, loop = True):
        self.imglist = imglist
        self.framelength = framelength
        self.loop = loop
        self.num = 0
        self.ended = False
    def get_image(self):
        self.num+=1
        if self.num == len(self.imglist) * self.framelength:
            if self.loop:
                self.num = 0
            else:
                self.num = len(self.imglist) * self.framelength - 1
                self.ended = True
        return self.imglist[self.num // self.framelength]

class Button():
    def __init__(self, x, y, image, scale):
        width = image.get_width()
        height = image.get_height()
        self.image = pygame.transform.scale(image, (int(width * scale), int(height * scale)))
        self.pressed_image = image.copy()
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.fill((100,100,100,100))
        self.pressed_image.blit( surface, (0,0))
        self.unpressed_image = self.image
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.pressed = False

    def click(self, surface):
        # draw button on screen
        surface.blit(self.image, (self.rect.x, self.rect.y))

        # get mouse position
        pos = pygame.mouse.get_pos()

        # check mouseover and clicked conditions
        if self.rect.collidepoint(pos):
            if pygame.mouse.get_pressed()[0] == 1 and not self.pressed:
                self.pressed = True
                self.image = self.pressed_image

        if pygame.mouse.get_pressed()[0] == 0 and self.pressed:
            self.pressed = False
            self.image = self.unpressed_image
            return True
        else:
            return False


marioSS = SmartSpriteSheet('Sprites/mario.png', 64, 64)
tilesSS = SmartSpriteSheet('Sprites/fantasy-tiles.png', 64, 64)
ghostSS = SmartSpriteSheet('Sprites/ghosts.png', 48, 48)
fireballSS = SmartSpriteSheet('Sprites/Fireball.png',64,64)

imgs_ghost_right = [ghostSS.get_image(6 + i, 2) for i in range(6)]
imgs_ghost_left = [ghostSS.get_image(6 + i, 1) for i in range(6)]

imgs_fireball = [fireballSS.get_image(i,0,TILE//2,TILE//2) for i in range(6)]+[fireballSS.get_image(i,1,TILE//2,TILE//2) for i in range(6)]+\
                [fireballSS.get_image(i,2,TILE//2,TILE//2) for i in range(6)]

imgPlatformM = tilesSS.get_image(0, 1)
imgHeart = tilesSS.get_image(5, 6, TILE // 2, TILE // 2)


class GroundDetector():
    def __init__(self, w, h):
        self.rect = pygame.Rect(0, 0, w, h)

    def update(self, x, y):
        self.rect.topleft = (x, y)

    def hascollision(self):
        for c in colliders:
            hits = self.rect.colliderect(c)
            if hits:
                return True
        return False


class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, imglist, isFacindRight, speed, amplitude, period, isFriendlyToPlayer,father):
        super(Projectile, self).__init__()
        all_sprites.add(self)
        self.image = imglist[0]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.startx = x
        self.starty = y
        self.anim = Animation(imglist,3)
        self.period = period
        self.father = father
        if isFacindRight:
            self.speed = speed
        else:
            self.speed = -speed
        self.amplitude = amplitude
        if not isFriendlyToPlayer:
            damagers.append(self)
        else:
            hero_shells.append(self)

    def update(self):
        self.rect.x += self.speed
        self.rect.y = self.starty + math.sin((self.rect.x - self.startx)/self.period) * self.amplitude
        self.image = self.anim.get_image()
        for c in colliders:
            if self.rect.colliderect(c) and c!=self.father:
                print(c)
                self.kill()
                if self in hero_shells:
                    hero_shells.remove(self)
                if self in damagers:
                    damagers.remove(self)





class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, screenx, screeny):
        super().__init__()
        colliders.append(self)
        all_sprites.add(self)

        self.imgs_idle = [marioSS.get_image(0, 0), marioSS.get_image(0, 1), marioSS.get_image(0, 2),
                          marioSS.get_image(0, 1)]
        self.imgs_run_right = [marioSS.get_image(6 + i, 0) for i in range(3)]
        self.imgs_run_left = [marioSS.get_image(i, 0) for i in range(3)]
        self.imgs_jump_idle = [marioSS.get_image(4, 5)]
        self.imgs_jump_left = [marioSS.get_image(3, 3)]
        self.imgs_jump_right = [pygame.transform.flip(marioSS.get_image(3, 3), True, False)]
        self.image = self.imgs_idle[0]
        self.rect = self.image.get_rect()
        self.vel = vec(0, 0)
        self.acc = vec(0, 0)
        self.groundDetector = GroundDetector(self.rect.width - 2, 5)
        hero_shells.append(self.groundDetector)

        self.rect.x = x
        self.rect.y = y
        self.startx = screenx
        self.starty = screeny

        self.checkpointx = x
        self.checkpointy = y

        self.state = "idle"
        self.old_state = "idle"
        self.current_imgs = self.imgs_idle
        self.frame = 0
        self.hp = 5
        self.isvulnerable = True
        self.respawntimer = 120

        self.isFacingRight = True
        self.shotTimer = 0

    def update(self):
        print(self.vel.y)
        self.oldX = self.rect.x
        self.oldY = self.rect.y
        self.move()
        self.damage()
        if self.isvulnerable:
            self.checkCheckpoint()
            self.checkCollisions()
            self.groundDetector.update(self.rect.x + 1, self.rect.bottom + 1)  # update after move() required
            self.jump()
            self.offset()
            self.shot()
            self.animate()
        else:
            self.respawn()

    def shot(self):
        global stat_shots
        if(self.shotTimer>0):
            self.shotTimer-=1
            return
        pressed_keys = pygame.key.get_pressed()
        if pressed_keys[K_x]:
            Projectile(self.rect.centerx, self.rect.y, imgs_fireball, self.isFacingRight, 2, 10, 10, True,self)
            self.shotTimer=60
            stat_shots+=1

    def respawn(self):
        self.respawntimer -= 1
        if self.respawntimer == 0:
            if self.hp > 0:
                self.respawntimer = 120
                self.rect.x = self.checkpointx
                self.rect.y = self.checkpointy
                self.isvulnerable = True
            else:
                pygame.quit()
                sys.exit()

    def damage(self):
        for d in damagers:
            if self.rect.colliderect(d) and self.isvulnerable:
                self.hp -= 1
                self.vel.y = -10
                self.isvulnerable = False
                break

    def checkCheckpoint(self):
        for c in checkpoints:
            if self.rect.colliderect(c):
                self.checkpointx = self.rect.x
                self.checkpointy = self.rect.y
                break

    def checkCollisions(self):
        for c in colliders:
            if c != self and self.rect.colliderect(c):
                if self.rect.left < c.rect.right or self.rect.right > c.rect.left:
                    self.rect.x = self.oldX
            if c != self and self.rect.colliderect(c):
                if self.rect.top < c.rect.bottom or self.rect.bottom > c.rect.top:
                    self.rect.y = self.oldY
                    self.vel.y = 0

    def move(self):
        self.acc = vec(0, 0.5)
        pressed_keys = pygame.key.get_pressed()
        if self.isvulnerable:
            if pressed_keys[K_LEFT]:
                self.acc.x = -ACC
                self.state = "run_left"
                self.isFacingRight = False
            elif pressed_keys[K_RIGHT]:
                self.acc.x = ACC
                self.state = "run_right"
                self.isFacingRight = True
            else:
                self.state = "idle"
        self.acc.x += self.vel.x * FRIC
        self.vel += self.acc
        self.rect.x += round(self.vel.x + 0.5 * self.acc.x)
        self.rect.y += self.vel.y + 0.5 * self.acc.y

    def jump(self):
        pressed_keys = pygame.key.get_pressed()
        if pressed_keys[K_UP] and self.groundDetector.hascollision():
            self.vel.y = -18

    def offset(self):
        self.offsetx = self.startx - self.rect.x
        self.offsety = self.starty - self.rect.y

    def animate(self):
        if self.state != self.old_state:
            self.old_state = self.state
            self.frame = 0
        if self.state == "idle":
            if self.groundDetector.hascollision():
                self.current_imgs = self.imgs_idle
            else:
                self.current_imgs = self.imgs_jump_idle
        elif self.state == "run_left":
            if self.groundDetector.hascollision():
                self.current_imgs = self.imgs_run_left
            else:
                self.current_imgs = self.imgs_jump_left
        elif self.state == "run_right":
            if self.groundDetector.hascollision():
                self.current_imgs = self.imgs_run_right
            else:
                self.current_imgs = self.imgs_jump_right

        self.frame += 0.2
        if self.frame >= len(self.current_imgs):
            self.frame = 0
        self.image = self.current_imgs[int(self.frame)]


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, isFacingRight, imgs_right, imgs_left, acc_multiplier=1):
        super().__init__()
        colliders.append(self)
        all_sprites.add(self)
        damagers.append(self)
        self.isFacingRight = isFacingRight
        self.image = imgs_right[0]
        self.rightanim = Animation(imgs_right,5)
        self.leftanim = Animation(imgs_left, 5)
        self.rect = self.image.get_rect()
        self.vel = vec(0, 0)
        self.acc = vec(0, 0)
        self.acc_multiplier = acc_multiplier
        self.groundDetector = GroundDetector(1, 1)

        self.rect.x = x
        self.rect.y = y

        self.isvulnerable = True
        self.respawntimer = 420
        self.checkpointx = x
        self.checkpointy = y

    def update(self):
        self.oldY = self.rect.y
        self.oldX = self.rect.x
        self.move()
        self.damage()
        if self.isvulnerable:
            self.checkCollisions()
            self.checkGround()
            self.animate()
        else:
            self.respawn()

    def checkGround(self):
        if self.isFacingRight:
            self.groundDetector.update(self.rect.right + 1, self.rect.bottom + 1)
        else:
            self.groundDetector.update(self.rect.left - 2, self.rect.bottom + 1)
        if not self.groundDetector.hascollision() and self.vel.y == 0:
            self.isFacingRight = not self.isFacingRight

    def checkCollisions(self):
        global p
        for c in colliders:
            if c != self and self.rect.colliderect(c):
                if self.rect.bottom > c.rect.top:
                    self.rect.y = self.oldY
                    self.vel.y = 0
            if c != self and c != p and self.rect.colliderect(c):
                if self.rect.left < c.rect.right or self.rect.right > c.rect.left:
                    self.rect.x = self.oldX
                    self.vel.x = 0
                    self.isFacingRight = not self.isFacingRight

    def respawn(self):
        self.respawntimer -= 1
        if self.respawntimer == 0:
            self.respawntimer = 420
            self.rect.x = self.checkpointx
            self.rect.y = self.checkpointy
            self.isvulnerable = True
            self.vel.y = 0
            damagers.append(self)

    def damage(self):
        for d in hero_shells:
            if self.rect.colliderect(d) and self.isvulnerable:
                self.vel.y = -10
                self.isvulnerable = False
                damagers.remove(self)
                break

    def move(self):
        self.acc = vec(0, 0.5)
        if self.isFacingRight:
            self.acc.x = ACC * self.acc_multiplier
        else:
            self.acc.x = -ACC * self.acc_multiplier
        self.acc.x += self.vel.x * FRIC
        self.vel += self.acc
        self.rect.x += round(self.vel.x + 0.5 * self.acc.x)
        self.rect.y += self.vel.y + 0.5 * self.acc.y

    def animate(self):
        if self.isFacingRight:
            self.image = self.rightanim.get_image()
        else:
            self.image = self.leftanim.get_image()



class Platform(pygame.sprite.Sprite):
    def __init__(self, image, x, y):
        super().__init__()
        all_sprites.add(self)
        colliders.append(self)
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

class Finish(pygame.sprite.Sprite):
    def __init__(self, image, x, y):
        super().__init__()
        all_sprites.add(self)
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
    def update(self):
        global p,stat_coins, stat_shots, stat_kills,stat_time, isplaying
        if self.rect.colliderect(p):
            isplaying = False
            dataframe = pd.DataFrame([[stat_coins, stat_shots, stat_kills, stat_time]],
                              index=['Value'], columns=['coins', 'shots', 'kills', 'time'])
            with pd.ExcelWriter('Stats.xlsx') as writer:
                dataframe.to_excel(writer, sheet_name='sheet1')


class Checkpoint():
    def __init__(self, x, y, w=TILE, h=TILE):
        checkpoints.append(self)
        self.rect = pygame.Rect(x, y, w, h)


def defineCurrenSprites():
    global p
    current_sprites.empty()
    for s in all_sprites:
        if abs(s.rect.x - p.rect.x) < WIDTH / 2 + TILE:
            current_sprites.add(s)


def drawLives():
    for i in range(p.hp):
        screen.blit(imgHeart, (i * TILE // 2, 10))

def init(lvl):
    global stat_coins, stat_shots, stat_kills,stat_time, all_sprites,players,colliders,damagers,hero_shells,checkpoints,current_sprites,textFile,level,p,fakescreen,btn
    stat_coins = 0
    stat_shots = 0
    stat_kills = 0
    stat_time = 0
    all_sprites = pygame.sprite.Group()
    players = pygame.sprite.Group()
    colliders = []
    damagers = []
    hero_shells = []
    checkpoints = []
    current_sprites = pygame.sprite.Group()
    textFile = open("Levels/Level.txt")
    level = textFile.readlines()
    for i in range(len(level)):
        for j in range(len(level[i])):
            if level[i][j] == 'G' or level[i][j] == 'W' or level[i][j] == 'r':
                Platform(imgPlatformM, j * TILE, i * TILE)
            if (level[i][j] == 'P'):
                p = Player(j * TILE, i * TILE, 350, 400)
            if (level[i][j] == 'E'):
                Enemy(j * TILE, i * TILE, True, imgs_ghost_right, imgs_ghost_left, 0.2)
            if (level[i][j] == 'd'):
                Checkpoint(j * TILE, i * TILE)
            if (level[i][j] == 'F'):
                Finish(imgHeart, j * TILE, i * TILE)

    fakescreen = pygame.Surface([len(level[0]) * TILE, len(level) * TILE], pygame.SRCALPHA)
btn = Button(100, 100, imgs_ghost_left[0], 1)


def gameplay():
    screen.fill((0, 0, 0))
    fakescreen.fill((0, 0, 0))
    all_sprites.update()
    defineCurrenSprites()

    current_sprites.draw(fakescreen)
    screen.blit(fakescreen, (p.offsetx, p.offsety))
    drawLives()

def mainmenu():
    global isplaying
    if (btn.click(screen)):
        init(1)
        isplaying = True

def pause():
    pass


while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
    if not isplaying:
        mainmenu()
    elif ispaused:
        pause()
    else:
        gameplay()
    pygame.display.flip()
    clock.tick(60)
