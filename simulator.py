import pygame
import random
import time
from classes import *

# Configuração inicial do simulador
def setup_simulator():
    simulator = Simulator('MEDIUM', 60)
    track = Track((100, 100), 200, 4)
    simulator.add(track)

    car = Car(simulator.get_center(), center=(1.36, 1.4))
    simulator.add(car)

    track.set_center(car.get_center())
    track.set_pivot(car.get_center())

    display = Display(simulator.get_center(), simulator.get_window_size())
    simulator.add(display)

    FPS_position = (1.99*simulator.get_center()[0], 0.01*simulator.get_center()[1])
    fps = Statistics(FPS_position)
    simulator.add(fps)

    coordenate_position = (1.99*simulator.get_center()[0], 1.95*simulator.get_center()[1])
    coordenate = Statistics(coordenate_position)
    simulator.add(coordenate)

    compass = Compass((1.85*simulator.get_center()[0], 1.75*simulator.get_center()[1]))
    simulator.add(compass)

    setup_display_graphs(display)

    return simulator, track, display, car, fps, coordenate, compass

# Configuração dos gráficos da interface
def setup_display_graphs(display):
    display.add_graph("wheels")
    display.add_line_to_graph("wheels", "left", color=(0, 200, 0))
    display.add_line_to_graph("wheels", "right", color=(200, 0, 0))

    display.add_graph("speed")
    display.add_line_to_graph("speed", "vm", color=(0, 0, 200))

    display.add_graph("omega")
    display.add_line_to_graph("omega", "ω", color=(200, 200, 0))

# Loop principal do simulador
def main_loop(simulator, track, display, fps, coordenate, compass):
    tempo = time.time()
    counter = 0

    while simulator.is_running():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                simulator.stop_running()

        handle_input(track)

        update_compass_and_coordinates(track, compass, coordenate)
        
        update_random_graph_data(display)

        counter, tempo = update_fps(simulator, fps, tempo, counter)

        simulator.step()

# Tratamento de entrada de teclado
def handle_input(track):
    keys = pygame.key.get_pressed()
    dx, dy = 0, 0
    theta = 0

    if keys[pygame.K_LEFT]:
        dx = -2
    if keys[pygame.K_RIGHT]:
        dx = 2
    if keys[pygame.K_UP]:
        dy = -2
    if keys[pygame.K_DOWN]:
        dy = 2
    if keys[pygame.K_a]:
        theta = 0.01
    if keys[pygame.K_d]:
        theta = -0.01

    track.step(dx, dy, theta)

# Atualização da bússola e coordenadas
def update_compass_and_coordinates(track, compass, coordenate):
    compass.set_angle(-track.get_angle() - math.pi/2)
    coordenate.set_text(f"X: {round(track.get_center()[0], 1)} Y: {round(track.get_center()[1], 1)}")

# Atualização dos dados aleatórios para os gráficos
def update_random_graph_data(display):
    random_left = random.randint(-50, 50)
    random_right = random.randint(-50, 50)
    random_vm = random.randint(-50, 50)
    random_ω = random.randint(-50, 50)

    display.update_graph_data("wheels", "left", random_left)
    display.update_graph_data("wheels", "right", random_right)
    display.update_graph_data("speed", "vm", random_vm)
    display.update_graph_data("omega", "ω", random_ω)

# Atualização do FPS
def update_fps(simulator, fps, tempo, counter):
    current_time = time.time()
    if current_time - tempo >= 1:
        fps.set_text(f"FPS: {counter}")
        fps.set_color((0, 200, 0) if counter >= simulator.get_FPS() else (200, 0, 0))
        counter = 0
        tempo = current_time
    return counter + 1, tempo

if __name__ == "__main__":
    simulator, track, display, car, fps, coordenate, compass = setup_simulator()
    main_loop(simulator, track, display, fps, coordenate, compass)
