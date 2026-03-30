import csv
import argparse
from pathlib import Path

import cv2
import numpy as np


def load_binary_image(image_path, threshold=127, invert=False):
    """
    Lê a imagem e converte para binária.
    Retorna:
        - matriz binária
        - largura
        - altura
    """
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Não foi possível abrir a imagem: {image_path}")

    height, width = img.shape

    if invert:
        _, bin_img = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)
        track = bin_img == 255
    else:
        _, bin_img = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY_INV)
        track = bin_img == 255

    return track.astype(np.uint8), width, height


def find_connected_components(binary_track, min_component_size=20):
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary_track, connectivity=8
    )

    components = []
    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]
        if area < min_component_size:
            continue

        ys, xs = np.where(labels == label)
        points = np.column_stack((ys, xs))
        components.append(points)

    return components


def build_neighbor_graph(points):
    point_set = set(map(tuple, points.tolist()))
    neighbors = {}

    offsets = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]

    for p in point_set:
        y, x = p
        nbrs = []
        for dy, dx in offsets:
            q = (y + dy, x + dx)
            if q in point_set:
                nbrs.append(q)
        neighbors[p] = nbrs

    return point_set, neighbors


def order_component_points(points):
    point_set, neighbors = build_neighbor_graph(points)

    degrees = {p: len(neighbors[p]) for p in point_set}
    endpoints = [p for p, deg in degrees.items() if deg == 1]

    if endpoints:
        start = min(endpoints, key=lambda p: (p[1], p[0]))
    else:
        start = min(point_set, key=lambda p: (p[1], p[0]))

    ordered = [start]
    visited = {start}
    current = start
    previous = None

    while True:
        candidates = [n for n in neighbors[current] if n not in visited]

        if not candidates:
            break

        if previous is None or len(candidates) == 1:
            nxt = candidates[0]
        else:
            py, px = previous
            cy, cx = current
            v1 = np.array([cx - px, cy - py], dtype=float)
            v1_norm = np.linalg.norm(v1)

            if v1_norm < 1e-9:
                nxt = candidates[0]
            else:
                best_score = -1e18
                best_n = candidates[0]

                for cand in candidates:
                    ny, nx = cand
                    v2 = np.array([nx - cx, ny - cy], dtype=float)
                    v2_norm = np.linalg.norm(v2)

                    if v2_norm < 1e-9:
                        continue

                    score = np.dot(v1 / v1_norm, v2 / v2_norm)
                    if score > best_score:
                        best_score = score
                        best_n = cand

                nxt = best_n

        ordered.append(nxt)
        visited.add(nxt)
        previous = current
        current = nxt

    # converte (y,x) → (x,y)
    return np.array([(x, y) for (y, x) in ordered], dtype=float)


def center_points(points_xy, width, height):
    """
    Move origem para o centro da imagem (0,0)
    e inverte eixo Y (pra cima positivo)
    """
    cx = width / 2
    cy = height / 2

    x = (points_xy[:, 0] - cx)
    y = -(points_xy[:, 1] - cy)

    return np.column_stack((x, y))


def limit_points(points_xy, max_points=None):
    if max_points is None or len(points_xy) <= max_points:
        return points_xy

    idx = np.linspace(0, len(points_xy) - 1, max_points).astype(int)
    return points_xy[idx]


def export_to_csv(all_tracks, output_csv):
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["track_id", "point_id", "x", "y"])

        for track_id, pts in enumerate(all_tracks):
            for point_id, (x, y) in enumerate(pts):
                writer.writerow([track_id, point_id, float(x), float(y)])


def process_image(
    image_path,
    output_csv,
    threshold=127,
    min_component_size=20,
    invert=False,
    max_points=None,
):
    binary_track, width, height = load_binary_image(
        image_path, threshold=threshold, invert=invert
    )

    components = find_connected_components(
        binary_track,
        min_component_size=min_component_size
    )

    if not components:
        raise RuntimeError("Nenhum trajeto encontrado.")

    all_tracks = []

    for i, comp in enumerate(components):
        ordered = order_component_points(comp)
        centered = center_points(ordered, width, height)
        final = limit_points(centered, max_points)

        all_tracks.append(final)

        print(f"Track {i}: {len(comp)} px -> {len(final)} pontos")

    export_to_csv(all_tracks, output_csv)
    print(f"\nCSV salvo em: {output_csv}")


def main():
    parser = argparse.ArgumentParser(
        description="Imagem → CSV (sem spline, com origem no centro)"
    )
    parser.add_argument("image")
    parser.add_argument("output")
    parser.add_argument("--threshold", type=int, default=127)
    parser.add_argument("--min-size", type=int, default=20)
    parser.add_argument("--max-points", type=int, default=None)
    parser.add_argument("--invert", action="store_true")

    args = parser.parse_args()

    process_image(
        image_path=Path(args.image),
        output_csv=Path(args.output),
        threshold=args.threshold,
        min_component_size=args.min_size,
        invert=args.invert,
        max_points=args.max_points,
    )


if __name__ == "__main__":
    main()