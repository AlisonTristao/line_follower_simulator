from copy import deepcopy

from models.detection_border import DetectionBorder
from models.marking import Marking


class HistoryAction:
    """Represents an action in the undo/redo history."""

    def __init__(
        self,
        action_type,
        index,
        segment,
        marking,
        segment_new=None,
        previous_marking=None,
    ):
        self.action_type = action_type
        self.index = index
        self.segment = segment
        self.segment_new = segment_new
        self.marking = marking
        self.previous_marking = previous_marking

    @property
    def tipo(self):
        return _to_legacy_action_type(self.action_type)

    @tipo.setter
    def tipo(self, value):
        self.action_type = _normalize_action_type(value)

    @property
    def indice(self):
        return self.index

    @indice.setter
    def indice(self, value):
        self.index = value

    @property
    def segmento(self):
        return self.segment

    @segmento.setter
    def segmento(self, value):
        self.segment = value

    @property
    def segmento_novo(self):
        return self.segment_new

    @segmento_novo.setter
    def segmento_novo(self, value):
        self.segment_new = value

    @property
    def marcacao(self):
        return self.marking

    @marcacao.setter
    def marcacao(self, value):
        self.marking = value

    @property
    def marcacao_anterior(self):
        return self.previous_marking

    @marcacao_anterior.setter
    def marcacao_anterior(self, value):
        self.previous_marking = value


