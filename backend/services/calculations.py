"""Small geometry calculations shared by exercise services."""
import math


class InvalidGeometryError(ValueError):
    """The supplied points cannot describe a reliable angle."""


def calculate_angle(first, vertex, last) -> float:
    """Return the angle at vertex, in degrees, for three 2D pixel points."""
    for point in (first, vertex, last):
        if len(point) != 2:
            raise InvalidGeometryError("Each point must contain two coordinates.")
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in point):
            raise InvalidGeometryError("Point coordinates must be finite numbers.")

    first_vector = (first[0] - vertex[0], first[1] - vertex[1])
    last_vector = (last[0] - vertex[0], last[1] - vertex[1])
    first_length = math.hypot(*first_vector)
    last_length = math.hypot(*last_vector)

    if first_length < 1e-8 or last_length < 1e-8:
        raise InvalidGeometryError("An angle needs distinct points.")

    dot_product = first_vector[0] * last_vector[0] + first_vector[1] * last_vector[1]
    cosine = dot_product / (first_length * last_length)
    # Floating-point rounding must not move acos outside its valid range.
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))
