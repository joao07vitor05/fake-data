"""Escrita dos resultados: um CSV por tabela (na ordem de criação) e um popular.sql com INSERTs em lote."""
import csv
from datetime import date, datetime, time

from .esquema import COLUNAS, PKS


def _csv(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, float):
        return f"{v:.2f}"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, (date, time)):
        return v.isoformat()
    return v


def _sql(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(_csv(v))
    return "'" + str(_csv(v)).replace("'", "''") + "'"


def escrever(ctx, pasta, com_sql=True, lote=500, dialeto="postgres", limpar=False):
    pasta.mkdir(parents=True, exist_ok=True)
    for n, (tab, cols) in enumerate(COLUNAS.items(), 1):
        with open(pasta / f"{n:02d}_{tab.lower()}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows([_csv(l[c]) for c in cols] for l in ctx.t[tab])
    if not com_sql:
        return
    pg = dialeto == "postgres"
    # Postgres: colunas IDENTITY (GENERATED ALWAYS) só aceitam id explícito com OVERRIDING SYSTEM VALUE
    override = " OVERRIDING SYSTEM VALUE" if pg else ""
    with open(pasta / "popular.sql", "w", encoding="utf-8") as f:
        f.write("-- Gerado pelo data-fake. Rode depois de criar as tabelas (ordem de criação já respeitada).\n")
        if limpar:
            if pg:
                f.write(f"TRUNCATE {', '.join(COLUNAS)} RESTART IDENTITY CASCADE;\n")
            else:
                f.write("SET FOREIGN_KEY_CHECKS = 0;\n" + "".join(f"TRUNCATE TABLE {t};\n" for t in COLUNAS)
                        + "SET FOREIGN_KEY_CHECKS = 1;\n")
        for tab, cols in COLUNAS.items():
            linhas = ctx.t[tab]
            for i in range(0, len(linhas), lote):
                valores = ",\n".join("(" + ", ".join(_sql(l[c]) for c in cols) + ")" for l in linhas[i:i + lote])
                f.write(f"INSERT INTO {tab} ({', '.join(cols)}){override} VALUES\n{valores};\n")
        if pg:   # avança as sequências para o app não reutilizar ids já carregados
            f.write("-- Acerta os contadores de id (sem efeito em tabelas sem sequência)\n")
            for tab, cols in COLUNAS.items():
                if len(PKS[tab]) == 1:
                    c = cols[0]
                    f.write(f"SELECT setval(pg_get_serial_sequence('{tab}', '{c}'), (SELECT max({c}) FROM {tab}));\n")
