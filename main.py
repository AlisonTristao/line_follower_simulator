import numpy as np
import random
import threading
from settings import *
from serial_com import SerialCom

def simulate_robot_data():
    """
    Simulate robot data for testing.
    This will be replaced with actual serial communication data.
    """
    import random
    import math
    
    # Simulate some varying data for visualization
    timestamp = np.linspace(0, 10, 1000)
    sine_wave = 50 * np.sin(2 * np.pi * timestamp)
    
    return {
        "encoder_left": sine_wave[random.randint(-100, 100)],
        "encoder_right": sine_wave[random.randint(-100, 100)],
        "imu_ax": random.uniform(-10, 10),
        "imu_ay": random.uniform(-10, 10),
        "imu_az": random.uniform(0, 50),
        "motor_current_left": random.uniform(-100, 100),
        "motor_current_right": random.uniform(-100, 100),
        "pwm_left": random.uniform(-100, 100),
        "pwm_right": random.uniform(-100, 100),
        "sensor_front": random.uniform(0, 100),
        "vel_filtered": sine_wave[int(timestamp[0] * 100) % 1000] / 2,
        "omega_filtered": random.uniform(-50, 50),
    }

def main(sim) -> None:
    # ------------------------------------------------------------------
    # Main control loop - Serial Backend + Pygame Simulator
    # ------------------------------------------------------------------

    # Initialize serial communication
    com = SerialCom()
    
    print("\n" + "="*60)
    print("LINHA FOLLOWER - SERIAL BACKEND + SIMULATOR")
    print("="*60)
    
    # List and select port
    port = com.select_port()
    if not port:
        print("\n✗ Nenhuma porta selecionada. Usando simulador standalone.")
        use_serial = False
    else:
        # Try to connect
        if com.connect(port):
            use_serial = True
            print("\n✓ Conexão estabelecida com o robô!")
        else:
            print("\n✗ Falha ao conectar. Usando simulador standalone.")
            use_serial = False

    print("\nSimulador + Backend Serial inicializando...\n")
    
    frame_count = 0
    last_message = None
    
    def read_messages():
        """Thread para ler mensagens do robô continuamente"""
        nonlocal last_message
        while com.is_connected():
            msg = com.read_message()
            if msg:
                last_message = msg
                print(f"\n[RX]: {msg}")
    
    # Start read thread if connected
    if use_serial:
        read_thread = threading.Thread(target=read_messages, daemon=True)
        read_thread.start()
    
    while True:
        frame_count += 1
        
        # Default movement (will be replaced with serial data)
        delta_x = random.uniform(-1e-3, 1e-3)
        delta_y = random.uniform(-1e-3, 1e-3)
        
        # Print received message if any
        if last_message:
            print(f"Frame {frame_count}: {last_message}")
            last_message = None
        
        # Use simulated data for graphs (or will come from parser later)
        robot_data = simulate_robot_data()
        sim.update_robot_data(robot_data)
        sim.update_graphs_from_robot_data()

        data = sim.step(delta_x, delta_y)
        if data is None:
            break

        # ---------------------------------------------------------------
        # Receive visualization data from simulator
        # ---------------------------------------------------------------

        line, future_pts = data
    
    # Disconnect before exiting
    if use_serial:
        com.disconnect()
        print("\n✓ Desconectado.")

if __name__ == "__main__":
    sim = settings()
    main(sim)
