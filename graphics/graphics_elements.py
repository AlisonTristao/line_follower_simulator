import pygame
import math
import numpy as np

FULL = 'FULL'
MEDIUM = 'MEDIUM'
SMALL = 'SMALL'

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
        self._color = color
        self._size = size
        self._pivot = (0, 0)
        self.set_angle(angle)

    def get_center(self):
        # returns the center coordinates of the shape
        return self._x, self._y

    def get_angle(self):
        # returns the current angle of the shape
        return self._angle

    def set_angle(self, angle):
        # sets a new angle for the shape and updates the 2D rotation matrix
        self._angle = angle
        cos_theta = math.cos(angle)
        sin_theta = math.sin(angle)
        self._rotation_matrix = [
            [cos_theta, -sin_theta],
            [sin_theta, cos_theta]
        ]

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

    def set_size(self, size):
        # sets a new size for the shape
        self._size = size

    def get_size(self):
        # returns the size of the shape
        return self._size

    def step(self, dx, dy, angle):
        # moves and rotates the shape
        self._rotate(angle)
        self._move(dx, dy)

    def _rotate(self, angle):
        # rotates the shape by the given angle
        self.set_angle(self._angle + angle)

    def _move(self, dx, dy):
        # moves the shape by dx and dy considering rotation
        c, s = math.cos(-self._angle), math.sin(-self._angle)
        self._x += dx * c - dy * s
        self._y += dx * s + dy * c

    def rotate_around_origin(self, theta):
        # rotates the shape around the origin by theta radians
        x_new = self._x * math.cos(theta) - self._y * math.sin(theta)
        y_new = self._x * math.sin(theta) + self._y * math.cos(theta)
        self._x, self._y = x_new, y_new

    def _rotate_point(self, coo):
        R = self._rotation_matrix
        return coo[0] * R[0][0] + coo[1] * R[0][1], coo[0] * R[1][0] + coo[1] * R[1][1]

    def rotate_around_pivot(self, coo):
        # rotates a point around the track's pivot
        ox, oy = self._pivot
        x, y = self._rotate_point((coo[0] - ox, coo[1] - oy))
        return x + ox, y + oy

    def draw(self, surface):
        # raises an error because it must be implemented by subclasses
        raise NotImplementedError("this method should be implemented by subclasses.")

    def update(self):
        pass

class Car(Shape):
    """
    represents the car in the simulator
    """
    def __init__(self, coo, color=(0, 0, 200), size=35, angle=30, center=(1, 2)):
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

    def set_size(self, size):
        # sets a new size for the car
        self._size = size
        self._calculate_vertices()

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

class FuturePoints(Shape):
    """
    represents a set of points drawn in screen coordinates (reference / predicted path)
    """
    def __init__(self, coo, color=(200, 0, 0), size=5, angle=0):
        """
        initializes the future points
        args:
            coo (tuple): initial coordinates of the future points
            color (tuple): color of the future points in rgb format
            size (int): size of the future points
            angle (float): initial angle in radians
        """
        super().__init__(coo, color, size, angle)
        self._points = []

    def set_points(self, points):
        # sets the future points to be drawn (iterable of (x, y) in pixels)
        self._points = np.asarray(points, dtype=float).tolist()

    def draw(self, surface):
        # draws the future points as circles on the given surface
        circle = pygame.draw.circle
        for point in self._points:
            circle(surface, self._color, point, self._size)

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
        self._base_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        self._base_surface.fill(color)

    def draw(self, surface):
        # draws the wall as a rotated rectangle on the given surface
        rotated_surface = pygame.transform.rotate(self._base_surface, math.degrees(self._angle))
        rotated_rect = rotated_surface.get_rect(center=(int(self._x), int(self._y)))
        surface.blit(rotated_surface, rotated_rect)

