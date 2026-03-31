from dataclasses import dataclass
import math


@dataclass
class Marcacao:
    """Representação de uma marcação (waypoint) no trajeto.
    
    Attributes:
        ordem: Ordem da marcação no trajeto (qual segmento finaliza)
        lado: "esquerda" ou "direita" (relativo à direção do trajeto)
        distancia: Distância perpendicular ao trajeto em metros
        x: Coordenada X da marcação em metros
        y: Coordenada Y da marcação em metros
    """
    ordem: int
    lado: str  # "esquerda" ou "direita"
    distancia: float  # em metros
    x: float = 0.0  # será calculado
    y: float = 0.0  # será calculado
    
    @property
    def tipo(self):
        return "marcacao"
    
    def __str__(self):
        return f"Marcação #{self.ordem} | lado={self.lado} | distância={self.distancia:.3f}m | pos=({self.x:.3f}, {self.y:.3f})"
