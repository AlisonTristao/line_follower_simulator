from dataclasses import dataclass


@dataclass
class StraightSegment:
    length: float
    angle_degrees: float

    @property
    def type(self) -> str:
        return "straight"

    @property
    def tipo(self) -> str:
        return "reta"

    @property
    def comprimento(self) -> float:
        return self.length

    @comprimento.setter
    def comprimento(self, value: float):
        self.length = value

    @property
    def angulo_graus(self) -> float:
        return self.angle_degrees

    @angulo_graus.setter
    def angulo_graus(self, value: float):
        self.angle_degrees = value


@dataclass
class CurveSegment:
    radius: float
    side: str  # 'left' or 'right'
    central_angle_degrees: float

    def __post_init__(self):
        self.side = _normalize_side(self.side)

    @property
    def type(self) -> str:
        return "curve"

    @property
    def tipo(self) -> str:
        return "curva"

    @property
    def raio(self) -> float:
        return self.radius

    @raio.setter
    def raio(self, value: float):
        self.radius = value

    @property
    def lado(self) -> str:
        return _to_legacy_side(self.side)

    @lado.setter
    def lado(self, value: str):
        self.side = _normalize_side(value)

    @property
    def angulo_central_graus(self) -> float:
        return self.central_angle_degrees

    @angulo_central_graus.setter
    def angulo_central_graus(self, value: float):
        self.central_angle_degrees = value


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
