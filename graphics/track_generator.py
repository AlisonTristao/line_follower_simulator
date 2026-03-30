import math
import random
import csv
import numpy as np
from scipy.interpolate import splprep, splev

LEMNISCATE = 0
CIRCLE = 1
CSV_TRACK = 2


def circle_checkpoints(ckeckpoints_number, track_radius, noise):
    checkpoints = []
    for c in range(ckeckpoints_number):
        t = 2 * math.pi * c / ckeckpoints_number

        x = track_radius * math.cos(t)
        y = track_radius * math.sin(t)

        x += random.uniform(noise / 2, noise)
        y += random.uniform(noise / 2, noise)

        checkpoints.append((x, y))

    return checkpoints


def lemniscate_checkpoints(ckeckpoints_number, track_radius, noise):
    checkpoints = []
    for c in range(ckeckpoints_number):
        t = 2 * math.pi * c / ckeckpoints_number

        x = track_radius * math.cos(t)
        y = track_radius * math.sin(t) * math.cos(t)

        x += random.uniform(noise / 3, noise)
        y += random.uniform(noise / 3, noise)

        checkpoints.append((x, y))

    return checkpoints

def load_track_from_csv(csv_path, track_id=0):
    """
    Lê CSV e retorna x_arr, y_arr DIRETO (sem spline)
    """
    rows = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if int(row["track_id"]) == track_id:
                rows.append((
                    int(row["point_id"]),
                    float(row["x"])/100,
                    float(row["y"])/100
                ))

    if not rows:
        raise ValueError(f"Nenhum ponto encontrado para track_id={track_id}")

    # Ordena pela sequência correta
    rows.sort(key=lambda item: item[0])

    x_arr = np.array([row[1] for row in rows], dtype=float)
    y_arr = np.array([row[2] for row in rows], dtype=float)

    return x_arr, y_arr


def generate_track(
    type=LEMNISCATE,
    checkpoints=24,
    track_rad=40,
    noise_level=0.12,
    resolution=250,
    csv_path=None,
    track_id=0
):
    """
    Agora:
    - CSV_TRACK retorna direto os pontos do CSV
    - SEM spline
    """

    # 🔥 CSV = retorno direto
    if type == CSV_TRACK:
        if csv_path is None:
            raise ValueError("csv_path precisa ser definido para CSV_TRACK")
        return load_track_from_csv(csv_path, track_id)

    # resto igual ao seu original
    SEED = None
    if SEED is None:
        SEED = random.randint(0, 2**32 - 1)
    random.seed(SEED)

    CHECKPOINTS = checkpoints
    TRACK_RADIUS = track_rad
    NOISE_LEVEL = noise_level * track_rad

    if type == CIRCLE:
        checkpoints = circle_checkpoints(CHECKPOINTS, TRACK_RADIUS, NOISE_LEVEL)
    elif type == LEMNISCATE:
        checkpoints = lemniscate_checkpoints(CHECKPOINTS, TRACK_RADIUS, NOISE_LEVEL)
    else:
        raise ValueError("Invalid track type")

    checkpoints = np.array(checkpoints)
    tck, u = splprep([checkpoints[:, 0], checkpoints[:, 1]], s=0, per=True)
    u_new = np.linspace(0, 1, len(checkpoints) * resolution)
    smooth_x, smooth_y = splev(u_new, tck)

    return smooth_x[::-1], smooth_y[::-1]


def points_in_square(x0, y0, size, x_arr, y_arr):
    x_arr = np.array(x_arr)
    y_arr = np.array(y_arr)

    inside_x = (x_arr > x0 - size) & (x_arr < x0 + size)
    inside_y = (y_arr > y0 - size) & (y_arr < y0 + size)
    inside_square = inside_x & inside_y

    return np.where(inside_square)[0].tolist()


def generate_cluster(length, width, scale, x_arr, y_arr):
    cluster_matrix = []
    position = []

    processed_points = set()
    for i in range(-length // 2, length // 2):
        for j in range(-width // 2, width // 2):
            index_arr = points_in_square(i, j, 0.5, x_arr, y_arr)

            if len(index_arr) > 0:
                cluster_array = []

                for index in index_arr:
                    if index not in processed_points:
                        x = (x_arr[index] - i) * scale
                        y = (y_arr[index] - j) * scale
                        cluster_array.append((x, y, index))
                        processed_points.add(index)

                cluster_matrix.append(cluster_array)
                position.append((i + length // 2, j + width // 2))

    return cluster_matrix, position