import csv
import json
import zipfile
import os
import tempfile
import shutil
from dataclasses import asdict

from services.geometria import GeometriaTrajeto


class ExportadorTrajeto:
    @staticmethod
    def obter_fator_unidade(unidade, fator_personalizado):
        mapa = {
            "m": 1.0,
            "cm": 100.0,
            "mm": 1000.0,
            "km": 0.001,
        }

        if unidade in mapa:
            return mapa[unidade], unidade

        fator = float(fator_personalizado)
        if fator <= 0:
            raise ValueError("Fator personalizado inválido. Use um número maior que zero.")
        return fator, "custom"

    @staticmethod
    def _montar_dados_json(trajeto, qtd_pontos, unidade_saida, fator, origem_x, origem_y, modo_resolucao_auto=True, pontos_por_metro="10"):
        dados_segmentos = []
        for i, seg in enumerate(trajeto.segmentos, start=1):
            item = asdict(seg)
            item["ordem"] = i
            item["tipo"] = seg.tipo
            dados_segmentos.append(item)

        dados_marcacoes = []
        if hasattr(trajeto, 'marcacoes') and trajeto.marcacoes:
            for marcacao in trajeto.marcacoes:
                item = asdict(marcacao)
                dados_marcacoes.append(item)

        espacamento_medio_m = GeometriaTrajeto.espacamento_medio(trajeto, qtd_pontos) if qtd_pontos is not None else None

        return {
            "origem_trajeto_m": {"x": 0.0, "y": 0.0},
            "origem_visual_exportacao_m": {"x": origem_x, "y": origem_y},
            "comprimento_total_m": GeometriaTrajeto.comprimento_total(trajeto),
            "qtd_pontos_exportados": qtd_pontos,
            "espacamento_medio_entre_pontos_m": espacamento_medio_m,
            "unidade_saida": unidade_saida,
            "fator_multiplicador_da_unidade": fator,
            "modo_resolucao_auto": modo_resolucao_auto,
            "pontos_por_metro": pontos_por_metro,
            "segmentos": dados_segmentos,
            "marcacoes": dados_marcacoes,
        }

    @staticmethod
    def salvar_json_projeto(caminho_json, trajeto, qtd_pontos, unidade, fator_personalizado, origem_x, origem_y, modo_resolucao_auto=True, pontos_por_metro="10"):
        fator, unidade_saida = ExportadorTrajeto.obter_fator_unidade(unidade, fator_personalizado)
        dados = ExportadorTrajeto._montar_dados_json(
            trajeto=trajeto,
            qtd_pontos=qtd_pontos,
            unidade_saida=unidade_saida,
            fator=fator,
            origem_x=origem_x,
            origem_y=origem_y,
            modo_resolucao_auto=modo_resolucao_auto,
            pontos_por_metro=pontos_por_metro,
        )

        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

    @staticmethod
    def exportar_csv_e_json(caminho_csv, trajeto, qtd_pontos, unidade, fator_personalizado, origem_x, origem_y, modo_resolucao_auto=True, pontos_por_metro="10"):
        pontos = GeometriaTrajeto.amostrar_por_quantidade(trajeto, qtd_pontos)

        # CSV da pista com apenas idx, x, y (em metros)
        with open(caminho_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["idx", "x", "y"])
            for i, (x, y) in enumerate(pontos):
                writer.writerow([i, x, y])

        # JSON com metadata e config
        fator, unidade_saida = ExportadorTrajeto.obter_fator_unidade(unidade, fator_personalizado)
        caminho_json = caminho_csv.rsplit(".", 1)[0] + "_segmentos.json"
        ExportadorTrajeto.salvar_json_projeto(
            caminho_json=caminho_json,
            trajeto=trajeto,
            qtd_pontos=qtd_pontos,
            unidade=unidade,
            fator_personalizado=fator_personalizado,
            origem_x=origem_x,
            origem_y=origem_y,
            modo_resolucao_auto=modo_resolucao_auto,
            pontos_por_metro=pontos_por_metro,
        )
        
        # CSV de marcações com idx, lado, x, y (em metros)
        if trajeto.marcacoes:
            caminho_marcacoes = caminho_csv.rsplit(".", 1)[0] + "_marcacoes.csv"
            with open(caminho_marcacoes, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["idx", "lado", "x", "y"])
                for marcacao in trajeto.marcacoes:
                    writer.writerow([marcacao.ordem, marcacao.lado, marcacao.x, marcacao.y])
        
        return caminho_json

    @staticmethod
    def exportar_tfg(caminho_tfg, trajeto, qtd_pontos, unidade, fator_personalizado, origem_x, origem_y, modo_resolucao_auto=True, pontos_por_metro="10"):
        """Exporta tudo em um único arquivo .tfg (Track File Generator) que é um ZIP contendo CSVs e JSON."""
        # Cria diretório temporário
        tmpdir = tempfile.mkdtemp()
        try:
            # Nome base sem extensão
            nome_base = os.path.splitext(os.path.basename(caminho_tfg))[0]
            caminho_csv_temp = os.path.join(tmpdir, f"{nome_base}.csv")
            
            # Exporta CSV e JSON normalmente no temp
            caminho_json_temp = ExportadorTrajeto.exportar_csv_e_json(
                caminho_csv_temp, trajeto, qtd_pontos, unidade, fator_personalizado, 
                origem_x, origem_y, modo_resolucao_auto, pontos_por_metro
            )
            
            # Cria o arquivo ZIP .tfg
            with zipfile.ZipFile(caminho_tfg, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Adiciona pista.csv
                zipf.write(caminho_csv_temp, f"{nome_base}.csv")
                
                # Adiciona segmentos.json
                zipf.write(caminho_json_temp, os.path.basename(caminho_json_temp))
                
                # Adiciona marcações.csv se existir
                caminho_marcacoes = caminho_csv_temp.rsplit(".", 1)[0] + "_marcacoes.csv"
                if os.path.exists(caminho_marcacoes):
                    zipf.write(caminho_marcacoes, os.path.basename(caminho_marcacoes))
        
        finally:
            # Limpa temp
            shutil.rmtree(tmpdir, ignore_errors=True)
