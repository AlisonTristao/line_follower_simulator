from dataclasses import dataclass


@dataclass
class BordaDeteccao:
    """Modelo para representar a borda de detecção da pista."""
    altura: float = 0.5  # A altura em metros (configurável)
    cor: str = "gray"  # Cor da borda (fixo em cinza)
    estilo_borda: str = "dashed"  # Tipo de borda (fixo em tracejado)
    
    def to_dict(self):
        """Converte para dicionário para serialização."""
        return {
            "altura": self.altura,
            "cor": self.cor,
            "estilo_borda": self.estilo_borda,
        }
    
    @classmethod
    def from_dict(cls, data):
        """Cria uma instância a partir de um dicionário."""
        if data is None:
            return cls()
        return cls(
            altura=float(data.get("altura", 0.5)),
            cor=str(data.get("cor", "gray")),
            estilo_borda=str(data.get("estilo_borda", "dashed")),
        )
