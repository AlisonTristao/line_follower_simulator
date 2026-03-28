import numpy as np
import random
import threading
import time
from settings import *
from serial_com import SerialCom

# Global serial communication object
com = None
serial_connected = False
serial_lock = threading.Lock()
read_thread = None
sim_obj = None

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

def read_serial_thread():
    """Thread para ler mensagens do robô continuamente"""
    global com, serial_connected, sim_obj
    
    while serial_connected:
        try:
            if com and com.is_connected():
                msg = com.read_message()
                if msg:
                    with serial_lock:
                        if sim_obj and hasattr(sim_obj, 'serial_monitor') and sim_obj.serial_monitor:
                            sim_obj.serial_monitor.add_message(f"[RX] {msg}", (0, 180, 255))
            time.sleep(0.01)  # Small delay to prevent busy waiting
        except Exception as e:
            time.sleep(0.1)

def serial_connect(port: str):
    """Connect to serial port and start read thread"""
    global com, serial_connected, read_thread
    
    if not com:
        com = SerialCom()
    
    if com.connect(port):
        serial_connected = True
        read_thread = threading.Thread(target=read_serial_thread, daemon=True)
        read_thread.start()
        return True
    return False

def serial_disconnect():
    """Disconnect from serial port"""
    global com, serial_connected
    
    serial_connected = False
    time.sleep(0.1)  # Give thread time to exit
    if com:
        com.disconnect()

def serial_send(message: str):
    """Send message via serial"""
    global com
    
    if com and com.is_connected():
        com.send_message(message)
        return True
    return False

def main(sim) -> None:
    global com, serial_connected, sim_obj
    
    sim_obj = sim
    
    # Setup serial monitor
    if sim.serial_monitor:
        # Get available ports
        com_test = SerialCom()
        available_ports = com_test.list_ports()
        
        if available_ports:
            sim.serial_monitor.port_dropdown.set_options(available_ports)
        else:
            sim.serial_monitor.port_dropdown.set_options(["Nenhuma porta"])
        
        def on_connect_click():
            port = sim.serial_monitor.port_dropdown.get_selected()
            if serial_connect(port):
                sim.serial_monitor.connected = True
                sim.serial_monitor.add_message(f"[SISTEMA] Conectado em {port}", (0, 200, 0))
            else:
                sim.serial_monitor.connected = False
                sim.serial_monitor.add_message(f"[SISTEMA] Falha ao conectar em {port}", (200, 0, 0))
        
        def on_disconnect_click():
            serial_disconnect()
            sim.serial_monitor.connected = False
            sim.serial_monitor.add_message("[SISTEMA] Desconectado", (200, 100, 0))
        
        def on_send_click():
            text = sim.serial_monitor.text_input.get_text()
            if text:
                if serial_send(text):
                    sim.serial_monitor.add_message(f"[TX] {text}", (200, 200, 0))
                else:
                    sim.serial_monitor.add_message("[SISTEMA] Não conectado", (200, 0, 0))
                sim.serial_monitor.text_input.clear()
        
        sim.serial_monitor.btn_connect.callback = on_connect_click
        sim.serial_monitor.btn_disconnect.callback = on_disconnect_click
        sim.serial_monitor.btn_send.callback = on_send_click
        
        sim.serial_monitor.add_message("[SISTEMA] Inicializado", (100, 200, 100))
    
    frame_count = 0
    
    while True:
        frame_count += 1
        
        # Default movement (will be replaced with serial data)
        delta_x = random.uniform(-1e-3, 1e-3)
        delta_y = random.uniform(-1e-3, 1e-3)
        
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
        
        # Small delay to prevent CPU hogging and let other threads run
        time.sleep(0.001)
    
    # Disconnect before exiting
    serial_disconnect()

if __name__ == "__main__":
    sim = settings()
    main(sim)
