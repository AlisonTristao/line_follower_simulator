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
            color (tuple): coatualize_next_pointlor of the shape in rgb format
            size (int): size of the shape
            angle (float): initial angle in radians
        """
        self._x = coo[0]
        self._y = coo[1]
        self._angle = angle
        self._color = color
        self._size = size
        self._pivot = (0, 0)
        self.visible = True  # Visibility flag for toggling display
        
        # World boundary limits (default to None - disabled)
        self._world_width = None
        self._world_height = None

        self._update_rotation_matrix()

    def _update_rotation_matrix(self):
        """Updates rotation matrix based on current angle"""
        cos_theta = math.cos(self._angle)
        sin_theta = math.sin(self._angle)
        # Matriz de rotação 2D
        self._rotation_matrix = [
            [cos_theta, -sin_theta],
            [sin_theta, cos_theta]
        ]

    def get_center(self):
        # returns the center coordinates of the shape
        return self._x, self._y

    def get_angle(self):
        # returns the current angle of the shape
        return self._angle

    def set_angle(self, angle):
        # sets a new angle for the shape
        self._angle = angle
        self._update_rotation_matrix()

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

    def set_world_bounds(self, width, height):
        """
        sets the world boundary limits for this shape
        args:
            width (float): maximum x coordinate (width of world)
            height (float): maximum y coordinate (height of world)
        """
        self._world_width = width
        self._world_height = height

    def _clamp_position(self):
        """clamps the shape position within world boundaries"""
        if self._world_width is not None:
            self._x = max(0, min(self._x, self._world_width))
        if self._world_height is not None:
            self._y = max(0, min(self._y, self._world_height))

    def step(self, dx, dy, angle):
        # moves and rotates the shape
        self._rotate(angle)
        self._move(dx, dy)

    def _rotate(self, angle):
        # rotates the shape by the given angle
        self._angle += angle
        self.set_angle(self._angle)

    def _move(self, dx, dy):
        # moves the shape by dx and dy considering rotation
        s = dx * math.cos(-self._angle) - dy * math.sin(-self._angle)
        dy = dx * math.sin(-self._angle) + dy * math.cos(-self._angle)
        dx = s
        self._x += dx
        self._y += dy
        self._clamp_position()

    def rotate_around_origin(self, theta):
        # rotates the shape around the origin by theta radians
        x_new = self._x * math.cos(theta) - self._y * math.sin(theta)
        y_new = self._x * math.sin(theta) + self._y * math.cos(theta)
        self._x, self._y = x_new, y_new

    def _rotate_point(self, coo):
        x = coo[0]
        y = coo[1]
        x_rotated = x * self._rotation_matrix[0][0] + y * self._rotation_matrix[0][1]
        y_rotated = x * self._rotation_matrix[1][0] + y * self._rotation_matrix[1][1]
        return x_rotated, y_rotated

    def rotate_around_pivot(self, coo):
        # rotates a point around the track's pivot
        ox, oy = self._pivot
        translated_x = coo[0] - ox
        translated_y = coo[1] - oy
        x_rotated = translated_x * self._rotation_matrix[0][0] + translated_y * self._rotation_matrix[0][1]
        y_rotated = translated_x * self._rotation_matrix[1][0] + translated_y * self._rotation_matrix[1][1]
        return x_rotated + ox, y_rotated + oy

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
        self._x = center[0] * coo[0] #+ math.cos(math.radians(angle))
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
    represents the future points of the car in the simulator
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
        # sets the future points to be drawn
        self._points = points

    def draw(self, surface):
        # draws the future points as circles on the given surface
        for point in self._points:
            pygame.draw.circle(surface, self._color, (int(point[0]), int(point[1])), self._size)

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
    def __init__(self, coo=(0, 0, 0), color=(100, 100, 100), size=(70, 70)):
        """
        initializes a wall object
        args:
            coo (tuple): coordinates of the wall
            color (tuple): color of the wall in rgb format
            size (tuple): width and height of the wall
        """
        super().__init__(coo, color, size)

    def draw(self, surface):
        # draws the wall as a rotated rectangle on the given surface
        temp_surface = pygame.Surface(self._size, pygame.SRCALPHA)
        temp_surface.fill(self._color)
        rotated_surface = pygame.transform.rotate(temp_surface, math.degrees(-self._angle))
        rotated_rect = rotated_surface.get_rect(center=(int(self._x), int(self._y)))
        surface.blit(rotated_surface, rotated_rect)

class Cluster(Shape):
    """
    Represents a cluster of points on the track
    static variables:
        _master (tuple): coordinates of the master point
        _master_distance (int): radius of the master point
        _next_point (int): next point to be reached
        _arr_next_points (list): list of next points to be reached
        _future_count (int): number of future points
        _future_space (int): space between future points
    """
    _master             = (0, 0)   
    _master_distance    = 0         
    _next_point         = 0        
    _max_point          = None       # Limit for _next_point (stops incrementing when reached)
    _arr_next_points    = []        
    _future_count       = 10       
    _future_space       = 30        

    def __init__(self, coo=(0, 0), color=(0, 0, 0), size=3, angle=0):
        """
        Initializes the cluster object
        """
        super().__init__(coo, color, size, angle)
        self.__global_index = []
        self.__points_arr = [] 
        self.__colors_arr = []

    def add_point(self, point, color=(0, 0, 0)):
        self.__points_arr.append((point[0], point[1]))
        self.__colors_arr.append(color)
        self.__global_index.append(point[2])

    @classmethod
    def set_future_count(cls, future_count, future_space):
        cls._future_count = future_count
        cls._future_space = future_space
        cls._arr_next_points = [(0, 0)] * future_count

    @classmethod
    def set_master(cls, master, master_distance):
        cls._master = master
        cls._master_distance = master_distance

    @classmethod
    def update_next_point(cls):
        # Only increment if we haven't reached the max point limit
        if cls._max_point is None or cls._next_point < cls._max_point:
            cls._next_point += 1

    @classmethod
    def set_max_point(cls, max_point):
        """Set the maximum point limit (stops incrementing when _next_point reaches this)"""
        cls._max_point = max_point

    @classmethod
    def add_next_point(cls, point, index):
        cls._arr_next_points[index] = point

    @ classmethod
    def get_next_point(cls):
        return [(float(x), float(y)) for x, y in list(cls._arr_next_points)]

    def update(self):
        """
        Optimized: Pre-calculate future indices in set for O(1) lookup instead of O(n²) loops
        """
        # Build future indices set once
        future_indices = set(
            self._next_point + j 
            for j in range(self._future_space, 
                          self._future_space * self._future_count + self._future_space, 
                          self._future_space)
        )
        
        # Check which points have indices in future_indices (O(n) with O(1) lookups)
        for i in range(len(self.__points_arr)):
            if self.__global_index[i] in future_indices:
                point_ = self._rotate_point(self.__points_arr[i])
                x = point_[0] + self._x
                y = point_[1] + self._y
                offset = (self.__global_index[i] - self._next_point) // self._future_space - 1
                self.add_next_point((x, y), offset)

    def draw(self, surface):
        """
        Draws the cluster on the given surface (optimized)
        Pre-calculate geometry checks to avoid repeated expensive operations
        """
        # Get master point parameters
        x0, y0 = self._master
        d = self._master_distance
        
        for i in range(len(self.__points_arr)):
            point_ = self._rotate_point(self.__points_arr[i])
            x = point_[0] + self._x
            y = point_[1] + self._y

            # Check if point is in square (geometry check)
            if (x0 - d < x < x0 + d) and (y0 < y < y0 + d):
                if self.__global_index[i] == self._next_point:
                    self.__colors_arr[i] = (100, 100, 100)
                    self.update_next_point()

            pygame.draw.circle(surface, self.__colors_arr[i], (x, y), self._size)
    
    def get_points(self):
        return self.__points_arr

    def _points_in_square(self, x1, y1):
        x0, y0 = self._master
        return (x0 - self._master_distance < x1 < x0 + self._master_distance) and (y0 < y1 < y0 + self._master_distance)

class MiniMap(Shape):
    """
    Represents a minimap object on the simulator
    """
    MAX_TRAIL_POINTS = 50  # Maximum number of trail points to store
    
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
        self._points = []  # Lista de pontos do track no formato [(x, y)]
        self._trail = []   # Array para armazenar histórico de posições do carrinho (trilha azul)
        self._left_sensor_points = []   # Marcadores amarelos (sensor esquerdo)
        self._right_sensor_points = []  # Marcadores roxos (sensor direito)
        self._player = (0, 0)

    def add_point(self, point):
        """Add a track point to the minimap"""
        self._points.append(point)
    
    def add_trail_point(self, player_x, player_y):
        """Add current player position to the trail history"""
        self._trail.append((player_x, player_y))
        # Remove oldest point if exceeding maximum to prevent performance degradation
        if len(self._trail) > self.MAX_TRAIL_POINTS:
            self._trail.pop(0)
    
    def add_left_sensor_point(self, sensor_x, sensor_y):
        """Add left sensor activation point (yellow marker)"""
        self._left_sensor_points.append((sensor_x, sensor_y))
    
    def add_right_sensor_point(self, sensor_x, sensor_y):
        """Add right sensor activation point (purple marker)"""
        self._right_sensor_points.append((sensor_x, sensor_y))
    
    def clear_trail(self):
        """Clear the trail history"""
        self._trail = []
        self._left_sensor_points = []
        self._right_sensor_points = []

    def set_player_position(self, player):
        self._player = player

    def draw(self, surface):
        # coordinates and dimensions of the minimap rectangle
        rect_x = self._x - self._width // 2
        rect_y = self._y - self._height // 2
        rect_width = self._width
        rect_height = self._height

        #border_color = (100, 100, 100)
        border_width = 1

        # draw background
        pygame.draw.rect(surface, self._color,
                         (rect_x + border_width, rect_y + border_width,
                          rect_width - 2 * border_width, rect_height - 2 * border_width))

        # Pre-calculate scale factors to avoid recalculation in loops
        scale_x = self._width // 2
        scale_y = self._height // 2

        # draw track (black points)
        point_color = (0, 0, 0)
        for px, py in self._points:
            # normalize the point coordinates
            x = int(self._x + px * scale_x)
            y = int(self._y + py * scale_y)
            pygame.draw.circle(surface, point_color, (x, y), 1)
        
        # draw trail (blue line showing where the robot has been)
        if len(self._trail) >= 2:
            trail_color = (0, 100, 255)  # Blue
            for i in range(len(self._trail) - 1):
                x1 = int(self._x + self._trail[i][0] * scale_x)
                y1 = int(self._y - self._trail[i][1] * scale_y)
                x2 = int(self._x + self._trail[i + 1][0] * scale_x)
                y2 = int(self._y - self._trail[i + 1][1] * scale_y)
                pygame.draw.line(surface, trail_color, (x1, y1), (x2, y2), 2)
        
        # draw left sensor activation points (yellow circles)
        left_sensor_color = (255, 255, 0)  # Yellow
        for sx, sy in self._left_sensor_points:
            x = int(self._x + sx * scale_x)
            y = int(self._y - sy * scale_y)
            pygame.draw.circle(surface, left_sensor_color, (x, y), 3)
        
        # draw right sensor activation points (purple circles)
        right_sensor_color = (200, 0, 255)  # Purple
        for sx, sy in self._right_sensor_points:
            x = int(self._x + sx * scale_x)
            y = int(self._y - sy * scale_y)
            pygame.draw.circle(surface, right_sensor_color, (x, y), 3)

        # draw player position (red circle)
        player_color = (200, 0, 0)
        x = int(self._x + self._player[0] * scale_x)
        y = int(self._y - self._player[1] * scale_y)

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
        super().__init__(coo=(size[0] * point_spacing, size[1] * point_spacing // 2), size=size, angle=0)
        self.screen_size = screen_size
        self.__visible = visible
        self.__point_spacing = point_spacing
        self._center = (0, 0) #(self.screen_size[0] // 1.5, self.screen_size[1] // 2)
        
        # Set world boundaries based on track size
        # World size = (size - 1) (in cells) * point_spacing (pixels per cell) to limit to 0-99 and 0-49
        self.set_world_bounds((size[0] - 1) * point_spacing, (size[1] - 1) * point_spacing)

        # lenght and width of the space between the chunks of the track
        len_chunk = point_spacing//5
        size_wall = point_spacing//2

        # initializes the matrix of points and walls
        self.wall_hor = Wall(size=(len_chunk, size_wall))
        self.wall_ver = Wall(size=(size_wall, len_chunk))
        self.wall_lim = Wall(size=(len_chunk, len_chunk))
        self.default = Default()
        self.matrix = self._create_matrix(size)

    def _create_matrix(self, size):
        # creates the initial matrix of track objects
        matrix = []
        for i in range(size[0]):
            row = []
            for j in range(size[1]):
                # math case if x = 0 or x = size[0] - 1 or y = 0 or y = size[1] - 1, then it's a wall, otherwise it's a default point
                if (i == 0 or i == size[0] - 1) and not (j == 0 or j == size[1] - 1):
                    row.append(self.wall_hor)
                elif (j == 0 or j == size[1] - 1) and not (i == 0 or i == size[0] - 1):
                    row.append(self.wall_ver)
                elif (i == 0 or i == size[0] - 1) and (j == 0 or j == size[1] - 1):
                    row.append(self.wall_lim)
                else:
                    row.append(self.default)
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

            self.matrix[i][j].set_coordinates((x, y))
            self.matrix[i][j].set_angle(self._angle)
            self.matrix[i][j].draw(surface)

        # update the elements
        for i, j in points:
            self.matrix[i][j].update()

    def __points_in_circle(self, x0, y0):
        # returns the points within a circle of visibility
        rows, cols = self._size
        x, y = np.ogrid[:rows, :cols]
        dist_sq = (x - x0) ** 2 + (y - y0) ** 2
        return np.argwhere(dist_sq < self.__visible ** 2)

class Checkbox:
    def __init__(self, x, y, size, label="", font_size=24, text_color=(0, 0, 0)):
        self.rect = pygame.Rect(x, y, size/2, size/2)
        self.color = (0, 0, 0)
        self.checked = False
        self.label = label
        self.text_color = text_color
        self.font = pygame.font.SysFont(None, font_size)
        self.label_surface = self.font.render(label, True, text_color)

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

        self.__checbox_arr = {}
        
        # Checkboxes for compass and coordinates visibility
        self.checkbox_compass = Checkbox(0, 0, 30, "Compass")
        self.checkbox_compass.checked = True
        self.checkbox_coordinates = Checkbox(0, 0, 30, "Coordinates")
        self.checkbox_coordinates.checked = True

    # define time of the x axis
    def set_time(self, fps):
        self.__len_data = int(fps)

    def verify_checkbox(self, event):
        for graph_name, checkbox in self.__checbox_arr.items():
            checkbox.handle_event(event)
        # Handle compass and coordinates checkboxes
        self.checkbox_compass.handle_event(event)
        self.checkbox_coordinates.handle_event(event)

    # adds a new graph with a specific line name
    def add_graph(self, graph_name):
        if graph_name not in self.__graph_data:
            self.__graph_data[graph_name] = {}
            self.__graph_colors[graph_name] = {}

            # create checkboxes for each line in the graph
            self.__checbox_arr[graph_name] = Checkbox(0, 0, 30, graph_name)

            if len(self.__graph_data) <= 4:
                self.__checbox_arr[graph_name].checked = True

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

    # update the array of data for a specific graph
    def set_graph_data(self, graph_name, line_name, data):
        self.__graph_data[graph_name][line_name] = data

    # draws the display as a rectangle with rounded corners, including graphs and text
    def draw(self, surface):
        # calculate the height of each graph useing the number of selected graphs
        selected = sum(1 for checkbox in self.__checbox_arr.values() if checkbox.checked)
        
        # Only draw background if any graph is selected (FPS optimization)
        if selected > 0:
            # draw the display rectangle with rounded corners
            rect = pygame.Rect(self._x, self._y, self._size[0], self._size[1])
            pygame.draw.rect(surface, self._color, rect, border_radius=15)
        
        graph_height = (self._size[1] - 30) // selected if selected > 0 else 0

        # draw each graph
        selected = []
        for idx, (graph_name, lines) in enumerate(self.__graph_data.items()):

            # draw the checkbox for all graps
            checkbox = self.__checbox_arr[graph_name]
            x = self._x + self._size[0] + 5
            y = self._y + idx * 20
            checkbox.set_coordinates((x, y))
            checkbox.draw(surface)

            if checkbox.checked:
                selected.append(graph_name)

        # Draw compass and coordinates checkboxes below graph checkboxes
        num_graphs = len(self.__graph_data)
        compass_y = self._y + num_graphs * 20
        coordinates_y = self._y + (num_graphs + 1) * 20
        
        self.checkbox_compass.set_coordinates((self._x + self._size[0] + 5, compass_y))
        self.checkbox_compass.draw(surface)
        
        self.checkbox_coordinates.set_coordinates((self._x + self._size[0] + 5, coordinates_y))
        self.checkbox_coordinates.draw(surface)

        for i in range(len(selected)):
            graph_name = selected[i]
            lines = self.__graph_data[graph_name]

            # calculate the position of the graph
            graph_x = self._x + 15
            graph_y = self._y + i * graph_height + 15
            graph_width = self._size[0] - 30
            graph_height_ = graph_height - 15 if i < len(selected) - 1 else graph_height

            # draw the graph
            self.draw_graph(surface, lines, (graph_x, graph_y, graph_width, graph_height_), graph_name)

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
            y_pos = graph_y + (i * graph_height // (num_divisions))
            label = self.font.render(str(value), True, (0, 0, 0))
            surface.blit(label, (graph_x - 45, y_pos - 10))

    # draw title 
    def __draw_title(self, surface, title, graph_width, graph_x, graph_y):
        font = pygame.font.SysFont(None, 20)
        title_label = font.render(title, True, (0, 0, 0))
        text_width = title_label.get_width()
        text_height = title_label.get_height()

        # Centraliza o retângulo e o texto
        rect_x = graph_x + graph_width // 2 - text_width // 2 - 10  # 10 de padding
        rect_y = graph_y + 10
        rect_width = text_width + 20  # 10 de padding em cada lado
        rect_height = text_height + 10

        pygame.draw.rect(surface, (255, 255, 255), (rect_x, rect_y, rect_width, rect_height))
        surface.blit(title_label, (graph_x + graph_width // 2 - text_width // 2, rect_y + 5))

    # draw each line in the graph
    def __draw_graph_separate(self, surface, lines, title, graph_width, graph_height, graph_x, graph_y):
        for line_name, data in lines.items():
            normalized_data = [
                graph_height - (graph_height * (value - self.__min_value) / (self.__max_value - self.__min_value))
                for value in data
            ]
            step_width = graph_width / len(data)
            color = self.__graph_colors[title][line_name]

            for i in range(len(normalized_data)):
                x1 = graph_x + i * step_width
                y1 = graph_y + normalized_data[i]
                x2 = graph_x + (i + 1) * step_width
                y2 = graph_y + normalized_data[i + 1] if i < len(normalized_data) - 1 else y1
                # draw the horizontal step
                pygame.draw.line(surface, color, (x1, y1), (x2, y1), 2)
                # draw the vertical connection to the next step
                pygame.draw.line(surface, color, (x2, y1), (x2, y2), 2)

    # draw legend
    def __draw_legend(self, surface, graph_x, graph_y, title):
        legend_x = graph_x + 10
        legend_y = graph_y + 10
        for idx, (line_name, color) in enumerate(self.__graph_colors[title].items()):
            # draw a background rectangle
            #pygame.draw.rect(surface, (255, 255, 255), (graph_x, graph_y + idx * 23, 100, 25))
            pygame.draw.rect(surface, color, (legend_x, legend_y + idx * 20, 10, 10))
            legend_label = self.font.render(line_name, True, (0, 0, 0))
            surface.blit(legend_label, (legend_x + 15, legend_y + idx * 20 - 5))

    # draw label for y values
    def __draw_label_last_y(self, surface, graph_x, graph_y, graph_height, graph_width, lines):
        # draw the last value of each line
        for i, (line_name, data) in enumerate(lines.items()):
            # draw a background rectangle
            #pygame.draw.rect(surface, (200, 200, 200), (graph_x, graph_y + graph_height - 25 - i * 23, 100, 25))
            # round 2 decimal places
            value = round(data[-1], 2)
            label = self.font.render(f"{line_name}: {value}", True, (0, 0, 0))
            # draw the label
            x = graph_x + 10
            y = graph_y + graph_height - 20 - i * 20
            surface.blit(label, (x, y))
            
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

        # draw each line in the graph
        self.__draw_graph_separate(surface, lines, title, graph_width, graph_height, graph_x, graph_y)

        # draw axes values
        self.__draw_axis_values(surface, graph_height, graph_x, graph_y)

        # draw title
        self.__draw_title(surface, title, graph_width, graph_x, graph_y)

        # draw legend
        self.__draw_legend(surface, graph_x, graph_y, title)

        # draw label for y values
        self.__draw_label_last_y(surface, graph_x, graph_y, graph_height, graph_width, lines)

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
        draws the text on the given surface
        args:
            surface (pygame.Surface): the surface to draw on
        """
        if not self.visible:
            return
        text_surface = self._font.render(self.text, True, self._color)
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
        # Check if visible before drawing
        if not self.visible:
            return
            
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

