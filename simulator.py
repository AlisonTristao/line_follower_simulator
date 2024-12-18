import pygame
from classes import *

# create the simulator
simulator = Simulator(width=1200, height=600)

# create the track
track = Track((100, 100), 150, 4)
simulator.add(track)

# add the car
car = Car(simulator.get_center(), center=(1.5, 1.7))
simulator.add(car)

# set the center of the track and the pivot relative to the center of the car
track.set_center(car.get_center())
track.set_pivot(car.get_center())

while simulator.is_running():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            simulator.stop_running()

    keys = pygame.key.get_pressed()
    dx, dy = 0, 0
    theta = 0

    if keys[pygame.K_LEFT]:
        dx = -5
    if keys[pygame.K_RIGHT]:
        dx = 5
    if keys[pygame.K_UP]:
        dy = -5
    if keys[pygame.K_DOWN]:
        dy = 5
    if keys[pygame.K_a]:
        theta = 0.01
    if keys[pygame.K_d]:
        theta = -0.01

    # update the world
    track.step(dx, dy, theta)
    simulator.step()
