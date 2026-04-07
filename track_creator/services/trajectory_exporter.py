import csv
import json
import zipfile
import os
import tempfile
import shutil
from dataclasses import asdict

from services.trajectory_geometry import TrajectoryGeometry


class TrajectoryExporter:
    @staticmethod
    def _convert_segment_to_unit(segment_item, factor):
        item = dict(segment_item)
        segment_type = item.get("type")
        if segment_type == "straight":
            if "length" in item:
                item["length"] = float(item["length"]) * factor
        elif segment_type == "curve":
            if "radius" in item:
                item["radius"] = float(item["radius"]) * factor
        return item

    @staticmethod
    def _convert_marking_to_unit(marking_item, factor):
        item = dict(marking_item)
        for key in ("distance", "x", "y"):
            if key in item:
                item[key] = float(item[key]) * factor
        return item

    @staticmethod
    def get_unit_factor(unit, custom_factor):
        unit_map = {
            "m": 1.0,
            "cm": 0.01,
            "mm": 0.001,
        }

        if unit in unit_map:
            return unit_map[unit], unit

        factor = float(custom_factor)
        if factor <= 0:
            raise ValueError("Invalid custom factor. Use a number greater than zero.")
        return factor, "custom"

    @staticmethod
    def _build_json_data(
        trajectory,
        point_count,
        output_unit,
        factor,
        origin_x,
        origin_y,
        auto_resolution_mode=True,
        points_per_meter="10",
        background_image_config=None,
    ):
        segments_data = []
        for i, segment in enumerate(trajectory.segments, start=1):
            item = asdict(segment)
            segment_type = getattr(segment, "type", "unknown")

            item["order"] = i
            item["type"] = segment_type

            segments_data.append(TrajectoryExporter._convert_segment_to_unit(item, factor))

        markings_data = []
        if hasattr(trajectory, "markings") and trajectory.markings:
            for marking in trajectory.markings:
                item = asdict(marking)
                markings_data.append(TrajectoryExporter._convert_marking_to_unit(item, factor))

        average_spacing_m = (
            TrajectoryGeometry.average_spacing(trajectory, point_count) if point_count is not None else None
        )
        average_spacing_output = average_spacing_m * factor if average_spacing_m is not None else None
        total_length_output = TrajectoryGeometry.total_length(trajectory) * factor

        border_data = {}
        if hasattr(trajectory, "detection_border") and trajectory.detection_border:
            height_m = trajectory.detection_border.height
            border_data = {
                "height_m": height_m,
                "height": height_m * factor,
                "color": trajectory.detection_border.color,
                "border_style": trajectory.detection_border.border_style,
            }

        data = {
            "trajectory_origin_m": {"x": 0.0, "y": 0.0},
            "visual_export_origin_m": {"x": origin_x, "y": origin_y},
            "trajectory_origin": {"x": 0.0, "y": 0.0},
            "visual_export_origin": {"x": origin_x * factor, "y": origin_y * factor},
            "total_length_m": TrajectoryGeometry.total_length(trajectory),
            "total_length": total_length_output,
            "exported_point_count": point_count,
            "average_point_spacing_m": average_spacing_m,
            "average_point_spacing": average_spacing_output,
            "output_unit": output_unit,
            "unit_multiplier": factor,
            "dimensions_converted_to_output_unit": True,
            "auto_resolution_mode": auto_resolution_mode,
            "points_per_meter": points_per_meter,
            "segments": segments_data,
            "markings": markings_data,
            "detection_border": border_data,
        }
        if background_image_config:
            data["background_image"] = background_image_config
        return data

    @staticmethod
    def save_project_json(
        json_path,
        trajectory,
        point_count,
        unit,
        custom_factor,
        origin_x,
        origin_y,
        auto_resolution_mode=True,
        points_per_meter="10",
        background_image_config=None,
    ):
        factor, output_unit = TrajectoryExporter.get_unit_factor(unit, custom_factor)
        data = TrajectoryExporter._build_json_data(
            trajectory=trajectory,
            point_count=point_count,
            output_unit=output_unit,
            factor=factor,
            origin_x=origin_x,
            origin_y=origin_y,
            auto_resolution_mode=auto_resolution_mode,
            points_per_meter=points_per_meter,
            background_image_config=background_image_config,
        )

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def export_csv_and_json(
        csv_path,
        trajectory,
        point_count,
        unit,
        custom_factor,
        origin_x,
        origin_y,
        auto_resolution_mode=True,
        points_per_meter="10",
        background_image_config=None,
    ):
        points = TrajectoryGeometry.sample_by_count(trajectory, point_count)
        points = points[::-1]

        factor, _ = TrajectoryExporter.get_unit_factor(unit, custom_factor)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["idx", "x", "y"])
            for i, (x, y) in enumerate(points):
                x_converted = (x - origin_x) * factor
                y_converted = -((y - origin_y) * factor)
                writer.writerow([i, f"{x_converted:.6f}", f"{y_converted:.6f}"])

        json_path = csv_path.rsplit(".", 1)[0] + "_segments.json"
        TrajectoryExporter.save_project_json(
            json_path=json_path,
            trajectory=trajectory,
            point_count=point_count,
            unit=unit,
            custom_factor=custom_factor,
            origin_x=origin_x,
            origin_y=origin_y,
            auto_resolution_mode=auto_resolution_mode,
            points_per_meter=points_per_meter,
            background_image_config=background_image_config,
        )

        if trajectory.markings:
            import math

            markings_path = csv_path.rsplit(".", 1)[0] + "_markings.csv"
            with open(markings_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["idx", "side", "distance", "angle_x_axis_degrees", "x", "y"])
                for marking in trajectory.markings:
                    angle_degrees = math.degrees(marking.angle_x_axis)
                    distance_converted = marking.distance * factor
                    x_converted = (marking.x - origin_x) * factor
                    y_converted = -((marking.y - origin_y) * factor)
                    writer.writerow(
                        [
                            marking.order,
                            marking.side,
                            f"{distance_converted:.2f}",
                            f"{angle_degrees:.2f}",
                            f"{x_converted:.6f}",
                            f"{y_converted:.6f}",
                        ]
                    )

        return json_path

    @staticmethod
    def export_tfg(
        tfg_path,
        trajectory,
        point_count,
        unit,
        custom_factor,
        origin_x,
        origin_y,
        auto_resolution_mode=True,
        points_per_meter="10",
        background_image_payload=None,
    ):
        """Exports all data to a single .tfg file (ZIP with CSVs and JSON)."""
        temp_dir = tempfile.mkdtemp()
        try:
            base_name = os.path.splitext(os.path.basename(tfg_path))[0]
            temp_csv_path = os.path.join(temp_dir, f"{base_name}.csv")

            background_json_config = None
            background_archive_path = None
            background_temp_path = None
            if background_image_payload and background_image_payload.get("bytes"):
                background_filename = os.path.basename(background_image_payload.get("filename") or "imagem_fundo.png")
                background_archive_path = f"background/{background_filename}"
                background_temp_path = os.path.join(temp_dir, background_filename)

                background_json_config = dict(background_image_payload.get("config") or {})
                background_json_config["archive_path"] = background_archive_path

            temp_json_path = TrajectoryExporter.export_csv_and_json(
                temp_csv_path,
                trajectory,
                point_count,
                unit,
                custom_factor,
                origin_x,
                origin_y,
                auto_resolution_mode,
                points_per_meter,
                background_image_config=background_json_config,
            )

            if background_temp_path and background_image_payload and background_image_payload.get("bytes"):
                with open(background_temp_path, "wb") as f:
                    f.write(background_image_payload["bytes"])

            with zipfile.ZipFile(tfg_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(temp_csv_path, f"{base_name}.csv")
                zipf.write(temp_json_path, os.path.basename(temp_json_path))

                markings_path = temp_csv_path.rsplit(".", 1)[0] + "_markings.csv"
                if os.path.exists(markings_path):
                    zipf.write(markings_path, os.path.basename(markings_path))

                if background_temp_path and background_archive_path and os.path.exists(background_temp_path):
                    zipf.write(background_temp_path, background_archive_path)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