class SideSensor(Shape):
    """
    Represents a side sensor (left or right) on the simulator
    Draws as a circle that can change color
    """
    def __init__(self, coo, color=(100, 100, 100), size=8, angle=0):
        """
        Initialize the side sensor object
        args:
            coo (tuple): coordinates of the sensor
            color (tuple): color of the sensor in rgb format
            size (int): radius of the sensor circle
            angle (float): initial angle (unused for circular sensor)
        """
        super().__init__(coo, color, size, angle)
        self.active_color = (0, 255, 0)  # Green when active
        self.inactive_color = (100, 100, 100)  # Gray when inactive
        self.is_active = False

    def draw(self, surface):
        """Draw the sensor as a circle"""
        current_color = self.active_color if self.is_active else self.inactive_color
        pygame.draw.circle(surface, current_color, (int(self._x), int(self._y)), self._size)

    def set_active(self, active: bool):
        """Set sensor active state (green if True, gray if False)"""
        self.is_active = active

    def get_x(self):
        return self._x
    
    def get_y(self):
        return self._y

class SerialMonitorToggle(Shape):
    """
    represents a toggle button (checkbox) for the serial monitor
    stays visible even when serial monitor is disabled
    """
    def __init__(self, coo=(10, 10), color=(75, 75, 75)):
        """
        initializes the serial monitor toggle
        args:
            coo (tuple): coordinates of the toggle button
            color (tuple): background color in rgb format
        """
        super().__init__(coo, color, (30, 30))
        self.checkbox = Checkbox(0, 0, 30, "Serial Monitor")
        self.checkbox.checked = True
        self._update_position()
    
    def _update_position(self):
        """update checkbox position"""
        self.checkbox.set_coordinates((int(self._x), int(self._y)))
    
    def set_coordinates(self, coo):
        """set coordinates and update checkbox"""
        super().set_coordinates(coo)
        self._update_position()
    
    def handle_event(self, event):
        """handle events for the checkbox"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Update position first to match what's being drawn
            self.checkbox.set_coordinates((int(self._x), int(self._y)))
            self.checkbox.handle_event(event)
    
    def is_enabled(self):
        """return if serial monitor is enabled"""
        return self.checkbox.checked
    
    def set_enabled(self, enabled):
        """set enabled state"""
        self.checkbox.checked = enabled
    
    def draw(self, surface):
        """draw the toggle checkbox"""
        self.checkbox.draw(surface)

class Button:
    """
    represents a simple clickable button UI element
    """
    def __init__(self, x, y, width, height, text="", font_size=16, bg_color=(100, 100, 100), text_color=(255, 255, 255)):
        """
        initializes a button
        args:
            x (int): x coordinate of the button
            y (int): y coordinate of the button
            width (int): width of the button
            height (int): height of the button
            text (str): text displayed on the button
            font_size (int): font size of the text
            bg_color (tuple): background color in rgb format
            text_color (tuple): text color in rgb format
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = pygame.font.SysFont(None, font_size)
        self.bg_color = bg_color
        self.text_color = text_color
        self.hovered = False
        self.callback = None  # Optional callback function

    def draw(self, surface):
        # draw button background
        color = tuple(min(c + 30, 255) for c in self.bg_color) if self.hovered else self.bg_color
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2, border_radius=5)
        
        # draw button text
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def set_position(self, x, y):
        self.rect.x = x
        self.rect.y = y

