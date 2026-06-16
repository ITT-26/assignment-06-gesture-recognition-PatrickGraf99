# $1 gesture recognizer
from __future__ import annotations  # ??? WTF is even happening here, thanks for your help anyway chatty
import math


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def distance(self, other: Point):
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __str__(self):
        return f'({self.x}, {self.y})'

    def __repr__(self):
        return self.__str__()

class Rectangle:
    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

from templates import unistroke_templates # This import needs to be after Point exists to prevent an import error
class Recognizer:

    def __init__(self):
        self.phi = 0.5 * (-1 + math.sqrt(5))
        self.templates = {}
        for name, template in unistroke_templates.items():
            modified = self.resample_points(template)
            angle = self.get_indicative_angle(modified)
            modified = self.rotate_by(modified, -angle)
            modified = self.scale_to(modified)
            modified = self.translate_to(modified)
            self.templates[name] = modified

    def prepare_input_gesture(self, points: list[Point]) -> list[Point]:
        modified_points = points.copy()
        modified_points = self.resample_points(modified_points)
        angle = self.get_indicative_angle(modified_points)
        modified_points = self.rotate_by(modified_points, -angle)
        modified_points = self.scale_to(modified_points)
        modified_points = self.translate_to(modified_points)
        return modified_points

    def get_path_length(self, points: list[Point]) -> float:
        length = 0.0
        for i in range(1, len(points)):
            length += points[i - 1].distance(points[i])
        return float(length)

    def resample_points(self, points: list[Point], target_amount: int = 64) -> list[Point]:
        interval_length = self.get_path_length(points) / (target_amount - 1)  # Copy this from wobbrock
        distance = 0.0
        points = points.copy()
        resampled_points = [points[0]]
        i = 1

        # AI helped with rewriting the loop since python does not handle lists changing during iteration the way I would
        # have liked
        while i < len(points):
            current_distance = points[i - 1].distance(points[i])
            if distance + current_distance >= interval_length:
                x_next = points[i - 1].x + ((interval_length - distance) / current_distance) * (
                        points[i].x - points[i - 1].x)
                y_next = points[i - 1].y + ((interval_length - distance) / current_distance) * (
                        points[i].y - points[i - 1].y)
                p_next = Point(x_next, y_next)
                points.insert(i, p_next)
                resampled_points.append(p_next)
                distance = 0.0
                i += 1
            else:
                distance += current_distance
                i += 1

        if len(resampled_points) == target_amount - 1:
            resampled_points.append(Point(points[-1].x, points[-1].y))

        if len(resampled_points) != target_amount:
            print(f'Got {len(resampled_points)} points, expected {target_amount}')
            raise ValueError
        return resampled_points

    def get_centroid(self, points: list[Point]) -> Point:
        centroid_x = 0.0
        centroid_y = 0.0
        for point in points:
            centroid_x += point.x
            centroid_y += point.y
        centroid_x = centroid_x / len(points)
        centroid_y = centroid_y / len(points)
        return Point(centroid_x, centroid_y)

    def get_indicative_angle(self, points: list[Point]) -> float:
        centroid = self.get_centroid(points)
        return math.atan2(centroid.y - points[0].y, centroid.x - points[0].x)  # Steal this from Wobbrock

    def rotate_by(self, points: list[Point], angle: float) -> list[Point]:
        centroid = self.get_centroid(points)
        rotated_points = []
        for point in points:
            p_next_x = (point.x - centroid.x) * math.cos(angle) - (point.y - centroid.y) * math.sin(angle) + centroid.x
            p_next_y = (point.x - centroid.x) * math.sin(angle) + (point.y - centroid.y) * math.cos(angle) + centroid.y
            rotated_points.append(Point(p_next_x, p_next_y))

        return rotated_points

    def get_bounding_box(self, points: list[Point]) -> Rectangle:
        x_min = min(p.x for p in points)
        x_max = max(p.x for p in points)
        y_min = min(p.y for p in points)
        y_max = max(p.y for p in points)
        return Rectangle(x_min, y_min, x_max - x_min, y_max - y_min)

    def scale_to(self, points: list[Point], size: int = 250) -> list[Point]:
        bounding_box = self.get_bounding_box(points)
        if bounding_box.height == 0:  # prevent division by 0
            bounding_box.height = 0.01
        if bounding_box.width == 0:
            bounding_box.width = 0.01
        scaled_points = []
        for point in points:
            x_next = point.x * size / bounding_box.width
            y_next = point.y * size / bounding_box.height
            scaled_points.append(Point(x_next, y_next))
        return scaled_points

    def translate_to(self, points: list[Point], origin: Point | None = None) -> list[Point]:
        if not origin:
            origin = Point(0, 0)
        centroid = self.get_centroid(points)
        translated_points = []
        for point in points:
            x_next = point.x + origin.x - centroid.x
            y_next = point.y + origin.y - centroid.y
            translated_points.append(Point(x_next, y_next))

        return translated_points

    def recognize(self, points: list[Point], templates: dict[str, list[Point]], angle: float = 45.0,
                  angle_precision: float = 2.0, size: int = 250) -> tuple[str, float]:
        angle = math.radians(angle)
        angle_precision = math.radians(angle_precision)
        best = math.inf
        best_template_name = ''
        # results = []
        for name, template in templates.items():
            distance = self.distance_at_best_angle(points, template, -angle, angle, angle_precision)
            # results.append((name, distance))
            if distance < best:
                best = distance
                best_template_name = name

        # results.sort(key=lambda x: x[1])
        # for name, distance in results[:10]:
        #     print(name, distance)

        score = float(1 - best / (0.5 * ((size ** 2 + size ** 2) ** 0.5)))
        return best_template_name, score

    def distance_at_best_angle(self, points: list[Point], template: list[Point], neg_angle: float,
                               pos_angle: float, angle_precision: float) -> float:
        x_one = self.phi * neg_angle + (1 - self.phi) * pos_angle
        y_one = self.distance_at_angle(points, template, x_one)
        x_two = (1 - self.phi) * neg_angle + self.phi * pos_angle
        y_two = self.distance_at_angle(points, template, x_two)
        while math.fabs(neg_angle - pos_angle) > angle_precision:
            if y_one < y_two:
                pos_angle = x_two
                x_two = x_one
                y_two = y_one
                x_one = self.phi * neg_angle + (1 - self.phi) * pos_angle
                y_one = self.distance_at_angle(points, template, x_one)
            else:
                neg_angle = x_one
                x_one = x_two
                y_one = y_two
                x_two = (1 - self.phi) * neg_angle + self.phi * pos_angle
                y_two = self.distance_at_angle(points, template, x_two)

        return min(y_one, y_two)

    def distance_at_angle(self, points: list[Point], template: list[Point], angle: float) -> float:
        _points = self.rotate_by(points, angle)
        distance = self.path_distance(_points, template)
        return distance

    def path_distance(self, points_a: list[Point], points_b: list[Point]) -> float:
        distance = 0.0
        for i in range(len(points_a)):
            distance += points_a[i].distance(points_b[i])
        return distance / len(points_a)



