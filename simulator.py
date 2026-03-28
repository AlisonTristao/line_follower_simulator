import pygame
import random
import time
import math
import threading
from dataclasses import dataclass

from graphics.graphics_elements import *
from graphics.track_generator import *
from serial_com import SerialCom
import numpy as np

@dataclass
class SimulationConfig:
    """Configuration values used to start a simulation."""

    screen_size: int
    fps: int
    length: int
    width: int
    scale: int
    render: int
    track_type: int = 0
    track_length: float = 0.02
    sensor_spacing: float = 0.001


# Graph scale limits (min and max percentages for real robot data)
GRAPH_LIMITS = {
    "encoder": {"min": -100, "max": 100},           # RPM or velocity percentage
    "imu_accel": {"min": -100, "max": 100},         # m/s² or g
    "motor_current": {"min": -100, "max": 100},     # mA or percentage
    "pwm": {"min": -100, "max": 100},               # -100% to 100%
    "sensor_front": {"min": 0, "max": 100},         # 0-100% (line presence)
    "vel_filtered": {"min": -100, "max": 100},      # velocity and omega
}

class GameSimulation:
    """High level controller responsible for running the simulation."""

    def __init__(self, config: SimulationConfig):
        self.config = config

        # copy frequently used values for convenience
        self.screen_size = config.screen_size
        self.FPS = config.fps
        self.LENGTH = config.length
        self.WIDTH = config.width
        self.SCALE = config.scale
        self.RENDER = config.render
        self.track_type = config.track_type
        self.track_length = config.track_length
        self.array_sensor_dist = config.sensor_spacing

        self.time_simulation = 0
        self.timer = time.time()

        self._init_simulation_objects()
        self._setup_simulator()

    def _init_simulation_objects(self):
        self.simulator = Simulator(self.screen_size, self.FPS)
        self.car = None
        self.track = None
        self.display = None
        self.minimap = None
        self.fps_display = None
        self.coordinates_display = None
        self.compass = None
        self.line_sensor = None
        self.future_points = None
        self.track_percentage = None
        self.points = None
        self.serial_monitor = None
        self.serial_monitor_toggle = None
        self.win = None

        self.future_points_count = 10

        # Serial communication
        self.com = None
        self.serial_connected = False
        self.serial_lock = threading.Lock()
        self.read_thread = None

        # Real robot data storage
        self.robot_data = {
            "encoder_left": 0.0,
            "encoder_right": 0.0,
            "imu_ax": 0.0,
            "imu_ay": 0.0,
            "imu_az": 0.0,
            "motor_current_left": 0.0,
            "motor_current_right": 0.0,
            "pwm_left": 0.0,
            "pwm_right": 0.0,
            "sensor_front": 0.0,
            "vel_filtered": 0.0,
            "omega_filtered": 0.0,
        }

    # divide the track in clusters for rendering
    def configurate_cluster(self):
        # create clusters of points in the track
        cluster_matrix, position = generate_cluster(self.LENGTH, self.WIDTH, self.SCALE, self.x_track, self.y_track)

        # create the cluster
        for i in range(len(cluster_matrix)):
            cluster = Cluster(size=self.track_length * self.SCALE)
            for k in cluster_matrix[i]:
                cluster.add_point(k)
            self.track.set_obj(position[i][0], position[i][1], cluster)

    def _setup_simulator(self):
        # print the initialization message
        print("Initializing simulator...")

        # generate trajectory
        self.x_track, self.y_track = generate_track(
            self.track_type, noise_level=0.225, checkpoints=36, resolution=500, track_rad=30
        )
        self.win = len(self.x_track) - 1

        # create car
        self.car_draw = Car(self.simulator.get_center(), center=(1.36, 1.8))

        # create the track
        self.track = Track((self.LENGTH, self.WIDTH), self.SCALE, self.RENDER)

        # create line sensor
        self.line_sensor = LineSensor((self.car_draw.get_center()[0], self.car_draw.get_center()[1]))

        # create future points
        self.future_points = FuturePoints(self.car_draw.get_center(), size=self.track_length * 0.5 * self.SCALE)

        # create minimap
        minimap_position = (0.9 * self.simulator.get_center()[0], 1.75 * self.simulator.get_center()[1])
        self.minimap = MiniMap(minimap_position, (200, 150))
        for k in range(0, len(self.x_track), self.SCALE // 10):
            self.minimap.add_point((2 * self.x_track[k] / self.LENGTH, 2 * self.y_track[k] / self.WIDTH))

        # set track properties
        self.track.set_coordinates(
            ((self.x_track[0] + self.LENGTH // 2) * self.SCALE, (self.y_track[0] + self.WIDTH // 2) * self.SCALE)
        )
        self.track.set_center(self.car_draw.get_center())
        self.track.set_pivot(self.car_draw.get_center())

        # create display
        self.display = Display(self.simulator.get_center(), self.simulator.get_window_size())
        self._setup_display_graphs()

        # create coordinates display
        coordinates_position = (1.85 * self.simulator.get_center()[0], 1.95 * self.simulator.get_center()[1])
        self.coordinates_display = Statistics(coordinates_position)
        self.coordinates_display.set_offset(2)

        # if the screen is big, raise the font size
        if self.screen_size == FULL:
            self.coordinates_display.set_font_size(25)
        if self.screen_size == MEDIUM:
            self.coordinates_display.set_font_size(18)
        if self.screen_size == SMALL:
            self.coordinates_display.set_font_size(12)

        # create statistics displays
        self.fps_display = Statistics((1.99 * self.simulator.get_center()[0], 0.01 * self.simulator.get_center()[1]))

        # create display points
        self.track_percentage = Statistics((1.0 * self.simulator.get_center()[0], 1.95 * self.simulator.get_center()[1]))

        # pontuation of the track
        self.points = Statistics((0.25 * self.simulator.get_center()[0], 1.95 * self.simulator.get_center()[1]))

        # create compass
        self.compass = Compass((1.85 * self.simulator.get_center()[0], 1.75 * self.simulator.get_center()[1]))

        # create serial monitor toggle (checkbox) - positioned above the graph checkboxes
        display_center = self.display.get_center()
        display_size = self.display.get_size()
        toggle_x = display_center[0] + display_size[0] + 5
        toggle_y = display_center[1] - 25
        self.serial_monitor_toggle = SerialMonitorToggle((toggle_x, toggle_y))

        # create serial monitor on the right side
        serial_monitor_width = 380
        serial_monitor_height = 450
        serial_monitor_x = self.simulator.get_window_size()[0] - serial_monitor_width + 2
        serial_monitor_y = 40
        self.serial_monitor = SerialMonitor(
            (serial_monitor_x, serial_monitor_y),
            (serial_monitor_width, serial_monitor_height)
        )
        # Link the toggle button to the serial monitor
        self.serial_monitor.set_toggle_button(self.serial_monitor_toggle)

        # add objects to the simulator
        # the order of the objects is the layer order
        self.simulator.add(self.track)
        self.simulator.add(self.car_draw)
        self.simulator.add(self.line_sensor)
        #self.simulator.add(self.minimap)
        self.simulator.add(self.fps_display)
        self.simulator.add(self.coordinates_display)
        self.simulator.add(self.compass)
        self.simulator.add(self.future_points)
        self.simulator.add(self.track_percentage)
        self.simulator.add(self.points)
        self.simulator.add(self.display)
        self.simulator.add(self.serial_monitor)
        self.simulator.add(self.serial_monitor_toggle)  # Add toggle AFTER monitor so it renders on top

        # configurate the cluster
        self.configurate_cluster()

        # print the initialization message
        print("Simulator initialized")

        self.simulator.start()

    def get_rand_color(self):
        random.seed(None)
        return tuple(random.randint(0, 255) for _ in range(3))

    def _setup_display_graphs(self):
        """Setup all graphs to display real robot data."""
        # Encoder data (wheel velocities)
        self.display.add_graph("encoder")
        self.display.add_line_to_graph("encoder", "left", color=self.get_rand_color())
        self.display.add_line_to_graph("encoder", "right", color=self.get_rand_color())

        # IMU acceleration
        self.display.add_graph("imu_accel")
        self.display.add_line_to_graph("imu_accel", "ax", color=self.get_rand_color())
        self.display.add_line_to_graph("imu_accel", "ay", color=self.get_rand_color())
        self.display.add_line_to_graph("imu_accel", "az", color=self.get_rand_color())

        # Motor current
        self.display.add_graph("motor_current")
        self.display.add_line_to_graph("motor_current", "left", color=self.get_rand_color())
        self.display.add_line_to_graph("motor_current", "right", color=self.get_rand_color())

        # PWM applied
        self.display.add_graph("pwm")
        self.display.add_line_to_graph("pwm", "left", color=self.get_rand_color())
        self.display.add_line_to_graph("pwm", "right", color=self.get_rand_color())

        # Front sensor reading
        self.display.add_graph("sensor_front")
        self.display.add_line_to_graph("sensor_front", "value", color=self.get_rand_color())

        # Filtered velocity and omega (to be implemented with filtering)
        self.display.add_graph("vel_filtered")
        self.display.add_line_to_graph("vel_filtered", "vm", color=self.get_rand_color())
        self.display.add_line_to_graph("vel_filtered", "ω", color=self.get_rand_color())

        '''self.display.add_graph("free_response")
        self.display.add_line_to_graph("free_response", "d", color=self.get_rand_color())
        self.display.add_line_to_graph("free_response", "θ", color=self.get_rand_color())

        self.display.add_graph("future_control")
        self.display.add_line_to_graph("future_control", "left", color=self.get_rand_color())
        self.display.add_line_to_graph("future_control", "right", color=self.get_rand_color())

        self.display.add_graph("reference")
        self.display.add_line_to_graph("reference", "d", color=self.get_rand_color())
        self.display.add_line_to_graph("reference", "θ", color=self.get_rand_color())

        self.display.add_graph("error")
        self.display.add_line_to_graph("error", "d", color=self.get_rand_color())
        self.display.add_line_to_graph("error", "θ", color=self.get_rand_color())'''

    def _update_graphs(self):
        """Update all graphs with real robot data (to be received from serial)."""
        # TODO: Update with real robot data once serial communication is implemented
        pass

    def update_robot_data(self, data_dict):
        """
        Update robot data from serial communication.
        
        Args:
            data_dict: Dictionary with keys like 'encoder_left', 'encoder_right', etc.
        """
        for key, value in data_dict.items():
            if key in self.robot_data:
                self.robot_data[key] = float(value)

    def update_graphs_from_robot_data(self):
        """Update all graphs with current robot data."""
        # Encoder data
        self.display.update_graph_data("encoder", "left", self.robot_data["encoder_left"])
        self.display.update_graph_data("encoder", "right", self.robot_data["encoder_right"])

        # IMU acceleration
        self.display.update_graph_data("imu_accel", "ax", self.robot_data["imu_ax"])
        self.display.update_graph_data("imu_accel", "ay", self.robot_data["imu_ay"])
        self.display.update_graph_data("imu_accel", "az", self.robot_data["imu_az"])

        # Motor current
        self.display.update_graph_data("motor_current", "left", self.robot_data["motor_current_left"])
        self.display.update_graph_data("motor_current", "right", self.robot_data["motor_current_right"])

        # PWM applied
        self.display.update_graph_data("pwm", "left", self.robot_data["pwm_left"])
        self.display.update_graph_data("pwm", "right", self.robot_data["pwm_right"])

        # Front sensor reading
        self.display.update_graph_data("sensor_front", "value", self.robot_data["sensor_front"])

        # Filtered velocity and omega
        self.display.update_graph_data("vel_filtered", "vm", self.robot_data["vel_filtered"])
        self.display.update_graph_data("vel_filtered", "ω", self.robot_data["omega_filtered"])

    def get_robot_data(self):
        """Return a copy of the current robot data dictionary."""
        return self.robot_data.copy()

    def update_FPS(self, fps):
        """
        update the FPS display with the given value.
        """
        self.fps_display.set_text(f"fps: {fps}")

    def update_coverage(self, coverage):
        """
        update the coverage display with the given value.
        """
        self.track_percentage.set_text(f"covered: {coverage}")

    def update_points(self, points):
        """Update the points display with the given value."""
        self.points.set_text(f"score: {points}")

    def set_future_points(self, count, space):
        """Initialize future points visualization."""
        from graphics.graphics_elements import Cluster
        Cluster.set_future_count(future_count=count, future_space=space)

    # ------------------------------------------------------------------
    # Simulation main loop helpers
    # ------------------------------------------------------------------
    def _handle_events(self) -> bool:
        """Process pygame events. Returns False when simulation should stop."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                print("Simulation stopped using X button")
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    print("Simulation stopped using ESC")
                    return False

            self.display.verify_checkbox(event)
            self.serial_monitor_toggle.handle_event(event)
            self.serial_monitor.handle_event(event)
        return True

    def _step_physics(self, delta_x, delta_y):
        """Apply robot movement to the track without simulating car dynamics."""
        # Apply the delta movement received from real robot
        self.track.step(delta_x * self.SCALE, delta_y * self.SCALE, 0)

        # Update cluster master position (car's current position) for tracking coverage
        car_pos = self.track.get_center()
        car_size = self.car_draw.get_size()
        Cluster.set_master(car_pos, car_size)
        
        # DEBUG
        if self.time_simulation < 0.5:  # Only print first few frames
            print(f"[DEBUG] car_pos={car_pos}, car_size={car_size}, next_point={Cluster._next_point}")

        self.compass.set_angle(-self.track.get_angle() - math.pi / 2)
        self.coordinates_display.set_text(
            f"x: {round(self.track.get_center()[0]/self.SCALE, 2):.2f} y: {round(self.track.get_center()[1]/self.SCALE, 2):.2f}"
        )

        self.minimap.set_player_position(
            (2 * self.track.get_center()[0] / (self.SCALE * self.LENGTH) - 1,
             -2 * self.track.get_center()[1] / (self.SCALE * self.WIDTH) + 1)
        )

        self.simulator.draw()

        if Cluster._next_point == self.win:
            print("Congratulations!")
            print("You win the game, you score is {:.2f}".format(100 * 100 / self.time_simulation))
            return None

        future_point = Cluster.get_next_point()
        self.future_points.set_points(future_point)
        future_point = [
            ((x - self.car_draw.get_center()[0]) / self.SCALE,
             (-y + self.car_draw.get_center()[1]) / self.SCALE)
            for x, y in future_point
        ]

        line = self.simulator.screen.subsurface(
            (
                self.line_sensor.get_x() - self.line_sensor.get_size() / 2,
                self.line_sensor.get_y() - 1,
                self.line_sensor.get_size(),
                1,
            )
        )
        line_arr = pygame.surfarray.pixels3d(line)
        line_pb = line_arr.mean(axis=2)  # calculate the mediam
        line_pb = np.array(line_pb[:, 0], dtype=np.uint8)  # remove dimension
        block_len = int(self.array_sensor_dist * self.SCALE)
        block_count = line_pb.shape[0] // block_len
        final_line = line_pb[: block_count * block_len].reshape(block_count, block_len).mean(axis=1)

        return (
            1 - final_line / 255,
            future_point
        )

    def step(self, delta_x, delta_y):
        """Public method used by external modules to advance the simulation."""
        if not self._handle_events():
            return None
        
        self.serial_monitor.update()

        data = self._step_physics(delta_x, delta_y)
        if data is None:
            pygame.quit()
            return None

        self.time_simulation += 1 / self.FPS
        coverage = Cluster._next_point / self.win * 100
        self.update_coverage("{:.2f}%".format(coverage))
        self.update_points("{:.2f}".format(100 * coverage / self.time_simulation))

        while (time.time() - self.timer) < 1 / self.FPS:
            pass

        self.update_FPS("{:.1f}".format(1 / (time.time() - self.timer)))
        self.timer = time.time()

        return data

    # ========================================================================
    # Serial Communication Methods
    # ========================================================================

    def _read_serial_thread(self):
        """Thread para ler mensagens do robô continuamente"""
        while self.serial_connected:
            try:
                if self.com and self.com.is_connected():
                    msg = self.com.read_message()
                    if msg:
                        with self.serial_lock:
                            if self.serial_monitor:
                                self.serial_monitor.add_message(f"[RX] {msg}", (0, 180, 255))
                time.sleep(0.01)
            except Exception as e:
                time.sleep(0.1)

    def serial_connect(self, port: str):
        """Connect to serial port and start read thread"""
        if not self.com:
            self.com = SerialCom()
        
        if self.com.connect(port):
            self.serial_connected = True
            self.read_thread = threading.Thread(target=self._read_serial_thread, daemon=True)
            self.read_thread.start()
            return True
        return False

    def serial_disconnect(self):
        """Disconnect from serial port"""
        self.serial_connected = False
        time.sleep(0.1)
        if self.com:
            self.com.disconnect()

    def serial_send(self, message: str):
        """Send message via serial"""
        if self.com and self.com.is_connected():
            self.com.send_message(message)
            return True
        return False

    def serial_setup_ui(self):
        """Setup serial monitor UI callbacks"""
        if not self.serial_monitor:
            return
        
        # Get available ports - create SerialCom if needed
        if not self.com:
            self.com = SerialCom()
        
        available_ports = self.com.list_ports()
        if available_ports:
            self.serial_monitor.port_dropdown.set_options(available_ports)
        else:
            self.serial_monitor.port_dropdown.set_options(["Nenhuma porta"])
        
        # Create and connect callbacks
        def on_connect_click():
            port = self.serial_monitor.port_dropdown.get_selected()
            if self.serial_connect(port):
                self.serial_monitor.connected = True
                self.serial_monitor.add_message(f"[SISTEMA] Conectado em {port}", (0, 200, 0))
            else:
                self.serial_monitor.connected = False
                self.serial_monitor.add_message(f"[SISTEMA] Falha ao conectar em {port}", (200, 0, 0))
        
        def on_disconnect_click():
            self.serial_disconnect()
            self.serial_monitor.connected = False
            self.serial_monitor.add_message("[SISTEMA] Desconectado", (200, 100, 0))
        
        def on_send_click():
            text = self.serial_monitor.text_input.get_text()
            if text:
                if self.serial_send(text):
                    self.serial_monitor.add_message(f"[TX] {text}", (200, 200, 0))
                else:
                    self.serial_monitor.add_message("[SISTEMA] Não conectado", (200, 0, 0))
                self.serial_monitor.text_input.clear()
        
        self.serial_monitor.btn_connect.callback = on_connect_click
        self.serial_monitor.btn_disconnect.callback = on_disconnect_click
        self.serial_monitor.btn_send.callback = on_send_click
        
        self.serial_monitor.add_message("[SISTEMA] Inicializado", (100, 200, 100))

_simulation: GameSimulation | None = None

def start_simulation(
    screen_size=MEDIUM,
    fps=120,
    length=100,
    width=100,
    scale=300,
    render=4,
    seed=None,
    track_type=0,
    track_length=0.02,
    sensor_spacing=0.001,
):
    """Create and configure a :class:`GameSimulation` instance."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    global _simulation
    if _simulation is not None:
        print("Simulator already initialized")
        return _simulation

    config = SimulationConfig(
        screen_size,
        fps,
        length,
        width,
        scale,
        render,
        track_type,
        track_length,
        sensor_spacing,
    )
    _simulation = GameSimulation(config)
    return _simulation

def _require_simulation() -> GameSimulation | None:
    if _simulation is None:
        print("Simulator not initialized")
        return None
    return _simulation

def set_car_dynamics(
    wheels_radius,
    wheels_distance,
    wheels_RPM,
    ke_l,
    ke_r,
    accommodation_time_l,
    accommodation_time_r,
    sensor_distance,
    sensor_count,
):
    sim = _require_simulation()
    if sim is None:
        return
    sim.setup_car_dynamics(
        wheels_radius,
        wheels_distance,
        wheels_RPM,
        ke_l,
        ke_r,
        1,
        accommodation_time_l,
        accommodation_time_r,
        sensor_distance,
        sensor_count,
    )

def set_future_points(count, space):
    sim = _require_simulation()
    if sim is None:
        return
    sim.set_future_points(count, space)

'''def set_graph_future_control(left, right):
    sim = _require_simulation()
    if sim is None:
        return
    sim.future_control_left = left
    sim.future_control_right = right

def set_graph_reference(omega, v):
    sim = _require_simulation()
    if sim is None:
        return
    sim.future_v = v
    sim.future_omega = omega

def set_graph_free_response(omega, v):
    sim = _require_simulation()
    if sim is None:
        return
    sim.free_response_omega = omega
    sim.free_response_v = v

def set_graph_forced_response(omega, v):
    sim = _require_simulation()
    if sim is None:
        return
    sim.forced_response_omega = omega
    sim.forced_response_v = v

def set_graph_error(omega, v):
    sim = _require_simulation()
    if sim is None:
        return
    sim.error_omega = omega
    sim.error_v = v'''

def step_simulation(v1, v2):
    sim = _require_simulation()
    if sim is None or sim.car is None:
        return None
    return sim.step(v1, v2)