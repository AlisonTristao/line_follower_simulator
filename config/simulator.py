import pygame
import random
import time
import math
import threading
from dataclasses import dataclass

from graphics.graphics_elements import *
from graphics.track_generator import *
from .serial_com import SerialCom
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
    sensor_spacing: float = 0.001
    tail_time: float = 0.1
    
    # Robot dimensions (in meters)
    car_size: float = 0.15              # Car width/size in meters
    front_sensor_distance: float = 0.12 # Distance from car center to front sensor in meters
    front_sensor_size: float = 0.08     # Front sensor length in meters
    side_sensor_distance_x: float = 0.08  # Horizontal distance from car center to side sensors in meters
    side_sensor_distance_y: float = 0.10  # Vertical distance from car center to side sensors in meters
    side_sensor_size: float = 0.03      # Side sensor diameter in meters

    # track 
    track_length: float = 0.02
    track_noise: float = 0.12
    track_radius: float = 30
    track_file_path: str = None  # Path to .tfg file for TFG track type
    resolution: int = None  # Resolution read from TFG JSON

# Graph scale limits (min and max percentages for real robot data)
GRAPH_LIMITS = {
    "encoder": {"min": -100, "max": 100},           # RPM or velocity percentage
    "IMU": {"min": -100, "max": 100},         # m/s┬▓ or g
    "Current": {"min": -100, "max": 100},     # mA or percentage
    "PWM": {"min": -100, "max": 100},               # -100% to 100%
    "Array_Sensor": {"min": 0, "max": 100},         # 0-100% (line presence)
    "speed": {"min": -100, "max": 100},      # velocity and omega
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
        self.track_length = config.track_length
        self.array_sensor_dist = config.sensor_spacing
        
        # Robot dimensions (in meters) - converted to pixels via SCALE
        self.car_size_meters = config.car_size
        self.front_sensor_size_meters = config.front_sensor_size
        self.side_sensor_distance_x_meters = config.side_sensor_distance_x
        self.side_sensor_distance_y_meters = config.side_sensor_distance_y
        self.side_sensor_size_meters = config.side_sensor_size

        self.time_simulation = 0
        self.timer = time.time()

        self._init_simulation_objects()
        self._setup_simulator()

        # frames per secod 
        self.frames_per_secod = 0
        self.last_FPS_update = 0

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
        self.left_sensor = None
        self.right_sensor = None
        self.future_points = None
        self.track_percentage = None
        self.points = None
        self.serial_monitor = None
        self.serial_monitor_toggle = None
        self.win = None
        self.clear_trail_button = None
        self.slider_trail_limit = None
        self.last_trail_update_time = time.time()  # Track last time trail point was added

        self.cluster_future_count = 10

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
            "Current_left": 0.0,
            "Current_right": 0.0,
            "PWM_left": 0.0,
            "PWM_right": 0.0,
            "Array_Sensor": 0.0,
            "speed": 0.0,
            "omega_filtered": 0.0,
        }

    # divide the track in clusters for rendering
    def configurate_cluster(self):
        # create clusters of points in the track
        cluster_matrix, position = generate_cluster(self.LENGTH, self.WIDTH, self.SCALE, self.x_track, self.y_track)

        # create the cluster
        for i in range(len(cluster_matrix)):
            cluster = Cluster(size=self.track_length * self.SCALE//2)
            for k in cluster_matrix[i]:
                cluster.add_point(k)
            self.track.set_obj(position[i][0], position[i][1], cluster)
            
        # Process markings into grid cells
        marking_data = process_markings(self.markings, self.LENGTH, self.WIDTH, self.SCALE)
        
        # Add markings to track
        for (row, col), marking_list in marking_data.items():
            existing = None
            cell_item = self.track.matrix[row][col]
            
            if isinstance(cell_item, list):
                for item in cell_item:
                    if isinstance(item, MarkingCluster):
                        existing = item
                        break
            elif isinstance(cell_item, MarkingCluster):
                existing = cell_item
                
            if not existing:
                existing = MarkingCluster(
                    width_pixels=int(self.track_length * self.SCALE), 
                    length_pixels=int(0.04 * self.SCALE)
                )
                self.track.set_obj(row, col, existing)
            
            for x_pix, y_pix, angle in marking_list:
                existing.add_marking(x_pix, y_pix, angle)

    def _setup_simulator(self):
        # print the initialization message
        print("Initializing simulator...")

        # generate trajectory
        # Load track from .tfg file
        if self.config.track_file_path is None:
            raise ValueError("track_file_path must be provided when using TFG track type")
        self.x_track, self.y_track, self.markings, self.config.resolution, limites_altura, limites_largura = load_track_from_tfg(self.config.track_file_path)
        
        # Calcular dimensões do track com base nos limites (ceil(altura) + 2, ceil(largura) + 2)
        self.WIDTH = math.ceil(limites_altura) + 2
        self.LENGTH = math.ceil(limites_largura) + 4
        self.win = len(self.x_track) - 1

        # create car with configured size (convert meters to pixels)
        car_size_pixels = int(self.car_size_meters * self.SCALE) 
        # onde o carrinho vai ficar 1,36 e 1,8 // original
        self.car_draw = Car(self.simulator.get_center(), size=car_size_pixels, center=(1.4, 1.4))

        # create the track
        self.track = Track((self.LENGTH, self.WIDTH), self.SCALE, self.RENDER)

        # create line sensor (front sensor - convert meters to pixels)
        #front_sensor_distance_pixels = int(self.front_sensor_distance_meters * self.SCALE)
        #front_sensor_size_pixels = int(self.front_sensor_size_meters * self.SCALE)
        #self.line_sensor = LineSensor(
        #    (self.car_draw.get_center()[0], self.car_draw.get_center()[1] - front_sensor_distance_pixels),
        #    size=front_sensor_size_pixels
        #)

        # create side sensors (left and right - convert meters to pixels)
        side_sensor_distance_x_pixels = int(self.side_sensor_distance_x_meters * self.SCALE)
        side_sensor_distance_y_pixels = int(self.side_sensor_distance_y_meters * self.SCALE)
        side_sensor_size_pixels = int(self.side_sensor_size_meters * self.SCALE)
        car_x = self.car_draw.get_center()[0]
        car_y = self.car_draw.get_center()[1]
        self.left_sensor = SideSensor((car_x - side_sensor_distance_x_pixels, car_y - side_sensor_distance_y_pixels), size=side_sensor_size_pixels)
        self.right_sensor = SideSensor((car_x + side_sensor_distance_x_pixels, car_y - side_sensor_distance_y_pixels), size=side_sensor_size_pixels)

        # create future points
        #self.future_points = FuturePoints(self.car_draw.get_center(), size=self.track_length * 0.5 * self.SCALE)

        # create display with reduced size
        display_height = int(0.7 * self.simulator.get_window_size()[1])
        display_size = (self.simulator.get_window_size()[0], display_height)
        display_center = (self.simulator.get_center()[0], display_height // 2)
        self.display = Display(display_center, display_size)
        self._setup_display_graphs()

        # create minimap below the graphs
        minimap_size = (500, 250)
        minimap_center_x = minimap_size[0] // 2 + 40  # Position on the left with some padding
        minimap_y = int(display_height + 140) - 40  # Position below the graphs
        minimap_position = (minimap_center_x, minimap_y)
        self.minimap = MiniMap(minimap_position, minimap_size)
        
        # Calculate spacing proportional to real map size vs minimap size
        # Each minimap pixel represents this many real pixels
        pixels_per_minimap_pixel_x = (self.LENGTH * self.SCALE) / minimap_size[0] 
        pixels_per_minimap_pixel_y = (self.WIDTH * self.SCALE) / minimap_size[1]
        max_ratio = max(pixels_per_minimap_pixel_x, pixels_per_minimap_pixel_y)
        minimap_spacing = max(1, int(max_ratio / 3))  # Divide by 3 for denser points
        
        for k in range(0, len(self.x_track), minimap_spacing):
            # Keep minimap path in the same centered world frame used by Track (LENGTH//2, WIDTH//2 offsets).
            minimap_x = 2 * (self.x_track[k] + self.LENGTH // 2) / self.LENGTH - 1
            # Track points are drawn with +Y in MiniMap, so this formula mirrors player/trail placement.
            minimap_y = 2 * (self.y_track[k] + self.WIDTH // 2) / self.WIDTH - 1
            self.minimap.add_point((minimap_x, minimap_y))
        
        # Create controls below the minimap and keep them centered as a group.
        controls_top = int(minimap_position[1] + minimap_size[1] // 2 + 12)
        controls_group_width = 100 + 20 + 200  # button + gap + slider
        controls_start_x = int(minimap_position[0] - controls_group_width // 2)

        # create clear trail button (below minimap)
        button_x = controls_start_x
        button_y = controls_top
        self.clear_trail_button = Button(button_x, button_y, 100, 30, text="Clear Trail", font_size=12, 
                                        bg_color=(200, 50, 50), text_color=(255, 255, 255))
        self.clear_trail_button.callback = lambda: self.minimap.clear_trail()
        
        # create trail limit slider (below minimap, next to clear trail button)
        slider_x = button_x + 120
        slider_y = controls_top + 2
        self.slider_trail_limit = Slider(slider_x, slider_y, 200, 35, min_val=10, max_val=7500, 
                                         initial_val=50, label="Max Trail")
        self.slider_trail_limit.callback = lambda val: setattr(self.minimap, 'MAX_TRAIL_POINTS', val)

        # set track properties
        self.track.set_coordinates(
            ((self.x_track[0] + self.LENGTH // 2) * self.SCALE, (self.y_track[0] + self.WIDTH // 2) * self.SCALE)
        )
        self.track.set_center(self.car_draw.get_center())
        self.track.set_pivot(self.car_draw.get_center())

        if len(self.x_track) > 1:
            dx = self.x_track[1] - self.x_track[0]
            dy = self.y_track[1] - self.y_track[0]
            track_native_angle = math.atan2(dy, dx)
        else:
            track_native_angle = 0
        
        # We rotate the track so its native direction visually aligns with the car's UP direction (-math.pi / 2).
        track_initial_rot = -math.pi / 2 - track_native_angle
        self.track.set_angle(track_initial_rot)

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

        # create compass
        self.compass = Compass((1.85 * self.simulator.get_center()[0], 1.75 * self.simulator.get_center()[1]))

        # create serial monitor toggle (checkbox) - positioned above the graph checkboxes
        display_center = self.display.get_center()
        display_size = self.display.get_size()
        toggle_x = display_center[0] + display_size[0] + 5
        toggle_y = display_center[1] - 25
        self.serial_monitor_toggle = SerialMonitorToggle((toggle_x, toggle_y))

        # create serial monitor on the right side
        serial_monitor_width = 450
        serial_monitor_height = 250
        serial_monitor_x = self.simulator.get_window_size()[0] - serial_monitor_width + 30
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
        #self.simulator.add(self.line_sensor)
        self.simulator.add(self.left_sensor)
        self.simulator.add(self.right_sensor)
        self.simulator.add(self.minimap)
        self.simulator.add(self.clear_trail_button)  # Add before display layer
        self.simulator.add(self.slider_trail_limit)  # Add slider next to button
        self.simulator.add(self.fps_display)
        self.simulator.add(self.coordinates_display)
        self.simulator.add(self.compass)
        #self.simulator.add(self.future_points)
        self.simulator.add(self.display)
        self.simulator.add(self.serial_monitor)
        self.simulator.add(self.serial_monitor_toggle)  # Add toggle AFTER monitor so it renders on top

        # configurate the cluster
        self.configurate_cluster()

        # Setup Cluster's future points tracking with count=10, space=30
        self.setup_cluster_future_points(count=self.cluster_future_count, space=30)

        # Set maximum point limit - stops incrementing when reaching end of track
        Cluster.set_max_point(self.win)

        # print the initialization message
        print("Simulator initialized")

        self.simulator.start()

    def get_rand_color(self):
        random.seed(None)
        return tuple(random.randint(0, 255) for _ in range(3))

    def _setup_display_graphs(self):
        """Setup all graphs to display real robot data."""
        # Define graphs structure: {graph_name: [list of line_names]}
        graphs_structure = {
            "Encoder": ["left", "right"],
            "IMU": ["ax", "ay", "az"],
            "Current": ["left", "right"],
            "PWM": ["left", "right"],
            "Array_Sensor": ["value"],
            "speed": ["vm", "¤ë"],
        }
        
        # Create graphs using structure
        for graph_name, line_names in graphs_structure.items():
            self.display.add_graph(graph_name)
            for line_name in line_names:
                self.display.add_line_to_graph(graph_name, line_name, color=self.get_rand_color())

        '''self.display.add_graph("free_response")
        self.display.add_line_to_graph("free_response", "d", color=self.get_rand_color())
        self.display.add_line_to_graph("free_response", "╬©", color=self.get_rand_color())

        self.display.add_graph("future_control")
        self.display.add_line_to_graph("future_control", "left", color=self.get_rand_color())
        self.display.add_line_to_graph("future_control", "right", color=self.get_rand_color())

        self.display.add_graph("reference")
        self.display.add_line_to_graph("reference", "d", color=self.get_rand_color())
        self.display.add_line_to_graph("reference", "╬©", color=self.get_rand_color())

        self.display.add_graph("error")
        self.display.add_line_to_graph("error", "d", color=self.get_rand_color())
        self.display.add_line_to_graph("error", "╬©", color=self.get_rand_color())'''

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
        # Define mapping: (graph_name, line_name) -> robot_data_key
        graph_updates = [
            ("Encoder", "left", "encoder_left"),
            ("Encoder", "right", "encoder_right"),
            ("IMU", "ax", "imu_ax"),
            ("IMU", "ay", "imu_ay"),
            ("IMU", "az", "imu_az"),
            ("Current", "left", "Current_left"),
            ("Current", "right", "Current_right"),
            ("PWM", "left", "PWM_left"),
            ("PWM", "right", "PWM_right"),
            ("Array_Sensor", "value", "Array_Sensor"),
            ("speed", "vm", "speed"),
            ("speed", "¤ë", "omega_filtered"),
        ]
        
        # Update all graphs in single loop
        for graph_name, line_name, data_key in graph_updates:
            self.display.update_graph_data(graph_name, line_name, self.robot_data[data_key])

    def get_robot_data(self):
        """Return a copy of the current robot data dictionary."""
        return self.robot_data.copy()

    def update_FPS(self, fps):
        """
        update the FPS display with the given value.
        """
        self.fps_display.set_text(f"fps: {fps}")

    def setup_cluster_future_points(self, count, space):
        """Setup Cluster's future points tracking."""
        from graphics.graphics_elements import Cluster
        Cluster.set_future_count(future_count=count, future_space=space)

    def set_left_sensor(self, active: bool):
        """
        Set left side sensor color (green if active, gray if inactive).
        
        Args:
            active (bool): True to activate (green), False to deactivate (gray)
        """
        if self.left_sensor:
            self.left_sensor.set_active(active)

    def set_right_sensor(self, active: bool):
        """
        Set right side sensor color (green if active, gray if inactive).
        
        Args:
            active (bool): True to activate (green), False to deactivate (gray)
        """
        if self.right_sensor:
            self.right_sensor.set_active(active)

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
            self.clear_trail_button.handle_event(event)
            self.slider_trail_limit.handle_event(event)
        return True

    def _step_physics(self, delta_x, delta_y, delta_theta=0.0):
        """Apply robot movement to the track without simulating car dynamics."""
        # Input convention: +Y means up in world frame.
        # Pygame screen coordinates grow downwards, so we invert Y here.
        screen_delta_y = -delta_y
        self.track.step(delta_x * self.SCALE, screen_delta_y * self.SCALE, delta_theta)

        # Update cluster master position (car's current position) for tracking coverage
        car_pos = self.car_draw.get_center()
        car_size = self.car_draw.get_size()
        Cluster.set_master(car_pos, car_size)

        self.compass.set_angle(-self.track.get_angle() - math.pi / 2)
        world_x = self.track.get_center()[0] / self.SCALE
        world_y = -self.track.get_center()[1] / self.SCALE
        self.coordinates_display.set_text(f"x: {world_x:.2f} y: {world_y:.2f}")

        minimap_x = 2 * self.track.get_center()[0] / (self.SCALE * self.LENGTH) - 1
        minimap_y = -2 * self.track.get_center()[1] / (self.SCALE * self.WIDTH) + 1
        
        self.minimap.set_player_position((minimap_x, minimap_y))
        
        # Add current position to minimap trail (only every 0.5 seconds to reduce memory usage)
        current_time = time.time()
        if current_time - self.last_trail_update_time >= self.config.tail_time:
            self.minimap.add_trail_point(minimap_x, minimap_y)
            self.last_trail_update_time = current_time

        # Update all clusters BEFORE drawing to recalculate future points
        # This ensures FuturePoints are synchronized with current position
        for i in range(len(self.track.matrix)):
            for j in range(len(self.track.matrix[i])):
                if hasattr(self.track.matrix[i][j], 'update'):
                    self.track.matrix[i][j].update()
        
        # Now get the updated future points for FuturePoints object
        future_point = Cluster.get_next_point()
        #self.future_points.set_points(future_point)

        self.simulator.draw()
        
        # Single display update after all draws
        pygame.display.flip()

        if Cluster._next_point == self.win:
            print("Congratulations!")
            print("You win the game, you score is {:.2f}".format(100 * 100 / self.time_simulation))
            return None
        
        return True

        '''future_point = [
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
        )'''

    def step(self, delta_x, delta_y, delta_theta=0.0):
        """Public method used by external modules to advance the simulation."""
        if not self._handle_events():
            return None
        
        self.serial_monitor.update()
        
        # Update visibility of compass and coordinates based on checkboxes
        self.compass.visible = self.display.checkbox_compass.checked
        self.coordinates_display.visible = self.display.checkbox_coordinates.checked

        data = self._step_physics(delta_x, delta_y, delta_theta)
        if data is None:
            pygame.quit()
            return None

        self.time_simulation += 1 / self.FPS
        #while (time.time() - self.timer) < 1 / self.FPS:
        #    pass

        self.frames_per_secod += 1
        if time.time() - self.last_FPS_update >= 1.0:
            self.update_FPS("{:.1f}".format(self.frames_per_secod))
            self.frames_per_secod = 0
            self.last_FPS_update = time.time()
        self.timer = time.time()

        return data

    def update_step(self, step_data):
        """
        Consolidated method for a single loop iteration.
        All data (robot data, movement, sensors) passed in a single dictionary.
        
        Args:
            step_data (dict): Dictionary containing:
                - "delta_x" (float): movement in x direction (in meters)
                - "delta_y" (float): movement in y direction (in meters, +Y is up)
                - "delta_theta" (float): rotation angle (in radians)
                - "left_sensor_active" (bool): activate left side sensor
                - "right_sensor_active" (bool): activate right side sensor
                - All other robot sensor data to plot
                
        Returns:
            tuple: (line_sensor_data, future_points) or None if simulation ended
        """
        # Extract movement and sensor data
        delta_x = step_data.get("delta_x", 0.0)
        delta_y = step_data.get("delta_y", 0.0)
        delta_theta = step_data.get("delta_theta", 0.0)
        left_sensor_active = step_data.get("left_sensor_active", False)
        right_sensor_active = step_data.get("right_sensor_active", False)
        
        # Extract robot data (everything except movement/sensors)
        robot_data = {k: v for k, v in step_data.items() 
                      if k not in ["delta_x", "delta_y", "delta_theta", "left_sensor_active", "right_sensor_active"]}
        
        # Update robot data and graphs
        self.update_robot_data(robot_data)
        self.update_graphs_from_robot_data()
        
        # Update sensor states
        self.set_left_sensor(left_sensor_active)
        self.set_right_sensor(right_sensor_active)
        
        # Advance simulation with physics and drawing
        result = self.step(delta_x, delta_y, delta_theta)
        
        # Track sensor activations on minimap (after step calculates positions)
        if result is not None:  # step() returns tuple
            minimap_x = 2 * self.track.get_center()[0] / (self.SCALE * self.LENGTH) - 1
            minimap_y = -2 * self.track.get_center()[1] / (self.SCALE * self.WIDTH) + 1
            if left_sensor_active:
                self.minimap.add_left_sensor_point(minimap_x, minimap_y)
            if right_sensor_active:
                self.minimap.add_right_sensor_point(minimap_x, minimap_y)
        
        return result

    # ========================================================================
    # Serial Communication Methods
    # ========================================================================

    def _read_serial_thread(self):
        """Thread para ler mensagens do rob├┤ continuamente"""
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
                    self.serial_monitor.add_message("[SISTEMA] N├úo conectado", (200, 0, 0))
                self.serial_monitor.text_input.clear()
        
        def on_clear_click():
            self.serial_monitor.clear_messages()
            self.serial_monitor.add_message("[SISTEMA] Hist├│rico limpo", (100, 200, 100))
        
        self.serial_monitor.btn_connect.callback = on_connect_click
        self.serial_monitor.btn_disconnect.callback = on_disconnect_click
        self.serial_monitor.btn_send.callback = on_send_click
        self.serial_monitor.btn_clear.callback = on_clear_click
        
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

'''def set_future_points(count, space):
    sim = _require_simulation()
    if sim is None:
        return
    sim.set_future_points(count, space)'''

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
