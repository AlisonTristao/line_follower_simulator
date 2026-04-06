import math
import random
import numpy as np
import csv
import json
import zipfile
from scipy.interpolate import splprep, splev

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
    
    inside_x = (x_arr >= x0 - size) & (x_arr < x0 + size)
    inside_y = (y_arr >= y0 - size) & (y_arr < y0 + size)
    inside_square = inside_x & inside_y

    return np.where(inside_square)[0].tolist()

def generate_cluster(length, width, scale, x_arr, y_arr):
    """
    Generates a cluster of points in a square area.
    
    Args:
        length (float): Length of the square.
        width (float): Width of the square.

    Returns:
        array of arrays: Array of points in the cluster.
    """

    # matriz of 3 dimensions
    cluster_matrix = []
    position = []

    # save the points useds
    processed_points = set()
    for i in range(-length//2, length//2):
        for j in range(-width//2, width//2):
            # verify if has in the square
            index_arr = points_in_square(i, j, 0.5, x_arr, y_arr)
            if len(index_arr) > 0:
                cluster_array = []
                # create the cluster
                for index in index_arr:
                    # verify if the point is already used
                    if index not in processed_points:
                        x = (x_arr[index] - i) * scale
                        y = (y_arr[index] - j) * scale
                        cluster_array.append((x, y, index))
                        processed_points.add(index)
            
                # add the cluster to the matrix
                cluster_matrix.append([])
                cluster_matrix[-1] = cluster_array
                position.append((i + length // 2, j + width // 2))

    total_points = len(x_arr)
    missing_points = set(range(total_points)) - processed_points
    if missing_points:
        print(
            f"[Clustering Warning] {len(missing_points)} points were not assigned to any cluster "
            f"(outside grid or on boundary edges)."
        )
    else:
        print(f"[Clustering] All {total_points} points were assigned to grid cells successfully.")

    return cluster_matrix, position


def process_markings(markings, length, width, scale):
    """
    Process markings into grid cells using the same square assignment
    strategy used by cluster generation (points_in_square).
    
    Args:
        markings (list): List of (x, y, angle) tuples
        length (int): Grid length
        width (int): Grid width
        scale (int): Scale factor for pixel conversion
        
    Returns:
        dict: {(row, col): [(x_pix, y_pix, angle), ...]}
    """
    marking_data = {}

    if not markings:
        return marking_data

    x_arr = np.array([m[0] for m in markings])
    y_arr = np.array([m[1] for m in markings])

    # Keep one-cell ownership per marking, mirroring generate_cluster behavior.
    processed_points = set()

    for i in range(-length // 2, length // 2):
        for j in range(-width // 2, width // 2):
            index_arr = points_in_square(i, j, 0.5, x_arr, y_arr)
            if not index_arr:
                continue

            unique_indices = [idx for idx in index_arr if idx not in processed_points]
            if not unique_indices:
                continue

            key = (i + length // 2, j + width // 2)
            if key not in marking_data:
                marking_data[key] = []

            for idx in unique_indices:
                x, y, angle = markings[idx]
                x_pix = (x - i) * scale
                y_pix = (y - j) * scale
                marking_data[key].append((x_pix, y_pix, angle))
                processed_points.add(idx)

    # Fallback for rare boundary/out-of-grid cases to avoid dropping markings.
    missing_points = set(range(len(markings))) - processed_points
    for idx in missing_points:
        x, y, angle = markings[idx]

        i = int(math.floor(x + 0.5))
        j = int(math.floor(y + 0.5))

        i = max(-length // 2, min(i, length // 2 - 1))
        j = max(-width // 2, min(j, width // 2 - 1))

        key = (i + length // 2, j + width // 2)
        if key not in marking_data:
            marking_data[key] = []

        x_pix = (x - i) * scale
        y_pix = (y - j) * scale
        marking_data[key].append((x_pix, y_pix, angle))

    return marking_data


def load_track_from_tfg(tfg_file_path):
    """
    Load track points from a .tfg file (which is a ZIP archive).
    
    Args:
        tfg_file_path (str): Path to the .tfg file
        
    Returns:
        tuple: (x_array, y_array, markings, resolution, track_height_limit, track_width_limit)
               - numpy arrays of x and y coordinates
               - optional resolution value
               - track limits from detection border metadata
    """
    x_points = []
    y_points = []
    resolution = None
    markings = []
    track_height_limit = 0.5
    track_width_limit = 1.0

    def _read_positive_float(data, *keys):
        if not isinstance(data, dict):
            return None
        for key in keys:
            if key not in data:
                continue
            try:
                value = float(data.get(key))
                if math.isfinite(value) and value > 0:
                    return value
            except (TypeError, ValueError):
                continue
        return None

    # Open the .tfg file (which is a ZIP archive)
    with zipfile.ZipFile(tfg_file_path, 'r') as zip_file:
        # List all files in the ZIP
        file_list = zip_file.namelist()
        
        # Find the JSON file generated by the current exporter.
        json_file = None
        for file_name in file_list:
            if file_name.endswith('.json') and '_segments' in file_name:
                json_file = file_name
                break
        
        # Read resolution and limits from JSON if found.
        if json_file:
            try:
                with zip_file.open(json_file) as jf:
                    json_data = json.loads(jf.read().decode('utf-8'))
                    resolution = json_data.get('exported_point_count')

                    # CSV points are exported in output unit, so prefer limits in the
                    # same unit (height/width). Fallback to *_m converted by unit_multiplier.
                    unit_multiplier = _read_positive_float(json_data, 'unit_multiplier')
                    if unit_multiplier is None:
                        unit_multiplier = 1.0

                    def _extract_limits(limit_data):
                        height_limit = _read_positive_float(limit_data, 'height', 'altura')
                        width_limit = _read_positive_float(limit_data, 'width', 'largura')

                        if height_limit is None:
                            height_m = _read_positive_float(limit_data, 'height_m', 'altura_m')
                            if height_m is not None:
                                height_limit = height_m * unit_multiplier

                        if width_limit is None:
                            width_m = _read_positive_float(limit_data, 'width_m', 'largura_m')
                            if width_m is not None:
                                width_limit = width_m * unit_multiplier

                        if width_limit is None and height_limit is not None:
                            width_limit = height_limit * 2.0
                        if height_limit is None and width_limit is not None:
                            height_limit = width_limit / 2.0

                        return height_limit, width_limit

                    size_data = json_data.get('track_size')
                    if not isinstance(size_data, dict):
                        size_data = json_data.get('tamanho_pista', {})

                    size_height, size_width = _extract_limits(size_data)
                    border_height, border_width = _extract_limits(json_data.get('detection_border', {}))

                    if size_height is not None:
                        track_height_limit = size_height
                    elif border_height is not None:
                        track_height_limit = border_height

                    if size_width is not None:
                        track_width_limit = size_width
                    elif border_width is not None:
                        track_width_limit = border_width
                    elif track_height_limit > 0:
                        track_width_limit = track_height_limit * 2.0
            except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
                print(f"[WARN] Failed to parse JSON metadata: {e}. Using defaults.")
                pass
        
        # Find track CSV (ignore markings CSV).
        track_csv = None
        for file_name in file_list:
            if file_name.endswith('.csv') and '_markings' not in file_name:
                track_csv = file_name
                break
        
        if track_csv is None:
            raise ValueError("No track CSV file found in the .tfg file")
        
        # Read the CSV file
        with zip_file.open(track_csv) as csv_file:
            # Decode bytes to string for csv reader
            text_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.reader(text_file)
            
            # Skip header row
            next(reader)
            
            # Read x and y points
            for row in reader:
                if len(row) >= 3:  # idx, x, y
                    try:
                        x = float(row[1]) 
                        y = float(row[2]) 
                        x_points.append(x)
                        y_points.append(y)
                    except (ValueError, IndexError):
                        continue
    
        # Read markings if available.
        markings_csv = None
        for file_name in file_list:
            if file_name.endswith('.csv') and '_markings' in file_name:
                markings_csv = file_name
                break

        if markings_csv:
            with zip_file.open(markings_csv) as csv_file:
                text_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(text_file)

                for row in reader:
                    try:
                        # CSV already stores Y mirrored for simulator space.
                        # Mirror the angle as well so non-orthogonal markings keep the expected direction.
                        ang_deg = float(row.get('angle_x_axis_degrees', 0.0))
                        ang = math.radians(-ang_deg)
                        x = float(row.get('x', 0.0))
                        y = float(row.get('y', 0.0))
                        markings.append((x, y, ang))
                    except (ValueError, IndexError) as e:
                        print(f"Failed to parse marking row: {e}")
                        continue

    # Convert to numpy arrays
    x_array = np.array(x_points[::-1])
    y_array = np.array(y_points[::-1])

    return x_array, y_array, markings, resolution, track_height_limit, track_width_limit