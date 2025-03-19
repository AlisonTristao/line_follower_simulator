import pygame
import math
import numpy as np

import pygame
import math
import numpy as np

class Shape:
    """
    represents a basic geometric shape with position, color, size, and angle
    """
    def __init__(self, coo, color=None, size=None, angle=0):
        """
        initializes the shape
        args:
            coo (tuple): coordinates of the shape (x, y)
            color (tuple): color of the shape in rgb format
            size (int): size of the shape
            angle (float): initial angle in radians
        """
        self._x = coo[0]
        self._y = coo[1]
        self._angle = angle
        self._color = color
        self._size = size
        self._pivot = (0, 0)

    def get_center(self):
        # returns the center coordinates of the shape
        return self._x, self._y

    def get_angle(self):
        # returns the current angle of the shape
        return self._angle

    def set_angle(self, angle):
        # sets a new angle for the shape
        self._angle = angle

    def set_coordinates(self, coo):
        # sets new coordinates for the shape
        self._x, self._y = coo

    def set_color(self, color):
        # sets a new color for the shape
        self._color = color

    def set_pivot(self, pivot):
        # sets the pivot point for rotations
        self._pivot = pivot

    def get_pivot(self):
        # returns the pivot point for rotations
        return self._pivot

    def step(self, dx, dy, angle):
        # moves and rotates the shape
        self._rotate(angle)
        self._move(dx, dy)

    def _rotate(self, angle):
        # rotates the shape by the given angle
        self._angle += angle

    def _move(self, dx, dy):
        # moves the shape by dx and dy considering rotation
        s = dx * math.cos(-self._angle) - dy * math.sin(-self._angle)
        dy = dx * math.sin(-self._angle) + dy * math.cos(-self._angle)
        dx = s
        self._x += dx
        self._y += dy

    def rotate_around_origin(self, theta):
        # rotates the shape around the origin by theta radians
        x_new = self._x * math.cos(theta) - self._y * math.sin(theta)
        y_new = self._x * math.sin(theta) + self._y * math.cos(theta)
        self._x, self._y = x_new, y_new

    def rotate_around_pivot(self, pivot, theta):
        # rotates the shape around a given pivot point by theta radians
        ox, oy = pivot
        translated_x = self._x - ox
        translated_y = self._y - oy
        rotated_x = translated_x * math.cos(theta) - translated_y * math.sin(theta)
        rotated_y = translated_x * math.sin(theta) + translated_y * math.cos(theta)
        self._x = rotated_x + ox
        self._y = rotated_y + oy

    def draw(self, surface):
        # raises an error because it must be implemented by subclasses
        raise NotImplementedError("this method should be implemented by subclasses.")

class Car(Shape):
    """
    represents the car in the simulator
    """
    def __init__(self, coo, color=(255, 0, 0), size=35, angle=30, center=(1, 2)):
        """
        initializes the car
        args:
            coo (tuple): initial coordinates of the car
            color (tuple): color of the car in rgb format
            size (int): size of the car
            angle (float): initial angle in degrees
            center (tuple): center position multiplier for car positioning
        """
        super().__init__(coo, color, size, angle)
        self._x = center[0] * coo[0] + math.cos(math.radians(angle))
        self._y = center[1] * coo[1]
        self._vertices = []
        self._calculate_vertices()

    def _calculate_vertices(self):
        # calculates the vertices of the car for rendering
        angle_rad = math.radians(self._angle)
        half_size = self._size
        self._vertices = [
            (self._x + half_size * math.cos(angle_rad), self._y + half_size * math.sin(angle_rad)),
            (self._x + half_size * math.cos(angle_rad - 2.094), self._y + half_size * math.sin(angle_rad - 2.094)),
            (self._x + half_size * math.cos(angle_rad + 2.094), self._y + half_size * math.sin(angle_rad + 2.094)),
        ]

    def draw(self, surface):
        # draws the car as a polygon on the given surface
        pygame.draw.polygon(surface, self._color, self._vertices)

    def step(self, dx, dy, angle):
        """
        updates the car's position and rotation
        args:
            dx (float): change in x direction
            dy (float): change in y direction
            angle (float): change in angle in radians
        """
        super().step(dx, dy, angle)
        self._calculate_vertices()

