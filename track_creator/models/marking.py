from dataclasses import dataclass
import math


@dataclass
class Marking:
    """Represents a trajectory marking (waypoint)."""
    order: int
    side: str  # "left" or "right"
    distance: float  # in meters
    x: float = 0.0
    y: float = 0.0
    angle_x_axis: float = 0.0  # in radians

    def __post_init__(self):
        self.side = _normalize_side(self.side)
    
    @property
    def type(self):
        return "marking"

    @property
    def tipo(self):
        return "marcacao"

    @property
    def ordem(self) -> int:
        return self.order

    @ordem.setter
    def ordem(self, value: int):
        self.order = value

    @property
    def lado(self) -> str:
        return _to_legacy_side(self.side)

    @lado.setter
    def lado(self, value: str):
        self.side = _normalize_side(value)

    @property
    def distancia(self) -> float:
        return self.distance

    @distancia.setter
    def distancia(self, value: float):
        self.distance = value

    @property
    def angulo_eixo_x(self) -> float:
        return self.angle_x_axis

    @angulo_eixo_x.setter
    def angulo_eixo_x(self, value: float):
        self.angle_x_axis = value
    
    def __str__(self):
        angle_degrees = math.degrees(self.angle_x_axis)
        return (
            f"Marking #{self.order} | side={self.side} | distance={self.distance:.3f}m | "
            f"pos=({self.x:.3f}, {self.y:.3f}) | angle={angle_degrees:.2f}deg"
        )


def _normalize_side(side: str) -> str:
    if side == "esquerda":
        return "left"
    if side == "direita":
        return "right"
    return side


def _to_legacy_side(side: str) -> str:
    if side == "left":
        return "esquerda"
    if side == "right":
        return "direita"
    return side
