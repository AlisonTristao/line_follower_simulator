import json
import zipfile
import os
import tempfile
import shutil

from models.detection_border import DetectionBorder
from models.marking import Marking
from models.segments import CurveSegment, StraightSegment


class TrajectoryImporter:
    @staticmethod
    def load_json(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        unit_factor = data.get("unit_multiplier")
        try:
            unit_factor = float(unit_factor) if unit_factor is not None else 1.0
        except (TypeError, ValueError):
            unit_factor = 1.0
        if unit_factor <= 0:
            unit_factor = 1.0

        converted_dimensions = bool(data.get("dimensions_converted_to_output_unit", False))
        inverse_factor = (1.0 / unit_factor) if converted_dimensions else 1.0

        segment_items = data.get("segments")
        if not isinstance(segment_items, list):
            raise ValueError("Invalid JSON: missing or invalid 'segments' field.")

        segments = []
        for item in segment_items:
            if not isinstance(item, dict):
                raise ValueError("Invalid JSON: invalid segment item.")

            segment_type = item.get("type")
            if segment_type == "straight":
                length = float(item.get("length", 0.0)) * inverse_factor
                angle_degrees = float(item.get("angle_degrees", 0.0))
                segments.append(StraightSegment(length=length, angle_degrees=angle_degrees))
            elif segment_type == "curve":
                radius = float(item.get("radius", 0.0)) * inverse_factor
                side = str(item.get("side", "left"))
                central_angle_degrees = float(item.get("central_angle_degrees", 0.0))
                segments.append(
                    CurveSegment(
                        radius=radius,
                        side=side,
                        central_angle_degrees=central_angle_degrees,
                    )
                )
            else:
                raise ValueError(f"Unknown segment type in JSON: {segment_type!r}")

        markings = []
        marking_items = data.get("markings", [])
        if isinstance(marking_items, list):
            for item in marking_items:
                if not isinstance(item, dict):
                    continue
                markings.append(
                    Marking(
                        order=int(item.get("order", item.get("idx", 0))),
                        side=str(item.get("side", "left")),
                        distance=float(item.get("distance", 0.0)) * inverse_factor,
                        x=float(item.get("x", 0.0)) * inverse_factor,
                        y=float(item.get("y", 0.0)) * inverse_factor,
                        angle_x_axis=float(item.get("angle_x_axis", 0.0)),
                    )
                )

        visual_origin = data.get("visual_export_origin") if converted_dimensions else None
        if not isinstance(visual_origin, dict):
            visual_origin = data.get("visual_export_origin_m") or {}

        point_count = data.get("exported_point_count")
        output_unit = data.get("output_unit")
        auto_resolution_mode = data.get("auto_resolution_mode")
        points_per_meter = data.get("points_per_meter")

        border_item = data.get("detection_border", {})
        if border_item and isinstance(border_item, dict):
            try:
                if "height_m" in border_item:
                    border_height = float(border_item.get("height_m", 0.5))
                else:
                    border_height = float(border_item.get("height", 0.5))

                border_color = str(border_item.get("color", "gray"))
                border_style = str(border_item.get("border_style", "dashed"))
                detection_border = DetectionBorder(
                    height=border_height,
                    color=border_color,
                    border_style=border_style,
                )
            except (KeyError, ValueError, TypeError) as e:
                print(f"[WARN] Error loading detection_border: {e}. Using default.")
                detection_border = DetectionBorder()
        else:
            detection_border = DetectionBorder()

        background_image = data.get("background_image")
        if not isinstance(background_image, dict):
            background_image = None

        config = {
            "origin_x": float(visual_origin.get("x", 0.0)) * inverse_factor,
            "origin_y": float(visual_origin.get("y", 0.0)) * inverse_factor,
            "point_count": int(point_count) if point_count is not None else None,
            "unit": output_unit,
            "custom_factor": float(unit_factor) if unit_factor is not None else None,
            "auto_resolution_mode": auto_resolution_mode,
            "points_per_meter": points_per_meter,
            "background_image": background_image,
        }
        return segments, config, markings, detection_border

    @staticmethod
    def import_tfg(tfg_path):
        """Imports data from a .tfg file (ZIP with CSV and JSON)."""
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(tfg_path, "r") as zipf:
                zipf.extractall(temp_dir)

            json_files = [
                f
                for f in os.listdir(temp_dir)
                if f.endswith("_segments.json")
            ]
            if not json_files:
                raise ValueError("Invalid .tfg file: no _segments.json found.")

            json_path = os.path.join(temp_dir, json_files[0])

            segments, config, markings, detection_border = TrajectoryImporter.load_json(json_path)

            unit_factor = config.get("custom_factor", 1.0)
            if unit_factor is None:
                unit_factor = 1.0
            inverse_factor = 1.0 / float(unit_factor)

            base_name = os.path.splitext(json_files[0])[0]
            base_name = base_name.replace("_segments", "")

            markings_csv_path = os.path.join(temp_dir, f"{base_name}_markings.csv")
            chosen_markings_csv = markings_csv_path if os.path.exists(markings_csv_path) else None

            if chosen_markings_csv:
                import csv
                import math

                markings = []
                with open(chosen_markings_csv, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if not row:
                            continue

                        angle_degrees = float(row.get("angle_x_axis_degrees", 0.0))
                        angle_rad = math.radians(angle_degrees)

                        distance = float(row.get("distance", 0.0)) * inverse_factor
                        x = float(row.get("x", 0.0)) * inverse_factor
                        y = float(row.get("y", 0.0)) * inverse_factor

                        markings.append(
                            Marking(
                                order=int(row.get("idx", row.get("order", 0))),
                                side=str(row.get("side", "left")),
                                distance=distance,
                                x=x,
                                y=y,
                                angle_x_axis=angle_rad,
                            )
                        )

            background_payload = None
            background_config = config.get("background_image") if isinstance(config, dict) else None
            if isinstance(background_config, dict):
                archive_path = background_config.get("archive_path")
                if isinstance(archive_path, str) and archive_path.strip():
                    arquivo_relativo = archive_path.replace("/", os.sep)
                    caminho_arquivo = os.path.join(temp_dir, arquivo_relativo)

                    if not os.path.exists(caminho_arquivo):
                        nome_arquivo = os.path.basename(arquivo_relativo)
                        caminho_alternativo = os.path.join(temp_dir, nome_arquivo)
                        if os.path.exists(caminho_alternativo):
                            caminho_arquivo = caminho_alternativo

                    if os.path.exists(caminho_arquivo):
                        with open(caminho_arquivo, "rb") as f:
                            background_payload = {
                                "bytes": f.read(),
                                "filename": os.path.basename(caminho_arquivo),
                                "config": background_config,
                            }

            return segments, config, markings, detection_border, background_payload

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


