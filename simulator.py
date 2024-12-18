import pygame
import random
import time
from classes import *

# Create the simulator
simulator = Simulator(width=1400, height=800)

# Create the track
track = Track((100, 100), 150, 5)
simulator.add(track)

# Add the car
car = Car(simulator.get_center(), center=(1.36, 1.7))
simulator.add(car)

# Set the center of the track and the pivot relative to the center of the car
track.set_center(car.get_center())
track.set_pivot(car.get_center())

# Create the display
display = Display(simulator.get_center(), simulator.get_window_size())
simulator.add(display)

# Create a Statistic object
statistic = Statistics(simulator.get_center())
simulator.add(statistic)

# Add graphs with specific lines and colors
display.add_graph("wheels")
display.add_line_to_graph("wheels", "left", color=(0, 200, 0))
display.add_line_to_graph("wheels", "right", color=(200, 0, 0))

display.add_graph("speed")
display.add_line_to_graph("speed", "vm", color=(0, 0, 200))

display.add_graph("omega")
display.add_line_to_graph("omega", "ω", color=(200, 200, 0))

# Main simulation loop
tempo = time.time()
counter = 0
while simulator.is_running():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            simulator.stop_running()

    # handle keyboard input
    keys = pygame.key.get_pressed()
    dx, dy = 0, 0
    theta = 0

    # control the track (world)
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

    # Generate random data for the graphs
    random_left = random.randint(-50, 50)
    random_right = random.randint(-50, 50)
    random_vm = random.randint(-50, 50)
    random_ω = random.randint(-50, 50)

    # Update wheels
    display.update_graph_data("wheels", "left", random_left)
    display.update_graph_data("wheels", "right", random_right)

    # Update car
    display.update_graph_data("speed", "vm", random_vm)
    display.update_graph_data("omega", "ω", random_ω)

    # Step the simulation
    simulator.step()

    counter += 1
    if time.time() - tempo > 1:
        statistic.set_text("FPS: " + str(counter))
        counter = 0
        tempo = time.time()
