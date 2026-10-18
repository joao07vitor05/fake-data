"""Orquestra a geração respeitando as dependências entre tabelas."""
from . import academico, pessoas, vida
from .utils import Contexto
from .validacao import validar


def gerar(semente=None):
    ctx = Contexto(semente)
    pessoas.carregar_bases(ctx)
    academico.gerar_periodos(ctx)        # 02 Periodo_Letivo
    academico.gerar_catalogo(ctx)        # 03 Disciplina, 04 Curso, 08 Matriz, 09 Pre_Requisito, 12 Grade
    pessoas.gerar_campus(ctx)            # 01 Endereco (3 reais) + 05 Campus
    pessoas.gerar_professores(ctx)       # 06 Professor, 10 Professor_Campus (+ endereços)
    pessoas.gerar_alunos(ctx)            # 07 Aluno (+ endereços)
    vida.matricular_alunos(ctx)          # 13 Vinculo, 14 Turma, 15 Horario, 16 Aula, 17 Avaliacao, 18-20
    pessoas.gerar_usuarios(ctx)          # 11 Usuario
    return ctx, validar(ctx)


def resumo(ctx):
    linhas = [f"  {tab:<18}{len(l):>9,}".replace(",", ".") for tab, l in ctx.t.items()]
    return "\n".join(linhas) + f"\n  (matrículas sem turma disponível no semestre: {ctx.aux['sem_vaga']})"