class TextInput:
    """
    represents a text input UI element
    """
    def __init__(self, x, y, width, height, placeholder="", font_size=16, max_chars=100):
        """
        initializes a text input
        args:
            x (int): x coordinate of the text input
            y (int): y coordinate of the text input
            width (int): width of the text input
            height (int): height of the text input
            placeholder (str): placeholder text
            font_size (int): font size
            max_chars (int): maximum characters allowed
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.placeholder = placeholder
        self.font = pygame.font.SysFont(None, font_size)
        self.max_chars = max_chars
        self.active = False
        self.cursor_visible = True
        self.cursor_blink_time = 0
        self.submit_pressed = False  # Flag para Enter pressionado

    def _wrap_text(self, text, max_width):
        """quebra texto simples por caractere"""
        if not text:
            return [""]
        
        # Estima chars por linha baseado em max_width
        chars_per_line = max(15, int((max_width - 20) / 7))  # ~7px por char, 20px margin
        
        lines = []
        for i in range(0, len(text), chars_per_line):
            lines.append(text[i:i+chars_per_line])
        
        return lines if lines else [""]

    def draw(self, surface):
        # draw background
        pygame.draw.rect(surface, (255, 255, 255), self.rect, border_radius=3)
        pygame.draw.rect(surface, (0, 0, 0) if self.active else (150, 150, 150), self.rect, 2, border_radius=3)
        
        # draw text or placeholder
        display_text = self.text if self.text else self.placeholder
        is_placeholder = not self.text
        text_color = (150, 150, 150) if is_placeholder else (0, 0, 0)
        
        # wrap text
        lines = self._wrap_text(display_text, self.rect.width)
        
        # draw lines
        y_offset = self.rect.y + 5
        for line in lines:
            if y_offset > self.rect.bottom:
                break
            text_surface = self.font.render(line, True, text_color)
            surface.blit(text_surface, (self.rect.x + 5, y_offset))
            y_offset += text_surface.get_height()
        
        # draw cursor if active
        if self.active and self.cursor_visible and lines:
            last_line = lines[-1]
            last_line_surface = self.font.render(last_line, True, text_color)
            cursor_x = self.rect.x + 5 + last_line_surface.get_width()
            cursor_y = self.rect.y + 5 + (len(lines) - 1) * last_line_surface.get_height()
            if cursor_y < self.rect.bottom:
                pygame.draw.line(surface, (0, 0, 0), (cursor_x, cursor_y), (cursor_x, cursor_y + last_line_surface.get_height()), 2)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.submit_pressed = True
                return self.text
            elif len(self.text) < self.max_chars:
                self.text += event.unicode
        return None

    def update(self):
        # update cursor blink
        self.cursor_blink_time += 1
        if self.cursor_blink_time > 30:
            self.cursor_visible = not self.cursor_visible
            self.cursor_blink_time = 0

    def set_position(self, x, y):
        self.rect.x = x
        self.rect.y = y

    def get_text(self):
        return self.text

    def clear(self):
        self.text = ""

class Slider:
    """
    represents a horizontal slider UI element for numeric value control
    """
    def __init__(self, x, y, width, height, min_val=0, max_val=100, initial_val=50, label=""):
        """
        initializes a slider
        args:
            x (int): x coordinate of the slider
            y (int): y coordinate of the slider
            width (int): width of the slider track
            height (int): height of the slider
            min_val (int/float): minimum value
            max_val (int/float): maximum value
            initial_val (int/float): initial value
            label (str): label displayed above the slider
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.label = label
        self.font = pygame.font.SysFont(None, 14)
        self.dragging = False
        self.callback = None
        self.track_height = 4
        self.handle_radius = 8
        
    def _get_handle_x(self):
        """calculate handle x position based on current value"""
        ratio = (self.value - self.min_val) / (self.max_val - self.min_val)
        return self.rect.x + int(ratio * self.rect.width)
    
    def _set_value_from_x(self, x):
        """set value based on x coordinate"""
        x_relative = max(0, min(x - self.rect.x, self.rect.width))
        ratio = x_relative / self.rect.width
        new_value = self.min_val + ratio * (self.max_val - self.min_val)
        self.value = max(self.min_val, min(self.max_val, new_value))
        if self.callback:
            self.callback(int(self.value))
    
    def draw(self, surface):
        """draw the slider"""
        track_y = self.rect.centery
        
        # draw label
        if self.label:
            label_text = self.font.render(f"{self.label}: {int(self.value)}", True, (255, 255, 255))
            # Draw background for text visibility
            text_rect = label_text.get_rect(topleft=(self.rect.x, self.rect.y - 20))
            text_rect.inflate_ip(4, 2)
            pygame.draw.rect(surface, (50, 50, 50), text_rect)
            surface.blit(label_text, (self.rect.x + 2, self.rect.y - 19))
        
        # draw track
        pygame.draw.line(surface, (150, 150, 150), 
                        (self.rect.x, track_y), 
                        (self.rect.x + self.rect.width, track_y), 
                        self.track_height)
        
        # draw handle
        handle_x = self._get_handle_x()
        handle_color = (100, 150, 255) if self.dragging else (100, 100, 100)
        pygame.draw.circle(surface, handle_color, (handle_x, track_y), self.handle_radius)
        pygame.draw.circle(surface, (0, 0, 0), (handle_x, track_y), self.handle_radius, 1)
    
    def handle_event(self, event):
        """handle mouse events for slider interaction"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # check if clicked on or near the handle
            handle_x = self._get_handle_x()
            track_y = self.rect.centery
            dist = ((event.pos[0] - handle_x)**2 + (event.pos[1] - track_y)**2)**0.5
            if dist <= self.handle_radius + 5:
                self.dragging = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._set_value_from_x(event.pos[0])
                return True
        return False
    
    def set_position(self, x, y):
        """set slider position"""
        self.rect.x = x
        self.rect.y = y
    
    def get_value(self):
        """get current slider value"""
        return int(self.value)
    
    def set_value(self, value):
        """set slider value"""
        self.value = max(self.min_val, min(self.max_val, value))

class Dropdown:
    """
    represents a dropdown/combobox UI element
    """
    def __init__(self, x, y, width, height, options=None, font_size=14):
        """
        initializes a dropdown
        args:
            x (int): x coordinate of the dropdown
            y (int): y coordinate of the dropdown
            width (int): width of the dropdown
            height (int): height of the dropdown
            options (list): list of options to display
            font_size (int): font size
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.options = options or ["Opção 1", "Opção 2"]
        self.selected_index = 0
        self.font = pygame.font.SysFont(None, font_size)
        self.expanded = False
        self.option_height = height

    def draw(self, surface):
        # draw main button
        pygame.draw.rect(surface, (200, 200, 200), self.rect, border_radius=3)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2, border_radius=3)
        
        # draw selected text
        text_surface = self.font.render(self.options[self.selected_index], True, (0, 0, 0))
        surface.blit(text_surface, (self.rect.x + 5, self.rect.y + 5))
        
        # draw dropdown arrow
        arrow_x = self.rect.right - 15
        arrow_y = self.rect.centery
        pygame.draw.polygon(surface, (0, 0, 0), [(arrow_x - 5, arrow_y - 3), (arrow_x + 5, arrow_y - 3), (arrow_x, arrow_y + 3)])
        
        # draw dropdown list if expanded
        if self.expanded:
            for i, option in enumerate(self.options):
                option_rect = pygame.Rect(self.rect.x, self.rect.y + self.rect.height + i * self.option_height, 
                                         self.rect.width, self.option_height)
                bg_color = (150, 150, 200) if i == self.selected_index else (220, 220, 220)
                pygame.draw.rect(surface, bg_color, option_rect)
                pygame.draw.rect(surface, (0, 0, 0), option_rect, 1)
                
                text_surface = self.font.render(option, True, (0, 0, 0))
                surface.blit(text_surface, (option_rect.x + 5, option_rect.y + 5))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.expanded = not self.expanded
            elif self.expanded:
                for i in range(len(self.options)):
                    option_rect = pygame.Rect(self.rect.x, self.rect.y + self.rect.height + i * self.option_height,
                                             self.rect.width, self.option_height)
                    if option_rect.collidepoint(event.pos):
                        self.selected_index = i
                        self.expanded = False
                        return True
        return False

    def set_position(self, x, y):
        self.rect.x = x
        self.rect.y = y

    def get_selected(self):
        return self.options[self.selected_index]

    def set_options(self, options):
        self.options = options
        self.selected_index = 0

