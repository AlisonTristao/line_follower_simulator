import math

from models.segmentos import SegmentoCurva, SegmentoReta


class GeometriaTrajeto:
    @staticmethod
    def recalcular_poses(trajeto):
        trajeto.poses = [(0.0, 0.0, 0.0)]

        for seg in trajeto.segmentos:
            x0, y0, heading0 = trajeto.poses[-1]

            if isinstance(seg, SegmentoReta):
                heading1 = math.radians(seg.angulo_graus)
                x1 = x0 + seg.comprimento * math.cos(heading1)
                y1 = y0 + seg.comprimento * math.sin(heading1)
                trajeto.poses.append((x1, y1, heading1))

            elif isinstance(seg, SegmentoCurva):
                x1, y1, heading1 = GeometriaTrajeto.fim_curva(
                    x0, y0, heading0, seg.raio, seg.lado, seg.angulo_central_graus
                )
                trajeto.poses.append((x1, y1, heading1))

    @staticmethod
    def fim_curva(x0, y0, heading0, raio, lado, angulo_central_graus):
        sinal = 1 if lado == "esquerda" else -1
        angulo_central_rad = math.radians(angulo_central_graus)

        cx = x0 + sinal * raio * (-math.sin(heading0))
        cy = y0 + sinal * raio * math.cos(heading0)

        ang0 = math.atan2(y0 - cy, x0 - cx)
        ang1 = ang0 - sinal * angulo_central_rad

        x1 = cx + raio * math.cos(ang1)
        y1 = cy + raio * math.sin(ang1)
        heading1 = heading0 + sinal * angulo_central_rad

        return x1, y1, GeometriaTrajeto.normalizar_angulo(heading1)

    @staticmethod
    def normalizar_angulo(a):
        while a <= -math.pi:
            a += 2 * math.pi
        while a > math.pi:
            a -= 2 * math.pi
        return a

    @staticmethod
    def comprimento_segmento(seg):
        if isinstance(seg, SegmentoReta):
            return abs(seg.comprimento)
        if isinstance(seg, SegmentoCurva):
            return abs(math.radians(seg.angulo_central_graus) * seg.raio)
        return 0.0

    @staticmethod
    def comprimento_total(trajeto):
        return sum(GeometriaTrajeto.comprimento_segmento(seg) for seg in trajeto.segmentos)

    @staticmethod
    def pontos_densos_do_trajeto(trajeto, passos_minimos_curva=40):
        if not trajeto.segmentos:
            return [(0.0, 0.0)]

        pontos = [(0.0, 0.0)]
        x0, y0, heading0 = 0.0, 0.0, 0.0

        for seg in trajeto.segmentos:
            if isinstance(seg, SegmentoReta):
                heading1 = math.radians(seg.angulo_graus)
                x1 = x0 + seg.comprimento * math.cos(heading1)
                y1 = y0 + seg.comprimento * math.sin(heading1)
                pontos.append((x1, y1))
                x0, y0, heading0 = x1, y1, heading1

            elif isinstance(seg, SegmentoCurva):
                passos_curva = max(
                    passos_minimos_curva,
                    int(abs(seg.angulo_central_graus) / 180.0 * 120),
                )
                novos_pontos = GeometriaTrajeto.amostrar_curva(
                    x0,
                    y0,
                    heading0,
                    seg.raio,
                    seg.lado,
                    seg.angulo_central_graus,
                    passos_curva,
                )
                pontos.extend(novos_pontos[1:])
                x0, y0, heading0 = GeometriaTrajeto.fim_curva(
                    x0,
                    y0,
                    heading0,
                    seg.raio,
                    seg.lado,
                    seg.angulo_central_graus,
                )

        return pontos

    @staticmethod
    def pontos_segmentos_do_trajeto(trajeto, passos_minimos_curva=40):
        """Retorna lista de listas com os pontos de cada segmento separadamente"""
        if not trajeto.segmentos:
            return []

        pontos_segmentos = []
        x0, y0, heading0 = 0.0, 0.0, 0.0

        for seg in trajeto.segmentos:
            if isinstance(seg, SegmentoReta):
                heading1 = math.radians(seg.angulo_graus)
                x1 = x0 + seg.comprimento * math.cos(heading1)
                y1 = y0 + seg.comprimento * math.sin(heading1)
                pontos_segmentos.append([(x0, y0), (x1, y1)])
                x0, y0, heading0 = x1, y1, heading1

            elif isinstance(seg, SegmentoCurva):
                passos_curva = max(
                    passos_minimos_curva,
                    int(abs(seg.angulo_central_graus) / 180.0 * 120),
                )
                novos_pontos = GeometriaTrajeto.amostrar_curva(
                    x0,
                    y0,
                    heading0,
                    seg.raio,
                    seg.lado,
                    seg.angulo_central_graus,
                    passos_curva,
                )
                pontos_segmentos.append(novos_pontos)
                x0, y0, heading0 = GeometriaTrajeto.fim_curva(
                    x0,
                    y0,
                    heading0,
                    seg.raio,
                    seg.lado,
                    seg.angulo_central_graus,
                )

        return pontos_segmentos

    @staticmethod
    def amostrar_curva(x0, y0, heading0, raio, lado, angulo_central_graus, n_passos):
        sinal = 1 if lado == "esquerda" else -1
        angulo_central_rad = math.radians(angulo_central_graus)

        cx = x0 + sinal * raio * (-math.sin(heading0))
        cy = y0 + sinal * raio * math.cos(heading0)

        ang0 = math.atan2(y0 - cy, x0 - cx)
        ang1 = ang0 - sinal * angulo_central_rad

        pontos = []
        for i in range(n_passos + 1):
            t = i / n_passos
            ang = ang0 + (ang1 - ang0) * t
            x = cx + raio * math.cos(ang)
            y = cy + raio * math.sin(ang)
            pontos.append((x, y))
        return pontos

    @staticmethod
    def ponto_no_segmento(x0, y0, heading0, seg, distancia_local):
        if isinstance(seg, SegmentoReta):
            heading1 = math.radians(seg.angulo_graus)
            x = x0 + distancia_local * math.cos(heading1)
            y = y0 + distancia_local * math.sin(heading1)
            return x, y

        if isinstance(seg, SegmentoCurva):
            sinal = 1 if seg.lado == "esquerda" else -1
            angulo_total_rad = math.radians(seg.angulo_central_graus)
            comprimento_total = abs(angulo_total_rad * seg.raio)
            if comprimento_total == 0:
                return x0, y0

            fracao = max(0.0, min(1.0, distancia_local / comprimento_total))
            angulo_local = fracao * angulo_total_rad

            cx = x0 + sinal * seg.raio * (-math.sin(heading0))
            cy = y0 + sinal * seg.raio * math.cos(heading0)
            ang0 = math.atan2(y0 - cy, x0 - cx)
            ang = ang0 - sinal * angulo_local
            x = cx + seg.raio * math.cos(ang)
            y = cy + seg.raio * math.sin(ang)
            return x, y

        return x0, y0

    @staticmethod
    def amostrar_por_quantidade(trajeto, qtd_pontos):
        if not trajeto.segmentos:
            return [(0.0, 0.0)]
        if qtd_pontos <= 1:
            return [(0.0, 0.0)]

        comprimento_total = GeometriaTrajeto.comprimento_total(trajeto)
        if comprimento_total == 0:
            return [(0.0, 0.0)] * qtd_pontos

        alvos = [i * comprimento_total / (qtd_pontos - 1) for i in range(qtd_pontos)]
        resultado = []

        poses_inicio = trajeto.poses[:-1]
        comprimentos_segmentos = [GeometriaTrajeto.comprimento_segmento(seg) for seg in trajeto.segmentos]

        indice_segmento = 0
        acumulado_ate_segmento = 0.0

        for alvo in alvos:
            while (
                indice_segmento < len(trajeto.segmentos) - 1
                and acumulado_ate_segmento + comprimentos_segmentos[indice_segmento] < alvo
            ):
                acumulado_ate_segmento += comprimentos_segmentos[indice_segmento]
                indice_segmento += 1

            seg = trajeto.segmentos[indice_segmento]
            x0, y0, heading0 = poses_inicio[indice_segmento]
            distancia_local = alvo - acumulado_ate_segmento
            resultado.append(GeometriaTrajeto.ponto_no_segmento(x0, y0, heading0, seg, distancia_local))

        return resultado

    @staticmethod
    def espacamento_medio(trajeto, qtd_pontos):
        if qtd_pontos <= 1:
            return 0.0
        comprimento_total = GeometriaTrajeto.comprimento_total(trajeto)
        if comprimento_total == 0:
            return 0.0
        return comprimento_total / (qtd_pontos - 1)

    @staticmethod
    def calcular_posicao_marcacao(trajeto, indice_segmento, lado, distancia):
        """Calcula a posição de uma marcação perpendicular ao final de um segmento.
        
        Args:
            trajeto: O trajeto contendo os segmentos
            indice_segmento: Índice do segmento (0-based) cuja pose final será usada
            lado: "esquerda" ou "direita"
            distancia: Distância perpendicular em metros
            
        Returns:
            tupla (x, y, angulo_perpendicular) ou None se o índice for inválido
        """
        if indice_segmento < 0 or indice_segmento >= len(trajeto.segmentos):
            return None
        
        seg = trajeto.segmentos[indice_segmento]
        x, y, heading_final = trajeto.poses[indice_segmento + 1]

        # Estima a direção tangente no ponto final do segmento.
        # Em curvas, usa a secante entre o último e o penúltimo ponto para aproximar a derivada.
        if isinstance(seg, SegmentoReta):
            heading_tangente = math.radians(seg.angulo_graus)
        elif isinstance(seg, SegmentoCurva):
            x0, y0, heading0 = trajeto.poses[indice_segmento]
            comprimento = GeometriaTrajeto.comprimento_segmento(seg)
            delta = min(0.01, comprimento * 0.1)
            if comprimento <= 0 or delta <= 0:
                heading_tangente = heading_final
            else:
                x_prev, y_prev = GeometriaTrajeto.ponto_no_segmento(
                    x0,
                    y0,
                    heading0,
                    seg,
                    max(0.0, comprimento - delta),
                )
                dx = x - x_prev
                dy = y - y_prev
                if abs(dx) < 1e-12 and abs(dy) < 1e-12:
                    heading_tangente = heading_final
                else:
                    heading_tangente = math.atan2(dy, dx)
        else:
            heading_tangente = heading_final

        # Calcula a perpendicular (rotaciona tangente em 90 graus)
        sinal = 1 if lado == "esquerda" else -1
        perpendicular_heading = GeometriaTrajeto.normalizar_angulo(heading_tangente + sinal * math.pi / 2)

        # Calcula a posição da marcação
        x_marcacao = x + distancia * math.cos(perpendicular_heading)
        y_marcacao = y + distancia * math.sin(perpendicular_heading)

        return x_marcacao, y_marcacao, perpendicular_heading