class Default(Shape):
    """
    represents a default object on the track
    """
    def __init__(self, coo=(0, 0, 0), color=(50, 50, 50), size=2):
        """
        initializes a default object
        args:
            coo (tuple): coordinates of the object
            color (tuple): color of the object in rgb format
            size (int): size of the object
        """
        super().__init__(coo, color, size)

    def draw(self, surface):
        # draws the default object as a circle on the given surface
        pygame.draw.circle(surface, self._color, (int(self._x), int(self._y)), self._size)
        #pass

class Wall(Shape):
    """
    represents a wall on the track
    """
    def __init__(self, coo=(0, 0, 0), color=(100, 100, 100), size=70):
        """
        initializes a wall object
        args:
            coo (tuple): coordinates of the wall
            color (tuple): color of the wall in rgb format
            size (int): size of the wall
        """
        super().__init__(coo, color, size)

    def draw(self, surface):
        # draws the wall as a rotated rectangle on the given surface
        temp_surface = pygame.Surface((self._size, self._size), pygame.SRCALPHA)
        temp_surface.fill(self._color)
        rotated_surface = pygame.transform.rotate(temp_surface, math.degrees(self._angle))
        rotated_rect = rotated_surface.get_rect(center=(int(self._x), int(self._y)))
        surface.blit(rotated_surface, rotated_rect)

class Cluster(Shape):
    """
    Represents a cluster of points on the track
    """
    def __init__(self, coo=(0, 0), color=(0, 0, 0), size=5, angle=0):
        """
        initializes the cluster object
        args:
            coo (tuple): coordinates of the cluster
            color (tuple): color of the cluster in rgb format
            size (int): size of the cluster
            angle (float): initial angle of the cluster in radians
        """
        super().__init__(coo, color, size, angle)
        self.__points_arr = [] 

    def add_point(self, point):
        self.__points_arr.append(point)

    def draw(self, surface):
        """
        draws the cluster on the given surface
        args:
            surface (pygame.Surface): the surface to draw on
        """
        for point in self.__points_arr:
            point_ = self._rotate_point(point)
            pygame.draw.circle(surface, self._color, (point_[0] + self._x, point_[1] + self._y), self._size)

    def _rotate_point(self, coo):
        # rotates a point around the origin
        rotated_x = coo[0] * math.cos(-self._angle) - coo[1] * math.sin(-self._angle)
        rotated_y = coo[0] * math.sin(-self._angle) + coo[1] * math.cos(-self._angle)
        return rotated_x, rotated_y
    
    def get_points(self):
        return self.__points_arr

