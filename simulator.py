import pygame
import random
import time
from graphics_elements import *
from track_generator import *
from car_dynamics import *

class SimulatorController:
    def __init__(self, screen_size, fps, length, width, scale, render, track_type=0, track_length=0.02, sensor_spacing=0.001):
        # controler parameters
        self.FPS = fps
        self.screen_size = screen_size
        self.LENGTH = length
        self.WIDTH = width
        self.SCALE = scale
        self.RENDER = render
        self.time_simulation = 0

        # track parameters
        self.x_track = None
        self.y_track = None
        self.array_sensor_dist = sensor_spacing
        self.track_type = track_type
        self.track_length = track_length
        self.win = None

        # simulator objects
        self.simulator = Simulator(screen_size, self.FPS)
        self.track = None
        self.minimap = None
        self.display = None
        self.car = None
        self.fps_display = None
        self.coordinates_display = None
        self.compass = None
        self.line_sensor = None
        self.future_points = None
        self.track_percentage = None
        self.points = None

        # future parameters
        self.future_points_count = 10
        self.future_space = 30

        # model parameters
        self.car = None #car_dynamics(z=1/self.FPS)

        # setup the simulator
        self._setup_simulator()

    def setup_car_dynamics(self,  wheels_radius=0.04, wheels_distance=0.1, wheels_RPM=3000, ke=1, kq=1, accommodation_time=1.0, sensor_distance=0.1, sensor_count=8):
        z = 1/self.FPS
        self.car = car_dynamics(z, wheels_radius, wheels_distance, wheels_RPM, ke, kq, accommodation_time)
        self.car_draw.set_size(self.car.get_size()*self.SCALE)
        self.line_sensor.set_coordinates((self.car_draw.get_center()[0], self.car_draw.get_center()[1] - sensor_distance * self.SCALE))
        self.line_sensor.set_size(sensor_count * self.SCALE * self.array_sensor_dist) # 0.05 meter beetween sensors

    def set_future_points(self, count, space):
        self.future_points_count = count
        self.future_space = space
        Cluster.set_master(self.car_draw.get_center(), self.car_draw.get_size())    # set the master point
        Cluster.set_future_count(self.future_points_count, self.future_space)     # set the future points count

    # divide the track in clusters for rendering 
    def configurate_cluster(self):
        # create clusters of points in the track
        processed_points = set()
        for i in range(-self.LENGTH // 2, self.LENGTH // 2):
            for j in range(-self.WIDTH // 2, self.WIDTH // 2):
                # verify if has points in the square
                index = points_in_square(i, j, (self.LENGTH + self.WIDTH) / self.SCALE, self.x_track, self.y_track)
                if len(index) > 0:
                    # create a cluster of points
                    cluster = Cluster(size=self.track_length*self.SCALE)                        # create a cluster
                    # add the points to the cluster
                    for k in index:
                        if (self.x_track[k], self.y_track[k]) not in processed_points:
                            x = (self.x_track[k] - i) * self.SCALE
                            y = (self.y_track[k] - j) * self.SCALE
                            cluster.add_point((x, y), index=k)
                            processed_points.add((self.x_track[k], self.y_track[k]))
                    # set the cluster in the track
                    self.track.set_obj(i + self.LENGTH // 2, j + self.WIDTH // 2, cluster)

    def _setup_simulator(self):
        # print the initialization message
        print("Initializing simulator...")

        # generate trajectory
        self.x_track, self.y_track = generate_track(self.track_type, noise_level=0.3, checkpoints=36, resolution=1000, track_rad=30)
        self.win = len(self.x_track-1)

        # create car
        self.car_draw = Car(self.simulator.get_center(), center=(1.36, 1.8))
        
        # create the track
        self.track = Track((self.LENGTH, self.WIDTH), self.SCALE, self.RENDER)

        # create line sensor
        self.line_sensor = LineSensor((self.car_draw.get_center()[0], self.car_draw.get_center()[1]))

        # create future points
        self.future_points = FuturePoints(self.car_draw.get_center(), size=self.track_length*1.5*self.SCALE)

        # create minimap
        minimap_position = (0.9 * self.simulator.get_center()[0], 1.75 * self.simulator.get_center()[1])
        self.minimap = MiniMap(minimap_position, (200, 150))
        for k in range(0, len(self.x_track), self.SCALE // 10):
            self.minimap.add_point((2 * self.x_track[k] / self.LENGTH, 2 * self.y_track[k] / self.WIDTH))

        # set track properties
        self.track.set_coordinates(((self.x_track[0] + self.LENGTH//2) * self.SCALE, (self.y_track[0] + self.WIDTH//2) * self.SCALE))
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

        # add objects to the simulator
        # the order of the objects is the layer order
        self.simulator.add(self.track)
        self.simulator.add(self.car_draw)
        self.simulator.add(self.line_sensor)
        self.simulator.add(self.minimap)
        self.simulator.add(self.fps_display)
        self.simulator.add(self.coordinates_display)
        self.simulator.add(self.compass)
        self.simulator.add(self.future_points)
        self.simulator.add(self.track_percentage)
        self.simulator.add(self.points)
        self.simulator.add(self.display)

        # configurate the cluster
        self.configurate_cluster()

        # print the initialization message
        print("Simulator initialized")

        self.simulator.start()

    def _setup_display_graphs(self):
        self.display.add_graph("wheels")
        self.display.add_line_to_graph("wheels", "left", color=(0, 200, 0))
        self.display.add_line_to_graph("wheels", "right", color=(200, 0, 0))

        self.display.add_graph("car")
        self.display.add_line_to_graph("car", "vm", color=(0, 0, 200))
        self.display.add_line_to_graph("car", "ω", color=(200, 200, 0))

        self.display.add_graph("control")
        self.display.add_line_to_graph("control", "v1", color=(0, 200, 0))
        self.display.add_line_to_graph("control", "v2", color=(200, 0, 0))

    def _update_graps(self):
        """
        update the graphs with the given values.
        """
        self.display.update_graph_data("wheels", "left", self.car.getWheels()[0])
        self.display.update_graph_data("wheels", "right", self.car.getWheels()[1])
        self.display.update_graph_data("car", "vm", self.car.speed_norm())
        self.display.update_graph_data("car", "ω", self.car.omega_norm())
        self.display.update_graph_data("control", "v1", self.car.v1)
        self.display.update_graph_data("control", "v2", self.car.v2)

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
        """
        update the points display with the given value.
        """
        self.points.set_text(f"score: {points}")

    def step(self, v1, v2):
        """
        perform one simulation step with given movement and rotation inputs.
        """
        # step the car dynamics
        self.car.step(v1, v2)

        # calculates the car values normalized
        simulator._update_graps()

        # get the car values
        dx, dy, angle = self.car.get_space()

        dx *= -self.SCALE
        dy *= -self.SCALE
        self.track.step(dx, dy, angle)

        # update compass and coordinates
        self.compass.set_angle(-self.track.get_angle() - math.pi / 2)
        self.coordinates_display.set_text(
            f"x: {round(self.track.get_center()[0]/self.SCALE, 2):.2f} y: {round(self.track.get_center()[1]/self.SCALE, 2):.2f}"
        )

        # update minimap position
        self.minimap.set_player_position(
            (2 * self.track.get_center()[0]/(self.SCALE * self.LENGTH) - 1,
             -2 * self.track.get_center()[1]/(self.SCALE * self.WIDTH) + 1)
        )

        # render the simulator
        self.simulator.step()

        # verify if win the game
        if Cluster._next_point == self.win:
            print("Congratulations!")
            print("You win the game, you score is {:.2f}".format(100*100/self.time_simulation))
            return None

        # get the future points
        future_point = Cluster.get_next_point()
        self.future_points.set_points(future_point)
        future_point = [((x - self.car_draw.get_center()[0])/self.SCALE, (-y + self.car_draw.get_center()[1])/self.SCALE) for x, y in future_point]

        # return the sensor value
        line = self.simulator.screen.subsurface((self.line_sensor.get_x() - self.line_sensor.get_size()/2, self.line_sensor.get_y() -1, self.line_sensor.get_size(), 1))
        line_arr = pygame.surfarray.pixels3d(line)
        line_pb = line_arr.mean(axis=2)  # calculate the mediam 
        line_pb = np.array(line_pb[:, 0], dtype=np.uint8)  # remove dimension 
        block_len = int(self.array_sensor_dist * self.SCALE)
        block_count = line_pb.shape[0] // block_len
        final_line = line_pb[:block_count * block_len].reshape(block_count, block_len).mean(axis=1)

        return (1 - final_line/255), future_point, self.car.speed_norm(), self.car.omega_norm()
simulator = None #SimulatorController()
timer = time.time()

def start_simulation(screen_size=MEDIUM, fps=120, length=100, width=100, scale=300, render=5, seed=None, track_type=0, track_length=0.02, sensor_spacing=0.001):
    # define the seed
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    # check if the simulator is initialized
    global simulator
    if simulator is not None:
        print("Simulator already initialized")
        return
    
    simulator = SimulatorController(screen_size, fps, length, width, scale, render, track_type, track_length, sensor_spacing)
    return simulator

def set_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke, accommodation_time, sensor_distance, sensor_count):
    # check if the simulator is initialized
    if simulator is None:
        print("Simulator not initialized")
        return

    simulator.setup_car_dynamics(wheels_radius, wheels_distance, wheels_RPM, ke, 0, accommodation_time, sensor_distance, sensor_count)

def set_future_points(count, space):
    # check if the simulator is initialized
    if simulator is None:
        print("Simulator not initialized")
        return

    simulator.set_future_points(count, space)

def step_simulation(v1, v2):
    global timer

    # check if the simulator is initialized
    if simulator is None or simulator.car is None:
        print("Simulator not initialized")
        return None

    # check for events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            print("Simulation stopped using X button")
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                print("Simulation stopped using ESC")
                return None

    # render the simulator
    data = simulator.step(v1, v2)

    if data is None:
        return None

    # integrate the time simulation
    simulator.time_simulation += 1/simulator.FPS

    # calculate coverage percentage
    coverage = Cluster._next_point/simulator.win * 100
    simulator.update_coverage("{:.2f}%".format(coverage))

    # calculate the points of the track
    simulator.update_points("{:.2f}".format(100*coverage/simulator.time_simulation))

    # fix the fps
    while (time.time() - timer) < 1/simulator.FPS:
        pass

    # update the fps count
    simulator.update_FPS("{:.1f}".format(1/(time.time() - timer)))

    # update the timer
    timer = time.time()

    return data