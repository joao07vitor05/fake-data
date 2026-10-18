"""Uso:  python main.py                     (gera tudo em ./saida)
        python main.py --alunos 1000 --professores 150 --semente 7 --sem-sql"""
import argparse
from pathlib import Path

from datafake import config as cfg
from datafake.pipeline import gerar, resumo
from datafake.saida import escrever


def main():
    ap = argparse.ArgumentParser(description="Gerador de dados fictícios da universidade (Hogwarts).")
    ap.add_argument("--alunos", type=int, default=cfg.N_ALUNOS)
    ap.add_argument("--professores", type=int, default=cfg.N_PROFESSORES)
    ap.add_argument("--semente", type=int, default=cfg.SEMENTE)
    ap.add_argument("--saida", type=Path, default=cfg.DIR_SAIDA)
    ap.add_argument("--sem-sql", action="store_true", help="gera só os CSVs")
    ap.add_argument("--dialeto", choices=["postgres", "mysql"], default="postgres", help="sintaxe do popular.sql")
    ap.add_argument("--limpar", action="store_true", help="começa o popular.sql esvaziando as tabelas")
    a = ap.parse_args()
    cfg.N_ALUNOS, cfg.N_PROFESSORES = a.alunos, a.professores

    ctx, erros = gerar(a.semente)
    print(resumo(ctx))
    if erros:
        print("\nPROBLEMAS ENCONTRADOS:", *erros, sep="\n  - ")
        raise SystemExit(1)
    escrever(ctx, a.saida, com_sql=not a.sem_sql, dialeto=a.dialeto, limpar=a.limpar)
    print(f"\nValidação OK. Arquivos em: {a.saida}")


if __name__ == "__main__":
    main()
