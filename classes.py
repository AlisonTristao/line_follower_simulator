import pygame
import math
import numpy as np

class Shape:
    # initializes shape with coordinates, color, size, and angle
    def __init__(self, coo, color=None, size=None, angle=0):
        self._x     = coo[0]
        self._y     = coo[1]
        self._angle = angle
        self._color = color
        self._size  = size
        self._pivot = (0, 0)

    # returns the center coordinates
    def get_center(self):
        return self._x, self._y

    # rotates the shape by a given angle
    def __rotate(self, angle):
        self._angle += angle

    # sets the pivot point for rotations
    def set_pivot(self, pivot):
        self._pivot = pivot

    # moves the shape by dx and dy, considering rotation
    def __move(self, dx, dy):
        s = dx * math.cos(-self._angle) - dy * math.sin(-self._angle)
        dy = dx * math.sin(-self._angle) + dy * math.cos(-self._angle)
        dx = s
        self._x += dx
        self._y += dy

    # moves and rotates the shape
    def step(self, dx, dy, angle):
        self.__rotate(angle)
        self.__move(dx, dy)

    # sets the coordinates of the shape
    def set_coordinates(self, coo):
        self._x, self._y = coo

    # sets the angle of the shape
    def set_angle(self, angle):
        self._angle = angle

    # rotates the shape around the origin
    def rotate_around_origin(self, theta):
        x_new = self._x * math.cos(theta) - self._y * math.sin(theta)
        y_new = self._x * math.sin(theta) + self._y * math.cos(theta)
        self._x, self._y = x_new, y_new

    # rotates the shape around a pivot point
    def rotate_around_pivot(self, pivot, theta):
        ox, oy = pivot
        translated_x = self._x - ox
        translated_y = self._y - oy

        rotated_x = translated_x * math.cos(theta) - translated_y * math.sin(theta)
        rotated_y = translated_x * math.sin(theta) + translated_y * math.cos(theta)

        self._x = rotated_x + ox
        self._y = rotated_y + oy

    # draws the shape on a surface (to be implemented by subclasses)
    def draw(self, surface):
        raise NotImplementedError("This method should be implemented by subclasses.")

class Car(Shape):
    # initializes the car with coordinates, color, size, and angle
    def __init__(self, coo, color=(255, 0, 0), size=30, angle=30, center=(1, 2)):
        super().__init__(coo, color, size, angle)
        self._x = center[0] * coo[0] + math.cos(math.sin(angle))
        self._y = center[1] * coo[1]
        self.get_vertices()

    # calculates the vertices of the car
    def get_vertices(self):
        angle_rad = math.radians(self._angle)
        half_size = self._size
        vertices = [
            (self._x + half_size * math.cos(angle_rad), self._y + half_size * math.sin(angle_rad)),
            (self._x + half_size * math.cos(angle_rad - 2.094), self._y + half_size * math.sin(angle_rad - 2.094)),
            (self._x + half_size * math.cos(angle_rad + 2.094), self._y + half_size * math.sin(angle_rad + 2.094)),
        ]
        self._vertices = vertices

    # draws the car on a surface
    def draw(self, surface):
        pygame.draw.polygon(surface, self._color, self._vertices)

class Default(Shape):
    # initializes a default shape
    def __init__(self, coo=(0, 0, 0), color=(50, 50, 50), size=2):
        super().__init__(coo, color, size)

    # draws a default shape as a circle
    def draw(self, surface):
        pygame.draw.circle(surface, self._color, (self._x, self._y), self._size)

class Wall(Shape):
    # initializes a wall
    def __init__(self, coo=(0, 0, 0), color=(100, 100, 100), size=70):
        super().__init__(coo, color, size)

    # draws the wall as a rotated rectangle
    def draw(self, surface):
        temp_surface = pygame.Surface((self._size, self._size), pygame.SRCALPHA)
        temp_surface.fill(self._color)
        rotated_surface = pygame.transform.rotate(temp_surface, math.degrees(self._angle))
        rotated_rect = rotated_surface.get_rect(center=(self._x, self._y))
        surface.blit(rotated_surface, rotated_rect)

