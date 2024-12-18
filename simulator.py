import pygame
import math
import numpy as np

class Shape:
    # initializes shape with coordinates, color, size, and angle
    def __init__(self, coo, color=None, size=None, angle=0):
        self._x = coo[0]
        self._y = coo[1]
        self._angle = angle
        self._color = color
        self._size = size
        self._pivot = (0, 0)

    # returns the center coordinates
    def get_center(self):
        return self._x, self._y

    # rotates the shape by a given angle
    def rotate(self, angle):
        self._angle += angle

    # sets the pivot point for rotations
    def set_pivot(self, pivot):
        self._pivot = pivot

    # moves the shape by dx and dy, considering rotation
    def move(self, dx, dy):
        s = dx * math.cos(-self._angle) - dy * math.sin(-self._angle)
        dy = dx * math.sin(-self._angle) + dy * math.cos(-self._angle)
        dx = s
        self._x += dx
        self._y += dy

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

    # placeholder for getting vertices (to be implemented by subclasses)
    def get_vertices(self):
        raise NotImplementedError("This method should be implemented by subclasses.")

    # updates the shape (to be implemented by subclasses)
    def update(self):
        pass

    # draws the shape on a surface (to be implemented by subclasses)
    def draw(self, surface):
        raise NotImplementedError("This method should be implemented by subclasses.")

class Car(Shape):
    # initializes the car with coordinates, color, size, and angle
    def __init__(self, coo, color=(255, 0, 0), size=100, angle=30):
        super().__init__(coo, color, size, angle)
        self._x = coo[0] + math.cos(math.sin(angle))
        self._y = 2 * coo[1] - size
        self.update()
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
        self.screen_size = screen_size
        self.visible = visible
        self.point_spacing = point_spacing
        self._center = (self.screen_size[0] // 2, self.screen_size[1] // 2)

        # create the matrix of points and walls
        self.matrix = []
        for i in range(size[0]):
            linha = []
            for j in range(size[1]):
                if i == 0 or i == size[0] - 1 or j == 0 or j == size[1] - 1:
                    linha.append(Wall())
                else:
                    linha.append(Default())
            self.matrix.append(linha)

    # sets a point in the track to a specific type
    def set_point(self, row, col, obj_type):
        if 0 <= row < self._size[0] and 0 <= col < self._size[1]:
            self.matrix[row][col] = obj_type

    # sets the center of the track
    def set_center(self, coo):
        self._center = coo

    # draws the track on the surface
    def draw(self, surface):
        x0, y0 = int(self._x // self.point_spacing), int(self._y // self.point_spacing)
        d = (self._center[0] - self._x, self._center[1] - self._y)
        points = self.points_in_circle(np.array(self.matrix), x0, y0, self.visible)

        for i, j in points:
            x = i * self.point_spacing + d[0]
            y = j * self.point_spacing + d[1]

            x, y = self.rotate_point((x, y), self._pivot, self._angle)

            self.matrix[i][j].set_coordinates((x, y))
            self.matrix[i][j].set_angle(-self._angle)
            self.matrix[i][j].draw(surface)

    # returns the points within a circle
    def points_in_circle(self, matrix, x0, y0, r):
        rows, cols = matrix.shape
        x, y = np.ogrid[:rows, :cols]
        dist_sq = (x - x0) ** 2 + (y - y0) ** 2
        return np.argwhere(dist_sq <= r ** 2)

    # rotates a point around a pivot
    def rotate_point(self, coo, pivot, theta):
        ox, oy = pivot
        translated_x = coo[0] - ox
        translated_y = coo[1] - oy
        rotated_x = translated_x * math.cos(theta) - translated_y * math.sin(theta)
        rotated_y = translated_x * math.sin(theta) + translated_y * math.cos(theta)
        return rotated_x + ox, rotated_y + oy

class Simulator:
    __background = (200, 200, 200)

    # initializes the simulator
    def __init__(self):
        pygame.init()
        self.__width = 800
        self.__height = 600
        self.__screen = pygame.display.set_mode((self.__width, self.__height))
        self.__clock = pygame.time.Clock()
        self.__running = True
        self.__FPS = 60
        self.__objects = []

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

    # updates all objects in the simulator
    def update(self):
        if not self.__verify_objects():
            return
        for obj in self.__objects:
            obj.update()

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

# create the simulator
simulator = Simulator()

track = Track((100, 100), 150, 5)
simulator.add(track)

# add the car
car = Car(simulator.get_center())
simulator.add(car)

track.set_center(car.get_center())
track.set_pivot(car.get_center())

# simulator loop
while simulator.is_running():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            simulator.stop_running()

    # handle keyboard input
    keys = pygame.key.get_pressed()
    dx, dy = 0, 0
    theta = 0

    # control the track (world)
    if keys[pygame.K_LEFT]:
        dx = -5
    if keys[pygame.K_RIGHT]:
        dx = 5
    if keys[pygame.K_UP]:
        dy = -5
    if keys[pygame.K_DOWN]:
        dy = 5
    if keys[pygame.K_a]:
        theta = 0.01
    if keys[pygame.K_d]:
        theta = -0.01

    # update the world
    track.rotate(theta)
    track.move(dx, dy)

    simulator.step()