class Trajectory:
    def __init__(self):
        self.segments = []
        self.history = []
        self.redo_stack = []
        self.markings = []
        self.poses = [(0.0, 0.0, 0.0)]
        self.detection_border = DetectionBorder()

    @property
    def segmentos(self):
        return self.segments

    @segmentos.setter
    def segmentos(self, value):
        self.segments = value

    @property
    def historico(self):
        return self.history

    @historico.setter
    def historico(self, value):
        self.history = value

    @property
    def historico_desfazer(self):
        return self.redo_stack

    @historico_desfazer.setter
    def historico_desfazer(self, value):
        self.redo_stack = value

    @property
    def marcacoes(self):
        return self.markings

    @marcacoes.setter
    def marcacoes(self, value):
        self.markings = value

    @property
    def borda_deteccao(self):
        return self.detection_border

    @borda_deteccao.setter
    def borda_deteccao(self, value):
        self.detection_border = value

    @property
    def segmentos_desfeitos(self):
        return self.redo_stack

    @segmentos_desfeitos.setter
    def segmentos_desfeitos(self, value):
        self.redo_stack = value

    def add_segment(self, segment):
        self.segments.append(segment)
        marking_index = len(self.markings)
        marking = Marking(order=marking_index, side="left", distance=0.5, x=0.0, y=0.0)
        self.markings.append(marking)

        action = HistoryAction("add", len(self.segments) - 1, deepcopy(segment), deepcopy(marking))
        self.history.append(action)
        self.redo_stack.clear()

    def insert_segment(self, index, segment):
        if index < 0:
            index = 0
        if index > len(self.segments):
            index = len(self.segments)
        self.segments.insert(index, segment)
        marking = Marking(order=index, side="left", distance=0.5, x=0.0, y=0.0)
        self.markings.insert(index, marking)
        for i in range(index + 1, len(self.markings)):
            self.markings[i].order = i

        action = HistoryAction("insert", index, deepcopy(segment), deepcopy(marking))
        self.history.append(action)
        self.redo_stack.clear()

    def update_segment(self, index, segment):
        if index < 0 or index >= len(self.segments):
            return False
        previous_segment = deepcopy(self.segments[index])
        self.segments[index] = segment

        action = HistoryAction(
            "update",
            index,
            previous_segment,
            deepcopy(self.markings[index]) if index < len(self.markings) else None,
            segment_new=deepcopy(segment),
        )
        self.history.append(action)
        self.redo_stack.clear()
        return True

    def remove_segment(self, index):
        if index < 0 or index >= len(self.segments):
            return False

        removed_segment = deepcopy(self.segments[index])
        removed_marking = deepcopy(self.markings[index]) if index < len(self.markings) else None

        self.segments.pop(index)
        if index < len(self.markings):
            self.markings.pop(index)
        for i in range(index, len(self.markings)):
            self.markings[i].order = i

        action = HistoryAction("remove", index, removed_segment, removed_marking)
        self.history.append(action)
        self.redo_stack.clear()
        return True

    def get_segment(self, index):
        if index < 0 or index >= len(self.segments):
            return None
        return self.segments[index]

    def replace_segments(self, segments):
        self.segments = list(segments)
        if segments:
            while len(self.markings) < len(self.segments):
                index = len(self.markings)
                marking = Marking(order=index, side="left", distance=0.5, x=0.0, y=0.0)
                self.markings.append(marking)
            self.markings = self.markings[: len(self.segments)]
        else:
            self.markings = []
        self.history.clear()
        self.redo_stack.clear()

    def undo(self):
        if not self.history:
            return False

        action = self.history.pop()

        if action.action_type == "add":
            if self.segments:
                self.segments.pop()
                if self.markings:
                    self.markings.pop()

        elif action.action_type == "insert":
            if action.index < len(self.segments):
                self.segments.pop(action.index)
                if action.index < len(self.markings):
                    self.markings.pop(action.index)
                for i in range(action.index, len(self.markings)):
                    self.markings[i].order = i

        elif action.action_type == "remove":
            self.segments.insert(action.index, action.segment)
            self.markings.insert(action.index, action.marking)
            for i in range(action.index + 1, len(self.markings)):
                self.markings[i].order = i

        elif action.action_type == "update":
            self.segments[action.index] = action.segment
            if action.marking and action.index < len(self.markings):
                self.markings[action.index] = action.marking

        elif action.action_type == "update_marking":
            if action.index < len(self.markings) and action.previous_marking:
                self.markings[action.index] = action.previous_marking

        self.redo_stack.append(action)
        return True

    def redo(self):
        if not self.redo_stack:
            return False

        action = self.redo_stack.pop()

        if action.action_type == "add":
            self.segments.append(action.segment)
            marking = Marking(order=len(self.markings), side="left", distance=0.5, x=0.0, y=0.0)
            self.markings.append(marking)

        elif action.action_type == "insert":
            self.segments.insert(action.index, action.segment)
            self.markings.insert(action.index, action.marking)
            for i in range(action.index + 1, len(self.markings)):
                self.markings[i].order = i

        elif action.action_type == "remove":
            if action.index < len(self.segments):
                self.segments.pop(action.index)
                if action.index < len(self.markings):
                    self.markings.pop(action.index)
                for i in range(action.index, len(self.markings)):
                    self.markings[i].order = i

        elif action.action_type == "update":
            self.segments[action.index] = action.segment_new

        elif action.action_type == "update_marking":
            if action.index < len(self.markings) and action.marking:
                self.markings[action.index] = action.marking

        self.history.append(action)
        return True

    def clear(self):
        if not self.segments:
            return False

        while self.segments:
            action = HistoryAction(
                "remove",
                0,
                deepcopy(self.segments[0]),
                deepcopy(self.markings[0]) if self.markings else None,
            )
            self.history.append(action)
            self.segments.pop(0)
            if self.markings:
                self.markings.pop(0)
        self.redo_stack.clear()
        return True

    def add_marking(self, marking):
        self.markings.append(marking)

    def remove_marking(self, index):
        if index < 0 or index >= len(self.markings):
            return False
        self.markings.pop(index)
        return True

    def get_marking(self, index):
        if index < 0 or index >= len(self.markings):
            return None
        return self.markings[index]

    def update_marking(self, index, side, distance, x, y, angle_x_axis):
        if index < 0 or index >= len(self.markings):
            return False

        previous_marking = deepcopy(self.markings[index])

        self.markings[index].side = side
        self.markings[index].distance = distance
        self.markings[index].x = x
        self.markings[index].y = y
        self.markings[index].angle_x_axis = angle_x_axis

        action = HistoryAction(
            "update_marking",
            index,
            None,
            deepcopy(self.markings[index]),
            segment_new=None,
            previous_marking=previous_marking,
        )
        self.history.append(action)
        self.redo_stack.clear()
        return True

    def replace_markings(self, markings):
        self.markings = list(markings)

    # Legacy method aliases.
    def adicionar_segmento(self, segmento):
        self.add_segment(segmento)

    def inserir_segmento(self, indice, segmento):
        self.insert_segment(indice, segmento)

    def atualizar_segmento(self, indice, segmento):
        return self.update_segment(indice, segmento)

    def remover_segmento(self, indice):
        return self.remove_segment(indice)

    def obter_segmento(self, indice):
        return self.get_segment(indice)

    def substituir_segmentos(self, segmentos):
        self.replace_segments(segmentos)

    def desfazer(self):
        return self.undo()

    def refazer(self):
        return self.redo()

    def limpar(self):
        return self.clear()

    def adicionar_marcacao(self, marcacao):
        self.add_marking(marcacao)

    def remover_marcacao(self, indice):
        return self.remove_marking(indice)

    def obter_marcacao(self, indice):
        return self.get_marking(indice)

    def modificar_marcacao(self, indice, lado, distancia, x, y, angulo_eixo_x):
        return self.update_marking(indice, lado, distancia, x, y, angulo_eixo_x)

    def substituir_marcacoes(self, marcacoes):
        self.replace_markings(marcacoes)


def _normalize_action_type(action_type: str) -> str:
    mapping = {
        "adicionar": "add",
        "inserir": "insert",
        "remover": "remove",
        "atualizar": "update",
        "modificar_marcacao": "update_marking",
    }
    return mapping.get(action_type, action_type)


def _to_legacy_action_type(action_type: str) -> str:
    mapping = {
        "add": "adicionar",
        "insert": "inserir",
        "remove": "remover",
        "update": "atualizar",
        "update_marking": "modificar_marcacao",
    }
    return mapping.get(action_type, action_type)
