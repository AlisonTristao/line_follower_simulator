import tkinter as tk
import time
from io import BytesIO

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from services.trajectory_geometry import TrajectoryGeometry


class CanvasTrajectoryView:
    GRADE_ESPACO_PADRAO = 1.0  # 1 metro por padrão
    FUNDO_RENDER_MAX_LADO = 2200
    FUNDO_RENDER_MAX_PIXELS = 3_000_000
    FUNDO_REDRAW_ZOOM_INTERVALO_MS = 20
    FUNDO_INCLINACAO_LIMITE = 2.5
    
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
        self._ultimo_redesenho_mouse_tempo = 0.0
        self._redesenho_zoom_agendado = None

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

        # Configuração de imagem de fundo
        self._imagem_fundo_original = None
        self._imagem_fundo_preparada = None
        self._imagem_fundo_preparada_key = None
        self._imagem_fundo_photo = None
        self._imagem_fundo_cache_key = None
        self._fundo_visivel = False
        self._fundo_tamanho_quadrado_m = 1.0
        self._fundo_escala_horizontal = 1.0
        self._fundo_escala_vertical = 1.0
        self._fundo_zoom = 1.0
        self._fundo_offset_x_m = 0.0
        self._fundo_offset_y_m = 0.0
        self._fundo_opacidade_percent = 60.0
        self._fundo_perspectiva_horizontal = 0.0
        self._fundo_perspectiva_vertical = 0.0
        self._fundo_canto_superior_esquerdo = 0.0
        self._fundo_canto_superior_direito = 0.0
        self._fundo_canto_inferior_direito = 0.0
        self._fundo_canto_inferior_esquerdo = 0.0
        self._fundo_rotacao_graus = 0.0


    def set_redraw_callback(self, callback):
        self._callback_redesenho = callback

    def set_segmento_click_callback(self, callback):
        """Define callback para quando um segmento é clicado"""
        self._callback_selecionar_segmento = callback

    def set_origem_click_callback(self, callback):
        """Define callback para quando um ponto é clicado em modo de seleção de origem"""
        self._callback_origem_clicada = callback

    @staticmethod
    def suporte_imagem_fundo_disponivel():
        return Image is not None and ImageTk is not None

    def carregar_imagem_fundo_bytes(self, image_bytes):
        if not self.suporte_imagem_fundo_disponivel():
            raise RuntimeError("Pillow não está instalado. Instale com: pip install pillow")
        if not image_bytes:
            raise ValueError("Nenhum dado de imagem informado.")

        imagem = Image.open(BytesIO(image_bytes)).convert("RGBA")
        self._imagem_fundo_original = imagem
        self._imagem_fundo_preparada = None
        self._imagem_fundo_preparada_key = None
        self._imagem_fundo_photo = None
        self._imagem_fundo_cache_key = None

    def limpar_imagem_fundo(self):
        self._imagem_fundo_original = None
        self._imagem_fundo_preparada = None
        self._imagem_fundo_preparada_key = None
        self._imagem_fundo_photo = None
        self._imagem_fundo_cache_key = None
        self._fundo_visivel = False

    def configurar_imagem_fundo(
        self,
        tamanho_quadrado_m,
        escala_horizontal,
        escala_vertical,
        zoom,
        opacidade_percent,
        offset_x_m=0.0,
        offset_y_m=0.0,
        perspectiva_horizontal=0.0,
        perspectiva_vertical=0.0,
        canto_superior_esquerdo=0.0,
        canto_superior_direito=0.0,
        canto_inferior_direito=0.0,
        canto_inferior_esquerdo=0.0,
        rotacao_graus=0.0,
        visivel=True,
    ):
        self._fundo_tamanho_quadrado_m = max(0.001, float(tamanho_quadrado_m))
        self._fundo_escala_horizontal = max(0.001, float(escala_horizontal))
        self._fundo_escala_vertical = max(0.001, float(escala_vertical))
        self._fundo_zoom = max(0.001, float(zoom))
        self._fundo_offset_x_m = float(offset_x_m)
        self._fundo_offset_y_m = float(offset_y_m)
        self._fundo_opacidade_percent = max(0.0, min(100.0, float(opacidade_percent)))
        limite_inclinacao = float(self.FUNDO_INCLINACAO_LIMITE)
        self._fundo_perspectiva_horizontal = max(-limite_inclinacao, min(limite_inclinacao, float(perspectiva_horizontal)))
        self._fundo_perspectiva_vertical = max(-limite_inclinacao, min(limite_inclinacao, float(perspectiva_vertical)))
        self._fundo_canto_superior_esquerdo = max(-limite_inclinacao, min(limite_inclinacao, float(canto_superior_esquerdo)))
        self._fundo_canto_superior_direito = max(-limite_inclinacao, min(limite_inclinacao, float(canto_superior_direito)))
        self._fundo_canto_inferior_direito = max(-limite_inclinacao, min(limite_inclinacao, float(canto_inferior_direito)))
        self._fundo_canto_inferior_esquerdo = max(-limite_inclinacao, min(limite_inclinacao, float(canto_inferior_esquerdo)))
        self._fundo_rotacao_graus = max(-180.0, min(180.0, float(rotacao_graus)))
        self._fundo_visivel = bool(visivel)

        # Invalida cache intermediário quando parâmetros visuais mudam.
        self._imagem_fundo_preparada = None
        self._imagem_fundo_preparada_key = None
        self._imagem_fundo_photo = None
        self._imagem_fundo_cache_key = None

    def _agendar_redesenho_zoom(self):
        if self._redesenho_zoom_agendado is not None:
            self.canvas.after_cancel(self._redesenho_zoom_agendado)
        self._redesenho_zoom_agendado = self.canvas.after(
            self.FUNDO_REDRAW_ZOOM_INTERVALO_MS,
            self._executar_redesenho_zoom,
        )

    def _executar_redesenho_zoom(self):
        self._redesenho_zoom_agendado = None
        self._disparar_redesenho()

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

        # Limita redraw por movimento do mouse para evitar gargalo com imagem de fundo.
        tempo_atual = time.time()
        if (tempo_atual - self._ultimo_redesenho_mouse_tempo) < (1.0 / 30.0):
            return

        self._ultimo_redesenho_mouse_tempo = tempo_atual
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

        self._agendar_redesenho_zoom()

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

        self._agendar_redesenho_zoom()

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

        self._desenhar_imagem_fundo(largura, altura)
        self._desenhar_grade(largura, altura)
        self._desenhar_reguas(largura, altura, cx, cy)
        self.canvas.create_line(0, cy, largura, cy, fill="#bdbdbd")
        self.canvas.create_line(cx, 0, cx, altura, fill="#bdbdbd")
        self.canvas.create_text(cx + 55, cy + 14, text="Origem visual (0,0)", fill="#666666")

        # Desenhar trajeto segmento por segmento
        pontos_segmentos = TrajectoryGeometry.segment_trajectory_points(trajeto)
        
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

    def _desenhar_imagem_fundo(self, largura, altura):
        if not self._fundo_visivel:
            return
        if self._imagem_fundo_original is None:
            return

        largura_base_px = max(1, int(self._imagem_fundo_original.width))
        altura_base_px = max(1, int(self._imagem_fundo_original.height))
        maior_lado_base_px = float(max(largura_base_px, altura_base_px))
        fator_aspecto_largura = largura_base_px / maior_lado_base_px
        fator_aspecto_altura = altura_base_px / maior_lado_base_px

        origem_x, origem_y = self.obter_origem_visual_m()
        centro_x_mundo = origem_x + self._fundo_offset_x_m
        centro_y_mundo = origem_y + self._fundo_offset_y_m
        largura_m = (
            self._fundo_tamanho_quadrado_m
            * self._fundo_escala_horizontal
            * self._fundo_zoom
            * fator_aspecto_largura
        )
        altura_m = (
            self._fundo_tamanho_quadrado_m
            * self._fundo_escala_vertical
            * self._fundo_zoom
            * fator_aspecto_altura
        )
        if largura_m <= 0 or altura_m <= 0:
            return

        x1_mundo = centro_x_mundo - largura_m / 2.0
        y1_mundo = centro_y_mundo - altura_m / 2.0
        x2_mundo = centro_x_mundo + largura_m / 2.0
        y2_mundo = centro_y_mundo + altura_m / 2.0

        sx1, sy1 = self.mundo_para_tela(x1_mundo, y1_mundo, largura, altura)
        sx2, sy2 = self.mundo_para_tela(x2_mundo, y2_mundo, largura, altura)

        esquerda = min(sx1, sx2)
        direita = max(sx1, sx2)
        topo = min(sy1, sy2)
        base = max(sy1, sy2)

        if direita < 0 or esquerda > largura or base < 0 or topo > altura:
            return

        largura_px = max(1, int(round(direita - esquerda)))
        altura_px = max(1, int(round(base - topo)))
        largura_px, altura_px = self._limitar_tamanho_render_fundo(largura_px, altura_px)

        imagem = self._obter_imagem_fundo_renderizada(largura_px, altura_px)
        if imagem is None:
            return

        centro_x = (esquerda + direita) / 2.0
        centro_y = (topo + base) / 2.0
        self.canvas.create_image(centro_x, centro_y, image=imagem, anchor="center")

    def _obter_imagem_fundo_renderizada(self, largura_px, altura_px):
        if self._imagem_fundo_original is None or not self.suporte_imagem_fundo_disponivel():
            return None

        imagem_preparada = self._obter_imagem_fundo_preparada()
        if imagem_preparada is None:
            return None

        largura_px = self._quantizar_tamanho_render(largura_px)
        altura_px = self._quantizar_tamanho_render(altura_px)
        cantos_efetivos = self._obter_cantos_efetivos()

        chave = (
            largura_px,
            altura_px,
            round(cantos_efetivos["canto_superior_esquerdo"], 4),
            round(cantos_efetivos["canto_superior_direito"], 4),
            round(cantos_efetivos["canto_inferior_direito"], 4),
            round(cantos_efetivos["canto_inferior_esquerdo"], 4),
            round(self._fundo_rotacao_graus, 2),
            id(imagem_preparada),
        )
        if self._imagem_fundo_cache_key == chave and self._imagem_fundo_photo is not None:
            return self._imagem_fundo_photo

        resample = Image.Resampling.BILINEAR if hasattr(Image, "Resampling") else Image.BILINEAR
        imagem = imagem_preparada.resize((largura_px, altura_px), resample=resample)
        imagem = self._aplicar_perspectiva(imagem)

        self._imagem_fundo_photo = ImageTk.PhotoImage(imagem)
        self._imagem_fundo_cache_key = chave
        return self._imagem_fundo_photo

    def _obter_imagem_fundo_preparada(self):
        if self._imagem_fundo_original is None:
            return None

        chave_preparada = (
            round(self._fundo_opacidade_percent, 2),
            id(self._imagem_fundo_original),
        )
        if self._imagem_fundo_preparada_key == chave_preparada and self._imagem_fundo_preparada is not None:
            return self._imagem_fundo_preparada

        imagem = self._imagem_fundo_original.copy()

        if self._fundo_opacidade_percent < 100.0:
            fator = self._fundo_opacidade_percent / 100.0
            canal_alpha = imagem.getchannel("A")
            canal_alpha = canal_alpha.point(lambda p, f=fator: int(p * f))
            imagem.putalpha(canal_alpha)

        self._imagem_fundo_preparada = imagem
        self._imagem_fundo_preparada_key = chave_preparada
        self._imagem_fundo_photo = None
        self._imagem_fundo_cache_key = None
        return self._imagem_fundo_preparada

    def _limitar_tamanho_render_fundo(self, largura_px, altura_px):
        largura = max(1, int(largura_px))
        altura = max(1, int(altura_px))
        return largura, altura

    @staticmethod
    def _quantizar_tamanho_render(valor, passo=16):
        valor = max(1, int(round(valor)))
        if valor <= passo:
            return valor
        return max(1, int(round(valor / float(passo))) * passo)

    def _aplicar_perspectiva(self, imagem):
        cantos_efetivos = self._obter_cantos_efetivos()
        return self.aplicar_transformacao_em_imagem(
            imagem,
            canto_superior_esquerdo=cantos_efetivos["canto_superior_esquerdo"],
            canto_superior_direito=cantos_efetivos["canto_superior_direito"],
            canto_inferior_direito=cantos_efetivos["canto_inferior_direito"],
            canto_inferior_esquerdo=cantos_efetivos["canto_inferior_esquerdo"],
            rotacao_graus=self._fundo_rotacao_graus,
        )

    def _obter_cantos_efetivos(self):
        # Compatibilidade: combina controles novos por canto com os parâmetros legados.
        legado_sup_esq = self._fundo_perspectiva_horizontal - self._fundo_perspectiva_vertical
        legado_sup_dir = self._fundo_perspectiva_horizontal + self._fundo_perspectiva_vertical
        legado_inf_dir = -self._fundo_perspectiva_horizontal + self._fundo_perspectiva_vertical
        legado_inf_esq = -self._fundo_perspectiva_horizontal - self._fundo_perspectiva_vertical
        limite_inclinacao = float(self.FUNDO_INCLINACAO_LIMITE)

        return {
            "canto_superior_esquerdo": max(-limite_inclinacao, min(limite_inclinacao, self._fundo_canto_superior_esquerdo + legado_sup_esq)),
            "canto_superior_direito": max(-limite_inclinacao, min(limite_inclinacao, self._fundo_canto_superior_direito + legado_sup_dir)),
            "canto_inferior_direito": max(-limite_inclinacao, min(limite_inclinacao, self._fundo_canto_inferior_direito + legado_inf_dir)),
            "canto_inferior_esquerdo": max(-limite_inclinacao, min(limite_inclinacao, self._fundo_canto_inferior_esquerdo + legado_inf_esq)),
        }

    @staticmethod
    def aplicar_transformacao_em_imagem(
        imagem,
        canto_superior_esquerdo=0.0,
        canto_superior_direito=0.0,
        canto_inferior_direito=0.0,
        canto_inferior_esquerdo=0.0,
        rotacao_graus=0.0,
    ):
        if imagem is None:
            return imagem

        limite_inclinacao = float(CanvasTrajectoryView.FUNDO_INCLINACAO_LIMITE)
        canto_sup_esq = max(-limite_inclinacao, min(limite_inclinacao, float(canto_superior_esquerdo)))
        canto_sup_dir = max(-limite_inclinacao, min(limite_inclinacao, float(canto_superior_direito)))
        canto_inf_dir = max(-limite_inclinacao, min(limite_inclinacao, float(canto_inferior_direito)))
        canto_inf_esq = max(-limite_inclinacao, min(limite_inclinacao, float(canto_inferior_esquerdo)))
        rotacao = max(-180.0, min(180.0, float(rotacao_graus)))

        if abs(rotacao) > 1e-6:
            resample = Image.Resampling.BILINEAR if hasattr(Image, "Resampling") else Image.BILINEAR
            try:
                imagem = imagem.rotate(-rotacao, resample=resample, expand=True, fillcolor=(0, 0, 0, 0))
            except Exception:
                pass

        largura, altura = imagem.size
        if largura < 4 or altura < 4:
            return imagem

        if (
            abs(canto_sup_esq) < 1e-6
            and abs(canto_sup_dir) < 1e-6
            and abs(canto_inf_dir) < 1e-6
            and abs(canto_inf_esq) < 1e-6
        ):
            return imagem

        max_deslocamento = min(largura, altura) * 0.35

        def deslocamento(valor):
            return valor * max_deslocamento

        d_sup_esq = deslocamento(canto_sup_esq)
        d_sup_dir = deslocamento(canto_sup_dir)
        d_inf_dir = deslocamento(canto_inf_dir)
        d_inf_esq = deslocamento(canto_inf_esq)

        ul_x, ul_y = 0.0 - d_sup_esq, 0.0 - d_sup_esq
        ur_x, ur_y = float(largura - 1) + d_sup_dir, 0.0 - d_sup_dir
        lr_x, lr_y = float(largura - 1) + d_inf_dir, float(altura - 1) + d_inf_dir
        ll_x, ll_y = 0.0 - d_inf_esq, float(altura - 1) + d_inf_esq

        destino = [
            (ul_x, ul_y),
            (ur_x, ur_y),
            (lr_x, lr_y),
            (ll_x, ll_y),
        ]

        min_x = min(p[0] for p in destino)
        max_x = max(p[0] for p in destino)
        min_y = min(p[1] for p in destino)
        max_y = max(p[1] for p in destino)

        largura_saida = max(1, int(round(max_x - min_x)) + 1)
        altura_saida = max(1, int(round(max_y - min_y)) + 1)

        destino_ajustado = [(x - min_x, y - min_y) for (x, y) in destino]
        origem = [
            (0.0, 0.0),
            (float(largura - 1), 0.0),
            (float(largura - 1), float(altura - 1)),
            (0.0, float(altura - 1)),
        ]

        coeficientes = CanvasTrajectoryView._resolver_coeficientes_perspectiva(destino_ajustado, origem)
        if coeficientes is None:
            return imagem

        resample = Image.Resampling.BILINEAR if hasattr(Image, "Resampling") else Image.BILINEAR
        try:
            return imagem.transform(
                (largura_saida, altura_saida),
                Image.Transform.PERSPECTIVE,
                coeficientes,
                resample=resample,
                fillcolor=(0, 0, 0, 0),
            )
        except Exception:
            return imagem

    @staticmethod
    def aplicar_perspectiva_em_imagem(imagem, perspectiva_horizontal, perspectiva_vertical):
        limite_inclinacao = float(CanvasTrajectoryView.FUNDO_INCLINACAO_LIMITE)
        px = max(-limite_inclinacao, min(limite_inclinacao, float(perspectiva_horizontal)))
        py = max(-limite_inclinacao, min(limite_inclinacao, float(perspectiva_vertical)))
        return CanvasTrajectoryView.aplicar_transformacao_em_imagem(
            imagem,
            canto_superior_esquerdo=px - py,
            canto_superior_direito=px + py,
            canto_inferior_direito=-px + py,
            canto_inferior_esquerdo=-px - py,
            rotacao_graus=0.0,
        )

    @staticmethod
    def _resolver_coeficientes_perspectiva(pontos_destino, pontos_origem):
        matriz = []
        vetor = []
        for (x, y), (u, v) in zip(pontos_destino, pontos_origem):
            matriz.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y])
            vetor.append(u)
            matriz.append([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y])
            vetor.append(v)

        return CanvasTrajectoryView._resolver_sistema_linear(matriz, vetor)

    @staticmethod
    def _resolver_sistema_linear(matriz, vetor):
        n = len(vetor)
        if n == 0:
            return None

        a = [linha[:] + [vetor[i]] for i, linha in enumerate(matriz)]

        for col in range(n):
            piv = max(range(col, n), key=lambda r: abs(a[r][col]))
            if abs(a[piv][col]) < 1e-9:
                return None

            if piv != col:
                a[col], a[piv] = a[piv], a[col]

            pivo = a[col][col]
            for j in range(col, n + 1):
                a[col][j] /= pivo

            for row in range(n):
                if row == col:
                    continue
                fator = a[row][col]
                if abs(fator) < 1e-12:
                    continue
                for j in range(col, n + 1):
                    a[row][j] -= fator * a[col][j]

        return [a[i][n] for i in range(n)]

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
        """Desenha os limites da pista com borda tracejada cinza.

        A origem visual é usada como referência de alinhamento do centro do retângulo.
        Largura = altura * 2 (proporção fixa).
        """
        limites = trajeto.borda_deteccao
        altura_limites = limites.altura
        largura_limites = altura_limites * 2.0  # Largura é altura × 2
        
        # Obter origem visual (centro do retângulo)
        origem_x, origem_y = self.obter_origem_visual_m()
        
        # Retângulo centralizado na origem visual.
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
