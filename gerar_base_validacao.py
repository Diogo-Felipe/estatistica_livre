"""Cria CSV fictício com resultados estatísticos verificáveis.

Execute da pasta do programa: python gerar_base_validacao.py
Não usa dados reais ou informações identificáveis de pacientes.
"""
from __future__ import annotations
import csv
from pathlib import Path

DESTINO = Path(__file__).with_name('validacao_estatistica_ficticia.csv')
CAMPOS = ['id_teste', 'grupo_anova', 'pontuacao', 'antes', 'depois',
          'grupo_qui', 'resposta_qui', 'grupo_fisher', 'resposta_fisher']


def gerar() -> Path:
    valores = [6,7,8,9,10,11,12,13,14,15]*2
    antes = [5,8,6,10,7,9,11,12]
    dif = [1,2,3,4,5,6,7,8]
    linhas = []
    for i in range(60):
        idx, pos = divmod(i, 20)
        grupo = 'ABC'[idx]
        resposta_qui = 'sim' if pos < (8,12,16)[idx] else 'nao'
        # 2x2 independente com margens [6,6] e [6,6]:
        if i < 12:
            gf = 'A' if i < 6 else 'B'
            rf = ('nao' if i < 5 else 'sim') if i < 6 else ('nao' if i == 6 else 'sim')
        else:
            gf = rf = ''
        linhas.append({
            'id_teste': f'EX{i+1:03}', 'grupo_anova': grupo,
            'pontuacao': valores[pos]+idx*3,
            'antes': antes[i] if i < 8 else '',
            'depois': antes[i]+dif[i] if i < 8 else '',
            'grupo_qui': grupo, 'resposta_qui': resposta_qui,
            'grupo_fisher': gf, 'resposta_fisher': rf,
        })
    with DESTINO.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=';')
        w.writeheader()
        w.writerows(linhas)
    return DESTINO


if __name__ == '__main__':
    print(f'Arquivo de validação gerado: {gerar()}')
