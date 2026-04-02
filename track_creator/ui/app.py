import json
import math
import tkinter as tk
import zipfile
from tkinter import filedialog, messagebox, ttk

from models.segmentos import SegmentoCurva, SegmentoReta
from models.trajeto import Trajeto
from services.exportador import ExportadorTrajeto
from services.geometria import GeometriaTrajeto
from services.importador import ImportadorTrajeto
from ui.canvas_view import CanvasTrajetoView


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
}


class GeradorTrajetoApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gerador de Trajeto")

        self.trajeto = Trajeto()
        self.indice_selecionado = None
        self.projeto_modificado = False

        self._criar_variaveis()
        self._configurar_menu()
        self._montar_interface()
        self._atualizar_campo_limites_largura()
        
        # Defer shortcuts configuration to after UI is fully loaded
        self.root.after(100, self._configurar_atalhos)
        self.root.protocol("WM_DELETE_WINDOW", self.fechar_aplicativo)

        GeometriaTrajeto.recalcular_poses(self.trajeto)
        self._atualizar_lista_segmentos()
        self._redesenhar()

    def _marcar_como_modificado(self):
        if not self.projeto_modificado:
            self.projeto_modificado = True
            self.root.title("Gerador de Trajeto *")

    def _marcar_como_salvo(self):
        if self.projeto_modificado:
            self.projeto_modificado = False
            self.root.title("Gerador de Trajeto")

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

        self.canvas_view = CanvasTrajetoView(
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
            comprimento_total = GeometriaTrajeto.comprimento_total(self.trajeto)
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
        GeometriaTrajeto.recalcular_poses(self.trajeto)
        self._recalcular_posicoes_marcacoes()
        if self.var_modo_resolucao_auto.get():
            self._recalcular_resolucao_automatica()
        self._atualizar_campo_borda_largura()
        self._atualizar_lista_segmentos(indice)
        self._redesenhar()

    def _recalcular_posicoes_marcacoes(self):
        """Recalcula as posições de todas as marcações baseado nos segmentos atuais."""
        for i, marcacao in enumerate(self.trajeto.marcacoes):
            if i < len(self.trajeto.segmentos):
                pos = GeometriaTrajeto.calcular_posicao_marcacao(
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
        return SegmentoReta(comprimento=comprimento, angulo_graus=angulo_graus)

    def _construir_segmento_curva(self):
        raio = float(self.var_curva_raio.get())
        angulo_central_graus = float(self.var_curva_angulo.get())
        if raio <= 0:
            raise ValueError("Informe raio > 0.")
        if not (-360 <= angulo_central_graus <= 360):
            raise ValueError("Informe ângulo da curva entre -360° e 360°.")
        return SegmentoCurva(
            raio=raio,
            lado=self.var_curva_lado.get(),
            angulo_central_graus=angulo_central_graus,
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
        if not isinstance(segmento_atual, SegmentoReta):
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
        if not isinstance(segmento_atual, SegmentoCurva):
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
        pos = GeometriaTrajeto.calcular_posicao_marcacao(
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
                
            pos = GeometriaTrajeto.calcular_posicao_marcacao(
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
        if isinstance(segmento, SegmentoReta):
            self.var_reta_comprimento.set(str(segmento.comprimento))
            self.var_reta_angulo.set(str(segmento.angulo_graus))
        elif isinstance(segmento, SegmentoCurva):
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
            print(f"[DEBUG] Atualizando largura: altura={altura}, largura={largura}")
            
            self.entry_limites_largura_display.config(state="normal")
            self.entry_limites_largura_display.delete(0, tk.END)
            self.entry_limites_largura_display.insert(0, valor_formatado)
            self.entry_limites_largura_display.config(state="readonly")
        except Exception as e:
            print(f"[ERROR] Erro ao atualizar campo limites largura: {e}")
            import traceback
            traceback.print_exc()

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
        espacamento_medio = GeometriaTrajeto.espacamento_medio(self.trajeto, qtd_pontos_status) if self.trajeto.segmentos else 0.0
        txt = (
            f"Origem do trajeto: (0.00, 0.00) m\n"
            #f"Origem visual/exportação: ({origem_x:.3f}, {origem_y:.3f}) m\n"
            f"Segmentos: {len(self.trajeto.segmentos)}\n"
            #f"Segmentos desfeitos: {len(self.trajeto.segmentos_desfeitos)}\n"
            f"Comprimento total: {GeometriaTrajeto.comprimento_total(self.trajeto):.3f} m\n"
            f"Espaçamento médio atual: {espacamento_medio:.4f} m"
            #f"Ponto final exportado: ({x_fim_export:.3f}, {y_fim_export:.3f}) m\n"
            #f"Direção final: {math.degrees(heading):.2f}°"
        )
        self.lbl_status.config(text=txt)

    def _atualizar_lista_segmentos(self, indice_preferido=None):
        self.listbox_segmentos.delete(0, tk.END)
        for i, seg in enumerate(self.trajeto.segmentos, start=1):
            if isinstance(seg, SegmentoReta):
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
            ExportadorTrajeto.exportar_tfg(
                caminho_tfg=caminho,
                trajeto=self.trajeto,
                qtd_pontos=qtd_pontos,
                unidade=self.var_unidade.get(),
                fator_personalizado=self.var_fator_personalizado.get(),
                origem_x=origem_x,
                origem_y=origem_y,
                modo_resolucao_auto=self.var_modo_resolucao_auto.get(),
                pontos_por_metro=self.var_pontos_por_metro.get(),
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
            segmentos, config, marcacoes, limites_pista = ImportadorTrajeto.importar_tfg(caminho)
        except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as e:
            messagebox.showerror("Erro ao carregar .tfg", str(e))
            return

        self.trajeto.substituir_segmentos(segmentos)
        self.trajeto.substituir_marcacoes(marcacoes)
        self.trajeto.borda_deteccao = limites_pista
        self.indice_selecionado = 0 if self.trajeto.segmentos else None

        if config.get("qtd_pontos") is not None:
            self.var_resolucao.set(str(config["qtd_pontos"]))

        unidade = config.get("unidade")
        if unidade == "custom":
            self.var_unidade.set("personalizada")
            if config.get("fator_personalizado") is not None:
                self.var_fator_personalizado.set(str(config["fator_personalizado"]))
        elif unidade in ["m", "cm", "mm", "km", "personalizada"]:
            self.var_unidade.set(unidade)
        if unidade != "custom" and config.get("fator_personalizado") is not None:
            self.var_fator_personalizado.set(str(config["fator_personalizado"]))

        self.var_origem_x.set(str(config.get("origem_x", 0.0)))
        self.var_origem_y.set(str(config.get("origem_y", 0.0)))
        
        if config.get("modo_resolucao_auto") is not None:
            self.var_modo_resolucao_auto.set(config["modo_resolucao_auto"])
        if config.get("pontos_por_metro") is not None:
            self.var_pontos_por_metro.set(str(config["pontos_por_metro"]))
        
        self._atualizar_estado_fator()
        self._atualizar_estado_resolucao()
        
        # Carregar dados dos limites da pista (APÓS restaurar unidade)
        self.var_limites_altura.set(str(limites_pista.altura))
        
        self.canvas_view.centralizar_visao()
        self._atualizar_estado(modificado=False)
        # Garantir que o campo de largura está atualizado após tudo
        self._atualizar_campo_limites_largura()
        self._marcar_como_salvo()

        messagebox.showinfo(
            "Projeto carregado",
            f"Arquivo .tfg carregado com sucesso!\n\nSegmentos: {len(self.trajeto.segmentos)}\nMarcações: {len(self.trajeto.marcacoes)}",
        )