class Track(Shape):
    # initializes the track with size, point spacing, visibility, and screen size
    def __init__(self, size, point_spacing, visible, screen_size=(800, 600)):
        super().__init__(coo=(size[0] * point_spacing // 2, size[1] * point_spacing // 2), size=size, angle=0)
        self.__screen_size = screen_size
        self.__visible = visible
        self.__point_spacing = point_spacing
        self._center = (self.__screen_size[0] // 2, self.__screen_size[1] // 2)

        # create the matrix of points and walls
        self.wall = Wall()
        self.default = Default()

        self.matrix = []
        for i in range(size[0]):
            linha = []
            for j in range(size[1]):
                if i == 0 or i == size[0] - 1 or j == 0 or j == size[1] - 1:
                    linha.append(self.wall)
                else:
                    linha.append(self.default)
            self.matrix.append(linha)

    # sets a point in the track to a specific type
    def set_obj(self, row, col, obj_type):
        if 0 <= row < self._size[0] and 0 <= col < self._size[1]:
            self.matrix[row][col] = obj_type

    # sets the center of the track
    def set_center(self, coo):
        self._center = coo

    # draws the track on the surface
    def draw(self, surface):
        # get the indexes of the points in the matrix
        x0_col, y0_row = int(self._x // self.__point_spacing), int(self._y // self.__point_spacing)

        # calculate the distance from the center of screen
        d = (self._center[0] - self._x, self._center[1] - self._y)

        # get all lines and columns in the visible range
        points = self.__points_in_circle(x0_col, y0_row)

        # draw the points
        for i, j in points:

            # calculate the coordinates of the points
            x = i * self.__point_spacing + d[0]
            y = j * self.__point_spacing + d[1]

            # rotate the points around the pivot
            x, y = self.__rotate_point((x, y))

            # draw the points 
            self.matrix[i][j].set_coordinates((x, y))
            self.matrix[i][j].set_angle(-self._angle)
            self.matrix[i][j].draw(surface)

    # returns the points within a circle
    def __points_in_circle(self, x0, y0):
        rows, cols = self._size
        x, y = np.ogrid[:rows, :cols]
        dist_sq = (x - x0) ** 2 + (y - y0) ** 2
        return np.argwhere(dist_sq <= self.__visible ** 2)

    # rotates a point around a pivot
    def __rotate_point(self, coo):
        ox, oy = self._pivot
        translated_x = coo[0] - ox
        translated_y = coo[1] - oy
        rotated_x = translated_x * math.cos(self._angle) - translated_y * math.sin(self._angle)
        rotated_y = translated_x * math.sin(self._angle) + translated_y * math.cos(self._angle)
        return rotated_x + ox, rotated_y + oy

class Display(Shape):
    __len_data = 100
    __saturation = 100

    # initializes the display
    def __init__(self, coo=(0, 0), size=(10, 10), color=(75, 75, 75), horizontal_div=6, vertical_div=2.2):
        self.__max_value = self.__saturation
        self.__min_value = -self.__saturation
        middle = (size[0] // horizontal_div, int(size[1] // vertical_div))
        offset = (size[1] - 2 * middle[1]) / 2
        coo = (coo[0] - middle[0] - size[0] // (horizontal_div / 2) + offset, coo[1] - middle[1])
        super().__init__(coo, color, (size[0] // (horizontal_div / 2), int(size[1] // (vertical_div / 2))))

        self.__graph_data = {}
        self.__graph_colors = {}

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
        font = pygame.font.Font(None, 20)
        num_divisions = 5
        for i in range(num_divisions + 1):
            value = self.__max_value - (i * (self.__max_value - self.__min_value) // num_divisions)
            y_pos = graph_y + (i * graph_height // num_divisions)
            label = font.render(str(value), True, (0, 0, 0))
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
        font = pygame.font.Font(None, 20)
        for idx, (line_name, color) in enumerate(self.__graph_colors[title].items()):
            pygame.draw.rect(surface, color, (legend_x, legend_y + idx * 20, 10, 10))
            legend_label = font.render(line_name, True, (0, 0, 0))
            surface.blit(legend_label, (legend_x + 15, legend_y + idx * 20 - 5))

    # helper function to draw a graph with multiple lines
    def draw_graph(self, surface, lines, rect, title):
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
    def __init__(self, screen=(800, 600), color=(0, 200, 0), size=10, angle=0):
        self.text = "FPS: ___ "
        coo = (screen[0] - len(self.text)//2, screen[1] - 0.95*screen[1])
        super().__init__(coo, color, size, angle)
        self.font = pygame.font.Font(None, 36)  # Initialize the font once

    def set_text(self, text):
        self.text = text
        self._x = self._x

    def draw(self, surface):
        text_surface = self.font.render(self.text, True, self._color)
        surface.blit(text_surface, (self._x, self._y))


class Simulator:
    __background = (255, 255, 255)

    # initializes the simulator
    def __init__(self, width=800, height=600):
        pygame.init()
        self.__width    = width
        self.__height   = height
        self.__screen   = pygame.display.set_mode((self.__width, self.__height))
        self.__clock    = pygame.time.Clock()
        self.__running  = True
        self.__FPS      = 60
        self.__objects  = []

    # set and get FPS
    def set_FPS(self, FPS):
        self.__FPS = FPS
    
    def get_FPS(self):
        return self.__FPS

    # returns the window size
    def get_window_size(self):
        return self.__width, self.__height

    # returns the center of the window
    def get_center(self):
        return self.__width // 2, self.__height // 2

    # checks if the simulator is running
    def is_running(self):
        return self.__running

    # stops the simulator
    def stop_running(self):
        self.__running = False

    # adds an object to the simulator
    def add(self, obj):
        self.__objects.append(obj)

    # removes an object from the simulator
    def remove(self, obj):
        self.__objects.remove(obj)

    # verifies if there are objects to update or draw
    def __verify_objects(self):
        return len(self.__objects) > 0

    # draws all objects on the screen
    def draw(self):
        if not self.__verify_objects():
            return
        self.__screen.fill(self.__background)
        for obj in self.__objects:
            obj.draw(self.__screen)

    # performs a simulation step
    def step(self):
        self.draw()
        pygame.display.flip()
        self.__clock.tick(self.__FPS)
