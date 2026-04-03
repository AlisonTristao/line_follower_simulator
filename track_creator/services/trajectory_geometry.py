import math

from models.segments import CurveSegment, StraightSegment


class TrajectoryGeometry:
    @staticmethod
    def recalculate_poses(trajectory):
        trajectory.poses = [(0.0, 0.0, 0.0)]

        for segment in trajectory.segments:
            x0, y0, heading0 = trajectory.poses[-1]

            if isinstance(segment, StraightSegment):
                heading1 = math.radians(segment.angle_degrees)
                x1 = x0 + segment.length * math.cos(heading1)
                y1 = y0 + segment.length * math.sin(heading1)
                trajectory.poses.append((x1, y1, heading1))

            elif isinstance(segment, CurveSegment):
                x1, y1, heading1 = TrajectoryGeometry.curve_end(
                    x0,
                    y0,
                    heading0,
                    segment.radius,
                    segment.side,
                    segment.central_angle_degrees,
                )
                trajectory.poses.append((x1, y1, heading1))

    @staticmethod
    def curve_end(x0, y0, heading0, radius, side, central_angle_degrees):
        side = _normalize_side(side)
        direction = 1 if side == "left" else -1
        central_angle_rad = math.radians(central_angle_degrees)

        cx = x0 + direction * radius * (-math.sin(heading0))
        cy = y0 + direction * radius * math.cos(heading0)

        angle_start = math.atan2(y0 - cy, x0 - cx)
        angle_end = angle_start - direction * central_angle_rad

        x1 = cx + radius * math.cos(angle_end)
        y1 = cy + radius * math.sin(angle_end)

        delta = 0.001
        angle_previous = angle_start + (angle_end - angle_start) * (1.0 - delta)
        px = cx + radius * math.cos(angle_previous)
        py = cy + radius * math.sin(angle_previous)

        heading1 = math.atan2(y1 - py, x1 - px)
        return x1, y1, TrajectoryGeometry.normalize_angle(heading1)

    @staticmethod
    def normalize_angle(angle):
        while angle <= -math.pi:
            angle += 2 * math.pi
        while angle > math.pi:
            angle -= 2 * math.pi
        return angle

    @staticmethod
    def segment_length(segment):
        if isinstance(segment, StraightSegment):
            return abs(segment.length)
        if isinstance(segment, CurveSegment):
            return abs(math.radians(segment.central_angle_degrees) * segment.radius)
        return 0.0

    @staticmethod
    def total_length(trajectory):
        return sum(TrajectoryGeometry.segment_length(segment) for segment in trajectory.segments)

    @staticmethod
    def dense_trajectory_points(trajectory, min_curve_steps=40):
        if not trajectory.segments:
            return [(0.0, 0.0)]

        points = [(0.0, 0.0)]
        x0, y0, heading0 = 0.0, 0.0, 0.0

        for segment in trajectory.segments:
            if isinstance(segment, StraightSegment):
                heading1 = math.radians(segment.angle_degrees)
                x1 = x0 + segment.length * math.cos(heading1)
                y1 = y0 + segment.length * math.sin(heading1)
                points.append((x1, y1))
                x0, y0, heading0 = x1, y1, heading1

            elif isinstance(segment, CurveSegment):
                curve_steps = max(min_curve_steps, int(abs(segment.central_angle_degrees) / 180.0 * 120))
                new_points = TrajectoryGeometry.sample_curve(
                    x0,
                    y0,
                    heading0,
                    segment.radius,
                    segment.side,
                    segment.central_angle_degrees,
                    curve_steps,
                )
                points.extend(new_points[1:])
                x0, y0, heading0 = TrajectoryGeometry.curve_end(
                    x0,
                    y0,
                    heading0,
                    segment.radius,
                    segment.side,
                    segment.central_angle_degrees,
                )

        return points

    @staticmethod
    def segment_trajectory_points(trajectory, min_curve_steps=40):
        if not trajectory.segments:
            return []

        segment_points = []
        x0, y0, heading0 = 0.0, 0.0, 0.0

        for segment in trajectory.segments:
            if isinstance(segment, StraightSegment):
                heading1 = math.radians(segment.angle_degrees)
                x1 = x0 + segment.length * math.cos(heading1)
                y1 = y0 + segment.length * math.sin(heading1)
                segment_points.append([(x0, y0), (x1, y1)])
                x0, y0, heading0 = x1, y1, heading1

            elif isinstance(segment, CurveSegment):
                curve_steps = max(min_curve_steps, int(abs(segment.central_angle_degrees) / 180.0 * 120))
                new_points = TrajectoryGeometry.sample_curve(
                    x0,
                    y0,
                    heading0,
                    segment.radius,
                    segment.side,
                    segment.central_angle_degrees,
                    curve_steps,
                )
                segment_points.append(new_points)
                x0, y0, heading0 = TrajectoryGeometry.curve_end(
                    x0,
                    y0,
                    heading0,
                    segment.radius,
                    segment.side,
                    segment.central_angle_degrees,
                )

        return segment_points

    @staticmethod
    def sample_curve(x0, y0, heading0, radius, side, central_angle_degrees, steps):
        side = _normalize_side(side)
        direction = 1 if side == "left" else -1
        central_angle_rad = math.radians(central_angle_degrees)

        cx = x0 + direction * radius * (-math.sin(heading0))
        cy = y0 + direction * radius * math.cos(heading0)

        angle_start = math.atan2(y0 - cy, x0 - cx)
        angle_end = angle_start - direction * central_angle_rad

        points = []
        for i in range(steps + 1):
            t = i / steps
            angle = angle_start + (angle_end - angle_start) * t
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.append((x, y))
        return points

    @staticmethod
    def point_on_segment(x0, y0, heading0, segment, local_distance):
        if isinstance(segment, StraightSegment):
            heading1 = math.radians(segment.angle_degrees)
            x = x0 + local_distance * math.cos(heading1)
            y = y0 + local_distance * math.sin(heading1)
            return x, y

        if isinstance(segment, CurveSegment):
            direction = 1 if segment.side == "left" else -1
            total_angle_rad = math.radians(segment.central_angle_degrees)
            total_length = abs(total_angle_rad * segment.radius)
            if total_length == 0:
                return x0, y0

            fraction = max(0.0, min(1.0, local_distance / total_length))
            local_angle = fraction * total_angle_rad

            cx = x0 + direction * segment.radius * (-math.sin(heading0))
            cy = y0 + direction * segment.radius * math.cos(heading0)
            angle_start = math.atan2(y0 - cy, x0 - cx)
            angle = angle_start - direction * local_angle
            x = cx + segment.radius * math.cos(angle)
            y = cy + segment.radius * math.sin(angle)
            return x, y

        return x0, y0

    @staticmethod
    def sample_by_count(trajectory, point_count):
        if not trajectory.segments:
            return [(0.0, 0.0)]
        if point_count <= 1:
            return [(0.0, 0.0)]

        total_length = TrajectoryGeometry.total_length(trajectory)
        if total_length == 0:
            return [(0.0, 0.0)] * point_count

        targets = [i * total_length / (point_count - 1) for i in range(point_count)]
        result = []

        start_poses = trajectory.poses[:-1]
        segment_lengths = [TrajectoryGeometry.segment_length(seg) for seg in trajectory.segments]

        segment_index = 0
        accumulated = 0.0

        for target in targets:
            while (
                segment_index < len(trajectory.segments) - 1
                and accumulated + segment_lengths[segment_index] < target
            ):
                accumulated += segment_lengths[segment_index]
                segment_index += 1

            segment = trajectory.segments[segment_index]
            x0, y0, heading0 = start_poses[segment_index]
            local_distance = target - accumulated
            result.append(TrajectoryGeometry.point_on_segment(x0, y0, heading0, segment, local_distance))

        return result

    @staticmethod
    def average_spacing(trajectory, point_count):
        if point_count <= 1:
            return 0.0
        total_length = TrajectoryGeometry.total_length(trajectory)
        if total_length == 0:
            return 0.0
        return total_length / (point_count - 1)

    @staticmethod
    def compute_marking_position(trajectory, segment_index, side, distance):
        if segment_index < 0 or segment_index >= len(trajectory.segments):
            return None

        side = _normalize_side(side)
        segment = trajectory.segments[segment_index]
        x, y, heading_final = trajectory.poses[segment_index + 1]

        if isinstance(segment, StraightSegment):
            heading_tangent = math.radians(segment.angle_degrees)
        elif isinstance(segment, CurveSegment):
            x0, y0, heading0 = trajectory.poses[segment_index]
            length = TrajectoryGeometry.segment_length(segment)
            delta = min(0.01, length * 0.1)
            if length <= 0 or delta <= 0:
                heading_tangent = heading_final
            else:
                x_prev, y_prev = TrajectoryGeometry.point_on_segment(
                    x0,
                    y0,
                    heading0,
                    segment,
                    max(0.0, length - delta),
                )
                dx = x - x_prev
                dy = y - y_prev
                if abs(dx) < 1e-12 and abs(dy) < 1e-12:
                    heading_tangent = heading_final
                else:
                    heading_tangent = math.atan2(dy, dx)
        else:
            heading_tangent = heading_final

        direction = 1 if side == "left" else -1
        perpendicular_heading = TrajectoryGeometry.normalize_angle(
            heading_tangent + direction * math.pi / 2
        )

        marking_x = x + distance * math.cos(perpendicular_heading)
        marking_y = y + distance * math.sin(perpendicular_heading)
        return marking_x, marking_y, perpendicular_heading

def _normalize_side(side: str) -> str:
    if side == "esquerda":
        return "left"
    if side == "direita":
        return "right"
    return side
