"""Parâmetros do gerador. Para mudar o volume ou as regras, mexa só aqui (ou use os argumentos do main.py)."""
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_DADOS = RAIZ / "data"      # CSVs-base (entrada)
DIR_SAIDA = RAIZ / "saida"     # CSVs/SQL gerados (saída)

SEMENTE = 42                          # mesma semente = mesmos dados em qualquer computador
DATA_REFERENCIA = date(2026, 10, 16)  # "hoje" do banco: nada acontece depois dessa data
ANO_INICIAL, ANO_FINAL = 2020, 2026

N_PROFESSORES = 90
N_ALUNOS = 300

DOMINIO_PESSOAS = "example.com"
DOMINIO_UNIVERSIDADE = "hogwarts.com"
CPF_VALIDO = False        # False = dígitos verificadores propositalmente errados (nunca bate com CPF real)
DDD_ALEATORIO = False     # False = DDD do campus da pessoa (11 ou 21); True = sorteia entre todos os DDDs

# --- professores
PESO_ANO_CONTRATACAO = {2020: 35, 2021: 18, 2022: 14, 2023: 11, 2024: 10, 2025: 8, 2026: 4}
TITULACOES = [("especialista", 30), ("mestre", 45), ("doutor", 25)]
STATUS_PROFESSOR = [("ativo", 80), ("afastado", 8), ("desligado", 12)]
PROB_SEGUNDO_CAMPUS = 0.15
PROB_TER_USUARIO = 0.95

# --- vida acadêmica
SEMANAS_LETIVAS = 16
IDADE_MINIMA_INGRESSO = 18
MIN_PROF_ELEGIVEIS = 4          # aluno só ingressa em período/campus com pelo menos N professores aptos
MAX_TURMAS_PROFESSOR = 8        # por período
MAX_TURMAS_POR_OFERTA = 4       # mesma disciplina, período e campus
MAX_DISCIPLINAS_SEMESTRE = 6
PROB_CANCELAR = 0.025           # por semestre
PROB_TRANCAR = 0.015
MIN_FREQUENCIA = 0.75
MEDIA_APROVACAO = 6.0
