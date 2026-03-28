"""
Example of using serial communication with the simulator.

This file shows how to integrate the serial communication module with the main simulator
when real robot data is available.

To use this:
1. Configure ROBOT_SERIAL_PORT and other parameters below
2. Connect the microcontroller via USB
3. Run this script instead of main.py
"""

import numpy as np
from settings import *
from serial_communication import RobotSerialCommunication


def main_with_serial(sim, serial_port="COM3", use_serial=True):
    """
    Main control loop with serial communication from real robot.
    
    Args:
        sim: GameSimulation instance
        serial_port: Serial port where robot is connected
        use_serial: If False, will use simulated data for testing
    """
    
    robot_serial = None
    
    if use_serial:
        # Initialize serial communication
        robot_serial = RobotSerialCommunication(port=serial_port)
        if not robot_serial.connect():
            print(f"Warning: Could not connect to robot on {serial_port}. Using simulated data.")
            use_serial = False
    
    frame_count = 0
    
    try:
        while True:
            frame_count += 1
            
            delta_x = 0.0
            delta_y = 0.0
            robot_data = {}
            
            if use_serial and robot_serial:
                # Receive data from real robot
                result = robot_serial.receive_data()
                
                if result:
                    robot_data, delta_x, delta_y = result
                    
                    # Update simulator with real robot data
                    sim.update_robot_data(robot_data)
                    
                    # Log first few frames for debugging
                    if frame_count < 5:
                        print(f"Frame {frame_count}: encoder_left={robot_data['encoder_left']}, "
                              f"encoder_right={robot_data['encoder_right']}, "
                              f"sensor_front={robot_data['sensor_front']}")
                else:
                    # No data received, use zeros
                    sim.update_robot_data({})
            else:
                # Use simulated data for testing
                import random
                robot_data = {
                    "encoder_left": random.uniform(-50, 50),
                    "encoder_right": random.uniform(-50, 50),
                    "imu_ax": random.uniform(-10, 10),
                    "imu_ay": random.uniform(-10, 10),
                    "imu_az": random.uniform(0, 50),
                    "motor_current_left": random.uniform(-100, 100),
                    "motor_current_right": random.uniform(-100, 100),
                    "pwm_left": random.uniform(-100, 100),
                    "pwm_right": random.uniform(-100, 100),
                    "sensor_front": random.uniform(0, 100),
                    "vel_filtered": 0.0,
                    "omega_filtered": 0.0,
                }
                sim.update_robot_data(robot_data)
                delta_x = random.uniform(-0.01, 0.01)
                delta_y = random.uniform(-0.01, 0.01)
            
            # Update graphs with robot data
            sim.update_graphs_from_robot_data()
            
            # Step the simulation (render, update track position)
            data = sim.step(delta_x, delta_y)
            if data is None:
                break
            
            # Unpack visualization data
            line, future_pts = data
            
            # TODO: Send motor commands back to robot
            # Example: robot_serial.send_command(pwm_left, pwm_right)
            
    except KeyboardInterrupt:
        print("\nSimulation stopped by user")
    finally:
        if robot_serial:
            robot_serial.disconnect()


# Configuration - adjust these for your robot setup
ROBOT_SERIAL_PORT = "COM3"  # Change to your robot's port (COM3, /dev/ttyUSB0, etc.)
USE_SERIAL_COMMUNICATION = False  # Set to True when robot is connected, False for simulation

if __name__ == "__main__":
    sim = settings()
    main_with_serial(
        sim,
        serial_port=ROBOT_SERIAL_PORT,
        use_serial=USE_SERIAL_COMMUNICATION
    )
