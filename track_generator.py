import math
import random
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import splprep, splev

LEMNISCATE = 0
CIRCLE = 1

def generate_track(type=LEMNISCATE, checkpoints=24, track_rad=40, noise_level=0.12, resolution=250):
    if type == LEMNISCATE:
        return lemniscate_track(checkpoints, track_rad, noise_level, resolution)
    elif type == CIRCLE:
        return circle_track(checkpoints, track_rad, noise_level, resolution)
    else:
        raise ValueError("Invalid track type")

def circle_track(checkpoints, track_rad, noise_level, resolution):
    # Seed random generator
    SEED = None
    if SEED is None:
        SEED = random.randint(0, 2**32 - 1)
    random.seed(SEED)

    CHECKPOINTS = checkpoints
    TRACK_RADIUS = track_rad
    NOISE_LEVEL = noise_level * track_rad

    # Generate checkpoints for a circular track
    checkpoints = []
    for c in range(CHECKPOINTS):
        # Angle steps
        t = 2 * math.pi * c / CHECKPOINTS

        # Point coordinates
        x = TRACK_RADIUS * math.cos(t)
        y = TRACK_RADIUS * math.sin(t)

        # Add noise to points
        x += random.uniform(NOISE_LEVEL/3, NOISE_LEVEL)
        y += random.uniform(NOISE_LEVEL/3, NOISE_LEVEL)

        checkpoints.append((x, y))

    # Smooth the track using spline interpolation
    checkpoints = np.array(checkpoints)
    tck, u = splprep([checkpoints[:, 0], checkpoints[:, 1]], s=0, per=True)
    u_new = np.linspace(0, 1, len(checkpoints) * resolution)  # More points for smoothing
    smooth_x, smooth_y = splev(u_new, tck)

    return smooth_x, smooth_y

def lemniscate_track(checkpoints, track_rad, noise_level, resolution):
    # Seed random generator
    SEED = None
    if SEED is None:
        SEED = random.randint(0, 2**32 - 1)
    random.seed(SEED)

    CHECKPOINTS = checkpoints
    TRACK_RADIUS = track_rad
    NOISE_LEVEL = noise_level * track_rad

    # Generate checkpoints for a lemniscate-shaped track
    checkpoints = []
    for c in range(CHECKPOINTS):
        # Angle steps
        t = 2 * math.pi * c / CHECKPOINTS

        # Point coordinates
        x = TRACK_RADIUS * math.cos(t)
        y = TRACK_RADIUS * math.sin(t) * math.cos(t)  # Lemniscate function

        if c != 0 and c != CHECKPOINTS -1: 
            x += random.uniform(NOISE_LEVEL/9, NOISE_LEVEL)
            y += random.uniform(NOISE_LEVEL/9, NOISE_LEVEL)

        checkpoints.append((x, y))

    # Smooth the track using spline interpolation
    checkpoints = np.array(checkpoints)
    tck, u = splprep([checkpoints[:, 0], checkpoints[:, 1]], s=0, per=True)
    u_new = np.linspace(0, 1, len(checkpoints) * resolution)  # More points for smoothing
    smooth_x, smooth_y = splev(u_new, tck)

    return smooth_x, smooth_y

def points_in_square(x0, y0, size, x_arr, y_arr):
    """
    Returns the indices of points inside a square centered at (x0, y0) with a side length of 2 * size.
    
    Args:
        x0 (float): x-coordinate of the square's center.
        y0 (float): y-coordinate of the square's center.
        size (float): Half the side length of the square.
        x_arr (np.ndarray): Array of x-coordinates of the points.
        y_arr (np.ndarray): Array of y-coordinates of the points.

    Returns:
        list: Indices of points inside the square.
    """
    x_arr = np.array(x_arr)
    y_arr = np.array(y_arr)
    
    inside_x = (x_arr >= x0 - size) & (x_arr <= x0 + size)
    inside_y = (y_arr >= y0 - size) & (y_arr <= y0 + size)
    inside_square = inside_x & inside_y

    return np.where(inside_square)[0].tolist()
