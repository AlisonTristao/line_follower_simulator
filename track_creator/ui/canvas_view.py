import tkinter as tk
import time
import math

from services.geometria import GeometriaTrajeto


class CanvasTrajetoView:
    GRADE_ESPACO_PADRAO = 1.0  # 1 metro por padrão
    
    def __init__(self, parent, zoom_var, zoom_max_var, mostrar_grade_var, origem_x_var, origem_y_var, unidade_var, fator_personalizado_var=None):
        self.zoom_var = zoom_var
        self.zoom_max_var = zoom_max_var
        self.mostrar_grade_var = mostrar_grade_var
        self.unidade_var = unidade_var
        self.fator_personalizado_var = fator_personalizado_var
        self.origem_x_var = origem_x_var
        self.origem_y_var = origem_y_var

        self.pan_x_px = 0.0
        self.pan_y_px = 0.0
        self.drag_inicio_x = None
        self.drag_inicio_y = None
        self.pan_inicio_x = 0.0
        self.pan_inicio_y = 0.0
        self.mouse_x_px = 0
        self.mouse_y_px = 0

        self.frame = tk.Frame(parent)
        self.canvas = tk.Canvas(self.frame, bg="white", cursor="fleur")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Configure>", lambda e: self._disparar_redesenho())
        self.canvas.bind("<Button-1>", self._ao_clicar_canvas)
        self.canvas.bind("<B1-Motion>", self._arrastar)
        self.canvas.bind("<ButtonRelease-1>", self._ao_soltar_canvas)
        self.canvas.bind("<MouseWheel>", self._zoom_mousewheel)
        self.canvas.bind("<Button-4>", self._zoom_mousewheel_linux)
        self.canvas.bind("<Button-5>", self._zoom_mousewheel_linux)
        self.canvas.bind("<Motion>", self._ao_mover_mouse)

        self._callback_redesenho = None
        self._callback_selecionar_segmento = None
        self._callback_origem_clicada = None
        self.segmento_coords = {}  # {indice_segmento: [(x1,y1), (x2,y2), ...]}
        
        # Sistema de detecção de duplo clique
        self.ultimo_clique_tempo = 0
        self.ultimo_clique_x = 0
        self.ultimo_clique_y = 0
        self.timer_espera_duplo = None
        self.clique_pendente = None
        self.movimento_iniciado = False  # Flag para saber se já há movimento durante drag
        
        # Modo de seleção de origem
        self.modo_selecionando_origem = False


    def set_redraw_callback(self, callback):
        self._callback_redesenho = callback

    def set_segmento_click_callback(self, callback):
        """Define callback para quando um segmento é clicado"""
        self._callback_selecionar_segmento = callback

    def set_origem_click_callback(self, callback):
        """Define callback para quando um ponto é clicado em modo de seleção de origem"""
        self._callback_origem_clicada = callback

    def _disparar_redesenho(self):
        if self._callback_redesenho:
            self._callback_redesenho()

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def _ao_clicar_canvas(self, event):
        """Detecta clique no canvas com sistema de duplo clique"""
        tempo_atual = time.time()
        intervalo = tempo_atual - self.ultimo_clique_tempo
        distancia = ((event.x - self.ultimo_clique_x) ** 2 + (event.y - self.ultimo_clique_y) ** 2) ** 0.5
        
        # Cancelar timer anterior se houver
        if self.timer_espera_duplo is not None:
            self.canvas.after_cancel(self.timer_espera_duplo)
            self.timer_espera_duplo = None
        
        # Verificar se é duplo clique (< 100ms e < 5px de movimento)
        if intervalo < 0.3 and distancia < 5 and self.ultimo_clique_tempo > 0:
            # É duplo clique: não faz nada, apenas reseta
            self.clique_pendente = None
            self.movimento_iniciado = False
            self.drag_inicio_x = None
            self.drag_inicio_y = None
            self.ultimo_clique_tempo = 0
            return
        
        # Registrar este clique
        self.ultimo_clique_tempo = tempo_atual
        self.ultimo_clique_x = event.x
        self.ultimo_clique_y = event.y
        self.clique_pendente = event
        self.movimento_iniciado = False
        
        # Aguardar 100ms para ver se vem outro clique (duplo)
        self.timer_espera_duplo = self.canvas.after(100, self._processar_clique_unico)

    def _processar_clique_unico(self):
        """Processa o clique como sendo um clique único (não duplo)"""
        self.timer_espera_duplo = None
        
        if self.clique_pendente is None:
            return
        
        event = self.clique_pendente
        self.clique_pendente = None
        
        # Se estamos em modo de seleção de origem, processa como tal
        if self.modo_selecionando_origem:
            largura = max(self.canvas.winfo_width(), 10)
            altura = max(self.canvas.winfo_height(), 10)
            x_mundo, y_mundo = self.tela_para_mundo(event.x, event.y, largura, altura)
            if self._callback_origem_clicada:
                self._callback_origem_clicada(x_mundo, y_mundo)
            return
        
        # Tenta encontrar segmento mais próximo
        if self._callback_selecionar_segmento:
            indice = self._encontrar_segmento_proximo(event.x, event.y)
            if indice is not None:
                # Encontrou segmento: seleciona
                self._callback_selecionar_segmento(indice)
            else:
                # Não encontrou segmento: apenas inicia arraste como fallback
                self._iniciar_arraste(event)
        else:
            self._iniciar_arraste(event)

    def _iniciar_arraste(self, event):
        self.drag_inicio_x = event.x
        self.drag_inicio_y = event.y
        self.pan_inicio_x = self.pan_x_px
        self.pan_inicio_y = self.pan_y_px
        self.movimento_iniciado = False

    def _arrastar(self, event):
        # Se não temos clique inicial, nada a fazer
        if self.drag_inicio_x is None or self.drag_inicio_y is None:
            # Se há clique pendente (aguardando duplo), inicia movimento agora
            if self.clique_pendente is not None:
                self._iniciar_arraste(self.clique_pendente)
                # Cancela timer de duplo clique se houver
                if self.timer_espera_duplo is not None:
                    self.canvas.after_cancel(self.timer_espera_duplo)
                    self.timer_espera_duplo = None
                self.clique_pendente = None
                return  # Retorna para que o próximo movimento calcule com valores inicializados
            else:
                return
        
        # Calcular distância do clique inicial
        distancia = ((event.x - self.drag_inicio_x) ** 2 + (event.y - self.drag_inicio_y) ** 2) ** 0.5
        
        # Se ainda não iniciou movimento e distância < 5px, ainda está "pendente"
        if not self.movimento_iniciado and distancia < 5:
            return
        
        # Movimento real detectado
        self.movimento_iniciado = True
        
        # Se ainda havia clique pendente aguardando duplo, cancela esse espero
        if self.clique_pendente is not None:
            if self.timer_espera_duplo is not None:
                self.canvas.after_cancel(self.timer_espera_duplo)
                self.timer_espera_duplo = None
            self.clique_pendente = None
        
        # Faz o pan
        self.pan_x_px = self.pan_inicio_x + (event.x - self.drag_inicio_x)
        self.pan_y_px = self.pan_inicio_y + (event.y - self.drag_inicio_y)
        self._disparar_redesenho()

    def _ao_soltar_canvas(self, event):
        """Limpa estado quando botão do mouse é solto"""
        # Se houve movimento (drag), cancela o clique pendente
        # Se foi apenas um clique puro, deixa o timer rodar para processar o clique
        if self.movimento_iniciado:
            # Foi um drag, cancela o timer e clique pendente
            if self.timer_espera_duplo is not None:
                self.canvas.after_cancel(self.timer_espera_duplo)
                self.timer_espera_duplo = None
            self.clique_pendente = None
        # Se não houve movimento, deixa o timer rodar para _processar_clique_unico
        
        self.drag_inicio_x = None
        self.drag_inicio_y = None
        self.movimento_iniciado = False

    def _ao_mover_mouse(self, event):
        """Rastreia posição do mouse para exibir informações"""
        self.mouse_x_px = event.x
        self.mouse_y_px = event.y
        self._disparar_redesenho()

    def _encontrar_segmento_proximo(self, px_click, py_click, distancia_max=10):
        """Encontra o índice do segmento mais próximo do clique"""
        melhor_indice = None
        melhor_distancia = distancia_max
        
        for indice, coords in self.segmento_coords.items():
            if len(coords) < 2:
                continue
            # Calcula distância do ponto ao segmento
            for i in range(len(coords) - 1):
                x1, y1 = coords[i]
                x2, y2 = coords[i + 1]
                # Distância ponto-segmento
                dist = self._distancia_ponto_segmento(px_click, py_click, x1, y1, x2, y2)
                if dist < melhor_distancia:
                    melhor_distancia = dist
                    melhor_indice = indice
        
        return melhor_indice

    def _distancia_ponto_segmento(self, px, py, x1, y1, x2, y2):
        """Calcula distância de um ponto a um segmento de linha"""
        # Coeficientes da reta
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        
        # Parâmetro t da projeção
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        
        # Ponto mais próximo no segmento
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        
        return ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5

    def _zoom_mousewheel(self, event):
        """Realiza zoom centrado na posição do mouse"""
        # Obter posição do mouse em pixel
        mouse_px = event.x
        mouse_py = event.y
        
        # Obter dimensões do canvas
        largura = max(self.canvas.winfo_width(), 10)
        altura = max(self.canvas.winfo_height(), 10)
        
        # Converter mouse para coordenadas de mundo (antes do zoom)
        x_mundo, y_mundo = self.tela_para_mundo(mouse_px, mouse_py, largura, altura)
        
        # Obter o novo zoom
        try:
            zoom_max = float(self.zoom_max_var.get())
        except ValueError:
            zoom_max = 120.0
        
        if event.delta > 0:
            novo_zoom = min(zoom_max, self.zoom_var.get() * 1.1)
        else:
            novo_zoom = max(2.0, self.zoom_var.get() / 1.1)
        
        self.zoom_var.set(novo_zoom)
        
        # Converter mouse world back to screen (com novo zoom)
        novo_mouse_px, novo_mouse_py = self.mundo_para_tela(x_mundo, y_mundo, largura, altura)
        
        # Ajustar pan para manter a mesma posição de mundo sob o mouse
        self.pan_x_px += mouse_px - novo_mouse_px
        self.pan_y_px += mouse_py - novo_mouse_py
        
        self._disparar_redesenho()

    def _zoom_mousewheel_linux(self, event):
        """Realiza zoom centrado na posição do mouse (Linux)"""
        # Obter posição do mouse em pixel
        mouse_px = event.x
        mouse_py = event.y
        
        # Obter dimensões do canvas
        largura = max(self.canvas.winfo_width(), 10)
        altura = max(self.canvas.winfo_height(), 10)
        
        # Converter mouse para coordenadas de mundo (antes do zoom)
        x_mundo, y_mundo = self.tela_para_mundo(mouse_px, mouse_py, largura, altura)
        
        # Obter o novo zoom
        try:
            zoom_max = float(self.zoom_max_var.get())
        except ValueError:
            zoom_max = 120.0
        
        if event.num == 4:
            novo_zoom = min(zoom_max, self.zoom_var.get() * 1.1)
        else:
            novo_zoom = max(2.0, self.zoom_var.get() / 1.1)
        
        self.zoom_var.set(novo_zoom)
        
        # Converter mouse world back to screen (com novo zoom)
        novo_mouse_px, novo_mouse_py = self.mundo_para_tela(x_mundo, y_mundo, largura, altura)
        
        # Ajustar pan para manter a mesma posição de mundo sob o mouse
        self.pan_x_px += mouse_px - novo_mouse_px
        self.pan_y_py += mouse_py - novo_mouse_py
        
        self._disparar_redesenho()

    def centralizar_visao(self):
        self.pan_x_px = 0.0
        self.pan_y_px = 0.0
        self._disparar_redesenho()

    def ativar_modo_selecionando_origem(self):
        """Ativa o modo de seleção de origem"""
        self.modo_selecionando_origem = True
        self.canvas.config(cursor="crosshair")
        self._disparar_redesenho()

    def desativar_modo_selecionando_origem(self):
        """Desativa o modo de seleção de origem"""
        self.modo_selecionando_origem = False
        self.canvas.config(cursor="fleur")
        self._disparar_redesenho()

    def obter_origem_visual_m(self):
        try:
            origem_x = float(self.origem_x_var.get())
            origem_y = float(self.origem_y_var.get())
            return origem_x, origem_y
        except ValueError:
            return 0.0, 0.0

    def mundo_para_tela(self, x_mundo, y_mundo, largura, altura):
        origem_x, origem_y = self.obter_origem_visual_m()
        zoom = self.zoom_var.get()
        cx = largura / 2 + self.pan_x_px
        cy = altura / 2 + self.pan_y_px
        x_vis = x_mundo - origem_x
        y_vis = y_mundo - origem_y
        sx = cx + x_vis * zoom
        sy = cy - y_vis * zoom
        return sx, sy

    def tela_para_mundo(self, sx, sy, largura, altura):
        """Converte coordenadas de tela para coordenadas do mundo"""
        origem_x, origem_y = self.obter_origem_visual_m()
        zoom = self.zoom_var.get()
        cx = largura / 2 + self.pan_x_px
        cy = altura / 2 + self.pan_y_px
        x_vis = (sx - cx) / zoom
        y_vis = (cy - sy) / zoom
        x_mundo = x_vis + origem_x
        y_mundo = y_vis + origem_y
        return x_mundo, y_mundo

    def desenhar(self, trajeto, indice_selecionado=None):
        self.canvas.delete("all")
        self.segmento_coords = {}

        largura = max(self.canvas.winfo_width(), 10)
        altura = max(self.canvas.winfo_height(), 10)
        cx = largura / 2 + self.pan_x_px
        cy = altura / 2 + self.pan_y_px

        self._desenhar_grade(largura, altura)
        self._desenhar_reguas(largura, altura, cx, cy)
        self.canvas.create_line(0, cy, largura, cy, fill="#bdbdbd")
        self.canvas.create_line(cx, 0, cx, altura, fill="#bdbdbd")
        self.canvas.create_text(cx + 55, cy + 14, text="Origem visual (0,0)", fill="#666666")

        # Desenhar trajeto segmento por segmento
        pontos_segmentos = GeometriaTrajeto.pontos_segmentos_do_trajeto(trajeto)
        
        for indice, pontos_segmento in enumerate(pontos_segmentos):
            if len(pontos_segmento) >= 2:
                # Determina cor: selecionado em verde destacado, outros em azul
                eh_selecionado = (indice == indice_selecionado)
                cor = "#00AA00" if eh_selecionado else "#004aad"
                largura_linha = 6 if eh_selecionado else 3
                
                # Convertendo pontos do mundo para tela
                coords = []
                coords_pixel = []
                for x, y in pontos_segmento:
                    sx, sy = self.mundo_para_tela(x, y, largura, altura)
                    coords.extend([sx, sy])
                    coords_pixel.append((sx, sy))
                
                # Guardar coordenadas para detecção de clique
                self.segmento_coords[indice] = coords_pixel
                
                # Desenhar segmento
                self.canvas.create_line(*coords, fill=cor, width=largura_linha, smooth=False)

        sx_ini, sy_ini = self.mundo_para_tela(0.0, 0.0, largura, altura)
        self.canvas.create_oval(sx_ini - 5, sy_ini - 5, sx_ini + 5, sy_ini + 5, fill="green", outline="")
        self.canvas.create_text(sx_ini + 24, sy_ini - 12, text="Início", fill="green")
        
        # Desenhar borda de detecção se existir
        if hasattr(trajeto, 'borda_deteccao') and trajeto.borda_deteccao:
            self._desenhar_limites_pista(trajeto, largura, altura)
        
        # Se em modo de seleção de origem, mostrar indicação
        if self.modo_selecionando_origem:
            origem_x, origem_y = self.obter_origem_visual_m()
            sx_orig, sy_orig = self.mundo_para_tela(origem_x, origem_y, largura, altura)
            # Desenhar círculo maior marcando a origem visual
            self.canvas.create_oval(sx_orig - 15, sy_orig - 15, sx_orig + 15, sy_orig + 15, 
                                   outline="#FF00FF", width=3)
            self.canvas.create_line(sx_orig - 20, sy_orig, sx_orig + 20, sy_orig, fill="#FF00FF", width=2)
            self.canvas.create_line(sx_orig, sy_orig - 20, sx_orig, sy_orig + 20, fill="#FF00FF", width=2)
            self.canvas.create_text(sx_orig + 30, sy_orig - 30, text="Clique para mover origem", 
                                   fill="#FF00FF", font=("Arial", 9, "bold"))

        x_fim, y_fim, _ = trajeto.poses[-1]
        sx_fim, sy_fim = self.mundo_para_tela(x_fim, y_fim, largura, altura)
        self.canvas.create_oval(sx_fim - 5, sy_fim - 5, sx_fim + 5, sy_fim + 5, fill="red", outline="")

        # Desenhar marcações (waypoints)
        if hasattr(trajeto, 'marcacoes') and trajeto.marcacoes:
            for marcacao in trajeto.marcacoes:
                sx_marc, sy_marc = self.mundo_para_tela(marcacao.x, marcacao.y, largura, altura)
                # Cor diferente para esquerda/direita
                cor = "#0066cc" if marcacao.lado == "esquerda" else "#ff6600"
                self.canvas.create_oval(sx_marc - 6, sy_marc - 6, sx_marc + 6, sy_marc + 6, fill=cor, outline="white", width=2)
                # Opcional: desenhar número da marcação
                self.canvas.create_text(sx_marc, sy_marc, text=str(marcacao.ordem), fill="white", font=("Arial", 8, "bold"))
        
        # Desenhar informações no canto (escala e posição do mouse)
        self._desenhar_info_canto(largura, altura)

    def _desenhar_info_canto(self, largura, altura):
        """Desenha informações de escala da grid e posição do mouse no canto inferior direito"""
        zoom = self.zoom_var.get()
        
        # Calcular escala atual da grid em pixels por metro
        espaco_m = self.GRADE_ESPACO_PADRAO
        passo_px = espaco_m * zoom
        
        # Se o passo ficar muito pequeno, aumentar o espaçamento progressivamente
        espaco_grade = espaco_m
        while passo_px < 8 and espaco_grade > 0:
            espaco_grade *= 2
            passo_px = espaco_grade * zoom
        
        # Converter posição do mouse para coordenadas do mundo
        x_mundo, y_mundo = self.tela_para_mundo(self.mouse_x_px, self.mouse_y_px, largura, altura)
        
        # Obter unidade atual e aplicar fator de conversão
        unidade = self.unidade_var.get()
        
        # Fatores de conversão invertidos (10^n em vez de múltiplos diretos)
        # m: 10^0 = 1.0
        # cm: 10^-2 = 0.01
        # mm: 10^-3 = 0.001
        # km: 10^3 = 1000
        fatores_conversao = {
            "m": 1.0,           # 10^0
            "cm": 0.01,         # 10^-2
            "mm": 0.001,        # 10^-3
            "km": 1000.0        # 10^3
        }
        
        # Se for unidade personalizada, usar o fator configurado
        if unidade == "personalizada":
            try:
                fator = float(self.fator_personalizado_var.get()) if self.fator_personalizado_var else 1.0
            except (ValueError, TypeError):
                fator = 1.0
            unidade_label = "unid."
        else:
            fator = fatores_conversao.get(unidade, 1.0)
            unidade_label = unidade
        
        # Converter valores
        # A escala não precisa de conversão, apenas muda a etiqueta
        x_mundo_convertido = x_mundo * fator
        y_mundo_convertido = y_mundo * fator
        
        # Formatar informações apenas com valores
        info_escala = f"{espaco_grade:.1f} {unidade_label}"
        info_mouse = f"({x_mundo_convertido:.3f}, {y_mundo_convertido:.3f})"
        
        # Desenhar texto no canto inferior direito sem fundo
        x_pos = largura - 120
        y_pos = altura - 50
        
        # Desenhar textos (alinhado à direita)
        self.canvas.create_text(x_pos, y_pos, text=info_escala, anchor="nw", 
                               fill="#000000", font=("Arial", 9))
        self.canvas.create_text(x_pos, y_pos + 15, text=info_mouse, anchor="nw", 
                               fill="#000000", font=("Arial", 9))

    def _desenhar_grade(self, largura, altura):
        if not self.mostrar_grade_var.get():
            return

        espaco_m = self.GRADE_ESPACO_PADRAO
        zoom = self.zoom_var.get()
        passo_px = espaco_m * zoom
        
        # Se o passo ficar muito pequeno, aumentar o espaçamento progressivamente
        espaco_grade = espaco_m
        while passo_px < 8 and espaco_grade > 0:
            espaco_grade *= 2
            passo_px = espaco_grade * zoom

        cx = largura / 2 + self.pan_x_px
        cy = altura / 2 + self.pan_y_px

        x = cx
        while x <= largura:
            self.canvas.create_line(x, 0, x, altura, fill="#ebebeb")
            x += passo_px
        x = cx - passo_px
        while x >= 0:
            self.canvas.create_line(x, 0, x, altura, fill="#ebebeb")
            x -= passo_px

        y = cy
        while y <= altura:
            self.canvas.create_line(0, y, largura, y, fill="#ebebeb")
            y += passo_px
        y = cy - passo_px
        while y >= 0:
            self.canvas.create_line(0, y, largura, y, fill="#ebebeb")
            y -= passo_px

    def _desenhar_reguas(self, largura, altura, cx, cy):
        """Desenha réguas nos eixos X (topo) e Y (esquerda) com marcas apenas"""
        altura_regua = 20
        largura_regua = 25
        espaco_px = 150  # Marcas principais a cada 150 pixels
        espaco_marca_intermediaria = 30  # Marcas menores a cada 30 pixels
        
        # Desenhar régua horizontal (X) no topo
        self.canvas.create_rectangle(0, 0, largura, altura_regua, fill="#f0f0f0", outline="#cccccc")
        
        # Desenhar marcas intermediárias (risquinhos menores) na régua X
        x_px = largura_regua
        while x_px <= largura:
            self.canvas.create_line(x_px, altura_regua - 6, x_px, altura_regua - 1, fill="#999999", width=1)
            x_px += espaco_marca_intermediaria
        
        # Desenhar apenas marcas principais na régua X (sem números)
        x_px = largura_regua
        while x_px <= largura:
            self.canvas.create_line(x_px, altura_regua - 10, x_px, altura_regua - 2, fill="#666666", width=2)
            x_px += espaco_px
        
        # Desenhar régua vertical (Y) na esquerda
        self.canvas.create_rectangle(0, 0, largura_regua, altura, fill="#f0f0f0", outline="#cccccc")
        
        # Desenhar marcas intermediárias (risquinhos menores) na régua Y
        y_px = altura_regua
        while y_px <= altura:
            self.canvas.create_line(largura_regua - 6, y_px, largura_regua - 1, y_px, fill="#999999", width=1)
            y_px += espaco_marca_intermediaria
        
        # Desenhar apenas marcas principais na régua Y (sem números)
        y_px = altura_regua
        while y_px <= altura:
            self.canvas.create_line(largura_regua - 10, y_px, largura_regua - 2, y_px, fill="#666666", width=2)
            y_px += espaco_px

    def _desenhar_limites_pista(self, trajeto, largura, altura):
        """Desenha os limites da pista como um retângulo com borda tracejada cinza, centrado na origem visual.
        Largura = altura * 2 (proporção fixa)."""
        limites = trajeto.borda_deteccao
        altura_limites = limites.altura
        largura_limites = altura_limites * 2.0  # Largura é altura × 2
        
        # Obter origem visual (centro do retângulo)
        origem_x, origem_y = self.obter_origem_visual_m()
        
        # Posição dos limites centrada na origem visual
        # Quanto à horizontal: largura_limites
        # Quanto à vertical: altura_limites
        x1_mundo = origem_x - largura_limites / 2.0
        y1_mundo = origem_y - altura_limites / 2.0
        x2_mundo = origem_x + largura_limites / 2.0
        y2_mundo = origem_y + altura_limites / 2.0
        
        # Converter para coordenadas de tela
        sx1, sy1 = self.mundo_para_tela(x1_mundo, y1_mundo, largura, altura)
        sx2, sy2 = self.mundo_para_tela(x2_mundo, y2_mundo, largura, altura)
        
        # Desenhar retângulo com borda tracejada cinza
        # dash=(5, 5) cria um padrão tracejado (5 px sólido, 5 px vazio)
        self.canvas.create_rectangle(
            sx1, sy1, sx2, sy2,
            outline="gray",
            width=2,
            dash=(5, 5)
        )
