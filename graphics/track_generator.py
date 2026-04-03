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
        print(f"[Aviso Clustering] {len(missing_points)} pontos NÃO foram adicionados a nenhum cluster! (Fora do grid ou limites exatos)")
    else:
        print(f"[Clustering] Todos os {total_points} pontos foram adicionados com sucesso ao grid.")

    return cluster_matrix, position


def process_markings(markings, length, width, scale):
    """
    Process markings into grid cells.
    
    Args:
        markings (list): List of (x, y, angle) tuples
        length (int): Grid length
        width (int): Grid width
        scale (int): Scale factor for pixel conversion
        
    Returns:
        dict: {(row, col): [(x_pix, y_pix, angle), ...]}
    """
    marking_data = {}
    
    for x, y, angle in markings:
        i = int(x)
        j = int(y)
        ''
        #if -length//2 <= i < length//2 and -width//2 <= j < width//2:
        row = i + length // 2
        col = j + width // 2
        key = (row, col)
        
        x_pix = (x - i) * scale
        y_pix = (y - j) * scale
        
        if key not in marking_data:
            marking_data[key] = []
        
        marking_data[key].append((x_pix, y_pix, angle))
    
    return marking_data


def load_track_from_tfg(tfg_file_path):
    """
    Load track points from a .tfg file (which is a ZIP archive).
    
    Args:
        tfg_file_path (str): Path to the .tfg file
        
    Returns:
        tuple: (x_array, y_array, markings, resolution, limites_altura, limites_largura, fator_multiplicador)
               - numpy arrays of x and y coordinates and the resolution value
               - limites_altura, limites_largura: altura and largura from borda_deteccao
               - fator_multiplicador: factor for scaling the track dimensions
    """
    x_points = []
    y_points = []
    resolution = None
    fator_multiplicador = None
    markings = []
    limites_altura = 0.5  # default
    limites_largura = 1.0  # default (altura * 2)

    # Open the .tfg file (which is a ZIP archive)
    with zipfile.ZipFile(tfg_file_path, 'r') as zip_file:
        # List all files in the ZIP
        file_list = zip_file.namelist()
        
        # Find the JSON file (ends with _segmentos.json or similar)
        json_file = None
        for file_name in file_list:
            if file_name.endswith('.json') and '_segmentos' in file_name:
                json_file = file_name
                break
        
        # Read resolution and limites from JSON if found
        if json_file:
            try:
                with zip_file.open(json_file) as jf:
                    json_data = json.loads(jf.read().decode('utf-8'))
                    resolution = json_data.get('qtd_pontos_exportados')

                    # Ler dados de limites da pista (borda_deteccao)
                    borda_dados = json_data.get('borda_deteccao', {})
                    if borda_dados:
                        # Altura está em metros (altura_m) ou em unidades (altura)
                        limites_altura = float(borda_dados.get('altura', 0.5))
                        limites_largura = limites_altura * 2.0 
            except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
                print(f"[WARN] Erro ao ler JSON: {e}. Usando valores padrão.")
                pass
        
        # Find the track CSV file (ends with .csv and is not _marcacoes.csv)
        track_csv = None
        for file_name in file_list:
            if file_name.endswith('.csv') and '_marcacoes' not in file_name:
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
                        # multiplica todos os valores do vetor pelo fator multiplicador para converter para metros
                        x = float(row[1]) 
                        y = float(row[2]) 
                        x_points.append(x)
                        y_points.append(y)
                    except (ValueError, IndexError):
                        continue
    
        # Read markings if the file exists
        markings_csv = None
        for file_name in file_list:
            if file_name.endswith('.csv') and '_marcacoes' in file_name:       
                markings_csv = file_name
                break

        if markings_csv:
            with zip_file.open(markings_csv) as csv_file:
                text_file = csv_file.read().decode('utf-8').splitlines()       
                reader = csv.reader(text_file)

                # Skip header row
                try:
                    next(reader)
                except StopIteration:
                    pass

                for row in reader:
                    try:
                        # row[3] is angle in degrees, convert to radians   
                        ang_deg = float(row[3])
                        ang = math.radians(ang_deg)
                        # multiplica os valores de x e y pelo fator multiplicador para converter para metros
                        x = float(row[4])
                        y = float(row[5])
                        markings.append((x, y, ang))
                    except (ValueError, IndexError) as e:
                        print(f"Erro ao processar marcação: {e}")
                        continue

    # Convert to numpy arrays
    x_array = np.array(x_points[::-1])
    y_array = np.array(y_points[::-1])

    return x_array, y_array, markings, resolution, limites_altura, limites_largura