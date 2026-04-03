from dataclasses import dataclass


@dataclass
class DetectionBorder:
    """Model that represents the track detection border."""
    height: float = 0.5
    color: str = "gray"
    border_style: str = "dashed"
    
    def to_dict(self):
        """Converts to dictionary for serialization."""
        return {
            "height": self.height,
            "color": self.color,
            "border_style": self.border_style,
            # Legacy keys for backward compatibility.
            "altura": self.height,
            "cor": self.color,
            "estilo_borda": self.border_style,
        }
    
    @classmethod
    def from_dict(cls, data):
        """Creates an instance from a dictionary."""
        if data is None:
            return cls()
        return cls(
            height=float(data.get("height", data.get("altura", 0.5))),
            color=str(data.get("color", data.get("cor", "gray"))),
            border_style=str(data.get("border_style", data.get("estilo_borda", "dashed"))),
        )

    @property
    def altura(self) -> float:
        return self.height

    @altura.setter
    def altura(self, value: float):
        self.height = value

    @property
    def cor(self) -> str:
        return self.color

    @cor.setter
    def cor(self, value: str):
        self.color = value

    @property
    def estilo_borda(self) -> str:
        return self.border_style

    @estilo_borda.setter
    def estilo_borda(self, value: str):
        self.border_style = value