class MiniMap(Shape):
    """
    Represents a minimap object on the simulator
    """
    def __init__(self, coo, size, color=(255, 255, 255)):
        """
        Initializes the minimap object.
        Args:
            coo (tuple): Coordinates of the minimap.
            size (tuple): Size of the minimap.
            color (tuple): Color of the minimap in RGB format.
        """
        super().__init__(coo, color, size)
        self._width, self._height = size
        self._points = []  # Lista de pontos no formato [(x, y)]
        self._player = (0, 0)

    def add_point(self, point):
        self._points.append(point)

    def set_player_position(self, player):
        self._player = player

    def draw(self, surface):
        # coordinates and dimensions of the minimap rectangle
        rect_x = self._x - self._width // 2
        rect_y = self._y - self._height // 2
        rect_width = self._width
        rect_height = self._height

        border_color = (100, 100, 100)
        border_width = 1

        # draw border
        #pygame.draw.rect(surface, border_color,
        #                 (rect_x, rect_y, rect_width, rect_height), border_width)

        # draw background
        pygame.draw.rect(surface, self._color,
                         (rect_x + border_width, rect_y + border_width,
                          rect_width - 2 * border_width, rect_height - 2 * border_width))


        # draw track
        point_color = (0, 0, 0)
        for px, py in self._points:
            # normalize the point coordinates
            x = int(self._x + px * (self._width // 2))
            y = int(self._y + py * (self._height // 2))
            pygame.draw.circle(surface, point_color, (x, y), 1)

        # draw player position
        player_color = (200, 0, 0)
        x = int(self._x + self._player[0] * (self._width // 2))
        y = int(self._y - self._player[1] * (self._height // 2))

        pygame.draw.circle(surface, player_color, (x, y), 5)

class Track(Shape):
    """
    represents the track of the simulator with a matrix of points and walls
    """
    def __init__(self, size, point_spacing, visible, screen_size=(800, 600)):
        """
        initializes the track
        args:
            size (tuple): size of the track grid (rows, columns)
            point_spacing (int): spacing between points in the grid
            visible (int): radius of visibility for the track points
            screen_size (tuple): dimensions of the screen
        """
        super().__init__(coo=(size[0] * point_spacing // 1.1, size[1] * point_spacing // 2), size=size, angle=0)
        self.screen_size = screen_size
        self.__visible = visible
        self.__point_spacing = point_spacing
        self._center = (0, 0) #(self.screen_size[0] // 1.5, self.screen_size[1] // 2)

        # initializes the matrix of points and walls
        self.wall = Wall()
        self.default = Default()
        self.matrix = self._create_matrix(size)

    def _create_matrix(self, size):
        # creates the initial matrix of track objects
        matrix = []
        for i in range(size[0]):
            row = []
            for j in range(size[1]):
                row.append(self.wall if i in (0, size[0] - 1) or j in (0, size[1] - 1) else self.default)
            matrix.append(row)
        return matrix

    def set_obj(self, row, col, obj):
        # sets a specific object in the matrix at the given row and column
        if 0 <= row < self._size[0] and 0 <= col < self._size[1]:
            self.matrix[row][col] = obj

    def set_center(self, coo):
        # sets the center of the track
        self._center = coo

    def draw(self, surface):
        """
        draws the track on the given surface
        args:
            surface (pygame.Surface): the surface to draw on
        """
        x0_col, y0_row = int(self._x // self.__point_spacing), int(self._y // self.__point_spacing)
        d = (self._center[0] - self._x, self._center[1] - self._y)
        points = self.__points_in_circle(x0_col, y0_row)

        for i, j in points:
            x = i * self.__point_spacing + d[0]
            y = j * self.__point_spacing + d[1]
            x, y = self._rotate_point((x, y))

            self.matrix[i][j].set_coordinates((x, y))
            self.matrix[i][j].set_angle(-self._angle)
            self.matrix[i][j].draw(surface)

    def __points_in_circle(self, x0, y0):
        # returns the points within a circle of visibility
        rows, cols = self._size
        x, y = np.ogrid[:rows, :cols]
        dist_sq = (x - x0) ** 2 + (y - y0) ** 2
        return np.argwhere(dist_sq <= self.__visible ** 2)

    def _rotate_point(self, coo):
        # rotates a point around the track's pivot
        ox, oy = self._pivot
        translated_x = coo[0] - ox
        translated_y = coo[1] - oy
        rotated_x = translated_x * math.cos(self._angle) - translated_y * math.sin(self._angle)
        rotated_y = translated_x * math.sin(self._angle) + translated_y * math.cos(self._angle)
        return rotated_x + ox, rotated_y + oy

class Display(Shape):
    """
    represents a display for the simulator with graphs and text
    """
    __len_data = 100
    __saturation = 100

    # initializes the display
    def __init__(self, coo=(0, 0), size=(10, 10), color=(75, 75, 75), horizontal_div=3, vertical_div=1.1):
        """
        initializes the display
        args:
            coo (tuple): coordinates of the display
            size (tuple): size of the display
            color (tuple): color of the display in rgb format
            horizontal_div (int): number of horizontal divisions
            vertical_div (int): number of vertical divisions
        """
        self.font = pygame.font.SysFont("courier", 15, bold=True)

        # limits of y axis
        self.__max_value = self.__saturation
        self.__min_value = -self.__saturation

        # center and deslocation of display
        middle = (size[0] // horizontal_div, int(size[1] // (2*vertical_div)))
        offset = 40
        
        coo = (coo[0] - (middle[0]//2 * horizontal_div) + offset, coo[1] - middle[1])
        super().__init__(coo, color, (size[0] // (horizontal_div), int(size[1] // (vertical_div))))

        self.__graph_data = {}
        self.__graph_colors = {}

    # define time of the x axis
    def set_time(self, fps):
        self.__len_data = int(fps)

    # adds a new graph with a specific line name
    def add_graph(self, graph_name):
        if graph_name not in self.__graph_data:
            self.__graph_data[graph_name] = {}
            self.__graph_colors[graph_name] = {}

    # removes a graph from the display
    def remove_graph(self, graph_name):
        if graph_name in self.__graph_data:
            del self.__graph_data[graph_name]
            del self.__graph_colors[graph_name]

    # adds a new line to an existing graph
    def add_line_to_graph(self, graph_name, line_name, color=(0, 200, 0)):
        if graph_name in self.__graph_data:
            self.__graph_data[graph_name][line_name] = [0 for _ in range(self.__len_data)]
            self.__graph_colors[graph_name][line_name] = color

    # updates the data for a specific line in a graph
    def update_graph_data(self, graph_name, line_name, new_value):
        if graph_name in self.__graph_data and line_name in self.__graph_data[graph_name]:
            self.__graph_data[graph_name][line_name].append(new_value)
            if len(self.__graph_data[graph_name][line_name]) > self.__len_data:
                self.__graph_data[graph_name][line_name].pop(0)

    # draws the display as a rectangle with rounded corners, including graphs and text
    def draw(self, surface):
        # draw the display rectangle with rounded corners
        rect = pygame.Rect(self._x, self._y, self._size[0], self._size[1])
        pygame.draw.rect(surface, self._color, rect, border_radius=15)

        # calculate the sections for graphs
        graph_height = self._size[1] // len(self.__graph_data) if self.__graph_data else self._size[1]

        # draw each graph
        for idx, (graph_name, lines) in enumerate(self.__graph_data.items()):
            self.draw_graph(
                surface,
                lines,
                (
                    self._x + 15,
                    self._y + idx * graph_height + 15,
                    self._size[0] - 30,
                    graph_height - 30
                ),
                graph_name
            )

    # draw grid lines
    def __draw_grid(self, surface, graph_width, graph_height, graph_x, graph_y):
        grid_color = (200, 200, 200)
        for i in range(15, graph_width -15, max(1, graph_width // 10)):
            pygame.draw.line(surface, grid_color, (graph_x + i, graph_y), (graph_x + i, graph_y + graph_height))
        for i in range(15, graph_height -15, max(1, graph_height // 5)):
            pygame.draw.line(surface, grid_color, (graph_x, graph_y + i), (graph_x + graph_width, graph_y + i))

    # draw axis values
    def __draw_axis_values(self, surface, graph_height, graph_x, graph_y):
        num_divisions = 5
        for i in range(num_divisions + 1):
            value = self.__max_value - (i * (self.__max_value - self.__min_value) // num_divisions)
            y_pos = graph_y + ((i+0.35) * graph_height // (1.1*num_divisions))
            label = self.font.render(str(value), True, (0, 0, 0))
            surface.blit(label, (graph_x - 45, y_pos - 10))

    # draw title 
    def __draw_title(self, surface, title, graph_width, graph_x, graph_y):
        font = pygame.font.Font(None, 20)
        title_label = font.render(title, True, (0, 0, 0))
        offset = len(title) * 2
        surface.blit(title_label, (graph_x + graph_width // 2 - offset, graph_y + 10))

    # draw each line in the graph
    def __draw_graph_separate(self, surface, lines, title, graph_width, graph_height, graph_x, graph_y):
        for line_name, data in lines.items():
            normalized_data = [
                graph_height - (graph_height * (value - self.__min_value) / (self.__max_value - self.__min_value))
                for value in data
            ]
            step_width = graph_width / len(data)
            color = self.__graph_colors[title][line_name]

            for i in range(len(normalized_data) - 1):
                x1 = graph_x + i * step_width
                y1 = graph_y + normalized_data[i]
                x2 = graph_x + (i + 1) * step_width
                # draw the horizontal step
                pygame.draw.line(surface, color, (x1, y1), (x2, y1), 2)
                # draw the vertical connection to the next step
                pygame.draw.line(surface, color, (x2, y1), (x2, graph_y + normalized_data[i + 1]), 2)

    # draw legend
    def __draw_legend(self, surface, graph_x, graph_y, title):
        legend_x = graph_x + 10
        legend_y = graph_y + 15
        for idx, (line_name, color) in enumerate(self.__graph_colors[title].items()):
            pygame.draw.rect(surface, color, (legend_x, legend_y + idx * 20, 10, 10))
            legend_label = self.font.render(line_name, True, (0, 0, 0))
            surface.blit(legend_label, (legend_x + 15, legend_y + idx * 20 - 5))

    # helper function to draw a graph with multiple lines
    def draw_graph(self, surface, lines, rect, title):
        """
        draw a graph with multiple lines on the given surface
        """
        graph_width, graph_height = int(rect[2]), int(rect[3])
        graph_x, graph_y = int(rect[0]), int(rect[1])

        # draw white background for the graph
        pygame.draw.rect(surface, (255, 255, 255), (graph_x, graph_y, graph_width, graph_height), border_radius=10)

        # draw grid lines
        self.__draw_grid(surface, graph_width, graph_height, graph_x, graph_y)

        # draw axes values
        self.__draw_axis_values(surface, graph_height, graph_x, graph_y)

        # draw title
        self.__draw_title(surface, title, graph_width, graph_x, graph_y)

        # draw each line in the graph
        self.__draw_graph_separate(surface, lines, title, graph_width, graph_height, graph_x, graph_y)

        # draw legend
        self.__draw_legend(surface, graph_x, graph_y, title)

class Statistics(Shape):
    """
    represents statistical text information displayed on the simulator
    """
    def __init__(self, coo=(800, 600), color=(0, 200, 0), size=100, angle=0):
        """
        initializes the statistics display
        args:
            coo (tuple): coordinates of the statistics text
            color (tuple): color of the text in rgb format
            size (int): size of the text object (unused here but inherited)
            angle (float): rotation angle of the text (unused here but inherited)
        """
        super().__init__(coo, color, size, angle)
        self.text = "_____"
        self.font = pygame.font.Font(None, 24)
        self._offset = 1
        self.font = pygame.font.SysFont("courier", 15, bold=True)

    def set_offset(self, offset):
        # sets the offset for the text
        self._offset = offset 

    def set_text(self, text):
        # updates the text to be displayed
        self.text = text

    def draw(self, surface):
        """
        draws the text on the given surface
        args:
            surface (pygame.Surface): the surface to draw on
        """
        text_surface = self.font.render(self.text, True, self._color)
        x = self._x - text_surface.get_width() // self._offset
        surface.blit(text_surface, (x, self._y))

class Compass(Shape):
    """
    represents a compass object on the simulator
    """
    def __init__(self, coo, color=(0, 0, 0), size=40, angle=0):
        """
        initializes the compass object
        args:
            coo (tuple): coordinates of the compass object
            color (tuple): color of the compass in rgb format
            size (int): size of the compass object
            angle (float): initial angle of the compass in radians
        """
        #coo = (coo[0] - 2 * size, coo[1] - 2 * size)
        super().__init__(coo, color, size, angle)

    def draw(self, surface):
        # Draw the outer circle
        pygame.draw.circle(surface, self._color, (self._x, self._y), self._size, 2)

        # Points for the star
        star_points = []
        num_points = 8  # 4 major (N, E, S, W) and 4 minor (NE, SE, SW, NW)
        for i in range(num_points):
            angle = self._angle + (math.pi / 4) * i
            radius = self._size if i % 2 == 0 else self._size * 0.4
            x = self._x + radius * math.cos(angle)
            y = self._y + radius * math.sin(angle)
            star_points.append((x, y))

        # Draw the star
        pygame.draw.polygon(surface, self._color, star_points, 2)

        # Draw cardinal direction labels
        directions = {
            "N": (0, -1),
            "E": (1, 0),
            "S": (0, 1),
            "W": (-1, 0),
        }

        font = pygame.font.Font(None, 24)
        for direction, (dx, dy) in directions.items():
            end_x = self._x + dx * self._size * 1.3
            end_y = self._y + dy * self._size * 1.3
            color = self._color
            if direction in ["N"]:
                color = (200, 0, 0)
            text_surface = font.render(direction, True, color)
            text_rect = text_surface.get_rect(center=(end_x, end_y))
            surface.blit(text_surface, text_rect)

        # Draw a line indicating the current angle
        pointer_x = self._x + self._size * math.cos(self._angle)
        pointer_y = self._y + self._size * math.sin(self._angle)
        pygame.draw.line(surface, (255, 0, 0), (self._x, self._y), (pointer_x, pointer_y), 3)

class LineSensor(Shape):
    """
    represents a line sensor object on the simulator
    """
    def __init__(self, coo, color=(150, 150, 150), size=80, angle=0):
        """
        initializes the line sensor object
        args:
            coo (tuple): coordinates of the line sensor object
            color (tuple): color of the line sensor in rgb format
            size (int): size of the line sensor object
            angle (float): initial angle of the line sensor in radians
        """
        super().__init__(coo, color, size, angle)

    def draw(self, surface):
        # Draw the line sensor as a line
        end_x = self._x + self._size/2
        end_y = self._y
        begin_x = self._x - self._size/2
        begin_y = self._y
        pygame.draw.line(surface, self._color, (begin_x, begin_y), (end_x, end_y), 2)

    def get_y(self):
        # returns the y coordinate of the line sensor
        return self._y
    
    def get_x(self):
        # returns the x coordinate of the line sensor
        return self._x
    
    def get_size(self):
        # returns the size of the line sensor
        return self._size

class Simulator:
    """
    represents the simulator environment for the line follower
    """
    def __init__(self, win='FULL', FPS=160):
        """
        initializes the simulator environment
        args:
            win (str): window size mode ('FULL', 'MEDIUM', 'SMALL')
            FPS (int): frames per second for the simulator
        """
        pygame.init()

        # set the window size based on mode
        if win == 'FULL':
            info = pygame.display.Info()
            width = info.current_w
            height = info.current_h
            self.screen = pygame.display.set_mode((width, height),  pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
        elif win == 'MEDIUM':
            width = 1400
            height = 800
            self.screen = pygame.display.set_mode((width, height))
        elif win == 'SMALL':
            width = 800
            height = 600
            self.screen = pygame.display.set_mode((width, height))

        pygame.display.set_caption("SIMULATOR")
        self.__clock = pygame.time.Clock()

        self.__width = width
        self.__height = height
        self.__FPS = FPS
        self.__objects = []

    def set_FPS(self, FPS):
        # sets the frames per second for the simulator
        self.__FPS = FPS

    def get_FPS(self):
        # returns the current frames per second
        return self.__FPS

    def get_window_size(self):
        # returns the size of the simulator window
        return self.__width, self.__height

    def get_center(self):
        # returns the center coordinates of the simulator window
        return self.__width // 2, self.__height // 2

    def add(self, obj):
        # adds an object to the simulator environment
        self.__objects.append(obj)

    def remove(self, obj):
        # removes an object from the simulator environment
        self.__objects.remove(obj)

    def __verify_objects(self):
        # verifies if there are objects to update or draw
        return len(self.__objects) > 0

    def draw(self):
        # draws all objects on the simulator screen
        if not self.__verify_objects():
            return
        self.screen.fill((255, 255, 255))  # background color
        for obj in self.__objects:
            obj.draw(self.screen)

    def step(self):
        """
        performs a simulation step by updating and rendering objects
        """
        self.draw()
        pygame.display.flip()
        self.__clock.tick(self.__FPS)
