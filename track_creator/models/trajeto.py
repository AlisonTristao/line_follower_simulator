from models.marcacao import Marcacao
from models.borda_deteccao import BordaDeteccao
from copy import deepcopy


class AcaoHistorico:
    """Representa uma ação no histórico de undo/redo."""
    def __init__(self, tipo, indice, segmento, marcacao, segmento_novo=None, marcacao_anterior=None):
        self.tipo = tipo  # 'adicionar', 'inserir', 'remover', 'atualizar', 'modificar_marcacao'
        self.indice = indice  # Índice onde a ação ocorreu
        self.segmento = segmento  # Cópia do segmento (anterior para atualizar, removido para remover)
        self.segmento_novo = segmento_novo  # Novo segmento (apenas para 'atualizar')
        self.marcacao = marcacao  # Cópia da marcação (nova para 'modificar_marcacao')
        self.marcacao_anterior = marcacao_anterior  # Cópia anterior da marcação (apenas para 'modificar_marcacao')


class Trajeto:
    def __init__(self):
        self.segmentos = []
        self.historico = []  # Pilha de ações (AcaoHistorico)
        self.historico_desfazer = []  # Pilha para refazer
        self.marcacoes = []  # Lista de marcações (waypoints)
        self.poses = [(0.0, 0.0, 0.0)]  # (x, y, heading_rad)
        self.borda_deteccao = BordaDeteccao()  # Borda de detecção (altura configurável)
    
    @property
    def segmentos_desfeitos(self):
        """Para compatibilidade com código anterior."""
        return self.historico_desfazer
    
    @segmentos_desfeitos.setter
    def segmentos_desfeitos(self, value):
        """Para compatibilidade com código anterior."""
        self.historico_desfazer = value

    def adicionar_segmento(self, segmento):
        self.segmentos.append(segmento)
        # Cria marcação padrão para este segmento
        indice_marcacao = len(self.marcacoes)
        marcacao = Marcacao(ordem=indice_marcacao, lado="esquerda", distancia=0.5, x=0.0, y=0.0)
        self.marcacoes.append(marcacao)
        
        # Adiciona ação ao histórico
        acao = AcaoHistorico('adicionar', len(self.segmentos) - 1, deepcopy(segmento), deepcopy(marcacao))
        self.historico.append(acao)
        self.historico_desfazer.clear()

    def inserir_segmento(self, indice, segmento):
        if indice < 0:
            indice = 0
        if indice > len(self.segmentos):
            indice = len(self.segmentos)
        self.segmentos.insert(indice, segmento)
        # Insere marcação no mesmo índice
        marcacao = Marcacao(ordem=indice, lado="esquerda", distancia=0.5, x=0.0, y=0.0)
        self.marcacoes.insert(indice, marcacao)
        # Atualiza ordem de todas as marcações posteriores
        for i in range(indice + 1, len(self.marcacoes)):
            self.marcacoes[i].ordem = i
        
        # Adiciona ação ao histórico
        acao = AcaoHistorico('inserir', indice, deepcopy(segmento), deepcopy(marcacao))
        self.historico.append(acao)
        self.historico_desfazer.clear()

    def atualizar_segmento(self, indice, segmento):
        if indice < 0 or indice >= len(self.segmentos):
            return False
        segmento_anterior = deepcopy(self.segmentos[indice])
        self.segmentos[indice] = segmento
        
        # Adiciona ação ao histórico (guarda o segmento anterior E o novo)
        acao = AcaoHistorico('atualizar', indice, segmento_anterior, 
                            deepcopy(self.marcacoes[indice]) if indice < len(self.marcacoes) else None,
                            segmento_novo=deepcopy(segmento))
        self.historico.append(acao)
        self.historico_desfazer.clear()
        return True

    def remover_segmento(self, indice):
        if indice < 0 or indice >= len(self.segmentos):
            return False
        
        # Guarda estado completo do segmento e marcação
        segmento_removido = deepcopy(self.segmentos[indice])
        marcacao_removida = deepcopy(self.marcacoes[indice]) if indice < len(self.marcacoes) else None
        
        self.segmentos.pop(indice)
        # Remove marcação no mesmo índice
        if indice < len(self.marcacoes):
            self.marcacoes.pop(indice)
        # Atualiza ordem de todas as marcações posteriores
        for i in range(indice, len(self.marcacoes)):
            self.marcacoes[i].ordem = i
        
        # Adiciona ação ao histórico
        acao = AcaoHistorico('remover', indice, segmento_removido, marcacao_removida)
        self.historico.append(acao)
        self.historico_desfazer.clear()
        return True

    def obter_segmento(self, indice):
        if indice < 0 or indice >= len(self.segmentos):
            return None
        return self.segmentos[indice]

    def substituir_segmentos(self, segmentos):
        """Substitui todos os segmentos (usado ao carregar arquivos)."""
        self.segmentos = list(segmentos)
        # Se houver marcações no desfeito, restaura também
        if segmentos:
            # Garante que temos marcações para cada segmento
            while len(self.marcacoes) < len(self.segmentos):
                indice = len(self.marcacoes)
                marcacao = Marcacao(ordem=indice, lado="esquerda", distancia=0.5, x=0.0, y=0.0)
                self.marcacoes.append(marcacao)
            # Remove marcações extras
            self.marcacoes = self.marcacoes[:len(self.segmentos)]
        else:
            self.marcacoes = []
        # Limpar histórico quando substitui segmentos
        self.historico.clear()
        self.historico_desfazer.clear()

    def desfazer(self):
        """Desfaz a última ação realizada."""
        if not self.historico:
            return False
        
        acao = self.historico.pop()
        
        if acao.tipo == 'adicionar':
            # Desfazer adicionar = remover o último
            if self.segmentos and self.segmentos[-1] == acao.segmento:
                self.segmentos.pop()
                if self.marcacoes:
                    self.marcacoes.pop()
        
        elif acao.tipo == 'inserir':
            # Desfazer inserir = remover no índice
            if acao.indice < len(self.segmentos):
                self.segmentos.pop(acao.indice)
                if acao.indice < len(self.marcacoes):
                    self.marcacoes.pop(acao.indice)
                # Reordenar marcações
                for i in range(acao.indice, len(self.marcacoes)):
                    self.marcacoes[i].ordem = i
        
        elif acao.tipo == 'remover':
            # Desfazer remover = inserir novamente no índice
            self.segmentos.insert(acao.indice, acao.segmento)
            self.marcacoes.insert(acao.indice, acao.marcacao)
            # Reordenar marcações
            for i in range(acao.indice + 1, len(self.marcacoes)):
                self.marcacoes[i].ordem = i
        
        elif acao.tipo == 'atualizar':
            # Desfazer atualizar = restaurar segmento anterior
            self.segmentos[acao.indice] = acao.segmento
            if acao.marcacao and acao.indice < len(self.marcacoes):
                self.marcacoes[acao.indice] = acao.marcacao
        
        elif acao.tipo == 'modificar_marcacao':
            # Desfazer modificação de marcação = restaurar marcação anterior
            if acao.indice < len(self.marcacoes) and acao.marcacao_anterior:
                self.marcacoes[acao.indice] = acao.marcacao_anterior
        
        self.historico_desfazer.append(acao)
        return True

    def refazer(self):
        """Refaz a última ação desfeita."""
        if not self.historico_desfazer:
            return False
        
        acao = self.historico_desfazer.pop()
        
        if acao.tipo == 'adicionar':
            # Refazer adicionar = adicionar novamente no final
            self.segmentos.append(acao.segmento)
            marcacao = Marcacao(ordem=len(self.marcacoes), lado="esquerda", distancia=0.5, x=0.0, y=0.0)
            self.marcacoes.append(marcacao)
        
        elif acao.tipo == 'inserir':
            # Refazer inserir = inserir no mesmo índice
            self.segmentos.insert(acao.indice, acao.segmento)
            self.marcacoes.insert(acao.indice, acao.marcacao)
            # Reordenar marcações
            for i in range(acao.indice + 1, len(self.marcacoes)):
                self.marcacoes[i].ordem = i
        
        elif acao.tipo == 'remover':
            # Refazer remover = remover novamente no índice
            if acao.indice < len(self.segmentos):
                self.segmentos.pop(acao.indice)
                if acao.indice < len(self.marcacoes):
                    self.marcacoes.pop(acao.indice)
                # Reordenar marcações
                for i in range(acao.indice, len(self.marcacoes)):
                    self.marcacoes[i].ordem = i
        
        elif acao.tipo == 'atualizar':
            # Refazer atualizar = aplicar o novo segmento
            self.segmentos[acao.indice] = acao.segmento_novo
        
        elif acao.tipo == 'modificar_marcacao':
            # Refazer modificação de marcação = aplicar a marcação modificada
            if acao.indice < len(self.marcacoes) and acao.marcacao:
                self.marcacoes[acao.indice] = acao.marcacao
        
        self.historico.append(acao)
        return True

    def limpar(self):
        """Limpa todo o trajeto."""
        if not self.segmentos:
            return False
        
        # Guarda cada segmento removido no histórico (simula múltiplas remoções)
        while self.segmentos:
            acao = AcaoHistorico('remover', 0, deepcopy(self.segmentos[0]), 
                                deepcopy(self.marcacoes[0]) if self.marcacoes else None)
            self.historico.append(acao)
            self.segmentos.pop(0)
            if self.marcacoes:
                self.marcacoes.pop(0)
        self.historico_desfazer.clear()
        return True

    def adicionar_marcacao(self, marcacao):
        """Adiciona uma marcação ao trajeto."""
        self.marcacoes.append(marcacao)

    def remover_marcacao(self, indice):
        """Remove uma marcação pelo índice."""
        if indice < 0 or indice >= len(self.marcacoes):
            return False
        self.marcacoes.pop(indice)
        return True

    def obter_marcacao(self, indice):
        """Obtém uma marcação pelo índice."""
        if indice < 0 or indice >= len(self.marcacoes):
            return None
        return self.marcacoes[indice]

    def modificar_marcacao(self, indice, lado, distancia, x, y, angulo_eixo_x):
        """Modifica uma marcação e registra a ação no histórico."""
        if indice < 0 or indice >= len(self.marcacoes):
            return False
        
        # Guarda o estado anterior da marcação
        marcacao_anterior = deepcopy(self.marcacoes[indice])
        
        # Aplica as mudanças
        self.marcacoes[indice].lado = lado
        self.marcacoes[indice].distancia = distancia
        self.marcacoes[indice].x = x
        self.marcacoes[indice].y = y
        self.marcacoes[indice].angulo_eixo_x = angulo_eixo_x
        
        # Cria ação no histórico
        acao = AcaoHistorico('modificar_marcacao', indice, None, 
                            deepcopy(self.marcacoes[indice]), 
                            segmento_novo=None, 
                            marcacao_anterior=marcacao_anterior)
        self.historico.append(acao)
        self.historico_desfazer.clear()
        return True

    def substituir_marcacoes(self, marcacoes):
        """Substitui todas as marcações."""
        self.marcacoes = list(marcacoes)