class SerialMonitor(Shape):
    """
    represents a serial monitor UI element for viewing and sending serial messages
    """
    def __init__(self, coo=(0, 0), size=(400, 500), color=(75, 75, 75)):
        """
        initializes the serial monitor
        args:
            coo (tuple): coordinates of the serial monitor (top-right position)
            size (tuple): size of the serial monitor (width, height)
            color (tuple): background color in rgb format
        """
        super().__init__(coo, color, size)
        
        self.width, self.height = size
        self.enabled = True
        self.connected = False
        
        # External checkbox reference (will be set by simulator)
        self.toggle_button = None
        
        # Port selection dropdown
        self.port_dropdown = Dropdown(0, 0, 150, 30, 
                                     options=["COM1", "COM3", "COM4", "/dev/ttyUSB0", "/dev/ttyUSB1"])
        
        # Buttons
        self.btn_connect = Button(0, 0, 80, 30, "Conectar", 14, (50, 150, 50))
        self.btn_disconnect = Button(0, 0, 80, 30, "Desconectar", 14, (150, 50, 50))
        self.btn_clear = Button(0, 0, 80, 30, "Limpar", 14, (100, 100, 150))
        self.btn_send = Button(0, 0, 60, 30, "Enviar", 14, (100, 150, 100))
        
        # Text input for sending messages
        self.text_input = TextInput(0, 0, 230, 30, max_chars=999999)
        
        # Checkbox for clearing message history
        self.checkbox_limit_messages = Checkbox(0, 0, 30, "", text_color=(255, 255, 255))
        self.checkbox_limit_messages.checked = False  # Start unchecked (don't limit)
        
        # Message history
        self.messages = []  # list of tuples (text, color)
        self.messages_wrapped_cache = {}  # cache for wrapped messages to avoid recalculating
        self.scroll_offset = 0  # Scroll offset for message history
        
        # Font for messages (increased size)
        self.font_small = pygame.font.SysFont("courier", 12)
        self.font_label = pygame.font.SysFont(None, 12, bold=True)
        
        # Position offset (top-right of screen)
        self._offset_x = 0
        self._offset_y = 0
        
        # Current message color (cycles through options)
        self.message_colors = [
            (0, 0, 0),           # Black
            (0, 100, 200),       # Blue
            (200, 0, 0),         # Red
            (0, 150, 0),         # Green
            (150, 100, 0),       # Brown
        ]
        self.current_color_index = 0
        
        # Drag and drop support (optimized)
        self.is_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.header_height = 25  # Height of the draggable header
        self.handle_radius = 5  # Radius of the grab handle
        self.mouse_over_handle = False
        
        self._update_ui_positions()

    def _update_ui_positions(self):
        """update positions of all UI elements based on monitor position"""
        x, y = self._x, self._y
        
        # Header row: port selection (checkbox is now external)
        self.port_dropdown.set_position(x + 10, y + 10)
        
        # Control buttons row with more spacing
        self.btn_connect.set_position(x + 10, y + 50)
        self.btn_disconnect.set_position(x + 105, y + 50)
        self.btn_clear.set_position(x + 200, y + 50)
        
        # Limit messages checkbox (top right of messages area)
        # Messages area starts at y + 90, so checkbox goes there
        self.checkbox_limit_messages.set_coordinates((x + self.width - 40, y + 100))
        
        # Message input area with fixed height
        self.text_input.set_position(x + 10, y + self.height - 55)
        self.btn_send.set_position(x + self.width - 80, y + self.height - 55)

    def set_coordinates(self, coo):
        """set coordinates and update UI positions"""
        super().set_coordinates(coo)
        self._update_ui_positions()

    def set_toggle_button(self, toggle_button):
        """set the external toggle button reference"""
        self.toggle_button = toggle_button
    
    def get_max_visible_messages(self):
        """calculate maximum messages that fit on screen"""
        messages_height = self.height - 150
        return int(messages_height / 18)

    def _get_messages_that_fit(self):
        """calculate how many messages fit in the available space, considering their wrapped height"""
        messages_width = self.width - 40
        chars_per_line = max(15, int((messages_width - 20) / 7))
        messages_height = self.height - 150
        available_height = messages_height - 10  # Leave 10px margin
        
        # Iterate from end to beginning to find how many messages fit
        total_height = 0
        messages_count = 0
        
        for msg_text, _ in reversed(self.messages):
            if not msg_text:
                continue
            
            # Calculate wrapped height for this message
            lines = (len(msg_text) + chars_per_line - 1) // chars_per_line
            msg_height = max(1, lines) * 18
            
            if total_height + msg_height <= available_height:
                total_height += msg_height
                messages_count += 1
            else:
                break
        
        return messages_count if messages_count > 0 else 1  # At least 1 message

    def _is_mouse_over_handle(self, mouse_x, mouse_y):
        """check if mouse is over the grab handle (optimized)"""
        handle_x = self._x + self.width - 12
        handle_y = self._y - 10
        distance = ((mouse_x - handle_x) ** 2 + (mouse_y - handle_y) ** 2) ** 0.5
        return distance <= self.handle_radius + 3  # 3px tolerance

    def handle_event(self, event):
        """handle UI events"""
        # Check if enabled using external toggle button
        if self.toggle_button:
            self.enabled = self.toggle_button.is_enabled()
        
        # If disabled, don't process other events
        if not self.enabled:
            return
        
        # Handle drag and drop of header - only from handle
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                mouse_x, mouse_y = event.pos
                # Check if mouse is over grab handle (optimized)
                if self._is_mouse_over_handle(mouse_x, mouse_y):
                    self.is_dragging = True
                    self.drag_offset_x = mouse_x - self._x
                    self.drag_offset_y = mouse_y - self._y
                    return  # Don't process other events when starting drag
            elif event.button == 4:  # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - 6)
            elif event.button == 5:  # Scroll down
                self.scroll_offset += 6
        
        # Handle mouse move (drag only if already dragging)
        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                mouse_x, mouse_y = event.pos
                new_x = mouse_x - self.drag_offset_x
                new_y = mouse_y - self.drag_offset_y
                self.set_coordinates((new_x, new_y))
                return  # Don't process other events while dragging
            else:
                # Only check hover when not dragging (optimized)
                mouse_x, mouse_y = event.pos
                self.mouse_over_handle = self._is_mouse_over_handle(mouse_x, mouse_y)
        
        # Handle mouse release
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left mouse button
                self.is_dragging = False
                return
        
        # Only process button events if not dragging (optimized)
        if not self.is_dragging:
            # Handle buttons (callbacks will be called from main.py)
            self.btn_connect.handle_event(event)
            self.btn_disconnect.handle_event(event)
            self.btn_clear.handle_event(event)
            self.btn_send.handle_event(event)
            
            # Handle other UI elements
            self.port_dropdown.handle_event(event)
            self.text_input.handle_event(event)
            self.checkbox_limit_messages.handle_event(event)
        
        # Handle text input submit (Enter key)
        if self.text_input.submit_pressed:
            text = self.text_input.get_text()
            if text and self.btn_send.callback:
                self.btn_send.callback()
            self.text_input.submit_pressed = False

    def update(self):
        """update UI elements"""
        self.text_input.update()

    def add_message(self, text, color=None):
        """add a message to the history"""
        if color is None:
            color = (0, 0, 0)
        if text:
            self.messages.append((text, color))
        
        # Clear wrapped cache when new message added
        self.messages_wrapped_cache.clear()
        
        # If limit checkbox is enabled, keep only messages that fit in display
        if self.checkbox_limit_messages.checked:
            num_fit = self._get_messages_that_fit()
            if len(self.messages) > num_fit:
                self.messages = self.messages[-num_fit:]
        else:
            # Otherwise limit to 500 messages for memory
            if len(self.messages) > 500:
                self.messages = self.messages[-500:]
        
        # Calculate total height with wrapping
        total_height = self._calculate_total_message_height()
        messages_height = self.height - 150
        
        # Auto-scroll para bottom - scroll offset = 0 means we're at the bottom
        if total_height > messages_height:
            self.scroll_offset = max(0, total_height - messages_height)
        else:
            self.scroll_offset = 0

    def clear_messages(self):
        """clear all messages"""
        self.messages = []
        self.messages_wrapped_cache.clear()
        self.scroll_offset = 0
    
    def _calculate_total_message_height(self):
        """calculate total height of all messages with wrapping (fast estimation)"""
        messages_width = self.width - 40
        chars_per_line = max(15, int((messages_width - 20) / 7))
        total_height = 0
        
        # Get messages based on limit checkbox
        if self.checkbox_limit_messages.checked:
            # Dynamically calculate how many messages fit
            num_fit = self._get_messages_that_fit()
            messages_to_count = self.messages[-num_fit:] if num_fit > 0 else []
        else:
            messages_to_count = self.messages[-200:]
        
        for msg_text, _ in messages_to_count:
            if not msg_text:
                continue
            # Fast estimation without calling _wrap_text()
            lines = (len(msg_text) + chars_per_line - 1) // chars_per_line
            total_height += max(1, lines) * 18
        
        return total_height

    def draw(self, surface):
        """draw the serial monitor"""
        # Always update enabled state from toggle button
        if self.toggle_button:
            self.enabled = self.toggle_button.is_enabled()
        
        if not self.enabled:
            return
        
        x, y = self._x, self._y
        w, h = self.width, self.height
        
        # Draw main background
        pygame.draw.rect(surface, self._color, (x, y, w, h), border_radius=10)
        pygame.draw.rect(surface, (200, 200, 200), (x, y, w, h), 2, border_radius=10)
        
        # Draw grab handle (small circle) in top-right corner
        handle_x = x + w - 12
        handle_y = y - 10
        handle_color = (100, 200, 255) if self.mouse_over_handle else (150, 150, 150)
        pygame.draw.circle(surface, handle_color, (handle_x, handle_y), self.handle_radius)
        pygame.draw.circle(surface, (100, 100, 100), (handle_x, handle_y), self.handle_radius, 1)
        
        # Draw header line
        pygame.draw.line(surface, (200, 200, 200), (x, y + 20), (x + w, y + 20), 1)
        
        # Draw control buttons
        self.btn_connect.draw(surface)
        self.btn_disconnect.draw(surface)
        self.btn_clear.draw(surface)
        
        # Draw messages area
        messages_y = y + 90
        messages_height = h - 150
        messages_width = w - 40
        
        pygame.draw.rect(surface, (240, 240, 240), (x + 10, messages_y, w - 20, messages_height), border_radius=5)
        pygame.draw.rect(surface, (150, 150, 150), (x + 10, messages_y, w - 20, messages_height), 1, border_radius=5)
        
        # Draw connection status
        status_color = (0, 200, 0) if self.connected else (200, 0, 0)
        pygame.draw.circle(surface, status_color, (x + w - 15, y + 12), 6)
        pygame.draw.circle(surface, (0, 0, 0), (x + w - 15, y + 12), 6, 1)
        
        # Calculate total height of messages
        total_height = self._calculate_total_message_height()
        
        # Clamp scroll offset to valid range
        max_scroll = max(0, total_height - messages_height)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))
        
        # Draw messages with wrapping and scrolling
        current_y = messages_y + 5  # Start from top
        
        # Get messages based on limit checkbox
        if self.checkbox_limit_messages.checked:
            # Dynamically show only messages that fit in the available space
            num_fit = self._get_messages_that_fit()
            display_messages = self.messages[-num_fit:] if num_fit > 0 else []
        else:
            # Show all messages (but still limit to last 200 for performance)
            display_messages = self.messages[-200:]
        
        # Renderizar mensagens
        for idx, (msg_text, msg_color) in enumerate(display_messages):
            if not msg_text:
                continue
            
            # Use cache key based on message index
            cache_key = len(self.messages) - len(display_messages) + idx
            if cache_key not in self.messages_wrapped_cache:
                self.messages_wrapped_cache[cache_key] = self.text_input._wrap_text(msg_text, messages_width)
            
            wrapped = self.messages_wrapped_cache[cache_key]
            
            for line in wrapped:
                if not line:
                    continue
                
                # Apply scroll offset
                draw_y = current_y - self.scroll_offset
                
                # Only draw if visible
                if messages_y <= draw_y < messages_y + messages_height:
                    try:
                        text_surf = self.font_small.render(line, True, msg_color)
                        surface.blit(text_surf, (x + 15, draw_y))
                    except:
                        pass
                
                current_y += 18
        
        # Draw scrollbar
        if total_height > messages_height:
            scroll_h = max(10, int((messages_height / total_height) * messages_height))
            # Position scrollbar based on scroll_offset
            ratio = self.scroll_offset / (total_height - messages_height) if (total_height - messages_height) > 0 else 0
            scroll_y = messages_y + int(ratio * (messages_height - scroll_h))
            scroll_y = max(messages_y, min(scroll_y, messages_y + messages_height - scroll_h))
            pygame.draw.rect(surface, (180, 180, 180), (x + w - 15, scroll_y, 5, scroll_h))
        
        # Draw limit messages checkbox only (top right corner)
        self.checkbox_limit_messages.draw(surface)
        
        # Draw separator
        pygame.draw.line(surface, (200, 200, 200), (x + 10, y + h - 59), (x + w - 10, y + h - 59), 1)
        
        # Draw input area
        self.text_input.draw(surface)
        
        # Draw send button (gray if disconnected)
        if not self.connected:
            # Save original color and set to gray
            original_color = self.btn_send.bg_color
            self.btn_send.bg_color = (120, 120, 120)
            self.btn_send.draw(surface)
            self.btn_send.bg_color = original_color
        else:
            self.btn_send.draw(surface)
        
        self.port_dropdown.draw(surface)

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
            info = pygame.display.Info()
            width = info.current_w
            height = info.current_h
        elif win == MEDIUM:
            width = 1400
            height = 750
        elif win == SMALL:
            width = 800
            height = 600

        self.__width = width
        self.__height = height
        self.__FPS = FPS
        self.__objects = []

    def start(self):

        if self.win == 'FULL':
            self.screen = pygame.display.set_mode((self.__width, self.__height),  pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode((self.__width, self.__height))

        pygame.display.set_caption("SIMULATOR")
        self.__clock = pygame.time.Clock()

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
        # Note: pygame.display.flip() is called by the caller after additional draws