class Cluster(Shape):
    """
    Represents a cluster of points on the track
    static variables:
        _master (tuple): coordinates of the master point
        _master_distance (int): radius of the master point
        _next_point (int): next point to be reached
        _arr_next_points (np.ndarray): screen coordinates of the next points to be reached
        _current_point (tuple): screen coordinates of the point that is being reached
        _future_count (int): number of future points
        _future_space (int): space between future points
    """
    _master             = (0, 0)
    _master_distance    = 0
    _next_point         = 0
    _arr_next_points    = np.zeros((10, 2))
    _current_point      = (0.0, 0.0)
    _future_count       = 10
    _future_space       = 30

    _reached_color      = (100, 100, 100)

    def __init__(self, coo=(0, 0), color=(0, 0, 0), size=5, angle=0):
        """
        Initializes the cluster object
        """
        super().__init__(coo, color, size, angle)
        self._local = np.empty((0, 2))
        self._index = np.empty(0, dtype=int)
        self._reached = np.empty(0, dtype=bool)
        self._screen = None

    def set_points(self, points):
        # points: iterable of (x, y, global_index) relative to the cluster origin
        arr = np.asarray(points, dtype=float).reshape(-1, 3)
        order = np.argsort(arr[:, 2], kind="stable")
        arr = arr[order]
        self._local = arr[:, :2]
        self._index = arr[:, 2].astype(int)
        self._reached = np.zeros(len(arr), dtype=bool)

    @classmethod
    def set_future_count(cls, future_count, future_space):
        cls._future_count = future_count
        cls._future_space = future_space
        cls._arr_next_points = np.zeros((future_count, 2))

    @classmethod
    def set_master(cls, master, master_distance):
        cls._master = master
        cls._master_distance = master_distance

    @classmethod
    def get_next_point(cls):
        return cls._arr_next_points.copy()

    @classmethod
    def get_current_point(cls):
        return cls._current_point

    def _to_screen(self):
        R = self._rotation_matrix
        lx, ly = self._local[:, 0], self._local[:, 1]
        return np.column_stack((lx * R[0][0] + ly * R[0][1] + self._x,
                                lx * R[1][0] + ly * R[1][1] + self._y))

    def draw(self, surface):
        """
        Draws the cluster on the given surface and advances the next point to be reached
        """
        if len(self._index) == 0:
            self._screen = None
            return

        pts = self._to_screen()
        self._screen = pts

        # advance the next point while the car is over it
        while True:
            pos = np.searchsorted(self._index, Cluster._next_point)
            if pos < len(self._index) and self._index[pos] == Cluster._next_point and self._points_in_square(*pts[pos]):
                self._reached[pos] = True
                Cluster._next_point += 1
            else:
                break

        # draw only the points on the screen
        w, h = surface.get_size()
        s = self._size
        visible = (pts[:, 0] > -s) & (pts[:, 0] < w + s) & (pts[:, 1] > -s) & (pts[:, 1] < h + s)
        if not visible.any():
            return

        circle = pygame.draw.circle
        color, reached_color = self._color, self._reached_color
        for point, reached in zip(pts[visible].tolist(), self._reached[visible].tolist()):
            circle(surface, reached_color if reached else color, point, s)

    def update(self):
        # stores the screen coordinates of the future points belonging to this cluster
        if self._screen is None:
            return

        rel = self._index - Cluster._next_point
        space = Cluster._future_space
        mask = (rel > 0) & (rel % space == 0) & (rel <= space * Cluster._future_count)
        if mask.any():
            Cluster._arr_next_points[rel[mask] // space - 1] = self._screen[mask]

        current = np.flatnonzero(rel == 0)
        if len(current):
            Cluster._current_point = tuple(self._screen[current[0]])

    def get_points(self):
        return self._local

    def _points_in_square(self, x1, y1):
        x0, y0 = self._master
        return (x0 - self._master_distance < x1 < x0 + self._master_distance) and (y0 < y1 < y0 + self._master_distance)

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
        self._points = []
        self._player = (0, 0)
        self._surface = None

    def add_point(self, point):
        self._points.append(point)
        self._surface = None

    def set_player_position(self, player):
        self._player = player

    def _render_background(self):
        # the track never changes, so it is rendered only once
        border_width = 1
        self._surface = pygame.Surface((self._width, self._height), pygame.SRCALPHA)
        pygame.draw.rect(self._surface, self._color,
                         (border_width, border_width, self._width - 2 * border_width, self._height - 2 * border_width))
        half_w, half_h = self._width // 2, self._height // 2
        for px, py in self._points:
            pygame.draw.circle(self._surface, (0, 0, 0), (int(half_w + px * half_w), int(half_h + py * half_h)), 1)

    def draw(self, surface):
        if self._surface is None:
            self._render_background()
        surface.blit(self._surface, (self._x - self._width // 2, self._y - self._height // 2))

        # draw player position
        x = int(self._x + self._player[0] * (self._width // 2))
        y = int(self._y - self._player[1] * (self._height // 2))
        pygame.draw.circle(surface, (200, 0, 0), (x, y), 5)

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
        self._center = (0, 0)

        # offsets of the grid cells inside the visibility circle
        r = int(math.ceil(visible))
        di, dj = np.mgrid[-r:r + 1, -r:r + 1]
        inside = di ** 2 + dj ** 2 < visible ** 2
        self.__circle_offsets = np.column_stack((di[inside], dj[inside]))

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

        # configurate the track
        for i, j in points:
            x = i * self.__point_spacing + d[0]
            y = j * self.__point_spacing + d[1]
            x, y = self.rotate_around_pivot((x, y))

            obj = self.matrix[i][j]
            obj.set_coordinates((x, y))
            obj.set_angle(self._angle)
            obj.draw(surface)

        # update the elements
        for i, j in points:
            self.matrix[i][j].update()

    def __points_in_circle(self, x0, y0):
        # returns the grid cells within the circle of visibility
        rows, cols = self._size
        cells = self.__circle_offsets + (x0, y0)
        valid = (cells[:, 0] >= 0) & (cells[:, 0] < rows) & (cells[:, 1] >= 0) & (cells[:, 1] < cols)
        return cells[valid].tolist()

class Checkbox:
    def __init__(self, x, y, size, label="", font_size=24):
        self.rect = pygame.Rect(x, y, size/2, size/2)
        self.color = (0, 0, 0)
        self.checked = False
        self.label = label
        self.font = pygame.font.SysFont(None, font_size)
        self.label_surface = self.font.render(label, True, (0, 0, 0))

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, 2)
        if self.checked:
            pygame.draw.line(surface, (0, 0, 0), self.rect.topleft, self.rect.bottomright, 2)
            pygame.draw.line(surface, (0, 0, 0), self.rect.topright, self.rect.bottomleft, 2)
        surface.blit(self.label_surface, (self.rect.right + 10, self.rect.y))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.checked = not self.checked

    def set_coordinates(self, coo):
        # sets new coordinates for the checkbox
        self.rect.x = coo[0]
        self.rect.y = coo[1]

class Display(Shape):
    """
    represents a display for the simulator with graphs and text
    """
    __len_data = 100
    __saturation = 100
    __max_checked = 4

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
        self.font = pygame.font.SysFont("courier", 12, bold=True)
        self.title_font = pygame.font.SysFont(None, 20)
        self.__text_cache = {}

        # center and deslocation of display
        middle = (size[0] // horizontal_div, int(size[1] // (2*vertical_div)))
        offset = 40

        coo = (coo[0] - (middle[0]//2 * horizontal_div) + offset, coo[1] - middle[1])
        super().__init__(coo, color, (size[0] // (horizontal_div), int(size[1] // (vertical_div))))

        self.__graph_data = {}
        self.__graph_colors = {}
        self.__graph_range = {}

        self.__checbox_arr = {}

    # define time of the x axis
    def set_time(self, fps):
        self.__len_data = int(fps)

    def verify_checkbox(self, event):
        for checkbox in self.__checbox_arr.values():
            checkbox.handle_event(event)

    # adds a new graph with a specific line name
    def add_graph(self, graph_name, y_range=None, checked=None):
        if graph_name not in self.__graph_data:
            self.__graph_data[graph_name] = {}
            self.__graph_colors[graph_name] = {}
            self.__graph_range[graph_name] = y_range or (-self.__saturation, self.__saturation)

            # create checkboxes for each line in the graph
            self.__checbox_arr[graph_name] = Checkbox(0, 0, 30, graph_name)
            if checked is None:
                checked = sum(c.checked for c in self.__checbox_arr.values()) < self.__max_checked
            self.__checbox_arr[graph_name].checked = checked

    # removes a graph from the display
    def remove_graph(self, graph_name):
        if graph_name in self.__graph_data:
            del self.__graph_data[graph_name]
            del self.__graph_colors[graph_name]
            del self.__graph_range[graph_name]
            del self.__checbox_arr[graph_name]

    def has_graph(self, graph_name):
        return graph_name in self.__graph_data

    # adds a new line to an existing graph
    def add_line_to_graph(self, graph_name, line_name, color=(0, 200, 0)):
        if graph_name in self.__graph_data:
            self.__graph_data[graph_name][line_name] = [0] * self.__len_data
            self.__graph_colors[graph_name][line_name] = color

    # updates the data for a specific line in a graph
    def update_graph_data(self, graph_name, line_name, new_value):
        if graph_name in self.__graph_data and line_name in self.__graph_data[graph_name]:
            data = self.__graph_data[graph_name][line_name]
            data.append(new_value)
            if len(data) > self.__len_data:
                del data[0]

    # update the array of data for a specific graph
    def set_graph_data(self, graph_name, line_name, data):
        self.__graph_data[graph_name][line_name] = data

    def _text(self, text, font=None):
        # renders static text only once
        key = (text, font)
        surface = self.__text_cache.get(key)
        if surface is None:
            surface = (font or self.font).render(text, True, (0, 0, 0))
            self.__text_cache[key] = surface
        return surface

    # draws the display as a rectangle with rounded corners, including graphs and text
    def draw(self, surface):
        # draw the display rectangle with rounded corners
        rect = pygame.Rect(self._x, self._y, self._size[0], self._size[1])
        pygame.draw.rect(surface, self._color, rect, border_radius=15)

        # draw the checkbox for all graps
        selected = []
        for idx, (graph_name, checkbox) in enumerate(self.__checbox_arr.items()):
            checkbox.set_coordinates((self._x + self._size[0] + 5, self._y + idx * 20))
            checkbox.draw(surface)
            if checkbox.checked:
                selected.append(graph_name)

        if not selected:
            return

        # calculate the height of each graph useing the number of selected graphs
        graph_height = (self._size[1] - 30) // len(selected)
        for i, graph_name in enumerate(selected):
            graph_x = self._x + 15
            graph_y = self._y + i * graph_height + 15
            graph_width = self._size[0] - 30
            graph_height_ = graph_height - 15 if i < len(selected) - 1 else graph_height
            self.draw_graph(surface, self.__graph_data[graph_name], (graph_x, graph_y, graph_width, graph_height_), graph_name)

    # draw grid lines
    def __draw_grid(self, surface, graph_width, graph_height, graph_x, graph_y):
        grid_color = (200, 200, 200)
        for i in range(15, graph_width -15, max(1, graph_width // 10)):
            pygame.draw.line(surface, grid_color, (graph_x + i, graph_y), (graph_x + i, graph_y + graph_height))
        for i in range(15, graph_height -15, max(1, graph_height // 5)):
            pygame.draw.line(surface, grid_color, (graph_x, graph_y + i), (graph_x + graph_width, graph_y + i))

    # draw axis values
    def __draw_axis_values(self, surface, graph_height, graph_x, graph_y, y_range):
        num_divisions = 5
        y_min, y_max = y_range
        for i in range(num_divisions + 1):
            value = y_max - i * (y_max - y_min) / num_divisions
            label = self._text(f"{value:g}")
            surface.blit(label, (graph_x - 45, graph_y + (i * graph_height // num_divisions) - 10))

    # draw title
    def __draw_title(self, surface, title, graph_width, graph_x, graph_y):
        title_label = self._text(title, self.title_font)
        text_width = title_label.get_width()
        text_height = title_label.get_height()

        rect_x = graph_x + graph_width // 2 - text_width // 2 - 10
        rect_y = graph_y + 10
        pygame.draw.rect(surface, (255, 255, 255), (rect_x, rect_y, text_width + 20, text_height + 10))
        surface.blit(title_label, (graph_x + graph_width // 2 - text_width // 2, rect_y + 5))

    # draw each line in the graph as a step polyline
    def __draw_graph_separate(self, surface, lines, title, graph_width, graph_height, graph_x, graph_y, y_range):
        y_min, y_max = y_range
        for line_name, data in lines.items():
            n = len(data)
            if n == 0:
                continue
            values = np.clip(np.asarray(data, dtype=float), y_min, y_max)
            ys = graph_y + graph_height * (y_max - values) / (y_max - y_min)
            xs = graph_x + np.arange(n + 1) * (graph_width / n)

            # (x0, y0) (x1, y0) (x1, y1) (x2, y1) ... (xn, y_{n-1})
            pts = np.empty((2 * n, 2))
            pts[0::2, 0] = xs[:-1]
            pts[1::2, 0] = xs[1:]
            pts[0::2, 1] = ys
            pts[1::2, 1] = ys
            pygame.draw.lines(surface, self.__graph_colors[title][line_name], False, pts.tolist(), 2)

    # draw legend
    def __draw_legend(self, surface, graph_x, graph_y, title):
        legend_x = graph_x + 10
        legend_y = graph_y + 10
        for idx, (line_name, color) in enumerate(self.__graph_colors[title].items()):
            pygame.draw.rect(surface, color, (legend_x, legend_y + idx * 20, 10, 10))
            surface.blit(self._text(line_name), (legend_x + 15, legend_y + idx * 20 - 5))

    # draw label for y values
    def __draw_label_last_y(self, surface, graph_x, graph_y, graph_height, lines):
        for i, (line_name, data) in enumerate(lines.items()):
            if len(data) == 0:
                continue
            label = self.font.render(f"{line_name}: {float(data[-1]):.2f}", True, (0, 0, 0))
            surface.blit(label, (graph_x + 10, graph_y + graph_height - 20 - i * 20))

    # helper function to draw a graph with multiple lines
    def draw_graph(self, surface, lines, rect, title):
        """
        draw a graph with multiple lines on the given surface
        """
        graph_width, graph_height = int(rect[2]), int(rect[3])
        graph_x, graph_y = int(rect[0]), int(rect[1])
        y_range = self.__graph_range[title]

        pygame.draw.rect(surface, (255, 255, 255), (graph_x, graph_y, graph_width, graph_height), border_radius=10)
        self.__draw_grid(surface, graph_width, graph_height, graph_x, graph_y)
        self.__draw_graph_separate(surface, lines, title, graph_width, graph_height, graph_x, graph_y, y_range)
        self.__draw_axis_values(surface, graph_height, graph_x, graph_y, y_range)
        self.__draw_title(surface, title, graph_width, graph_x, graph_y)
        self.__draw_legend(surface, graph_x, graph_y, title)
        self.__draw_label_last_y(surface, graph_x, graph_y, graph_height, lines)

class Statistics(Shape):
    """
    represents statistical text information displayed on the simulator
    """
    _font = None
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
        self._offset = 1
        self._rendered = None
        # set the font for the text
        if not Statistics._font:
            Statistics._font = pygame.font.SysFont("courier", 20, bold=True)

    @classmethod
    def set_font_size(cls, size):
        # sets a new font for the text
        cls._font = pygame.font.SysFont("courier", size, bold=True)

    def set_offset(self, offset):
        # sets the offset for the text
        self._offset = offset

    def set_text(self, text):
        # updates the text to be displayed
        self.text = text

    def draw(self, surface):
        """
        draws the text on the given surface (re-rendered only when the text changes)
        args:
            surface (pygame.Surface): the surface to draw on
        """
        if self._rendered is None or self._rendered[0] != self.text or self._rendered[1] is not self._font:
            self._rendered = (self.text, self._font, self._font.render(self.text, True, self._color))
        text_surface = self._rendered[2]
        surface.blit(text_surface, (self._x - text_surface.get_width() // self._offset, self._y))

class Compass(Shape):
    """
    represents a compass object on the simulator
    """
    _directions = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}

    def __init__(self, coo, color=(0, 0, 0), size=40, angle=0):
        """
        initializes the compass object
        args:
            coo (tuple): coordinates of the compass object
            color (tuple): color of the compass in rgb format
            size (int): size of the compass object
            angle (float): initial angle of the compass in radians
        """
        super().__init__(coo, color, size, angle)
        font = pygame.font.Font(None, 24)
        self._labels = []
        for direction, (dx, dy) in self._directions.items():
            color_ = (200, 0, 0) if direction == "N" else self._color
            text_surface = font.render(direction, True, color_)
            center = (self._x + dx * self._size * 1.3, self._y + dy * self._size * 1.3)
            self._labels.append((text_surface, text_surface.get_rect(center=center)))

    def draw(self, surface):
        # Draw the outer circle
        pygame.draw.circle(surface, self._color, (self._x, self._y), self._size, 2)

        # Points for the star: 4 major (N, E, S, W) and 4 minor (NE, SE, SW, NW)
        star_points = []
        for i in range(8):
            angle = self._angle + (math.pi / 4) * i
            radius = self._size if i % 2 == 0 else self._size * 0.4
            star_points.append((self._x + radius * math.cos(angle), self._y + radius * math.sin(angle)))
        pygame.draw.polygon(surface, self._color, star_points, 2)

        # Draw cardinal direction labels
        for text_surface, text_rect in self._labels:
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
        pygame.draw.line(surface, self._color, (self._x - self._size/2, self._y), (self._x + self._size/2, self._y), 2)

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
        self.win = win
        pygame.init()

        # set the window size based on mode
        if win == FULL:
            width, height = pygame.display.get_desktop_sizes()[0]
        elif win == MEDIUM:
            width = 1400
            height = 750
        elif win == SMALL:
            width = 800
            height = 600
        else:
            raise ValueError(f"Invalid screen size: {win}")

        self.__width = width
        self.__height = height
        self.__FPS = FPS
        self.__objects = []
        self.__clock = pygame.time.Clock()

    def start(self):
        if self.win == FULL:
            self.screen = pygame.display.set_mode((self.__width, self.__height),  pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((self.__width, self.__height))

        pygame.display.set_caption("SIMULATOR")

    def tick(self, limit=True):
        # waits to keep the frame rate (without busy waiting) and returns the measured fps
        self.__clock.tick(self.__FPS if limit else 0)
        return self.__clock.get_fps()

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

    def draw(self):
        # draws all objects on the simulator screen
        if not self.__objects:
            return
        self.screen.fill((255, 255, 255))  # background color
        for obj in self.__objects:
            obj.draw(self.screen)

        pygame.display.flip()
