from dataclasses import dataclass


@dataclass
class SegmentoReta:
    comprimento: float
    angulo_graus: float

    @property
    def tipo(self) -> str:
        return "reta"


@dataclass
class SegmentoCurva:
    raio: float
    lado: str  # 'esquerda' ou 'direita'
    angulo_central_graus: float

    @property
    def tipo(self) -> str:
        return "curva"
