import json
import zipfile
import os
import tempfile
import shutil

from models.segmentos import SegmentoCurva, SegmentoReta
from models.marcacao import Marcacao


class ImportadorTrajeto:
    @staticmethod
    def carregar_json(caminho_json):
        with open(caminho_json, "r", encoding="utf-8") as f:
            dados = json.load(f)

        segmentos_dados = dados.get("segmentos")
        if not isinstance(segmentos_dados, list):
            raise ValueError("JSON inválido: campo 'segmentos' ausente ou inválido.")

        segmentos = []
        for item in segmentos_dados:
            if not isinstance(item, dict):
                raise ValueError("JSON inválido: item de segmento inválido.")

            tipo = item.get("tipo")
            if tipo == "reta":
                segmentos.append(
                    SegmentoReta(
                        comprimento=float(item["comprimento"]),
                        angulo_graus=float(item["angulo_graus"]),
                    )
                )
            elif tipo == "curva":
                segmentos.append(
                    SegmentoCurva(
                        raio=float(item["raio"]),
                        lado=str(item["lado"]),
                        angulo_central_graus=float(item["angulo_central_graus"]),
                    )
                )
            else:
                raise ValueError(f"Tipo de segmento desconhecido no JSON: {tipo!r}")

        marcacoes = []
        marcacoes_dados = dados.get("marcacoes", [])
        if isinstance(marcacoes_dados, list):
            for item in marcacoes_dados:
                if isinstance(item, dict):
                    marcacoes.append(
                        Marcacao(
                            ordem=int(item.get("ordem", 0)),
                            lado=str(item.get("lado", "esquerda")),
                            distancia=float(item.get("distancia", 0.0)),
                            x=float(item.get("x", 0.0)),
                            y=float(item.get("y", 0.0)),
                            angulo_eixo_x=float(item.get("angulo_eixo_x", 0.0)),
                        )
                    )

        origem_visual = dados.get("origem_visual_exportacao_m", {}) or {}
        qtd_pontos = dados.get("qtd_pontos_exportados")
        unidade_saida = dados.get("unidade_saida")
        fator_unidade = dados.get("fator_multiplicador_da_unidade")
        modo_resolucao_auto = dados.get("modo_resolucao_auto")
        pontos_por_metro = dados.get("pontos_por_metro")

        config = {
            "origem_x": float(origem_visual.get("x", 0.0)),
            "origem_y": float(origem_visual.get("y", 0.0)),
            "qtd_pontos": int(qtd_pontos) if qtd_pontos is not None else None,
            "unidade": unidade_saida,
            "fator_personalizado": float(fator_unidade) if fator_unidade is not None else None,
            "modo_resolucao_auto": modo_resolucao_auto,
            "pontos_por_metro": pontos_por_metro,
        }
        return segmentos, config, marcacoes

    @staticmethod
    def importar_tfg(caminho_tfg):
        """Importa dados de um arquivo .tfg (ZIP contendo CSV e JSON)."""
        tmpdir = tempfile.mkdtemp()
        try:
            # Extrai o arquivo ZIP
            with zipfile.ZipFile(caminho_tfg, 'r') as zipf:
                zipf.extractall(tmpdir)
            
            # Encontra o arquivo JSON
            arquivos_json = [f for f in os.listdir(tmpdir) if f.endswith('_segmentos.json')]
            if not arquivos_json:
                raise ValueError("Arquivo .tfg inválido: nenhum arquivo _segmentos.json encontrado.")
            
            caminho_json = os.path.join(tmpdir, arquivos_json[0])
            
            # Carrega usando o método carregar_json
            segmentos, config, marcacoes = ImportadorTrajeto.carregar_json(caminho_json)
            
            # Obtém o fator de conversão para converter de volta para metros
            fator_unidade = config.get("fator_personalizado", 1.0)
            if fator_unidade is None:
                fator_unidade = 1.0
            fator_inverso = 1.0 / float(fator_unidade)  # Converte de volta para metros
            
            # Tenta carregar marcações do CSV se existir
            nome_base = os.path.splitext(arquivos_json[0])[0].replace("_segmentos", "")
            caminho_marcacoes_csv = os.path.join(tmpdir, f"{nome_base}_marcacoes.csv")
            
            if os.path.exists(caminho_marcacoes_csv):
                import csv
                import math
                marcacoes = []
                with open(caminho_marcacoes_csv, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row:
                            angulo_graus = float(row.get("angulo_eixo_x_graus", 0.0))
                            angulo_rad = math.radians(angulo_graus)
                            
                            # Lê os valores (em unidades do CSV) e converte de volta para metros
                            distancia = float(row.get("distancia", 0.0)) * fator_inverso
                            x = float(row.get("x", 0.0)) * fator_inverso
                            y = float(row.get("y", 0.0)) * fator_inverso
                            
                            marcacoes.append(
                                Marcacao(
                                    ordem=int(row.get("idx", 0)),
                                    lado=str(row.get("lado", "esquerda")),
                                    distancia=distancia,
                                    x=x,
                                    y=y,
                                    angulo_eixo_x=angulo_rad,
                                )
                            )
            
            return segmentos, config, marcacoes
        
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

