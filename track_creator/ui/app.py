import json
import math
import os
import tkinter as tk
import zipfile
from io import BytesIO
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from models.segments import CurveSegment, StraightSegment
from models.trajectory import Trajectory
from services.trajectory_exporter import TrajectoryExporter
from services.trajectory_geometry import TrajectoryGeometry
from services.trajectory_importer import TrajectoryImporter
from ui.canvas_view import CanvasTrajectoryView


# Dicionário de ícones representativos
ICONOS = {
    "adicionar": "➕",
    "inserir": "⬇",
    "atualizar": "↻",
    "aplicar": "✓",
    "resetar": "↺",
    "selecionar": "◉",
    "centralizar": "⊕",
    "desfazer": "↶",
    "refazer": "↷",
    "limpar": "🗑",
    "remover": "✕",
    "imagem": "🖼",
}


class TrajectoryGeneratorApp:
    FUNDO_PREVIEW_BASE_PERCENT = 100.0
    FUNDO_INCLINACAO_LIMITE = 2.5

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Trajectory Generator")

        self.trajeto = Trajectory()
        self.indice_selecionado = None
        self.projeto_modificado = False

        self._criar_variaveis()
        self._configurar_menu()
        self._montar_interface()
        self._atualizar_status_imagem_fundo()
        self._atualizar_campo_limites_largura()
        
        # Defer shortcuts configuration to after UI is fully loaded
        self.root.after(100, self._configurar_atalhos)
        self.root.protocol("WM_DELETE_WINDOW", self.fechar_aplicativo)

        TrajectoryGeometry.recalculate_poses(self.trajeto)
        self._atualizar_lista_segmentos()
        self._redesenhar()

    def _marcar_como_modificado(self):
        if not self.projeto_modificado:
            self.projeto_modificado = True
            self.root.title("Trajectory Generator *")

    def _marcar_como_salvo(self):
        if self.projeto_modificado:
            self.projeto_modificado = False
            self.root.title("Trajectory Generator")

    def fechar_aplicativo(self):
        if self.projeto_modificado:
            # askyesnocancel: True (Yes), False (No), None (Cancel)
            resposta = messagebox.askyesnocancel(
                "Alterações não salvas", 
                "Você possui alterações não salvas. Deseja salvar antes de sair?"
            )
            if resposta is True:
                # O usuário quer salvar antes de sair
                # Se não exportar com sucesso (ex: cancelar no dialog de salvar), a gente aborta o fechamento
                if self.exportar_tfg():
                    self.root.destroy()
            elif resposta is False:
                # O usuário NÃO quer salvar, apenas sair
                self.root.destroy()
            # Se resposta is None, o usuário cancelou a ação de fechar, então não fazemos nada.
        else:
            # Não tem alterações, pode sair direto
            self.root.destroy()

    def _criar_variaveis(self):
        self.var_reta_comprimento = tk.StringVar(value="10")
        self.var_reta_angulo = tk.StringVar(value="0")
        self.var_curva_raio = tk.StringVar(value="5")
        self.var_curva_lado = tk.StringVar(value="esquerda")
        self.var_curva_angulo = tk.StringVar(value="180")
        self.var_resolucao = tk.StringVar(value="300")
        self.var_unidade = tk.StringVar(value="cm")
        self.var_fator_personalizado = tk.StringVar(value="1.0")
        self.var_zoom = tk.DoubleVar(value=18.0)
        self.var_zoom_max = tk.StringVar(value="120")
        self.var_mostrar_grade = tk.BooleanVar(value=True)
        self.var_origem_x = tk.StringVar(value="0")
        self.var_origem_y = tk.StringVar(value="0")
        self.var_segmento_selecionado = tk.StringVar(value="Nenhum trecho selecionado")
        self.var_modo_resolucao_auto = tk.BooleanVar(value=True)
        self.var_pontos_por_metro = tk.StringVar(value="100")
        self.var_expandir_resolucao = tk.BooleanVar(value=False)
        # Variáveis para marcações
        self.var_marcacao_distancia = tk.StringVar(value="0.5")
        self.var_marcacao_lado = tk.StringVar(value="esquerda")
        # Variáveis para labels dinâmicos de unidade
        self.var_label_comprimento = tk.StringVar(value="Comprimento (m)")
        self.var_label_raio = tk.StringVar(value="Raio (m)")
        self.var_label_distancia_marcacao = tk.StringVar(value="Distância (m)")
        self.var_label_origem_x = tk.StringVar(value="Origem X (m)")
        self.var_label_origem_y = tk.StringVar(value="Origem Y (m)")
        # Variáveis para limites da pista
        self.var_limites_altura = tk.StringVar(value="0.5")
        self.var_label_limites_altura = tk.StringVar(value="Altura (m)")

        # Variáveis para imagem de fundo
        self.var_fundo_tamanho_quadrado = tk.StringVar(value="1.0")
        self.var_fundo_escala_horizontal = tk.StringVar(value="1.0")
        self.var_fundo_escala_vertical = tk.StringVar(value="1.0")
        self.var_fundo_zoom = tk.StringVar(value="1.0")
        self.var_fundo_offset_x_m = tk.DoubleVar(value=0.0)
        self.var_fundo_offset_y_m = tk.DoubleVar(value=0.0)
        self.var_fundo_perspectiva_horizontal = tk.DoubleVar(value=0.0)
        self.var_fundo_perspectiva_vertical = tk.DoubleVar(value=0.0)
        self.var_fundo_canto_superior_esquerdo = tk.DoubleVar(value=0.0)
        self.var_fundo_canto_superior_direito = tk.DoubleVar(value=0.0)
        self.var_fundo_canto_inferior_direito = tk.DoubleVar(value=0.0)
        self.var_fundo_canto_inferior_esquerdo = tk.DoubleVar(value=0.0)
        self.var_fundo_rotacao_graus = tk.DoubleVar(value=0.0)
        self.var_fundo_tamanho_preview_percent = tk.DoubleVar(value=self.FUNDO_PREVIEW_BASE_PERCENT)
        self.var_fundo_opacidade = tk.DoubleVar(value=60.0)
        self.var_fundo_visivel = tk.BooleanVar(value=True)
        self.var_fundo_status = tk.StringVar(value="Nenhuma imagem de fundo carregada")
        self.var_fundo_label_opacidade = tk.StringVar(value="Opacidade: 60%")
        self._fundo_imagem_bytes = None
        self._fundo_imagem_nome = None
        self._fundo_carregado_no_canvas = False
        self._ignorar_callback_fundo = False

    def _configurar_menu(self):
        menubar = tk.Menu(self.root)

        menu_arquivo = tk.Menu(menubar, tearoff=0)
        menu_arquivo.add_command(label="Novo projeto", command=self.novo_projeto)
        menu_arquivo.add_separator()
        menu_arquivo.add_command(label="Salvar como .tfg...", command=self.exportar_tfg, accelerator="Ctrl+S")
        menu_arquivo.add_command(label="Carregar arquivo .tfg...", command=self.carregar_tfg, accelerator="Ctrl+O")
        menu_arquivo.add_separator()
        menu_arquivo.add_command(label="Sair", command=self.fechar_aplicativo)
        menubar.add_cascade(label="Arquivo", menu=menu_arquivo)

        menu_editar = tk.Menu(menubar, tearoff=0)
        menu_editar.add_command(label="Desfazer", command=self.desfazer, accelerator="Ctrl+Z")
        menu_editar.add_command(label="Refazer", command=self.refazer, accelerator="Ctrl+Y")
        menu_editar.add_separator()
        menu_editar.add_command(label="Remover seleção", command=self.remover_selecao)
        menu_editar.add_command(label="Limpar tudo", command=self.limpar_tudo)
        menubar.add_cascade(label="Editar", menu=menu_editar)

        menu_visualizacao = tk.Menu(menubar, tearoff=0)
        menu_visualizacao.add_command(label="Centralizar visão", command=self.centralizar_visao)
        menu_visualizacao.add_command(label="Resetar origem visual", command=self.resetar_origem_visual)
        menubar.add_cascade(label="Visualização", menu=menu_visualizacao)

        menu_fundo = tk.Menu(menubar, tearoff=0)
        menu_fundo.add_command(label="Carregar imagem...", command=self.carregar_imagem_fundo)
        menu_fundo.add_command(label="Ajustar cantos/rotação/zoom...", command=self.abrir_janela_ajuste_imagem_fundo)
        menu_fundo.add_separator()
        menu_fundo.add_command(label="Remover imagem de fundo", command=self.remover_imagem_fundo)
        menubar.add_cascade(label="Fundo", menu=menu_fundo)

        menu_ajuda = tk.Menu(menubar, tearoff=0)
        menu_ajuda.add_command(label="Atalhos de teclado", command=self.mostrar_ajuda)
        menubar.add_cascade(label="Ajuda", menu=menu_ajuda)

        self.root.config(menu=menubar)

    def _montar_interface(self):
        container = ttk.Frame(self.root, padding=10)
        container.pack(fill="both", expand=True)

        # Configurar grid: esquerda 10%, meio 80%, direita 10%
        # Usando pesos proporcionais: 1, 8, 1
        container.columnconfigure(0, weight=1)    # Esquerda 10%
        container.columnconfigure(1, weight=8)    # Meio 80%
        container.columnconfigure(2, weight=1)    # Direita 10%
        container.rowconfigure(0, weight=1)

        painel_esquerdo = ttk.Frame(container)
        painel_esquerdo.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        painel_esquerdo.rowconfigure(0, weight=1)
        painel_esquerdo.columnconfigure(0, weight=1)

        painel_centro = ttk.Frame(container)
        painel_centro.grid(row=0, column=1, sticky="nsew", padx=5)
        painel_centro.rowconfigure(0, weight=1)
        painel_centro.columnconfigure(0, weight=1)

        painel_direito = ttk.Frame(container)
        painel_direito.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        painel_direito.rowconfigure(0, weight=1)
        painel_direito.columnconfigure(0, weight=1)

        self._montar_painel_esquerdo(painel_esquerdo)
        self._montar_canvas(painel_centro)
        self._montar_painel_direito(painel_direito)

    def _montar_painel_esquerdo(self, parent):
        frame_reta = ttk.LabelFrame(parent, text="Reta", padding=10)
        frame_reta.pack(fill="x", pady=(0, 10))
        
        frame_reta_comp = ttk.Frame(frame_reta)
        frame_reta_comp.pack(fill="x", pady=(0, 4))
        ttk.Label(frame_reta_comp, textvariable=self.var_label_comprimento).pack(side="left")
        ttk.Entry(frame_reta_comp, textvariable=self.var_reta_comprimento, width=18).pack(side="right", padx=(4, 0))
        
        frame_reta_ang = ttk.Frame(frame_reta)
        frame_reta_ang.pack(fill="x", pady=(0, 8))
        ttk.Label(frame_reta_ang, text="Ângulo absoluto (graus)").pack(side="left")
        ttk.Entry(frame_reta_ang, textvariable=self.var_reta_angulo, width=18).pack(side="right", padx=(4, 0))
        
        frame_botoes_reta = ttk.Frame(frame_reta)
        frame_botoes_reta.pack(fill="x")
        ttk.Button(frame_botoes_reta, text=f"{ICONOS['adicionar']} Adicionar", command=self.adicionar_reta).pack(side="left", fill="both", expand=True, padx=(0, 2))
        ttk.Button(frame_botoes_reta, text=f"{ICONOS['inserir']} Inserir", command=self.inserir_reta_apos_selecao).pack(side="left", fill="both", expand=True, padx=(1, 2))
        ttk.Button(frame_botoes_reta, text=f"{ICONOS['atualizar']} Atualizar", command=self.atualizar_reta_selecionada).pack(side="left", fill="both", expand=True, padx=(1, 0))

        frame_curva = ttk.LabelFrame(parent, text="Curva", padding=10)
        frame_curva.pack(fill="x", pady=(0, 10))
        
        frame_curva_raio = ttk.Frame(frame_curva)
        frame_curva_raio.pack(fill="x", pady=(0, 4))
        ttk.Label(frame_curva_raio, textvariable=self.var_label_raio).pack(side="left")
        ttk.Entry(frame_curva_raio, textvariable=self.var_curva_raio, width=18).pack(side="right", padx=(4, 0))
        
        frame_curva_lado = ttk.Frame(frame_curva)
        frame_curva_lado.pack(fill="x", pady=(0, 4))
        ttk.Label(frame_curva_lado, text="Lado").pack(side="left")
        ttk.Combobox(
            frame_curva_lado,
            textvariable=self.var_curva_lado,
            values=["esquerda", "direita"],
            width=20,
            state="readonly",
        ).pack(side="right", padx=(4, 0))
        
        frame_curva_ang = ttk.Frame(frame_curva)
        frame_curva_ang.pack(fill="x", pady=(0, 8))
        ttk.Label(frame_curva_ang, text="Ângulo da curva (graus)").pack(side="left")
        ttk.Entry(frame_curva_ang, textvariable=self.var_curva_angulo, width=18).pack(side="right", padx=(4, 0))
        
        frame_botoes_curva = ttk.Frame(frame_curva)
        frame_botoes_curva.pack(fill="x")
        ttk.Button(frame_botoes_curva, text=f"{ICONOS['adicionar']} Adicionar", command=self.adicionar_curva).pack(side="left", fill="both", expand=True, padx=(0, 2))
        ttk.Button(frame_botoes_curva, text=f"{ICONOS['inserir']} Inserir", command=self.inserir_curva_apos_selecao).pack(side="left", fill="both", expand=True, padx=(1, 2))
        ttk.Button(frame_botoes_curva, text=f"{ICONOS['atualizar']} Atualizar", command=self.atualizar_curva_selecionada).pack(side="left", fill="both", expand=True, padx=(1, 0))

        frame_marcacao = ttk.LabelFrame(parent, text="Marcações", padding=10)
        frame_marcacao.pack(fill="x", pady=(0, 10))
        
        frame_marcacao_lado = ttk.Frame(frame_marcacao)
        frame_marcacao_lado.pack(fill="x", pady=(0, 4))
        ttk.Label(frame_marcacao_lado, text="Lado").pack(side="left")
        ttk.Combobox(
            frame_marcacao_lado,
            textvariable=self.var_marcacao_lado,
            values=["esquerda", "direita"],
            width=20,
            state="readonly",
        ).pack(side="right", padx=(4, 0))
        
        frame_marcacao_dist = ttk.Frame(frame_marcacao)
        frame_marcacao_dist.pack(fill="x", pady=(0, 8))
        ttk.Label(frame_marcacao_dist, textvariable=self.var_label_distancia_marcacao).pack(side="left")
        ttk.Entry(frame_marcacao_dist, textvariable=self.var_marcacao_distancia, width=18).pack(side="right", padx=(4, 0))
        
        ttk.Button(frame_marcacao, text=f"{ICONOS['aplicar']} Aplicar a todas", command=self.aplicar_marcacao_a_todas).pack(fill="x")

        frame_lista = ttk.LabelFrame(parent, text="Ordem dos trajetos", padding=10)
        frame_lista.pack(fill="both", expand=True, pady=(10, 0))

        ttk.Label(frame_lista, textvariable=self.var_segmento_selecionado, justify="left").pack(anchor="w", pady=(0, 8))

        botoes_lista = ttk.Frame(frame_lista)
        botoes_lista.pack(fill="x", pady=(0, 8))
        ttk.Button(botoes_lista, text=f"{ICONOS['desfazer']} Desfazer", command=self.desfazer).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(botoes_lista, text=f"{ICONOS['refazer']} Refazer", command=self.refazer).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(botoes_lista, text=f"{ICONOS['limpar']} Limpar tudo", command=self.limpar_tudo).pack(side="left", fill="x", expand=True, padx=(4, 0))

        botoes_lista2 = ttk.Frame(frame_lista)
        botoes_lista2.pack(fill="x", pady=(0, 8))
        ttk.Button(botoes_lista2, text=f"{ICONOS['remover']} Remover seleção", command=self.remover_selecao).pack(side="left", fill="x", expand=True)

        self.listbox_segmentos = tk.Listbox(frame_lista, width=40, height=10, selectmode=tk.SINGLE, 
                                            selectbackground="#4CAF50", selectforeground="white",
                                            bg="white", fg="black")
        self.listbox_segmentos.pack(side="left", fill="both", expand=True)
        self.listbox_segmentos.bind("<<ListboxSelect>>", self._ao_selecionar_segmento)

        scrollbar_lista = ttk.Scrollbar(frame_lista, orient="vertical", command=self.listbox_segmentos.yview)
        scrollbar_lista.pack(side="right", fill="y")
        self.listbox_segmentos.config(yscrollcommand=scrollbar_lista.set)

    def _montar_canvas(self, parent):
        frame_canvas = ttk.LabelFrame(parent, text="Visualização", padding=8)
        frame_canvas.pack(fill="both", expand=True)

        toolbar_canvas = ttk.Frame(frame_canvas)
        toolbar_canvas.pack(fill="x", pady=(0, 8))
        ttk.Label(toolbar_canvas, text="Zoom").pack(side="left")
        ttk.Scale(
            toolbar_canvas,
            from_=2.0,
            to=120.0,
            variable=self.var_zoom,
            command=lambda v: self._redesenhar(),
        ).pack(side="left", fill="x", expand=True, padx=(8, 12))
        ttk.Button(toolbar_canvas, text=f"{ICONOS['centralizar']} Centralizar", command=self.centralizar_visao).pack(side="left")

        self.canvas_view = CanvasTrajectoryView(
            frame_canvas,
            zoom_var=self.var_zoom,
            zoom_max_var=self.var_zoom_max,
            mostrar_grade_var=self.var_mostrar_grade,
            origem_x_var=self.var_origem_x,
            origem_y_var=self.var_origem_y,
            unidade_var=self.var_unidade,
            fator_personalizado_var=self.var_fator_personalizado,
        )
        self.canvas_view.set_redraw_callback(self._redesenhar)
        self.canvas_view.set_segmento_click_callback(self._ao_clicar_segmento_no_canvas)
        self.canvas_view.set_origem_click_callback(self._ao_origem_clicada)
        self.canvas_view.pack(fill="both", expand=True)

    def _montar_painel_direito(self, parent):
        frame_visual = ttk.LabelFrame(parent, text="Opções de visualização", padding=10)
        frame_visual.pack(fill="x", pady=(0, 10))
        # Checkbutton para mostrar grade
        ttk.Checkbutton(
            frame_visual,
            text="Mostrar grade cinza",
            variable=self.var_mostrar_grade,
            command=self._redesenhar,
        ).pack(anchor="w", pady=(0, 6))
        
        # Frames para organizar labels e entries em duas colunas
        frame_zoom_max = ttk.Frame(frame_visual)
        frame_zoom_max.pack(fill="x", pady=(0, 4))
        ttk.Label(frame_zoom_max, text="Limite máximo zoom").pack(side="left")
        ttk.Entry(frame_zoom_max, textvariable=self.var_zoom_max, width=10).pack(side="right", padx=(4, 0))
        
        frame_origem_x = ttk.Frame(frame_visual)
        frame_origem_x.pack(fill="x", pady=(0, 4))
        ttk.Label(frame_origem_x, textvariable=self.var_label_origem_x).pack(side="left")
        ttk.Entry(frame_origem_x, textvariable=self.var_origem_x, width=10).pack(side="right", padx=(4, 0))
        
        frame_origem_y = ttk.Frame(frame_visual)
        frame_origem_y.pack(fill="x", pady=(0, 8))
        ttk.Label(frame_origem_y, textvariable=self.var_label_origem_y).pack(side="left")
        ttk.Entry(frame_origem_y, textvariable=self.var_origem_y, width=10).pack(side="right", padx=(4, 0))
        
        # Frame para botões horizontais
        frame_botoes_visual = ttk.Frame(frame_visual)
        frame_botoes_visual.pack(fill="x", pady=(0, 0))
        ttk.Button(frame_botoes_visual, text=f"{ICONOS['aplicar']} Aplicar", command=self._redesenhar).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ttk.Button(frame_botoes_visual, text=f"{ICONOS['resetar']} Resetar", command=self.resetar_origem_visual).pack(side="left", fill="x", expand=True, padx=(1, 2))
        ttk.Button(frame_botoes_visual, text=f"{ICONOS['selecionar']} Selecionar", command=self.ativar_selecionador_origem).pack(side="left", fill="x", expand=True, padx=(1, 0))

        frame_fundo = ttk.LabelFrame(parent, text="Imagem de fundo", padding=10)
        frame_fundo.pack(fill="x", pady=(0, 10))

        ttk.Label(
            frame_fundo,
            textvariable=self.var_fundo_status,
            justify="left",
            wraplength=220,
        ).pack(anchor="w", pady=(0, 6))

        ttk.Checkbutton(
            frame_fundo,
            text="Mostrar imagem no canvas",
            variable=self.var_fundo_visivel,
            command=self._ao_alterar_visibilidade_fundo,
        ).pack(anchor="w", pady=(0, 6))

        ttk.Label(frame_fundo, textvariable=self.var_fundo_label_opacidade).pack(anchor="w")
        ttk.Scale(
            frame_fundo,
            from_=0.0,
            to=100.0,
            variable=self.var_fundo_opacidade,
            command=self._ao_alterar_opacidade_fundo,
        ).pack(fill="x", pady=(0, 8))

        frame_botoes_fundo = ttk.Frame(frame_fundo)
        frame_botoes_fundo.pack(fill="x")
        ttk.Button(frame_botoes_fundo, text=f"{ICONOS['imagem']} Carregar", command=self.carregar_imagem_fundo).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ttk.Button(frame_botoes_fundo, text="Ajustar", command=self.abrir_janela_ajuste_imagem_fundo).pack(side="left", fill="x", expand=True, padx=(1, 2))
        ttk.Button(frame_botoes_fundo, text="Remover", command=self.remover_imagem_fundo).pack(side="left", fill="x", expand=True, padx=(1, 0))

        frame_status = ttk.LabelFrame(parent, text="Status", padding=10)
        frame_status.pack(fill="x", pady=(10, 10))
        self.lbl_status = ttk.Label(frame_status, justify="left")
        self.lbl_status.pack(anchor="w", pady=(0, 8))
        
        # Seção colapsável de Resolução
        frame_resolucao_header = ttk.Frame(frame_status)
        frame_resolucao_header.pack(fill="x", pady=(8, 0))
        
        btn_expandir = ttk.Button(
            frame_resolucao_header,
            text="▼ Resolução",
            command=self._alternar_resolucao,
            width=20
        )
        btn_expandir.pack(fill="x")
        self.btn_expandir_resolucao = btn_expandir
        
        self.frame_resolucao_conteudo = ttk.Frame(frame_status)
        self.frame_resolucao_conteudo.pack(fill="x", pady=(4, 0))
        
        ttk.Checkbutton(
            self.frame_resolucao_conteudo,
            text="Automática",
            variable=self.var_modo_resolucao_auto,
            command=self._atualizar_estado_resolucao,
        ).pack(anchor="w", pady=(0, 4))
        
        ttk.Label(self.frame_resolucao_conteudo, text="Pontos por metro").pack(anchor="w")
        self.entry_pontos_por_metro = ttk.Entry(self.frame_resolucao_conteudo, textvariable=self.var_pontos_por_metro, width=18)
        self.entry_pontos_por_metro.pack(anchor="w", pady=(0, 4))
        self.var_pontos_por_metro.trace("w", lambda *args: self._ao_mudar_pontos_por_metro())
        
        ttk.Label(self.frame_resolucao_conteudo, text="Resolução (total)").pack(anchor="w")
        self.entry_resolucao = ttk.Entry(self.frame_resolucao_conteudo, textvariable=self.var_resolucao, width=18)
        self.entry_resolucao.pack(anchor="w", pady=(0, 8))
        
        ttk.Label(self.frame_resolucao_conteudo, text="Unidade de saída").pack(anchor="w")
        self.combo_unidade = ttk.Combobox(
            self.frame_resolucao_conteudo,
            textvariable=self.var_unidade,
            values=["m", "cm", "mm", "km", "personalizada"],
            width=16,
            state="readonly",
        )
        self.combo_unidade.pack(anchor="w", pady=(0, 4))
        self.combo_unidade.bind("<<ComboboxSelected>>", lambda e: self._atualizar_estado_fator())
        
        ttk.Label(self.frame_resolucao_conteudo, text="Fator personalizado").pack(anchor="w")
        self.entry_fator_personalizado = ttk.Entry(self.frame_resolucao_conteudo, textvariable=self.var_fator_personalizado, width=18)
        self.entry_fator_personalizado.pack(anchor="w", pady=(0, 4))
        self._atualizar_estado_fator()
        
        self._ocultar_resolucao()
        self._atualizar_estado_resolucao()

        frame_limites = ttk.LabelFrame(parent, text="Limites da Pista", padding=10)
        frame_limites.pack(fill="x", pady=(10, 0))
        
        frame_limites_altura = ttk.Frame(frame_limites)
        frame_limites_altura.pack(fill="x", pady=(0, 4))
        ttk.Label(frame_limites_altura, textvariable=self.var_label_limites_altura).pack(side="left")
        ttk.Entry(frame_limites_altura, textvariable=self.var_limites_altura, width=18).pack(side="right", padx=(4, 0))
        
        # Campo de largura não editável (calcula automaticamente: altura × 2)
        frame_limites_largura = ttk.Frame(frame_limites)
        frame_limites_largura.pack(fill="x", pady=(0, 8))
        ttk.Label(frame_limites_largura, text="Largura (altura × 2)").pack(side="left")
        self.entry_limites_largura_display = ttk.Entry(frame_limites_largura, width=18, state="readonly")
        self.entry_limites_largura_display.pack(side="right", padx=(4, 0))
        
        # Callback quando altura muda
        self.var_limites_altura.trace("w", lambda *args: self._ao_mudar_limites_altura())

        self._atualizar_label_opacidade_fundo()

    def _configurar_atalhos(self):
        # Usar bind() no root e bind_all() para garantir cobertura global
        self.root.bind("<Control-z>", lambda e: self._atalho_desfazer(e) or "break")
        self.root.bind("<Control-Z>", lambda e: self._atalho_desfazer(e) or "break")
        self.root.bind("<Control-y>", lambda e: self._atalho_refazer(e) or "break")
        self.root.bind("<Control-Y>", lambda e: self._atalho_refazer(e) or "break")
        self.root.bind("<Control-s>", lambda e: self._atalho_salvar(e) or "break")
        self.root.bind("<Control-S>", lambda e: self._atalho_salvar(e) or "break")
        self.root.bind("<Control-o>", lambda e: self._atalho_carregar(e) or "break")
        self.root.bind("<Control-O>", lambda e: self._atalho_carregar(e) or "break")
        self.root.bind("<Control-e>", lambda e: self._atalho_exportar(e) or "break")
        self.root.bind("<Control-E>", lambda e: self._atalho_exportar(e) or "break")
        self.root.bind("<Escape>", lambda e: self._atalho_deselecionar(e) or "break")

    def _atalho_desfazer(self, event=None):
        self.desfazer()
        return "break"

    def _atalho_refazer(self, event=None):
        self.refazer()
        return "break"

    def _atalho_salvar(self, event=None):
        self.exportar_tfg()
        return "break"

    def _atalho_carregar(self, event=None):
        self.carregar_tfg()
        return "break"

    def _atalho_exportar(self, event=None):
        self.exportar_tfg()
        return "break"

    def _atalho_deselecionar(self, event=None):
        self.deselecionar()
        return "break"

    def _atalho_resetar_zoom(self, event=None):
        self.resetar_origem_visual()
        return "break"

    def deselecionar(self):
        """Apenas desseleciona sem remover o segmento"""
        if self.trajeto.segmentos:
            self.listbox_segmentos.selection_clear(0, tk.END)
            self.indice_selecionado = None
            self.var_segmento_selecionado.set("Nenhum trecho selecionado")
            self._redesenhar()

    def _atualizar_estado_fator(self):
        estado = "normal" if self.var_unidade.get() == "personalizada" else "disabled"
        self.entry_fator_personalizado.configure(state=estado)
        
        # Atualizar labels com a unidade selecionada
        unidade = self.var_unidade.get()
        if unidade == "personalizada":
            unidade_label = "unid."
        else:
            unidade_label = unidade
        
        self.var_label_comprimento.set(f"Comprimento ({unidade_label})")
        self.var_label_raio.set(f"Raio ({unidade_label})")
        self.var_label_distancia_marcacao.set(f"Distância ({unidade_label})")
        self.var_label_origem_x.set(f"Origem X ({unidade_label})")
        self.var_label_origem_y.set(f"Origem Y ({unidade_label})")
        self.var_label_limites_altura.set(f"Altura ({unidade_label})")

    def _atualizar_estado_resolucao(self):
        modo_auto = self.var_modo_resolucao_auto.get()
        self.entry_pontos_por_metro.configure(state="normal" if modo_auto else "disabled")
        self.entry_resolucao.configure(state="disabled" if modo_auto else "normal")
        if modo_auto:
            self._recalcular_resolucao_automatica()

    def _ao_mudar_pontos_por_metro(self):
        if self.var_modo_resolucao_auto.get():
            self._recalcular_resolucao_automatica()

    def _recalcular_resolucao_automatica(self):
        try:
            comprimento_total = TrajectoryGeometry.total_length(self.trajeto)
            pontos_por_metro = float(self.var_pontos_por_metro.get())
            if comprimento_total <= 0 or pontos_por_metro <= 0:
                return
            qtd_pontos = max(2, int(comprimento_total * pontos_por_metro))
            self.var_resolucao.set(str(qtd_pontos))
        except ValueError:
            pass

    def _alternar_resolucao(self):
        if self.var_expandir_resolucao.get():
            self._ocultar_resolucao()
        else:
            self._mostrar_resolucao()

    def _mostrar_resolucao(self):
        self.var_expandir_resolucao.set(True)
        self.frame_resolucao_conteudo.pack(fill="x", pady=(4, 0))
        self.btn_expandir_resolucao.config(text="▲ Resolução")

    def _ocultar_resolucao(self):
        self.var_expandir_resolucao.set(False)
        self.frame_resolucao_conteudo.pack_forget()
        self.btn_expandir_resolucao.config(text="▼ Resolução")

    def _atualizar_estado(self, preservar_selecao=True, modificado=True):
        if modificado:
            self._marcar_como_modificado()
        indice = self.indice_selecionado if preservar_selecao else None
        TrajectoryGeometry.recalculate_poses(self.trajeto)
        self._recalcular_posicoes_marcacoes()
        if self.var_modo_resolucao_auto.get():
            self._recalcular_resolucao_automatica()
        self._atualizar_campo_limites_largura()
        self._atualizar_lista_segmentos(indice)
        self._redesenhar()

    def _recalcular_posicoes_marcacoes(self):
        """Recalcula as posições de todas as marcações baseado nos segmentos atuais."""
        for i, marcacao in enumerate(self.trajeto.marcacoes):
            if i < len(self.trajeto.segmentos):
                pos = TrajectoryGeometry.compute_marking_position(
                    self.trajeto,
                    i,
                    marcacao.lado,
                    marcacao.distancia
                )
                if pos is not None:
                    marcacao.x, marcacao.y, marcacao.angulo_eixo_x = pos

    def _construir_segmento_reta(self):
        comprimento = float(self.var_reta_comprimento.get())
        angulo_graus = float(self.var_reta_angulo.get())
        if comprimento <= 0:
            raise ValueError("Informe comprimento > 0.")
        if not (-360 <= angulo_graus <= 360):
            raise ValueError("Informe ângulo entre -360° e 360°.")
        return StraightSegment(length=comprimento, angle_degrees=angulo_graus)

    def _construir_segmento_curva(self):
        raio = float(self.var_curva_raio.get())
        angulo_central_graus = float(self.var_curva_angulo.get())
        if raio <= 0:
            raise ValueError("Informe raio > 0.")
        if not (-360 <= angulo_central_graus <= 360):
            raise ValueError("Informe ângulo da curva entre -360° e 360°.")
        return CurveSegment(
            radius=raio,
            side=self.var_curva_lado.get(),
            central_angle_degrees=angulo_central_graus,
        )

    def adicionar_reta(self):
        try:
            self.trajeto.adicionar_segmento(self._construir_segmento_reta())
        except ValueError as e:
            messagebox.showerror("Valor inválido", str(e))
            return
        self.indice_selecionado = len(self.trajeto.segmentos) - 1
        self._atualizar_estado()

    def inserir_reta_apos_selecao(self):
        try:
            segmento = self._construir_segmento_reta()
        except ValueError as e:
            messagebox.showerror("Valor inválido", str(e))
            return

        if self.indice_selecionado is None:
            self.trajeto.adicionar_segmento(segmento)
            self.indice_selecionado = len(self.trajeto.segmentos) - 1
        else:
            self.trajeto.inserir_segmento(self.indice_selecionado + 1, segmento)
            self.indice_selecionado += 1
        self._atualizar_estado()

    def atualizar_reta_selecionada(self):
        if self.indice_selecionado is None:
            messagebox.showwarning("Nenhuma seleção", "Selecione uma reta na lista antes de atualizar.")
            return
        segmento_atual = self.trajeto.obter_segmento(self.indice_selecionado)
        if not isinstance(segmento_atual, StraightSegment):
            messagebox.showwarning("Tipo incorreto", "O item selecionado não é uma reta.")
            return
        try:
            novo_segmento = self._construir_segmento_reta()
        except ValueError as e:
            messagebox.showerror("Valor inválido", str(e))
            return
        self.trajeto.atualizar_segmento(self.indice_selecionado, novo_segmento)
        self._ao_alterar_marcacao()
        self._atualizar_estado()

    def adicionar_curva(self):
        try:
            self.trajeto.adicionar_segmento(self._construir_segmento_curva())
        except ValueError as e:
            messagebox.showerror("Valor inválido", str(e))
            return
        self.indice_selecionado = len(self.trajeto.segmentos) - 1
        self._atualizar_estado()

    def inserir_curva_apos_selecao(self):
        try:
            segmento = self._construir_segmento_curva()
        except ValueError as e:
            messagebox.showerror("Valor inválido", str(e))
            return

        if self.indice_selecionado is None:
            self.trajeto.adicionar_segmento(segmento)
            self.indice_selecionado = len(self.trajeto.segmentos) - 1
        else:
            self.trajeto.inserir_segmento(self.indice_selecionado + 1, segmento)
            self.indice_selecionado += 1
        self._atualizar_estado()

    def atualizar_curva_selecionada(self):
        if self.indice_selecionado is None:
            messagebox.showwarning("Nenhuma seleção", "Selecione uma curva na lista antes de atualizar.")
            return
        segmento_atual = self.trajeto.obter_segmento(self.indice_selecionado)
        if not isinstance(segmento_atual, CurveSegment):
            messagebox.showwarning("Tipo incorreto", "O item selecionado não é uma curva.")
            return
        try:
            novo_segmento = self._construir_segmento_curva()
        except ValueError as e:
            messagebox.showerror("Valor inválido", str(e))
            return
        self.trajeto.atualizar_segmento(self.indice_selecionado, novo_segmento)
        self._ao_alterar_marcacao()
        self._atualizar_estado()

    def _ao_alterar_marcacao(self):
        """Atualiza a marcação do segmento selecionado quando lado ou distância mudam."""
        if self.indice_selecionado is None:
            return
        
        if self.indice_selecionado >= len(self.trajeto.marcacoes):
            return
        
        try:
            distancia = float(self.var_marcacao_distancia.get())
            if distancia <= 0:
                return
        except ValueError:
            return
        
        marcacao = self.trajeto.marcacoes[self.indice_selecionado]
        novo_lado = self.var_marcacao_lado.get()
        
        # Verifica se houve mudança real
        if marcacao.lado == novo_lado and marcacao.distancia == distancia:
            return
        
        # Recalcula a posição da marcação
        pos = TrajectoryGeometry.compute_marking_position(
            self.trajeto,
            self.indice_selecionado,
            novo_lado,
            distancia
        )
        
        if pos is not None:
            novo_x, novo_y, novo_angulo = pos
            # Registra a mudança no histórico
            self.trajeto.modificar_marcacao(
                self.indice_selecionado,
                novo_lado,
                distancia,
                novo_x,
                novo_y,
                novo_angulo
            )
            self._marcar_como_modificado()
            self._redesenhar()

    def aplicar_marcacao_a_todas(self):
        """Aplica a distância atual a todas as marcações do trajeto, mantendo os lados originais."""
        try:
            distancia = float(self.var_marcacao_distancia.get())
            if distancia <= 0:
                messagebox.showerror("Valor inválido", "A distância deve ser maior que zero.")
                return
        except ValueError:
            messagebox.showerror("Valor inválido", "Distância inválida.")
            return
        
        atualizou_alguma = False
        for i, marcacao in enumerate(self.trajeto.marcacoes):
            if marcacao.distancia == distancia:
                continue
                
            pos = TrajectoryGeometry.compute_marking_position(
                self.trajeto,
                i,
                marcacao.lado, # Mantém o lado original
                distancia
            )
            if pos is not None:
                novo_x, novo_y, novo_angulo = pos
                self.trajeto.modificar_marcacao(
                    i,
                    marcacao.lado, # Mantém o lado original
                    distancia,
                    novo_x,
                    novo_y,
                    novo_angulo
                )
                atualizou_alguma = True
                
        if atualizou_alguma:
            self._redesenhar()
            self._atualizar_estado()
            messagebox.showinfo("Sucesso", "Marcações atualizadas com sucesso!")

    def desfazer(self):
        if self.trajeto.desfazer():
            self.indice_selecionado = None
            self._atualizar_estado(preservar_selecao=False)

    def refazer(self):
        if self.trajeto.refazer():
            self.indice_selecionado = len(self.trajeto.segmentos) - 1
            self._atualizar_estado()

    def limpar_tudo(self):
        if self.trajeto.limpar():
            self.indice_selecionado = None
            self._atualizar_estado(preservar_selecao=False)

    def novo_projeto(self):
        if self.trajeto.segmentos:
            if self.projeto_modificado:
                resposta = messagebox.askyesnocancel(
                    "Novo projeto", 
                    "Você possui alterações não salvas. Deseja salvar antes de começar um novo projeto?"
                )
                if resposta is True:
                    if not self.exportar_tfg():
                        return
                elif resposta is None:
                    return
            else:
                ok = messagebox.askyesno("Novo projeto", "Limpar o trajeto atual e começar um projeto novo?")
                if not ok:
                    return

        self.trajeto.substituir_segmentos([])
        self.trajeto.segmentos_desfeitos.clear()
        self.indice_selecionado = None
        self.var_limites_altura.set("0.5")  # Reset limites para valor padrão

        self._ignorar_callback_fundo = True
        try:
            self._fundo_imagem_bytes = None
            self._fundo_imagem_nome = None
            self._fundo_carregado_no_canvas = False
            self.var_fundo_tamanho_quadrado.set("1.0")
            self.var_fundo_escala_horizontal.set("1.0")
            self.var_fundo_escala_vertical.set("1.0")
            self.var_fundo_zoom.set("1.0")
            self.var_fundo_offset_x_m.set(0.0)
            self.var_fundo_offset_y_m.set(0.0)
            self.var_fundo_perspectiva_horizontal.set(0.0)
            self.var_fundo_perspectiva_vertical.set(0.0)
            self.var_fundo_canto_superior_esquerdo.set(0.0)
            self.var_fundo_canto_superior_direito.set(0.0)
            self.var_fundo_canto_inferior_direito.set(0.0)
            self.var_fundo_canto_inferior_esquerdo.set(0.0)
            self.var_fundo_rotacao_graus.set(0.0)
            self.var_fundo_tamanho_preview_percent.set(self.FUNDO_PREVIEW_BASE_PERCENT)
            self.var_fundo_opacidade.set(60.0)
            self.var_fundo_visivel.set(True)
        finally:
            self._ignorar_callback_fundo = False

        self._atualizar_label_opacidade_fundo()
        self._atualizar_status_imagem_fundo()
        self.canvas_view.limpar_imagem_fundo()

        self.canvas_view.centralizar_visao()
        self.resetar_origem_visual()
        self._atualizar_estado(preservar_selecao=False, modificado=False)
        self._marcar_como_salvo()

    def remover_selecao(self):
        if self.indice_selecionado is None:
            messagebox.showwarning("Nenhuma seleção", "Selecione um trecho na lista antes de remover.")
            return
        if self.trajeto.remover_segmento(self.indice_selecionado):
            if self.indice_selecionado >= len(self.trajeto.segmentos):
                self.indice_selecionado = len(self.trajeto.segmentos) - 1 if self.trajeto.segmentos else None
            self._atualizar_estado()

    def carregar_selecao(self):
        if self.indice_selecionado is None:
            messagebox.showwarning("Nenhuma seleção", "Selecione um trecho na lista primeiro.")
            return
        segmento = self.trajeto.obter_segmento(self.indice_selecionado)
        if isinstance(segmento, StraightSegment):
            self.var_reta_comprimento.set(str(segmento.comprimento))
            self.var_reta_angulo.set(str(segmento.angulo_graus))
        elif isinstance(segmento, CurveSegment):
            self.var_curva_raio.set(str(segmento.raio))
            self.var_curva_lado.set(segmento.lado)
            self.var_curva_angulo.set(str(segmento.angulo_central_graus))

    def _ao_selecionar_segmento(self, event=None):
        """Seleciona um segmento - nunca permite desselecionar"""
        selecao = self.listbox_segmentos.curselection()
        
        # Se não há seleção e há um indice anterior válido, reseleciona o anterior
        if not selecao:
            if self.indice_selecionado is not None and 0 <= self.indice_selecionado < len(self.trajeto.segmentos):
                # Reseleciona o anterior
                self.listbox_segmentos.selection_clear(0, tk.END)
                self.listbox_segmentos.selection_set(self.indice_selecionado)
                self.listbox_segmentos.see(self.indice_selecionado)
                self._redesenhar()
            return
        
        # Se há seleção, atualiza
        indice = selecao[0]
        if indice >= len(self.trajeto.segmentos):
            return
        
        self.indice_selecionado = indice
        segmento = self.trajeto.segmentos[indice]
        self.var_segmento_selecionado.set(f"Selecionado: #{indice + 1} ({segmento.tipo})")
        
        # Atualiza os controles de marcação com os valores da marcação correspondente
        if indice < len(self.trajeto.marcacoes):
            marcacao = self.trajeto.marcacoes[indice]
            self.var_marcacao_lado.set(marcacao.lado)
            self.var_marcacao_distancia.set(str(marcacao.distancia))
        
        # Carrega os dados do segmento automaticamente
        self.carregar_selecao()

    def centralizar_visao(self):
        self.canvas_view.centralizar_visao()

    def resetar_origem_visual(self):
        self.var_origem_x.set("0")
        self.var_origem_y.set("0")
        self.var_zoom.set(18.0)  # Resetar zoom para o padrão
        self._redesenhar()

    def ativar_selecionador_origem(self):
        """Ativa o modo de seleção de origem com clique"""
        self.canvas_view.ativar_modo_selecionando_origem()

    def desativar_selecionador_origem(self):
        """Desativa o modo de seleção de origem"""
        self.canvas_view.desativar_modo_selecionando_origem()

    def _ao_origem_clicada(self, x_mundo, y_mundo):
        """Callback chamado quando um ponto é clicado no modo de seleção de origem"""
        # Atualizar as variáveis de origem
        self.var_origem_x.set(f"{x_mundo:.4f}")
        self.var_origem_y.set(f"{y_mundo:.4f}")
        
        # Desativar o modo de seleção
        self.desativar_selecionador_origem()

    def _ao_mudar_limites_altura(self):
        """Callback quando a altura dos limites é alterada."""
        try:
            altura = float(self.var_limites_altura.get())
            self.trajeto.borda_deteccao.altura = altura
            self._atualizar_campo_limites_largura()
            self._redesenhar()
            self._marcar_como_modificado()
        except ValueError:
            pass

    def _atualizar_campo_limites_largura(self):
        """Atualiza o campo de largura com base na altura (largura = altura * 2)."""
        try:
            # Largura = altura * 2 (proporção fixa, sem precisar de unidade)
            altura_str = self.var_limites_altura.get()
            altura = float(altura_str) if altura_str else 0.5
            largura = altura * 2.0
            
            valor_formatado = f"{largura:.2f}"
            self.entry_limites_largura_display.config(state="normal")
            self.entry_limites_largura_display.delete(0, tk.END)
            self.entry_limites_largura_display.insert(0, valor_formatado)
            self.entry_limites_largura_display.config(state="readonly")
        except Exception as e:
            print(f"[ERROR] Erro ao atualizar campo limites largura: {e}")
            import traceback
            traceback.print_exc()

    def _atualizar_label_opacidade_fundo(self):
        try:
            opacidade = int(round(float(self.var_fundo_opacidade.get())))
        except (ValueError, TypeError):
            opacidade = 60
        opacidade = max(0, min(100, opacidade))
        self.var_fundo_label_opacidade.set(f"Opacidade: {opacidade}%")

    def _atualizar_status_imagem_fundo(self):
        if self._fundo_imagem_bytes:
            nome = self._fundo_imagem_nome or "imagem sem nome"
            self.var_fundo_status.set(f"Imagem carregada: {nome}")
        else:
            self.var_fundo_status.set("Nenhuma imagem de fundo carregada")

    def _capturar_estado_fundo(self):
        return {
            "imagem_bytes": self._fundo_imagem_bytes,
            "imagem_nome": self._fundo_imagem_nome,
            "carregado_no_canvas": self._fundo_carregado_no_canvas,
            "tamanho_quadrado": self.var_fundo_tamanho_quadrado.get(),
            "escala_horizontal": self.var_fundo_escala_horizontal.get(),
            "escala_vertical": self.var_fundo_escala_vertical.get(),
            "zoom": self.var_fundo_zoom.get(),
            "offset_x_m": self.var_fundo_offset_x_m.get(),
            "offset_y_m": self.var_fundo_offset_y_m.get(),
            "perspectiva_horizontal": self.var_fundo_perspectiva_horizontal.get(),
            "perspectiva_vertical": self.var_fundo_perspectiva_vertical.get(),
            "canto_superior_esquerdo": self.var_fundo_canto_superior_esquerdo.get(),
            "canto_superior_direito": self.var_fundo_canto_superior_direito.get(),
            "canto_inferior_direito": self.var_fundo_canto_inferior_direito.get(),
            "canto_inferior_esquerdo": self.var_fundo_canto_inferior_esquerdo.get(),
            "rotacao_graus": self.var_fundo_rotacao_graus.get(),
            "tamanho_preview_percent": self.var_fundo_tamanho_preview_percent.get(),
            "opacidade": self.var_fundo_opacidade.get(),
            "visivel": self.var_fundo_visivel.get(),
        }

    def _restaurar_estado_fundo(self, estado, redesenhar=True):
        self._ignorar_callback_fundo = True
        try:
            self._fundo_imagem_bytes = estado.get("imagem_bytes")
            self._fundo_imagem_nome = estado.get("imagem_nome")
            self._fundo_carregado_no_canvas = False
            self.var_fundo_tamanho_quadrado.set(str(estado.get("tamanho_quadrado", "1.0")))
            self.var_fundo_escala_horizontal.set(str(estado.get("escala_horizontal", "1.0")))
            self.var_fundo_escala_vertical.set(str(estado.get("escala_vertical", "1.0")))
            self.var_fundo_zoom.set(str(estado.get("zoom", "1.0")))
            self.var_fundo_offset_x_m.set(float(estado.get("offset_x_m", 0.0)))
            self.var_fundo_offset_y_m.set(float(estado.get("offset_y_m", 0.0)))
            self.var_fundo_perspectiva_horizontal.set(float(estado.get("perspectiva_horizontal", 0.0)))
            self.var_fundo_perspectiva_vertical.set(float(estado.get("perspectiva_vertical", 0.0)))
            self.var_fundo_canto_superior_esquerdo.set(float(estado.get("canto_superior_esquerdo", 0.0)))
            self.var_fundo_canto_superior_direito.set(float(estado.get("canto_superior_direito", 0.0)))
            self.var_fundo_canto_inferior_direito.set(float(estado.get("canto_inferior_direito", 0.0)))
            self.var_fundo_canto_inferior_esquerdo.set(float(estado.get("canto_inferior_esquerdo", 0.0)))
            self.var_fundo_rotacao_graus.set(float(estado.get("rotacao_graus", 0.0)))
            self.var_fundo_tamanho_preview_percent.set(float(estado.get("tamanho_preview_percent", self.FUNDO_PREVIEW_BASE_PERCENT)))
            self.var_fundo_opacidade.set(float(estado.get("opacidade", 60.0)))
            self.var_fundo_visivel.set(bool(estado.get("visivel", True)))
        finally:
            self._ignorar_callback_fundo = False

        self._atualizar_label_opacidade_fundo()
        self._atualizar_status_imagem_fundo()
        self._sincronizar_fundo_canvas(mostrar_erros=False, redesenhar=redesenhar)

    def _validar_configuracao_fundo(
        self,
        tamanho_quadrado,
        escala_horizontal,
        escala_vertical,
        zoom,
        opacidade,
        offset_x_m=0.0,
        offset_y_m=0.0,
        perspectiva_horizontal=0.0,
        perspectiva_vertical=0.0,
        canto_superior_esquerdo=0.0,
        canto_superior_direito=0.0,
        canto_inferior_direito=0.0,
        canto_inferior_esquerdo=0.0,
        rotacao_graus=0.0,
    ):
        try:
            tamanho_quadrado_m = float(tamanho_quadrado)
            escala_h = float(escala_horizontal)
            escala_v = float(escala_vertical)
            zoom_fundo = float(zoom)
            opacidade_percent = float(opacidade)
            deslocamento_x_m = float(offset_x_m)
            deslocamento_y_m = float(offset_y_m)
            perspectiva_h = float(perspectiva_horizontal)
            perspectiva_v = float(perspectiva_vertical)
            canto_sup_esq = float(canto_superior_esquerdo)
            canto_sup_dir = float(canto_superior_direito)
            canto_inf_dir = float(canto_inferior_direito)
            canto_inf_esq = float(canto_inferior_esquerdo)
            rotacao = float(rotacao_graus)
        except ValueError:
            raise ValueError("Valores numéricos inválidos na configuração da imagem de fundo.")

        if tamanho_quadrado_m <= 0:
            raise ValueError("O tamanho do quadrado N deve ser maior que zero.")
        if escala_h <= 0 or escala_v <= 0:
            raise ValueError("As escalas horizontal e vertical devem ser maiores que zero.")
        if zoom_fundo <= 0:
            raise ValueError("O zoom da imagem de fundo deve ser maior que zero.")

        limite_inclinacao = float(self.FUNDO_INCLINACAO_LIMITE)

        opacidade_percent = max(0.0, min(100.0, opacidade_percent))
        perspectiva_h = max(-limite_inclinacao, min(limite_inclinacao, perspectiva_h))
        perspectiva_v = max(-limite_inclinacao, min(limite_inclinacao, perspectiva_v))
        canto_sup_esq = max(-limite_inclinacao, min(limite_inclinacao, canto_sup_esq))
        canto_sup_dir = max(-limite_inclinacao, min(limite_inclinacao, canto_sup_dir))
        canto_inf_dir = max(-limite_inclinacao, min(limite_inclinacao, canto_inf_dir))
        canto_inf_esq = max(-limite_inclinacao, min(limite_inclinacao, canto_inf_esq))
        rotacao = max(-180.0, min(180.0, rotacao))
        return {
            "tamanho_quadrado_m": tamanho_quadrado_m,
            "escala_horizontal": escala_h,
            "escala_vertical": escala_v,
            "zoom": zoom_fundo,
            "opacidade_percent": opacidade_percent,
            "offset_x_m": deslocamento_x_m,
            "offset_y_m": deslocamento_y_m,
            "perspectiva_horizontal": perspectiva_h,
            "perspectiva_vertical": perspectiva_v,
            "canto_superior_esquerdo": canto_sup_esq,
            "canto_superior_direito": canto_sup_dir,
            "canto_inferior_direito": canto_inf_dir,
            "canto_inferior_esquerdo": canto_inf_esq,
            "rotacao_graus": rotacao,
        }

    @staticmethod
    def _converter_perspectiva_legada_para_cantos(perspectiva_horizontal, perspectiva_vertical):
        try:
            p_h = float(perspectiva_horizontal)
            p_v = float(perspectiva_vertical)
        except (ValueError, TypeError):
            p_h = 0.0
            p_v = 0.0

        limite_inclinacao = float(TrajectoryGeneratorApp.FUNDO_INCLINACAO_LIMITE)
        return {
            "canto_superior_esquerdo": max(-limite_inclinacao, min(limite_inclinacao, p_h - p_v)),
            "canto_superior_direito": max(-limite_inclinacao, min(limite_inclinacao, p_h + p_v)),
            "canto_inferior_direito": max(-limite_inclinacao, min(limite_inclinacao, -p_h + p_v)),
            "canto_inferior_esquerdo": max(-limite_inclinacao, min(limite_inclinacao, -p_h - p_v)),
        }

    def _calcular_fator_escala_real_por_quadrado(self, zoom_fundo, preview_percent):
        try:
            zoom = float(zoom_fundo)
        except (ValueError, TypeError):
            zoom = 1.0

        try:
            percentual = float(preview_percent)
        except (ValueError, TypeError):
            percentual = self.FUNDO_PREVIEW_BASE_PERCENT

        percentual = max(1.0, min(300.0, percentual))
        # Ex.: N = 1.0 m e quadrado em 10% representa 0.1 m no mundo real.
        return zoom * (percentual / 100.0)

    def _sincronizar_fundo_canvas(self, mostrar_erros=True, redesenhar=True):
        if not self._fundo_imagem_bytes:
            self.canvas_view.limpar_imagem_fundo()
            self._fundo_carregado_no_canvas = False
            if redesenhar:
                self._redesenhar()
            return True

        if not self.canvas_view.suporte_imagem_fundo_disponivel():
            if mostrar_erros:
                messagebox.showerror(
                    "Dependência ausente",
                    "Para usar imagem de fundo, instale o Pillow:\n\npip install pillow",
                )
            return False

        try:
            config = self._validar_configuracao_fundo(
                self.var_fundo_tamanho_quadrado.get(),
                self.var_fundo_escala_horizontal.get(),
                self.var_fundo_escala_vertical.get(),
                self.var_fundo_zoom.get(),
                self.var_fundo_opacidade.get(),
                self.var_fundo_offset_x_m.get(),
                self.var_fundo_offset_y_m.get(),
                self.var_fundo_perspectiva_horizontal.get(),
                self.var_fundo_perspectiva_vertical.get(),
                self.var_fundo_canto_superior_esquerdo.get(),
                self.var_fundo_canto_superior_direito.get(),
                self.var_fundo_canto_inferior_direito.get(),
                self.var_fundo_canto_inferior_esquerdo.get(),
                self.var_fundo_rotacao_graus.get(),
            )
        except ValueError as e:
            if mostrar_erros:
                messagebox.showerror("Configuração inválida", str(e))
            return False

        try:
            if not self._fundo_carregado_no_canvas:
                self.canvas_view.carregar_imagem_fundo_bytes(self._fundo_imagem_bytes)
                self._fundo_carregado_no_canvas = True

            fator_escala_real = self._calcular_fator_escala_real_por_quadrado(
                config["zoom"],
                self.var_fundo_tamanho_preview_percent.get(),
            )

            self.canvas_view.configurar_imagem_fundo(
                tamanho_quadrado_m=config["tamanho_quadrado_m"],
                escala_horizontal=config["escala_horizontal"] * fator_escala_real,
                escala_vertical=config["escala_vertical"] * fator_escala_real,
                zoom=1.0,
                opacidade_percent=config["opacidade_percent"],
                offset_x_m=config["offset_x_m"],
                offset_y_m=config["offset_y_m"],
                perspectiva_horizontal=config["perspectiva_horizontal"],
                perspectiva_vertical=config["perspectiva_vertical"],
                canto_superior_esquerdo=config["canto_superior_esquerdo"],
                canto_superior_direito=config["canto_superior_direito"],
                canto_inferior_direito=config["canto_inferior_direito"],
                canto_inferior_esquerdo=config["canto_inferior_esquerdo"],
                rotacao_graus=config["rotacao_graus"],
                visivel=self.var_fundo_visivel.get(),
            )
        except Exception as e:
            if mostrar_erros:
                messagebox.showerror("Imagem de fundo", f"Falha ao aplicar imagem de fundo:\n{e}")
            return False

        if redesenhar:
            self._redesenhar()
        return True

    def _obter_payload_fundo_exportacao(self):
        if not self._fundo_imagem_bytes:
            return None

        config = self._validar_configuracao_fundo(
            self.var_fundo_tamanho_quadrado.get(),
            self.var_fundo_escala_horizontal.get(),
            self.var_fundo_escala_vertical.get(),
            self.var_fundo_zoom.get(),
            self.var_fundo_opacidade.get(),
            self.var_fundo_offset_x_m.get(),
            self.var_fundo_offset_y_m.get(),
            self.var_fundo_perspectiva_horizontal.get(),
            self.var_fundo_perspectiva_vertical.get(),
            self.var_fundo_canto_superior_esquerdo.get(),
            self.var_fundo_canto_superior_direito.get(),
            self.var_fundo_canto_inferior_direito.get(),
            self.var_fundo_canto_inferior_esquerdo.get(),
            self.var_fundo_rotacao_graus.get(),
        )

        fator_escala_real = self._calcular_fator_escala_real_por_quadrado(
            config["zoom"],
            self.var_fundo_tamanho_preview_percent.get(),
        )

        return {
            "bytes": self._fundo_imagem_bytes,
            "filename": self._fundo_imagem_nome or "imagem_fundo.png",
            "config": {
                "reference_square_size_m": config["tamanho_quadrado_m"],
                "horizontal_scale": config["escala_horizontal"],
                "vertical_scale": config["escala_vertical"],
                "zoom": config["zoom"],
                "offset_x_m": config["offset_x_m"],
                "offset_y_m": config["offset_y_m"],
                "horizontal_perspective": config["perspectiva_horizontal"],
                "vertical_perspective": config["perspectiva_vertical"],
                "corner_top_left": config["canto_superior_esquerdo"],
                "corner_top_right": config["canto_superior_direito"],
                "corner_bottom_right": config["canto_inferior_direito"],
                "corner_bottom_left": config["canto_inferior_esquerdo"],
                "rotation_degrees": config["rotacao_graus"],
                "reference_square_preview_percent": float(self.var_fundo_tamanho_preview_percent.get()),
                "real_horizontal_scale": config["escala_horizontal"] * fator_escala_real,
                "real_vertical_scale": config["escala_vertical"] * fator_escala_real,
                "opacity_percent": config["opacidade_percent"],
                "visible": bool(self.var_fundo_visivel.get()),
            },
        }

    def carregar_imagem_fundo(self):
        if not self.canvas_view.suporte_imagem_fundo_disponivel():
            messagebox.showerror(
                "Dependência ausente",
                "Para usar imagem de fundo, instale o Pillow:\n\npip install pillow",
            )
            return

        caminho = filedialog.askopenfilename(
            title="Selecionar imagem de fundo",
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not caminho:
            return

        try:
            with open(caminho, "rb") as f:
                image_bytes = f.read()
        except OSError as e:
            messagebox.showerror("Erro ao abrir imagem", str(e))
            return

        self.abrir_janela_ajuste_imagem_fundo(
            image_bytes=image_bytes,
            image_name=os.path.basename(caminho),
        )

    def abrir_janela_ajuste_imagem_fundo(self, image_bytes=None, image_name=None):
        if not self.canvas_view.suporte_imagem_fundo_disponivel() or Image is None or ImageTk is None:
            messagebox.showerror(
                "Dependência ausente",
                "Para usar imagem de fundo, instale o Pillow:\n\npip install pillow",
            )
            return

        if image_bytes is None and not self._fundo_imagem_bytes:
            messagebox.showwarning("Imagem de fundo", "Carregue uma imagem antes de ajustar.")
            return

        estado_anterior = self._capturar_estado_fundo()

        if image_bytes is not None:
            self._fundo_imagem_bytes = image_bytes
            self._fundo_imagem_nome = image_name or "imagem_fundo.png"
            self._fundo_carregado_no_canvas = False
            self._ignorar_callback_fundo = True
            self.var_fundo_visivel.set(True)
            self._ignorar_callback_fundo = False
            self._atualizar_status_imagem_fundo()

        try:
            imagem_base = Image.open(BytesIO(self._fundo_imagem_bytes)).convert("RGBA")
            resample_preview = Image.Resampling.BILINEAR if hasattr(Image, "Resampling") else Image.BILINEAR
            imagem_base_preview = imagem_base.copy()
            imagem_base_preview.thumbnail((1800, 1800), resample=resample_preview)
        except Exception as e:
            messagebox.showerror("Imagem inválida", f"Não foi possível abrir a imagem:\n{e}")
            self._restaurar_estado_fundo(estado_anterior, redesenhar=True)
            return

        janela = tk.Toplevel(self.root)
        janela.title("Ajuste de Perspectiva da Imagem")
        janela.grab_set()
        janela.geometry("1180x820")
        janela.minsize(760, 520)
        janela.resizable(True, True)
        janela.rowconfigure(0, weight=1)
        janela.columnconfigure(0, weight=1)

        frame = ttk.Frame(janela, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text=(
                "Use os quatro controles de canto para deformar a imagem e alinhar ao quadrado N x N. "
                "Use rotação para girar a imagem e arraste com o mouse para reposicionar."
            ),
            justify="left",
            wraplength=1120,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        var_local_tamanho = tk.StringVar(value=self.var_fundo_tamanho_quadrado.get())
        var_local_escala_h = tk.StringVar(value=self.var_fundo_escala_horizontal.get())
        var_local_escala_v = tk.StringVar(value=self.var_fundo_escala_vertical.get())
        zoom_minimo = 0.0001
        zoom_maximo = 1000.0
        limite_inclinacao = float(self.FUNDO_INCLINACAO_LIMITE)

        try:
            zoom_inicial = float(self.var_fundo_zoom.get())
        except (ValueError, TypeError):
            zoom_inicial = 1.0

        var_local_zoom = tk.DoubleVar(value=max(zoom_minimo, min(zoom_maximo, zoom_inicial)))
        var_local_offset_x_m = tk.DoubleVar(value=self.var_fundo_offset_x_m.get())
        var_local_offset_y_m = tk.DoubleVar(value=self.var_fundo_offset_y_m.get())
        var_local_canto_sup_esq = tk.DoubleVar(value=self.var_fundo_canto_superior_esquerdo.get())
        var_local_canto_sup_dir = tk.DoubleVar(value=self.var_fundo_canto_superior_direito.get())
        var_local_canto_inf_dir = tk.DoubleVar(value=self.var_fundo_canto_inferior_direito.get())
        var_local_canto_inf_esq = tk.DoubleVar(value=self.var_fundo_canto_inferior_esquerdo.get())
        var_local_rotacao = tk.DoubleVar(value=self.var_fundo_rotacao_graus.get())
        var_local_tamanho_preview_percent = tk.DoubleVar(value=self.var_fundo_tamanho_preview_percent.get())
        var_local_opacidade = tk.DoubleVar(value=self.var_fundo_opacidade.get())
        var_local_visivel = tk.BooleanVar(value=self.var_fundo_visivel.get())

        var_local_label_opacidade = tk.StringVar()
        var_local_label_posicao = tk.StringVar(value="Posição: x=0.0000 m | y=0.0000 m")
        var_feedback = tk.StringVar(value="")
        preview_ref = {
            "photo": None,
            "base_img": None,
            "base_key": None,
            "render_key": None,
            "after_id": None,
        }
        drag_estado = {"ativo": False, "ultimo_x": 0.0, "ultimo_y": 0.0, "lado_ref": 1.0}
        atalho_estado = {
            "g_pressionado": False,
            "q_pressionado": False,
            "w_pressionado": False,
            "a_pressionado": False,
            "s_pressionado": False,
            "tela_cheia": False,
        }
        conteudo_principal = ttk.Frame(frame)
        conteudo_principal.grid(row=1, column=0, sticky="nsew")
        conteudo_principal.rowconfigure(0, weight=1)
        conteudo_principal.columnconfigure(0, weight=1, minsize=260, uniform="fundo_ajuste")
        conteudo_principal.columnconfigure(1, weight=3, uniform="fundo_ajuste")

        painel_controles = ttk.Frame(conteudo_principal, padding=(0, 0, 12, 0))
        painel_controles.grid(row=0, column=0, sticky="nsew")

        painel_preview = ttk.Frame(conteudo_principal)
        painel_preview.grid(row=0, column=1, sticky="nsew")
        painel_preview.rowconfigure(1, weight=1)
        painel_preview.columnconfigure(0, weight=1)

        ttk.Label(
            painel_preview,
            text="Pré-visualização completa. Arraste com o mouse para reposicionar.",
            foreground="#444444",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        preview_canvas = tk.Canvas(
            painel_preview,
            bg="#f2f2f2",
            highlightthickness=1,
            highlightbackground="#bfbfbf",
        )
        preview_canvas.grid(row=1, column=0, sticky="nsew")

        def atualizar_label_opacidade_local():
            try:
                valor = int(round(float(var_local_opacidade.get())))
            except (ValueError, TypeError):
                valor = 60
            valor = max(0, min(100, valor))
            var_local_label_opacidade.set(f"Opacidade: {valor}%")

        def _arredondar_4(valor):
            try:
                numero = float(valor)
            except (ValueError, TypeError):
                numero = 0.0
            numero = round(numero, 4)
            if abs(numero) < 0.00005:
                numero = 0.0
            return numero

        def _aplicar_valor_slider_4casas(var_alvo, valor, minimo=None, maximo=None):
            numero = _arredondar_4(valor)
            if minimo is not None:
                numero = max(float(minimo), numero)
            if maximo is not None:
                numero = min(float(maximo), numero)
            var_alvo.set(_arredondar_4(numero))

        frame_valores = ttk.LabelFrame(painel_controles, text="Medidas", padding=8)
        frame_valores.pack(fill="x", pady=(0, 8))
        frame_valores.columnconfigure(1, weight=1)
        ttk.Label(frame_valores, text="N (m)").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame_valores, textvariable=var_local_tamanho, width=10).grid(row=0, column=1, sticky="ew", padx=(8, 0))

        frame_ajustes = ttk.LabelFrame(painel_controles, text="Ajustes principais", padding=8)
        frame_ajustes.pack(fill="x", pady=(0, 8))
        frame_ajustes.columnconfigure(1, weight=1)
        ttk.Label(frame_ajustes, text="Zoom").grid(row=0, column=0, sticky="w")
        ttk.Scale(
            frame_ajustes,
            from_=zoom_minimo,
            to=zoom_maximo,
            variable=var_local_zoom,
            command=lambda _v: _aplicar_valor_slider_4casas(var_local_zoom, _v, zoom_minimo, zoom_maximo),
        ).grid(row=0, column=1, sticky="ew", padx=(8, 6))
        ttk.Entry(frame_ajustes, textvariable=var_local_zoom, width=11).grid(row=0, column=2, sticky="e")
        ttk.Label(frame_ajustes, text="Rotação (graus)").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(
            frame_ajustes,
            from_=-180.0,
            to=180.0,
            variable=var_local_rotacao,
            command=lambda _v: _aplicar_valor_slider_4casas(var_local_rotacao, _v, -180.0, 180.0),
        ).grid(row=1, column=1, sticky="ew", padx=(8, 6), pady=(6, 0))
        ttk.Entry(frame_ajustes, textvariable=var_local_rotacao, width=11).grid(row=1, column=2, sticky="e", pady=(6, 0))
        ttk.Label(frame_ajustes, text="Quadrado ref. (%)").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(
            frame_ajustes,
            from_=1.0,
            to=300.0,
            variable=var_local_tamanho_preview_percent,
            command=lambda _v: _aplicar_valor_slider_4casas(var_local_tamanho_preview_percent, _v, 1.0, 300.0),
        ).grid(row=2, column=1, sticky="ew", padx=(8, 6), pady=(6, 0))
        ttk.Entry(frame_ajustes, textvariable=var_local_tamanho_preview_percent, width=11).grid(row=2, column=2, sticky="e", pady=(6, 0))

        frame_cantos = ttk.LabelFrame(painel_controles, text="Perspectiva por canto", padding=8)
        frame_cantos.pack(fill="x", pady=(0, 8))
        frame_cantos.columnconfigure(1, weight=1)
        ttk.Label(frame_cantos, text="Superior esquerdo").grid(row=0, column=0, sticky="w")
        ttk.Scale(
            frame_cantos,
            from_=-limite_inclinacao,
            to=limite_inclinacao,
            variable=var_local_canto_sup_esq,
            orient="horizontal",
            command=lambda _v: _aplicar_valor_slider_4casas(var_local_canto_sup_esq, _v, -limite_inclinacao, limite_inclinacao),
        ).grid(row=0, column=1, sticky="ew", padx=(8, 6))
        ttk.Entry(frame_cantos, textvariable=var_local_canto_sup_esq, width=11).grid(row=0, column=2, sticky="e")
        ttk.Label(frame_cantos, text="Superior direito").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(
            frame_cantos,
            from_=-limite_inclinacao,
            to=limite_inclinacao,
            variable=var_local_canto_sup_dir,
            orient="horizontal",
            command=lambda _v: _aplicar_valor_slider_4casas(var_local_canto_sup_dir, _v, -limite_inclinacao, limite_inclinacao),
        ).grid(row=1, column=1, sticky="ew", padx=(8, 6), pady=(6, 0))
        ttk.Entry(frame_cantos, textvariable=var_local_canto_sup_dir, width=11).grid(row=1, column=2, sticky="e", pady=(6, 0))
        ttk.Label(frame_cantos, text="Inferior esquerdo").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(
            frame_cantos,
            from_=-limite_inclinacao,
            to=limite_inclinacao,
            variable=var_local_canto_inf_esq,
            orient="horizontal",
            command=lambda _v: _aplicar_valor_slider_4casas(var_local_canto_inf_esq, _v, -limite_inclinacao, limite_inclinacao),
        ).grid(row=2, column=1, sticky="ew", padx=(8, 6), pady=(6, 0))
        ttk.Entry(frame_cantos, textvariable=var_local_canto_inf_esq, width=11).grid(row=2, column=2, sticky="e", pady=(6, 0))
        ttk.Label(frame_cantos, text="Inferior direito").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(
            frame_cantos,
            from_=-limite_inclinacao,
            to=limite_inclinacao,
            variable=var_local_canto_inf_dir,
            orient="horizontal",
            command=lambda _v: _aplicar_valor_slider_4casas(var_local_canto_inf_dir, _v, -limite_inclinacao, limite_inclinacao),
        ).grid(row=3, column=1, sticky="ew", padx=(8, 6), pady=(6, 0))
        ttk.Entry(frame_cantos, textvariable=var_local_canto_inf_dir, width=11).grid(row=3, column=2, sticky="e", pady=(6, 0))

        frame_opcoes = ttk.LabelFrame(painel_controles, text="Visibilidade e posição", padding=8)
        frame_opcoes.pack(fill="x")
        frame_opcoes.columnconfigure(1, weight=1)
        ttk.Checkbutton(
            frame_opcoes,
            text="Mostrar imagem",
            variable=var_local_visivel,
            command=lambda: agendar_previsualizacao(),
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame_opcoes, textvariable=var_local_label_opacidade).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(
            frame_opcoes,
            from_=0.0,
            to=100.0,
            variable=var_local_opacidade,
            command=lambda _v: _aplicar_valor_slider_4casas(var_local_opacidade, _v, 0.0, 100.0),
        ).grid(row=1, column=1, sticky="ew", padx=(8, 6), pady=(6, 0))
        ttk.Entry(frame_opcoes, textvariable=var_local_opacidade, width=11).grid(row=1, column=2, sticky="e", pady=(6, 0))
        ttk.Label(frame_opcoes, textvariable=var_local_label_posicao).grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Label(
            frame_opcoes,
            text=(
                "Atalhos: Ctrl +/− (zoom), segure G +/− (girar), "
                "segure Q/W/A/S +/− (cantos), setas (mover). "
                "Modificadores: Ctrl=fino, Alt=grosso"
            ),
            foreground="#444444",
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(6, 0))

        ttk.Label(painel_controles, textvariable=var_feedback, foreground="#444444", wraplength=340, justify="left").pack(fill="x", pady=(8, 0))

        botoes = ttk.Frame(painel_controles)
        botoes.pack(fill="x", pady=(8, 0))
        ttk.Button(botoes, text="Resetar", command=lambda: resetar_ajustes()).pack(side="left", padx=(0, 6))
        ttk.Button(botoes, text="Tela cheia", command=lambda: alternar_tela_cheia()).pack(side="left", padx=(0, 12))
        ttk.Button(botoes, text="Cancelar", command=lambda: cancelar()).pack(side="right", padx=(6, 0))
        ttk.Button(botoes, text="OK", command=lambda: confirmar()).pack(side="right")

        def cancelar_previsualizacao_pendente():
            after_id = preview_ref.get("after_id")
            if after_id is None:
                return
            try:
                janela.after_cancel(after_id)
            except tk.TclError:
                pass
            preview_ref["after_id"] = None

        def limitar_tamanho_preview(largura_img, altura_img):
            largura = max(1, int(largura_img))
            altura = max(1, int(altura_img))
            return largura, altura, 1.0

        def obter_preview_photo(config, largura_img, altura_img):
            base_key = (
                round(config["opacidade_percent"], 2),
                id(imagem_base_preview),
            )

            if preview_ref["base_key"] != base_key or preview_ref["base_img"] is None:
                imagem_processada = imagem_base_preview.copy()
                if config["opacidade_percent"] < 100.0:
                    fator_alpha = config["opacidade_percent"] / 100.0
                    canal_alpha = imagem_processada.getchannel("A")
                    canal_alpha = canal_alpha.point(lambda p, f=fator_alpha: int(p * f))
                    imagem_processada.putalpha(canal_alpha)
                preview_ref["base_img"] = imagem_processada
                preview_ref["base_key"] = base_key
                preview_ref["render_key"] = None
                preview_ref["photo"] = None

            render_key = (
                largura_img,
                altura_img,
                round(config["canto_superior_esquerdo"], 4),
                round(config["canto_superior_direito"], 4),
                round(config["canto_inferior_direito"], 4),
                round(config["canto_inferior_esquerdo"], 4),
                round(config["rotacao_graus"], 4),
                preview_ref["base_key"],
            )
            if preview_ref["render_key"] != render_key or preview_ref["photo"] is None:
                resample = Image.Resampling.BILINEAR if hasattr(Image, "Resampling") else Image.BILINEAR
                imagem_preview = preview_ref["base_img"].resize((largura_img, altura_img), resample=resample)
                imagem_preview = CanvasTrajectoryView.aplicar_transformacao_em_imagem(
                    imagem_preview,
                    canto_superior_esquerdo=config["canto_superior_esquerdo"],
                    canto_superior_direito=config["canto_superior_direito"],
                    canto_inferior_direito=config["canto_inferior_direito"],
                    canto_inferior_esquerdo=config["canto_inferior_esquerdo"],
                    rotacao_graus=config["rotacao_graus"],
                )
                preview_ref["photo"] = ImageTk.PhotoImage(imagem_preview)
                preview_ref["render_key"] = render_key

            return preview_ref["photo"]

        def desenhar_preview(config):
            preview_canvas.delete("all")
            largura_canvas = max(preview_canvas.winfo_width(), 10)
            altura_canvas = max(preview_canvas.winfo_height(), 10)

            centro_x = largura_canvas / 2.0
            centro_y = altura_canvas / 2.0
            base_referencia = float(max(10, min(largura_canvas, altura_canvas)))

            try:
                percentual = float(var_local_tamanho_preview_percent.get()) / 100.0
            except (ValueError, TypeError):
                percentual = self.FUNDO_PREVIEW_BASE_PERCENT / 100.0
            percentual = max(0.01, min(3.0, percentual))
            lado_referencia = max(4, int(base_referencia * percentual))
            drag_estado["lado_ref"] = float(lado_referencia)

            var_local_label_posicao.set(
                f"Posição: x={config['offset_x_m']:.4f} m | y={config['offset_y_m']:.4f} m"
            )

            offset_px_x = config["offset_x_m"] * (lado_referencia / max(config["tamanho_quadrado_m"], 1e-6))
            offset_px_y = -config["offset_y_m"] * (lado_referencia / max(config["tamanho_quadrado_m"], 1e-6))

            if var_local_visivel.get():
                largura_base = max(1, int(imagem_base_preview.width))
                altura_base = max(1, int(imagem_base_preview.height))
                maior_lado_base = float(max(largura_base, altura_base))
                fator_aspecto_largura = largura_base / maior_lado_base
                fator_aspecto_altura = altura_base / maior_lado_base

                largura_img_real = max(
                    1,
                    int(
                        round(
                            lado_referencia
                            * config["escala_horizontal"]
                            * config["zoom"]
                            * fator_aspecto_largura
                        )
                    ),
                )
                altura_img_real = max(
                    1,
                    int(
                        round(
                            lado_referencia
                            * config["escala_vertical"]
                            * config["zoom"]
                            * fator_aspecto_altura
                        )
                    ),
                )
                largura_img, altura_img, fator = limitar_tamanho_preview(largura_img_real, altura_img_real)

                imagem_preview_photo = obter_preview_photo(config, largura_img, altura_img)
                preview_canvas.create_image(
                    centro_x + offset_px_x,
                    centro_y + offset_px_y,
                    image=imagem_preview_photo,
                    anchor="center",
                )
            else:
                fator = 1.0

            meio = lado_referencia / 2
            preview_canvas.create_rectangle(
                centro_x - meio,
                centro_y - meio,
                centro_x + meio,
                centro_y + meio,
                outline="#00AA00",
                width=2,
                dash=(8, 5),
            )
            preview_canvas.create_text(
                centro_x,
                max(10.0, centro_y - meio - 14),
                text="Quadrado de referência N x N",
                fill="#007700",
                font=("Arial", 9, "bold"),
            )

            return fator

        def agendar_previsualizacao(_event=None):
            cancelar_previsualizacao_pendente()
            preview_ref["after_id"] = janela.after(25, previsualizar)

        def previsualizar(_event=None):
            preview_ref["after_id"] = None
            atualizar_label_opacidade_local()
            try:
                config = self._validar_configuracao_fundo(
                    tamanho_quadrado=var_local_tamanho.get(),
                    escala_horizontal=var_local_escala_h.get(),
                    escala_vertical=var_local_escala_v.get(),
                    zoom=var_local_zoom.get(),
                    opacidade=var_local_opacidade.get(),
                    offset_x_m=var_local_offset_x_m.get(),
                    offset_y_m=var_local_offset_y_m.get(),
                    perspectiva_horizontal=0.0,
                    perspectiva_vertical=0.0,
                    canto_superior_esquerdo=var_local_canto_sup_esq.get(),
                    canto_superior_direito=var_local_canto_sup_dir.get(),
                    canto_inferior_direito=var_local_canto_inf_dir.get(),
                    canto_inferior_esquerdo=var_local_canto_inf_esq.get(),
                    rotacao_graus=var_local_rotacao.get(),
                )
                fator = desenhar_preview(config)
                fator_escala_real = self._calcular_fator_escala_real_por_quadrado(
                    config["zoom"],
                    var_local_tamanho_preview_percent.get(),
                )
                if fator < 1.0:
                    var_feedback.set(
                        f"Pré-visualização otimizada para zoom alto (qualidade reduzida). "
                        f"Escala real: x{fator_escala_real:.4f}"
                    )
                else:
                    var_feedback.set(f"Ajuste aplicado. Escala real: x{fator_escala_real:.4f}")
            except Exception as e:
                var_feedback.set(f"Ajuste inválido: {e}")

        def confirmar():
            try:
                self._validar_configuracao_fundo(
                    tamanho_quadrado=var_local_tamanho.get(),
                    escala_horizontal=var_local_escala_h.get(),
                    escala_vertical=var_local_escala_v.get(),
                    zoom=var_local_zoom.get(),
                    opacidade=var_local_opacidade.get(),
                    offset_x_m=var_local_offset_x_m.get(),
                    offset_y_m=var_local_offset_y_m.get(),
                    perspectiva_horizontal=0.0,
                    perspectiva_vertical=0.0,
                    canto_superior_esquerdo=var_local_canto_sup_esq.get(),
                    canto_superior_direito=var_local_canto_sup_dir.get(),
                    canto_inferior_direito=var_local_canto_inf_dir.get(),
                    canto_inferior_esquerdo=var_local_canto_inf_esq.get(),
                    rotacao_graus=var_local_rotacao.get(),
                )
            except ValueError as e:
                messagebox.showerror("Configuração inválida", str(e), parent=janela)
                return

            cancelar_previsualizacao_pendente()

            self._ignorar_callback_fundo = True
            try:
                self.var_fundo_tamanho_quadrado.set(var_local_tamanho.get())
                self.var_fundo_escala_horizontal.set(var_local_escala_h.get())
                self.var_fundo_escala_vertical.set(var_local_escala_v.get())
                self.var_fundo_zoom.set(var_local_zoom.get())
                self.var_fundo_offset_x_m.set(var_local_offset_x_m.get())
                self.var_fundo_offset_y_m.set(var_local_offset_y_m.get())
                self.var_fundo_perspectiva_horizontal.set(0.0)
                self.var_fundo_perspectiva_vertical.set(0.0)
                self.var_fundo_canto_superior_esquerdo.set(var_local_canto_sup_esq.get())
                self.var_fundo_canto_superior_direito.set(var_local_canto_sup_dir.get())
                self.var_fundo_canto_inferior_direito.set(var_local_canto_inf_dir.get())
                self.var_fundo_canto_inferior_esquerdo.set(var_local_canto_inf_esq.get())
                self.var_fundo_rotacao_graus.set(var_local_rotacao.get())
                self.var_fundo_tamanho_preview_percent.set(var_local_tamanho_preview_percent.get())
                self.var_fundo_opacidade.set(var_local_opacidade.get())
                self.var_fundo_visivel.set(var_local_visivel.get())
            finally:
                self._ignorar_callback_fundo = False

            self._atualizar_label_opacidade_fundo()
            self._atualizar_status_imagem_fundo()
            if self._sincronizar_fundo_canvas(mostrar_erros=True, redesenhar=True):
                self._marcar_como_modificado()
                janela.destroy()

        def cancelar():
            cancelar_previsualizacao_pendente()
            self._restaurar_estado_fundo(estado_anterior, redesenhar=True)
            janela.destroy()

        def resetar_ajustes():
            var_local_tamanho.set("1.0")
            var_local_escala_h.set("1.0")
            var_local_escala_v.set("1.0")
            var_local_zoom.set(1.0)
            var_local_offset_x_m.set(0.0)
            var_local_offset_y_m.set(0.0)
            var_local_canto_sup_esq.set(0.0)
            var_local_canto_sup_dir.set(0.0)
            var_local_canto_inf_dir.set(0.0)
            var_local_canto_inf_esq.set(0.0)
            var_local_rotacao.set(0.0)
            var_local_tamanho_preview_percent.set(self.FUNDO_PREVIEW_BASE_PERCENT)
            var_local_opacidade.set(60.0)
            var_local_visivel.set(True)
            var_feedback.set("Ajustes resetados para o padrão.")
            agendar_previsualizacao()

        def alternar_tela_cheia(_event=None):
            novo_estado = not atalho_estado["tela_cheia"]
            atalho_estado["tela_cheia"] = novo_estado
            try:
                janela.attributes("-fullscreen", novo_estado)
            except tk.TclError:
                janela.state("zoomed" if novo_estado else "normal")
            return "break"

        MOD_SHIFT = 0x0001
        MOD_CTRL = 0x0004
        MOD_ALT = 0x0008

        def _obter_estado_teclas(event=None):
            try:
                return int(getattr(event, "state", 0) or 0)
            except (TypeError, ValueError):
                return 0

        def _obter_modo_ajuste(event=None):
            estado = _obter_estado_teclas(event)
            if estado & MOD_ALT:
                return "grosso"
            if estado & MOD_CTRL:
                return "fino"
            return "normal"

        def _atalho_escape_desfocar(_event=None):
            widget_foco = janela.focus_get()
            if widget_foco is not None:
                try:
                    classe_widget = widget_foco.winfo_class()
                except tk.TclError:
                    classe_widget = ""

                if classe_widget in {"Entry", "TEntry"}:
                    try:
                        widget_foco.selection_clear()
                    except tk.TclError:
                        pass
                    try:
                        widget_foco.icursor(tk.END)
                    except tk.TclError:
                        pass

            preview_canvas.focus_set()
            return "break"

        vars_4casas_limites = {
            str(var_local_zoom): (var_local_zoom, zoom_minimo, zoom_maximo),
            str(var_local_rotacao): (var_local_rotacao, -180.0, 180.0),
            str(var_local_tamanho_preview_percent): (var_local_tamanho_preview_percent, 1.0, 300.0),
            str(var_local_canto_sup_esq): (var_local_canto_sup_esq, -limite_inclinacao, limite_inclinacao),
            str(var_local_canto_sup_dir): (var_local_canto_sup_dir, -limite_inclinacao, limite_inclinacao),
            str(var_local_canto_inf_esq): (var_local_canto_inf_esq, -limite_inclinacao, limite_inclinacao),
            str(var_local_canto_inf_dir): (var_local_canto_inf_dir, -limite_inclinacao, limite_inclinacao),
            str(var_local_opacidade): (var_local_opacidade, 0.0, 100.0),
        }

        def _normalizar_entry_4casas(event=None):
            if event is None:
                return None

            widget = getattr(event, "widget", None)
            if widget is None:
                return None

            nome_var = widget.cget("textvariable")
            if not nome_var:
                return None

            info_var = vars_4casas_limites.get(str(nome_var))
            if info_var is None:
                return None

            var_alvo, minimo, maximo = info_var
            try:
                valor_atual = float(var_alvo.get())
            except (ValueError, TypeError, tk.TclError):
                valor_atual = float(minimo)

            valor_atual = _arredondar_4(max(minimo, min(maximo, valor_atual)))
            var_alvo.set(valor_atual)
            return None

        def _aplicar_zoom_atalho(direcao, event=None):
            try:
                atual = float(var_local_zoom.get())
            except (ValueError, TypeError):
                atual = 1.0

            modo = _obter_modo_ajuste(event)
            if modo == "fino":
                fator_zoom = 1.02
            elif modo == "grosso":
                fator_zoom = 1.25
            else:
                fator_zoom = 1.1

            if direcao > 0:
                novo = atual * fator_zoom
            else:
                novo = atual / fator_zoom

            var_local_zoom.set(_arredondar_4(max(zoom_minimo, min(zoom_maximo, novo))))
            agendar_previsualizacao()

        def _aplicar_rotacao_atalho(direcao, event=None):
            try:
                atual = float(var_local_rotacao.get())
            except (ValueError, TypeError):
                atual = 0.0

            modo = _obter_modo_ajuste(event)
            if modo == "fino":
                passo = 0.1
            elif modo == "grosso":
                passo = 5.0
            else:
                passo = 1.0

            novo = atual + (passo * direcao)
            var_local_rotacao.set(_arredondar_4(max(-180.0, min(180.0, novo))))
            agendar_previsualizacao()

        def _aplicar_canto_atalho(canto, direcao, event=None):
            modo = _obter_modo_ajuste(event)
            if modo == "fino":
                passo_base = 0.001
            elif modo == "grosso":
                passo_base = 0.05
            else:
                passo_base = 0.01

            passo = passo_base * direcao
            if canto == "q":
                atual = float(var_local_canto_sup_esq.get())
                var_local_canto_sup_esq.set(_arredondar_4(max(-limite_inclinacao, min(limite_inclinacao, atual + passo))))
            elif canto == "w":
                atual = float(var_local_canto_sup_dir.get())
                var_local_canto_sup_dir.set(_arredondar_4(max(-limite_inclinacao, min(limite_inclinacao, atual + passo))))
            elif canto == "a":
                atual = float(var_local_canto_inf_esq.get())
                var_local_canto_inf_esq.set(_arredondar_4(max(-limite_inclinacao, min(limite_inclinacao, atual + passo))))
            elif canto == "s":
                atual = float(var_local_canto_inf_dir.get())
                var_local_canto_inf_dir.set(_arredondar_4(max(-limite_inclinacao, min(limite_inclinacao, atual + passo))))
            agendar_previsualizacao()

        def _obter_canto_ativo():
            if atalho_estado["q_pressionado"]:
                return "q"
            if atalho_estado["w_pressionado"]:
                return "w"
            if atalho_estado["a_pressionado"]:
                return "a"
            if atalho_estado["s_pressionado"]:
                return "s"
            return None

        def _atalho_zoom_mais(event=None):
            if atalho_estado["g_pressionado"] or (_obter_canto_ativo() is not None):
                return _atalho_rotacao_mais(event)
            _aplicar_zoom_atalho(+1, event=event)
            return "break"

        def _atalho_zoom_menos(event=None):
            if atalho_estado["g_pressionado"] or (_obter_canto_ativo() is not None):
                return _atalho_rotacao_menos(event)
            _aplicar_zoom_atalho(-1, event=event)
            return "break"

        def _atalho_rotacao_mais(event=None):
            canto_ativo = _obter_canto_ativo()
            if atalho_estado["g_pressionado"]:
                _aplicar_rotacao_atalho(+1, event=event)
                return "break"
            if canto_ativo:
                _aplicar_canto_atalho(canto_ativo, +1, event=event)
                return "break"
            return None

        def _atalho_rotacao_menos(event=None):
            canto_ativo = _obter_canto_ativo()
            if atalho_estado["g_pressionado"]:
                _aplicar_rotacao_atalho(-1, event=event)
                return "break"
            if canto_ativo:
                _aplicar_canto_atalho(canto_ativo, -1, event=event)
                return "break"
            return None

        def _tecla_q_press(_event=None):
            atalho_estado["q_pressionado"] = True
            return "break"

        def _tecla_q_release(_event=None):
            atalho_estado["q_pressionado"] = False
            return None

        def _tecla_w_press(_event=None):
            atalho_estado["w_pressionado"] = True
            return "break"

        def _tecla_w_release(_event=None):
            atalho_estado["w_pressionado"] = False
            return None

        def _tecla_a_press(_event=None):
            atalho_estado["a_pressionado"] = True
            return "break"

        def _tecla_a_release(_event=None):
            atalho_estado["a_pressionado"] = False
            return None

        def _tecla_s_press(_event=None):
            atalho_estado["s_pressionado"] = True
            return "break"

        def _tecla_s_release(_event=None):
            atalho_estado["s_pressionado"] = False
            return None

        def _tecla_g_press(_event=None):
            atalho_estado["g_pressionado"] = True
            return "break"

        def _tecla_g_release(_event=None):
            atalho_estado["g_pressionado"] = False
            return None

        def _obter_passo_deslocamento_atalho(rapido=False, event=None):
            try:
                tamanho_n = float(var_local_tamanho.get())
            except (ValueError, TypeError):
                tamanho_n = 1.0

            passo = max(0.001, abs(tamanho_n) * 0.02)
            modo = _obter_modo_ajuste(event)
            if modo == "fino":
                passo *= 0.2
            elif modo == "grosso":
                passo *= 5.0
            if rapido:
                passo *= 5.0
            return passo

        def _aplicar_deslocamento_atalho(direcao_x, direcao_y, rapido=False, event=None):
            passo = _obter_passo_deslocamento_atalho(rapido=rapido, event=event)
            var_local_offset_x_m.set(var_local_offset_x_m.get() + (direcao_x * passo))
            var_local_offset_y_m.set(var_local_offset_y_m.get() + (direcao_y * passo))
            agendar_previsualizacao()

        def _atalho_seta_esquerda(event=None):
            rapido = bool(_obter_estado_teclas(event) & MOD_SHIFT)
            _aplicar_deslocamento_atalho(-1.0, 0.0, rapido=rapido, event=event)
            return "break"

        def _atalho_seta_direita(event=None):
            rapido = bool(_obter_estado_teclas(event) & MOD_SHIFT)
            _aplicar_deslocamento_atalho(+1.0, 0.0, rapido=rapido, event=event)
            return "break"

        def _atalho_seta_cima(event=None):
            rapido = bool(_obter_estado_teclas(event) & MOD_SHIFT)
            _aplicar_deslocamento_atalho(0.0, +1.0, rapido=rapido, event=event)
            return "break"

        def _atalho_seta_baixo(event=None):
            rapido = bool(_obter_estado_teclas(event) & MOD_SHIFT)
            _aplicar_deslocamento_atalho(0.0, -1.0, rapido=rapido, event=event)
            return "break"

        def _deve_capturar_atalho_mais_menos(event=None):
            estado = _obter_estado_teclas(event)
            if estado & MOD_CTRL:
                return True
            return atalho_estado["g_pressionado"] or (_obter_canto_ativo() is not None)

        def _atalho_mais_entry(event=None):
            if not _deve_capturar_atalho_mais_menos(event):
                return None
            estado = _obter_estado_teclas(event)
            if (estado & MOD_CTRL) and not atalho_estado["g_pressionado"] and (_obter_canto_ativo() is None):
                return _atalho_zoom_mais(event)
            return _atalho_rotacao_mais(event)

        def _atalho_menos_entry(event=None):
            if not _deve_capturar_atalho_mais_menos(event):
                return None
            estado = _obter_estado_teclas(event)
            if (estado & MOD_CTRL) and not atalho_estado["g_pressionado"] and (_obter_canto_ativo() is None):
                return _atalho_zoom_menos(event)
            return _atalho_rotacao_menos(event)

        def _registrar_atalhos_em_entries():
            pilha = [janela]
            while pilha:
                widget = pilha.pop()
                filhos = widget.winfo_children()
                if filhos:
                    pilha.extend(filhos)

                classe_widget = widget.winfo_class()
                if classe_widget not in {"Entry", "TEntry"}:
                    continue

                widget.bind("<KeyPress-g>", _tecla_g_press)
                widget.bind("<KeyPress-G>", _tecla_g_press)
                widget.bind("<KeyRelease-g>", _tecla_g_release)
                widget.bind("<KeyRelease-G>", _tecla_g_release)
                widget.bind("<KeyPress-q>", _tecla_q_press)
                widget.bind("<KeyPress-Q>", _tecla_q_press)
                widget.bind("<KeyRelease-q>", _tecla_q_release)
                widget.bind("<KeyRelease-Q>", _tecla_q_release)
                widget.bind("<KeyPress-w>", _tecla_w_press)
                widget.bind("<KeyPress-W>", _tecla_w_press)
                widget.bind("<KeyRelease-w>", _tecla_w_release)
                widget.bind("<KeyRelease-W>", _tecla_w_release)
                widget.bind("<KeyPress-a>", _tecla_a_press)
                widget.bind("<KeyPress-A>", _tecla_a_press)
                widget.bind("<KeyRelease-a>", _tecla_a_release)
                widget.bind("<KeyRelease-A>", _tecla_a_release)
                widget.bind("<KeyPress-s>", _tecla_s_press)
                widget.bind("<KeyPress-S>", _tecla_s_press)
                widget.bind("<KeyRelease-s>", _tecla_s_release)
                widget.bind("<KeyRelease-S>", _tecla_s_release)
                widget.bind("<KeyPress-plus>", _atalho_mais_entry)
                widget.bind("<KeyPress-KP_Add>", _atalho_mais_entry)
                widget.bind("<KeyPress-minus>", _atalho_menos_entry)
                widget.bind("<KeyPress-KP_Subtract>", _atalho_menos_entry)
                widget.bind("<Control-plus>", _atalho_zoom_mais)
                widget.bind("<Control-KP_Add>", _atalho_zoom_mais)
                widget.bind("<Control-equal>", _atalho_zoom_mais)
                widget.bind("<Control-minus>", _atalho_zoom_menos)
                widget.bind("<Control-KP_Subtract>", _atalho_zoom_menos)
                widget.bind("<Escape>", _atalho_escape_desfocar)
                widget.bind("<FocusOut>", _normalizar_entry_4casas)
                widget.bind("<Return>", _normalizar_entry_4casas)

        def iniciar_arraste(event):
            drag_estado["ativo"] = True
            drag_estado["ultimo_x"] = float(event.x)
            drag_estado["ultimo_y"] = float(event.y)

        def arrastar_imagem(event):
            if not drag_estado["ativo"]:
                return

            dx_px = float(event.x) - drag_estado["ultimo_x"]
            dy_px = float(event.y) - drag_estado["ultimo_y"]
            drag_estado["ultimo_x"] = float(event.x)
            drag_estado["ultimo_y"] = float(event.y)

            try:
                tamanho_n = float(var_local_tamanho.get())
            except (ValueError, TypeError):
                return

            lado_ref = max(1.0, float(drag_estado.get("lado_ref", 1.0)))
            metros_por_px = tamanho_n / lado_ref
            var_local_offset_x_m.set(var_local_offset_x_m.get() + (dx_px * metros_por_px))
            var_local_offset_y_m.set(var_local_offset_y_m.get() - (dy_px * metros_por_px))
            agendar_previsualizacao()

        def finalizar_arraste(_event):
            drag_estado["ativo"] = False

        for variavel in (
            var_local_tamanho,
            var_local_escala_h,
            var_local_escala_v,
            var_local_zoom,
            var_local_rotacao,
            var_local_tamanho_preview_percent,
            var_local_canto_sup_esq,
            var_local_canto_sup_dir,
            var_local_canto_inf_dir,
            var_local_canto_inf_esq,
            var_local_opacidade,
        ):
            variavel.trace_add("write", lambda *_args: agendar_previsualizacao())

        preview_canvas.bind("<ButtonPress-1>", iniciar_arraste)
        preview_canvas.bind("<B1-Motion>", arrastar_imagem)
        preview_canvas.bind("<ButtonRelease-1>", finalizar_arraste)
        preview_canvas.bind("<Configure>", lambda _e: agendar_previsualizacao())

        janela.bind("<Control-plus>", _atalho_zoom_mais)
        janela.bind("<Control-KP_Add>", _atalho_zoom_mais)
        janela.bind("<Control-equal>", _atalho_zoom_mais)
        janela.bind("<Control-minus>", _atalho_zoom_menos)
        janela.bind("<Control-KP_Subtract>", _atalho_zoom_menos)
        janela.bind("<KeyPress-g>", _tecla_g_press)
        janela.bind("<KeyPress-G>", _tecla_g_press)
        janela.bind("<KeyRelease-g>", _tecla_g_release)
        janela.bind("<KeyRelease-G>", _tecla_g_release)
        janela.bind("<KeyPress-q>", _tecla_q_press)
        janela.bind("<KeyPress-Q>", _tecla_q_press)
        janela.bind("<KeyRelease-q>", _tecla_q_release)
        janela.bind("<KeyRelease-Q>", _tecla_q_release)
        janela.bind("<KeyPress-w>", _tecla_w_press)
        janela.bind("<KeyPress-W>", _tecla_w_press)
        janela.bind("<KeyRelease-w>", _tecla_w_release)
        janela.bind("<KeyRelease-W>", _tecla_w_release)
        janela.bind("<KeyPress-a>", _tecla_a_press)
        janela.bind("<KeyPress-A>", _tecla_a_press)
        janela.bind("<KeyRelease-a>", _tecla_a_release)
        janela.bind("<KeyRelease-A>", _tecla_a_release)
        janela.bind("<KeyPress-s>", _tecla_s_press)
        janela.bind("<KeyPress-S>", _tecla_s_press)
        janela.bind("<KeyRelease-s>", _tecla_s_release)
        janela.bind("<KeyRelease-S>", _tecla_s_release)
        janela.bind("<KeyPress-plus>", _atalho_rotacao_mais)
        janela.bind("<KeyPress-KP_Add>", _atalho_rotacao_mais)
        janela.bind("<KeyPress-minus>", _atalho_rotacao_menos)
        janela.bind("<KeyPress-KP_Subtract>", _atalho_rotacao_menos)
        janela.bind("<Left>", _atalho_seta_esquerda)
        janela.bind("<Right>", _atalho_seta_direita)
        janela.bind("<Up>", _atalho_seta_cima)
        janela.bind("<Down>", _atalho_seta_baixo)
        janela.bind("<Escape>", _atalho_escape_desfocar)

        _registrar_atalhos_em_entries()

        janela.focus_force()
        atualizar_label_opacidade_local()
        previsualizar()
        janela.protocol("WM_DELETE_WINDOW", cancelar)

    def _ao_alterar_visibilidade_fundo(self):
        if self._ignorar_callback_fundo:
            return
        if not self._fundo_imagem_bytes:
            return

        if self._sincronizar_fundo_canvas(mostrar_erros=True, redesenhar=True):
            self._marcar_como_modificado()

    def _ao_alterar_opacidade_fundo(self, _valor=None):
        self._atualizar_label_opacidade_fundo()
        if self._ignorar_callback_fundo:
            return
        if not self._fundo_imagem_bytes:
            return

        if self._sincronizar_fundo_canvas(mostrar_erros=True, redesenhar=True):
            self._marcar_como_modificado()

    def remover_imagem_fundo(self):
        if not self._fundo_imagem_bytes:
            return

        self._ignorar_callback_fundo = True
        try:
            self._fundo_imagem_bytes = None
            self._fundo_imagem_nome = None
            self._fundo_carregado_no_canvas = False
            self.var_fundo_visivel.set(False)
        finally:
            self._ignorar_callback_fundo = False

        self.canvas_view.limpar_imagem_fundo()
        self._atualizar_status_imagem_fundo()
        self._redesenhar()
        self._marcar_como_modificado()

    def mostrar_ajuda(self):
        ajuda_window = tk.Toplevel(self.root)
        ajuda_window.title("Atalhos de Teclado")
        ajuda_window.geometry("500x600")
        ajuda_window.resizable(True, True)

        # Frame para scrollbar
        frame_main = ttk.Frame(ajuda_window)
        frame_main.pack(fill="both", expand=True, padx=10, pady=10)

        # Text widget com scrollbar
        text_ajuda = tk.Text(frame_main, wrap=tk.WORD, font=("Courier", 10))
        scrollbar = ttk.Scrollbar(frame_main, orient="vertical", command=text_ajuda.yview)
        text_ajuda.config(yscrollcommand=scrollbar.set)

        text_ajuda.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Conteúdo da ajuda
        ajuda_texto = """ATALHOS DE TECLADO
═══════════════════════════════════════════════════════

ARQUIVO
───────────────────────────────────────────────────────
Ctrl+S    Salvar como arquivo .tfg
Ctrl+O    Carregar arquivo .tfg
Ctrl+E    Exportar para pista

EDIÇÃO
───────────────────────────────────────────────────────
Ctrl+Z    Desfazer última ação
Ctrl+Y    Refazer última ação
ESC       Desselecionar segmento

NAVEGAÇÃO E VISUALIZAÇÃO
───────────────────────────────────────────────────────
Scroll    Zoom (usar slider na barra superior)
Drag      Mover a visualização (botão esquerdo do mouse)

ADICIONAR SEGMENTOS
───────────────────────────────────────────────────────
• Use painel "Reta" para adicionar segmentos retos
• Use painel "Curva" para adicionar curvas
• Clique "Adicionar no fim" ou "Inserir após seleção"
• Clique "Atualizar selecionada" para editar um segmento

MARCAÇÕES (WAYPOINTS)
───────────────────────────────────────────────────────
• Selecione um segmento na lista
• Use painel "Marcações" para editar lado e distância
• Mudanças de marcações entram no Ctrl+Z/Ctrl+Y

RESOLUÇÃO
───────────────────────────────────────────────────────
Automática:     Calcula pelo valor "Pontos por metro"
Manual:         Digite um número específico de pontos

DICAS
───────────────────────────────────────────────────────
• Clique em um segmento no canvas para selecioná-lo
• Duplo clique automaticamente carrega valores da seleção
• Grade cinza pode ser mostrada/ocultada nas opções
• Ajuste o espaço da grade em metros
• Use o menu "Fundo" para carregar e ajustar imagem de referência
• A opacidade da imagem vai de 0% (invisível) a 100% (opaca)
"""
        text_ajuda.insert("1.0", ajuda_texto)
        text_ajuda.config(state="disabled")

    def _redesenhar(self):
        self.canvas_view.desenhar(self.trajeto, indice_selecionado=self.indice_selecionado)
        self._atualizar_status()

    def _ao_clicar_segmento_no_canvas(self, indice_segmento):
        """Callback chamado quando um segmento é clicado no canvas"""
        if indice_segmento is not None and 0 <= indice_segmento < len(self.trajeto.segmentos):
            self.indice_selecionado = indice_segmento
            self.listbox_segmentos.selection_clear(0, tk.END)
            self.listbox_segmentos.selection_set(indice_segmento)
            self.listbox_segmentos.see(indice_segmento)
            self._ao_selecionar_segmento()
            self._redesenhar()

    def _atualizar_status(self):
        origem_x, origem_y = self.canvas_view.obter_origem_visual_m()
        x_fim, y_fim, heading = self.trajeto.poses[-1]
        x_fim_export = x_fim - origem_x
        y_fim_export = y_fim - origem_y
        try:
            qtd_pontos_status = max(2, int(self.var_resolucao.get() or 2))
        except ValueError:
            qtd_pontos_status = 2
        espacamento_medio = TrajectoryGeometry.average_spacing(self.trajeto, qtd_pontos_status) if self.trajeto.segmentos else 0.0
        txt = (
            f"Origem do trajeto: (0.00, 0.00) m\n"
            #f"Origem visual/exportação: ({origem_x:.3f}, {origem_y:.3f}) m\n"
            f"Segmentos: {len(self.trajeto.segmentos)}\n"
            #f"Segmentos desfeitos: {len(self.trajeto.segmentos_desfeitos)}\n"
            f"Comprimento total: {TrajectoryGeometry.total_length(self.trajeto):.3f} m\n"
            f"Espaçamento médio atual: {espacamento_medio:.4f} m"
            #f"Ponto final exportado: ({x_fim_export:.3f}, {y_fim_export:.3f}) m\n"
            #f"Direção final: {math.degrees(heading):.2f}°"
        )
        self.lbl_status.config(text=txt)

    def _atualizar_lista_segmentos(self, indice_preferido=None):
        self.listbox_segmentos.delete(0, tk.END)
        for i, seg in enumerate(self.trajeto.segmentos, start=1):
            if isinstance(seg, StraightSegment):
                txt = f"{i:02d} | reta | comprimento={seg.comprimento:.3f} m | ângulo={seg.angulo_graus:.2f}°"
            else:
                txt = (
                    f"{i:02d} | curva | raio={seg.raio:.3f} m | lado={seg.lado} | "
                    f"ângulo={seg.angulo_central_graus:.2f}°"
                )
            self.listbox_segmentos.insert(tk.END, txt)

        if not self.trajeto.segmentos:
            self.listbox_segmentos.insert(tk.END, "Nenhum trajeto adicionado.")
            self.indice_selecionado = None
            self.var_segmento_selecionado.set("Nenhum trecho selecionado")
            return

        # Sempre mantém um item selecionado
        if indice_preferido is None:
            indice_preferido = self.indice_selecionado if self.indice_selecionado is not None else 0
        indice_preferido = max(0, min(indice_preferido, len(self.trajeto.segmentos) - 1))
        self.listbox_segmentos.selection_clear(0, tk.END)
        self.listbox_segmentos.selection_set(indice_preferido)
        self.listbox_segmentos.see(indice_preferido)
        self.indice_selecionado = indice_preferido
        self._ao_selecionar_segmento()

    def _obter_resolucao(self):
        try:
            qtd_pontos = int(self.var_resolucao.get())
            if qtd_pontos < 2:
                raise ValueError
            return qtd_pontos
        except ValueError:
            raise ValueError("A resolução deve ser um inteiro maior ou igual a 2.")

    def exportar_tfg(self):
        if not self.trajeto.segmentos:
            messagebox.showwarning("Nada para exportar", "Adicione pelo menos um trajeto antes de exportar.")
            return

        try:
            qtd_pontos = self._obter_resolucao()
        except ValueError as e:
            messagebox.showerror("Resolução inválida", str(e))
            return False

        caminho = filedialog.asksaveasfilename(
            title="Exportar pista como pacote .tfg",
            defaultextension=".tfg",
            filetypes=[("Track File Generator", "*.tfg"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return False

        try:
            origem_x, origem_y = self.canvas_view.obter_origem_visual_m()
            fundo_payload = self._obter_payload_fundo_exportacao()
            TrajectoryExporter.export_tfg(
                tfg_path=caminho,
                trajectory=self.trajeto,
                point_count=qtd_pontos,
                unit=self.var_unidade.get(),
                custom_factor=self.var_fator_personalizado.get(),
                origin_x=origem_x,
                origin_y=origem_y,
                auto_resolution_mode=self.var_modo_resolucao_auto.get(),
                points_per_meter=self.var_pontos_por_metro.get(),
                background_image_payload=fundo_payload,
            )
        except ValueError as e:
            messagebox.showerror("Erro na exportação", str(e))
            return False
        except OSError as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return False

        messagebox.showinfo(
            "Exportação concluída",
            f"Pacote .tfg salvo com sucesso!\n\n{caminho}",
        )
        self._marcar_como_salvo()
        return True

    def carregar_tfg(self):
        caminho = filedialog.askopenfilename(
            title="Carregar projeto .tfg",
            filetypes=[("Track File Generator", "*.tfg"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return

        try:
            segmentos, config, marcacoes, limites_pista, imagem_fundo = TrajectoryImporter.import_tfg(caminho)
        except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as e:
            messagebox.showerror("Erro ao carregar .tfg", str(e))
            return

        self.trajeto.substituir_segmentos(segmentos)
        self.trajeto.substituir_marcacoes(marcacoes)
        self.trajeto.borda_deteccao = limites_pista
        self.indice_selecionado = 0 if self.trajeto.segmentos else None

        if config.get("point_count") is not None:
            self.var_resolucao.set(str(config["point_count"]))

        unidade = config.get("unit")
        if unidade == "custom":
            self.var_unidade.set("personalizada")
            if config.get("custom_factor") is not None:
                self.var_fator_personalizado.set(str(config["custom_factor"]))
        elif unidade in ["m", "cm", "mm", "km", "personalizada"]:
            self.var_unidade.set(unidade)
        if unidade != "custom" and config.get("custom_factor") is not None:
            self.var_fator_personalizado.set(str(config["custom_factor"]))

        self.var_origem_x.set(str(config.get("origin_x", 0.0)))
        self.var_origem_y.set(str(config.get("origin_y", 0.0)))
        
        if config.get("auto_resolution_mode") is not None:
            self.var_modo_resolucao_auto.set(config["auto_resolution_mode"])
        if config.get("points_per_meter") is not None:
            self.var_pontos_por_metro.set(str(config["points_per_meter"]))

        self._ignorar_callback_fundo = True
        try:
            if imagem_fundo and imagem_fundo.get("bytes"):
                fundo_config = imagem_fundo.get("config", {})
                self._fundo_imagem_bytes = imagem_fundo.get("bytes")
                self._fundo_imagem_nome = imagem_fundo.get("filename")
                self._fundo_carregado_no_canvas = False
                self.var_fundo_tamanho_quadrado.set(str(fundo_config.get("reference_square_size_m", 1.0)))
                self.var_fundo_escala_horizontal.set(str(fundo_config.get("horizontal_scale", 1.0)))
                self.var_fundo_escala_vertical.set(str(fundo_config.get("vertical_scale", 1.0)))
                self.var_fundo_zoom.set(str(fundo_config.get("zoom", 1.0)))
                self.var_fundo_offset_x_m.set(float(fundo_config.get("offset_x_m", 0.0)))
                self.var_fundo_offset_y_m.set(float(fundo_config.get("offset_y_m", 0.0)))
                perspectiva_h_legada = float(fundo_config.get("horizontal_perspective", 0.0))
                perspectiva_v_legada = float(fundo_config.get("vertical_perspective", 0.0))
                self.var_fundo_perspectiva_horizontal.set(0.0)
                self.var_fundo_perspectiva_vertical.set(0.0)

                corners_legado = self._converter_perspectiva_legada_para_cantos(
                    perspectiva_h_legada,
                    perspectiva_v_legada,
                )
                self.var_fundo_canto_superior_esquerdo.set(float(fundo_config.get("corner_top_left", corners_legado["canto_superior_esquerdo"])))
                self.var_fundo_canto_superior_direito.set(float(fundo_config.get("corner_top_right", corners_legado["canto_superior_direito"])))
                self.var_fundo_canto_inferior_direito.set(float(fundo_config.get("corner_bottom_right", corners_legado["canto_inferior_direito"])))
                self.var_fundo_canto_inferior_esquerdo.set(float(fundo_config.get("corner_bottom_left", corners_legado["canto_inferior_esquerdo"])))
                self.var_fundo_rotacao_graus.set(float(fundo_config.get("rotation_degrees", 0.0)))
                self.var_fundo_tamanho_preview_percent.set(float(fundo_config.get("reference_square_preview_percent", self.FUNDO_PREVIEW_BASE_PERCENT)))
                self.var_fundo_opacidade.set(float(fundo_config.get("opacity_percent", 60.0)))
                self.var_fundo_visivel.set(bool(fundo_config.get("visible", True)))
            else:
                self._fundo_imagem_bytes = None
                self._fundo_imagem_nome = None
                self._fundo_carregado_no_canvas = False
                self.var_fundo_tamanho_quadrado.set("1.0")
                self.var_fundo_escala_horizontal.set("1.0")
                self.var_fundo_escala_vertical.set("1.0")
                self.var_fundo_zoom.set("1.0")
                self.var_fundo_offset_x_m.set(0.0)
                self.var_fundo_offset_y_m.set(0.0)
                self.var_fundo_perspectiva_horizontal.set(0.0)
                self.var_fundo_perspectiva_vertical.set(0.0)
                self.var_fundo_canto_superior_esquerdo.set(0.0)
                self.var_fundo_canto_superior_direito.set(0.0)
                self.var_fundo_canto_inferior_direito.set(0.0)
                self.var_fundo_canto_inferior_esquerdo.set(0.0)
                self.var_fundo_rotacao_graus.set(0.0)
                self.var_fundo_tamanho_preview_percent.set(self.FUNDO_PREVIEW_BASE_PERCENT)
                self.var_fundo_opacidade.set(60.0)
                self.var_fundo_visivel.set(True)
        finally:
            self._ignorar_callback_fundo = False

        self._atualizar_label_opacidade_fundo()
        self._atualizar_status_imagem_fundo()
        self._sincronizar_fundo_canvas(mostrar_erros=False, redesenhar=False)
        
        self._atualizar_estado_fator()
        self._atualizar_estado_resolucao()
        
        # Carregar dados dos limites da pista (APÓS restaurar unidade)
        self.var_limites_altura.set(str(limites_pista.altura))
        
        self.canvas_view.centralizar_visao()
        self._atualizar_estado(modificado=False)
        # Garantir que o campo de largura está atualizado após tudo
        self._atualizar_campo_limites_largura()
        self._marcar_como_salvo()

        fundo_txt = "Sim" if self._fundo_imagem_bytes else "Não"

        messagebox.showinfo(
            "Projeto carregado",
            f"Arquivo .tfg carregado com sucesso!\n\nSegmentos: {len(self.trajeto.segmentos)}\nMarcações: {len(self.trajeto.marcacoes)}\nImagem de fundo: {fundo_txt}",
        )

