import numpy as np
import random
import pygame
from config.settings import *

def get_keyboard_input():
    """
    Read arrow keys and return delta_x, delta_y, and delta_theta.
    - Left/Right arrows: control delta_x (horizontal movement)
    - Up/Down arrows: control delta_y (+Y up, -Y down)
    - Q/E keys: control delta_theta (rotation)
    
    Returns:
        tuple: (delta_x, delta_y, delta_theta) based on pressed keys
    """
    keys = pygame.key.get_pressed()
    
    delta_x = 0.0
    delta_y = 0.0
    delta_theta = 0.0
    
    # Horizontal movement (Left/Right arrows)
    if keys[pygame.K_LEFT]:
        delta_x = -0.01
    elif keys[pygame.K_RIGHT]:
        delta_x = 0.01
    
    # Vertical movement (Up/Down arrows)
    if keys[pygame.K_UP]:
        delta_y = 0.01
    elif keys[pygame.K_DOWN]:
        delta_y = -0.01

    # Rotation (Q/E keys)
    if keys[pygame.K_q]:
        delta_theta = 0.01  # Rotate counter-clockwise
    elif keys[pygame.K_e]:
        delta_theta = -0.01  # Rotate clockwise
    
    return delta_x, delta_y, delta_theta

def simulate_robot_data():
    """
    Simulate all robot data and control inputs for testing.
    Returns a single dictionary with everything needed for one simulation step.
    """
    # Get movement from keyboard
    delta_x, delta_y, delta_theta = get_keyboard_input()
    
    # Simulate some varying data for visualization
    timestamp = np.linspace(0, 10, 1000)
    sine_wave = 50 * np.sin(2 * np.pi * timestamp)
    
    return {
        # Robot sensor data
        "encoder_left": random.randint(-100, 100),
        "encoder_right": random.randint(-100, 100),
        "imu_ax": random.uniform(-10, 10),
        "imu_ay": random.uniform(-10, 10),
        "imu_az": random.uniform(0, 50),
        "Current_left": random.uniform(-100, 100),
        "Current_right": random.uniform(-100, 100),
        "PWM_left": random.uniform(-100, 100),
        "PWM_right": random.uniform(-100, 100),
        "Array_Sensor": random.uniform(0, 100),
        "speed": sine_wave[int(timestamp[0] * 100) % 1000] / 2,
        "omega_filtered": random.uniform(-50, 50),
        
        # Control inputs from keyboard
        "delta_x": delta_x,
        "delta_y": delta_y,
        "delta_theta": delta_theta,
        "left_sensor_active": 1 if random.random() < 0.001 else 0,    # 0.1% chance
        "right_sensor_active": 1 if random.random() < 0.001 else 0,   # 0.1% chance
    }

def main(sim) -> None:
    # ------------------------------------------------------------------
    # Main control loop - Serial Backend + Pygame Simulator
    # ------------------------------------------------------------------
    # Controls:
    # - Up Arrow: move forward (+Y)
    # - Down Arrow: move backward (-Y)
    # - Left Arrow: move left (-X)
    # - Right Arrow: move right (+X)
    # - Q: rotate counter-clockwise
    # - E: rotate clockwise
    # - ESC: quit
    
    # Setup serial monitor UI
    sim.serial_setup_ui()
    
    while True:
        # Get all data for this step in a single dictionary
        step_data = simulate_robot_data()
        
        # Single call with one argument
        data = sim.update_step(step_data)
        
        if data is None:
            break
        
        # Receive visualization data from simulator
        #line_sensor, future_points = data
    
    # Disconnect before exiting
    sim.serial_disconnect()

if __name__ == "__main__":
    sim = settings()
    main(sim)
