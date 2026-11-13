"""Registros reproduzíveis e relatórios HTML, CSV e Excel; independentes do Streamlit."""
from __future__ import annotations

from datetime import datetime
from html import escape
import io
import math
import re
import pandas as pd


def registrar_resultado(teste: str, variaveis: str, tabela: pd.DataFrame,
                        n: int, alpha: float, estatistica: str = "", p: float | None = None,
                        efeito: str = "", nota: str = "", tipo: str = "inferencial", fonte: str = "") -> dict:
    return {
        "quando": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "teste": str(teste), "variaveis": str(variaveis), "estatistica": str(estatistica),
        "p": p, "n": int(n), "efeito": str(efeito), "nota": str(nota),
        "tipo": tipo, "tabela": tabela.copy(deep=True), "alpha": float(alpha),
        "fonte": str(fonte),
    }


def registrar_engine(resultado, parametros: dict, alpha: float, fonte: str) -> dict:
    if resultado.efeito_nome and math.isfinite(resultado.efeito_valor):
        efeito = f"{resultado.efeito_nome} = {resultado.efeito_valor:.5g}"
    else:
        efeito = ""
    return registrar_resultado(
        resultado.nome, ", ".join(f"{k}: {v}" for k, v in parametros.items()),
        resultado.detalhes, resultado.n, alpha,
        f"{resultado.estatistica} = {resultado.valor:.6g}", resultado.p,
        efeito, resultado.observacoes, resultado.tipo, fonte,
    )


def tabela_resumo(historico: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Data/hora": r["quando"], "Análise": r["teste"], "Variáveis": r.get("variaveis", ""),
        "Estatística": r["estatistica"], "p": r["p"], "N": r["n"],
        "Tamanho do efeito": r.get("efeito", ""), "α": r.get("alpha", .05),
    } for r in historico], columns=["Data/hora", "Análise", "Variáveis", "Estatística", "p", "N", "Tamanho do efeito", "α"])


def _ptexto(p) -> str:
    if p is None or pd.isna(p):
        return "—"
    if p < .0001:
        return "< 0,0001"
    return f"{p:.4f}".replace(".", ",")


def gerar_html(historico: list[dict], titulo: str, fonte: str, schema: dict | None = None) -> bytes:
    if not historico:
        raise ValueError("Execute uma análise antes de gerar o relatório.")
    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    styles = """<style>
      @page {size:A4; margin:17mm 16mm}
      body {font: 13px/1.55 Arial,Helvetica,sans-serif;color:#24313c;max-width:930px;margin:34px auto}
      h1 {font-size:24px;color:#173b52;margin-bottom:7px} h2 {font-size:17px;color:#173b52;margin-top:26px}
      .sub {color:#667783;font-size:12px}.entry {break-inside:avoid;margin-top:20px;border-top:1px solid #d5e0e7;padding-top:12px}
      .stats {display:flex;flex-wrap:wrap;gap:16px;background:#f1f7f8;padding:11px;border-radius:5px}
      .stats span {margin-right:14px} .note {color:#536575;font-size:12px}
      table {border-collapse:collapse;width:100%;font-size:12px;margin:10px 0 16px}
      td,th {border-bottom:1px solid #dce5eb;padding:7px;text-align:left;overflow-wrap:anywhere}
      th {background:#e9f1f4} .foot {margin-top:26px;border-top:1px solid #dce5eb;padding-top:10px;color:#586a76;font-size:11px}
      @media print {body {margin:0} .entry {break-inside:auto}}
    </style>"""
    out = ["<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>Relatório - Estatística Livre</title>",
           styles, "</head><body>", "<h1>Relatório estatístico</h1>",
           f"<div class='sub'><strong>{escape(titulo)}</strong> | Base: {escape(fonte)} | Gerado: {escape(hoje)}</div>",
           f"<p class='sub'>{len(historico)} análise(s). Dados e resultados devem ser revisados antes de utilização científica.</p>"]
    for idx, r in enumerate(historico, 1):
        out += [f"<section class='entry'><h2>{idx:02d}. {escape(r['teste'])}</h2>",
                f"<p><strong>Seleção:</strong> {escape(r.get('variaveis', ''))}</p>",
                "<div class='stats'>",
                f"<span><b>N:</b> {r['n']}</span>",
                f"<span><b>Estatística:</b> {escape(r.get('estatistica', '') or '—')}</span>",
                f"<span><b>p:</b> {escape(_ptexto(r.get('p')))}</span>",
                f"<span><b>α:</b> {r.get('alpha',.05):.2f}</span>",
                f"<span><b>Efeito:</b> {escape(r.get('efeito', '') or '—')}</span>",
                "</div>"]
        if r.get("conclusao"):
            out.append(f"<p><strong>Interpretação:</strong> {escape(r['conclusao'])}</p>")
        if r.get("magnitude"):
            out.append(f"<p><strong>Magnitude do efeito (referência convencional):</strong> {escape(r['magnitude'])}</p>")
        tabela = r.get("tabela")
        if isinstance(tabela, pd.DataFrame) and not tabela.empty:
            out.append(tabela.to_html(index=False, border=0, escape=True, na_rep="—", float_format=lambda v: f"{v:.5g}"))
        if r.get("nota"):
            out.append(f"<p class='note'><strong>Pressupostos e observações:</strong> {escape(r['nota'])}</p>")
        out.append("</section>")
    out.append("<div class='foot'>Estatística Livre 0.2 • Software educacional independente. Não substitui supervisão estatística; "
               "p-valores não demonstram causalidade, equivalência nem importância clínica. "
               "O relatório pode ser salvo em PDF pela função Imprimir do navegador.</div></body></html>")
    return "\n".join(out).encode("utf-8")


def gerar_excel(historico: list[dict], schema_tab: pd.DataFrame) -> bytes:
    if not historico:
        raise ValueError("Não existem análises para exportar.")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        tabela_resumo(historico).to_excel(writer, sheet_name="Resumo", index=False)
        schema_tab.to_excel(writer, sheet_name="Variáveis", index=False)
        for i, r in enumerate(historico, 1):
            sheet = f"Teste_{i:02d}"
            topo = pd.DataFrame({"Campo": ["Análise", "Variáveis", "N", "Estatística", "p", "Tamanho do efeito", "Observações"],
                                 "Valor": [r['teste'], r.get('variaveis',''), r['n'],r.get('estatistica',''),r.get('p'),r.get('efeito',''),r.get('nota','')]})
            topo.to_excel(writer, sheet_name=sheet, index=False)
            tab = r.get("tabela")
            if isinstance(tab, pd.DataFrame) and not tab.empty:
                tab.to_excel(writer, sheet_name=sheet, index=False, startrow=len(topo)+3)
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                from openpyxl.styles import Font, PatternFill
                cell.fill = PatternFill(fill_type="solid", fgColor="E8F1F4")
                cell.font = Font(bold=True, color="173B52")
            for column in ws.columns:
                letter = column[0].column_letter
                width = min(45, max(12, max(len(str(c.value or "")) for c in list(column)[:90]) + 2))
                ws.column_dimensions[letter].width = width
    return output.getvalue()
