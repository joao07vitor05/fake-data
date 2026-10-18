"""Ferramentas comuns: leitura de CSV, e-mail, CPF, telefone, datas e o Contexto (onde as tabelas ficam)."""
import csv
import random
import unicodedata
from datetime import date, timedelta

from . import config as cfg
from .esquema import COLUNAS


# ---------- CSV de entrada
def ler_csv(nome):
    caminho = cfg.DIR_DADOS / f"{nome}.csv"
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        texto = f.read()
    delim = ";" if ";" in texto.splitlines()[0] else ","
    return list(csv.DictReader(texto.splitlines(), delimiter=delim))


def ler_coluna(arquivo, coluna):
    """Lê a coluna `coluna`; se o cabeçalho for outro, usa a primeira coluna do arquivo."""
    linhas = ler_csv(arquivo)
    chave = coluna if coluna in linhas[0] else next(iter(linhas[0]))
    return [l[chave].strip() for l in linhas if l[chave] and l[chave].strip()]


# ---------- texto
def slug(texto):
    sem = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return "".join(c for c in sem.lower() if c.isalnum())


def trocar_dominio(email, dominio):
    return email.split("@")[0] + "@" + dominio


class GeradorEmail:
    """nome.sobrenome@dominio; repetidos viram nome.sobrenome1@, nome.sobrenome2@ ..."""
    def __init__(self):
        self.vistos = {}

    def novo(self, nome, sobrenome, dominio):
        base = f"{slug(nome)}.{slug(sobrenome)}"
        n = self.vistos.get(base, 0)
        self.vistos[base] = n + 1
        return f"{base}{n or ''}@{dominio}"


# ---------- documentos e telefone
def _dv(digitos):
    soma = sum(d * p for d, p in zip(digitos, range(len(digitos) + 1, 1, -1)))
    r = soma * 10 % 11
    return 0 if r == 10 else r


def gerar_cpf(rng, usados):
    while True:
        d = [rng.randrange(10) for _ in range(9)]
        if len(set(d)) == 1:
            continue
        d1 = _dv(d)
        d2 = _dv(d + [d1])
        if not cfg.CPF_VALIDO:
            d2 = (d2 + rng.randrange(1, 10)) % 10   # força o 2º dígito a ficar errado
        cpf = "".join(map(str, d + [d1, d2]))
        if cpf not in usados:
            usados.add(cpf)
            return cpf


DDDS_BR = [11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 24, 27, 28, 31, 32, 33, 34, 35, 37, 38, 41, 42, 43, 44, 45,
           46, 47, 48, 49, 51, 53, 54, 55, 61, 62, 63, 64, 65, 66, 67, 68, 69, 71, 73, 74, 75, 77, 79, 81, 82, 83,
           84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99]


def gerar_telefone(rng, usados, ddd, fixo=False):
    if cfg.DDD_ALEATORIO and not fixo:
        ddd = rng.choice(DDDS_BR)
    while True:
        if fixo:
            tel = f"({ddd}) 3{rng.randrange(1000):03d}-{rng.randrange(10000):04d}"
        else:
            tel = f"({ddd}) 9{rng.randrange(10000):04d}-{rng.randrange(10000):04d}"
        if tel not in usados:
            usados.add(tel)
            return tel


# ---------- sorteios
def escolher(rng, pares):
    itens, pesos = zip(*pares)
    return rng.choices(itens, pesos)[0]


def data_aleatoria(rng, ini, fim):
    return ini + timedelta(days=rng.randint(0, max(0, (fim - ini).days)))


def data_por_ano(rng, pesos, limite):
    ano = rng.choices(list(pesos), list(pesos.values()))[0]
    return data_aleatoria(rng, date(ano, 1, 1), min(date(ano, 12, 31), limite))


# ---------- contexto
class Contexto:
    """Guarda as tabelas geradas (listas de dicionários) e índices auxiliares usados entre etapas."""
    def __init__(self, semente=None):
        self.rng = random.Random(cfg.SEMENTE if semente is None else semente)
        self.t = {tab: [] for tab in COLUNAS}
        self.aux = {}
        self.emails = GeradorEmail()
        self.cpfs, self.telefones = set(), set()

    def add(self, tabela, **campos):
        if set(campos) != set(COLUNAS[tabela]):
            raise ValueError(f"Colunas de {tabela} não batem com o modelo: {sorted(set(campos) ^ set(COLUNAS[tabela]))}")
        self.t[tabela].append(campos)
        return campos

    def prox_id(self, tabela):
        return len(self.t[tabela]) + 1
