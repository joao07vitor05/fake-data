"""Períodos letivos e estrutura acadêmica (disciplinas, cursos, matrizes, grade e pré-requisitos)."""
from datetime import date, timedelta

from . import config as cfg
from .utils import ler_csv


def gerar_periodos(ctx):
    periodos = []
    for ano in range(cfg.ANO_INICIAL, cfg.ANO_FINAL + 1):
        for sem, mes in ((1, 2), (2, 8)):
            d = date(ano, mes, 1)
            ini = d + timedelta(days=(7 - d.weekday()) % 7)               # primeira segunda-feira do mês
            fim = ini + timedelta(days=7 * (cfg.SEMANAS_LETIVAS - 1) + 4)  # sexta da última semana
            id_ = ctx.prox_id("Periodo_Letivo")
            ctx.add("Periodo_Letivo", id_periodo=id_, codigo=f"{ano}.{sem}", data_inicio=ini, data_fim=fim,
                    data_inicio_matricula=ini - timedelta(days=30), data_fim_matricula=ini + timedelta(days=7),
                    data_limite_trancamento=ini + timedelta(days=60))
            periodos.append({"id": id_, "idx": len(periodos), "codigo": f"{ano}.{sem}", "inicio": ini, "fim": fim,
                             "ini_mat": ini - timedelta(days=30), "fim_mat": ini + timedelta(days=7)})
    ctx.aux["periodos"] = periodos


def gerar_catalogo(ctx):
    aux = ctx.aux
    aux.update(disc={}, grade={}, prereq={}, matriz_peso={})
    ref_id, contador = {}, {}
    for l in ler_csv("disciplinas"):
        contador[l["area"]] = contador.get(l["area"], 100) + 1
        id_ = ctx.prox_id("Disciplina")
        ctx.add("Disciplina", id_disciplina=id_, codigo=f"{l['area']}{contador[l['area']]}", nome=l["nome"],
                carga_horaria=int(l["carga_horaria"]), creditos=int(l["creditos"]), ementa=l["ementa"] or None)
        ref_id[l["ref"]] = id_
        aux["disc"][id_] = {"ch": int(l["carga_horaria"]), "dif": int(l["dificuldade"])}

    matrizes_da_grade = {}
    for l in ler_csv("cursos"):
        id_c = ctx.prox_id("Curso")
        ctx.add("Curso", id_curso=id_c, nome=l["nome"], grau=l["grau"], modalidade=l["modalidade"],
                duracao_semestres=int(l["duracao_semestres"]), carga_horaria_total=int(l["carga_horaria_total"]))
        id_m = ctx.prox_id("Matriz_Curricular")
        ctx.add("Matriz_Curricular", id_matriz=id_m, id_curso=id_c, ano_vigencia=int(l["ano_vigencia"]), ativa=True)
        matrizes_da_grade.setdefault(l["grade"], []).append(id_m)
        aux["matriz_peso"][id_m] = float(l["popularidade"])

    for l in ler_csv("grade_curricular"):
        id_d, obrig = ref_id[l["disciplina"]], l["obrigatoria"] == "1"
        for id_m in matrizes_da_grade[l["grade"]]:
            ctx.add("Grade_Curricular", id_matriz=id_m, id_disciplina=id_d,
                    periodo_sugerido=int(l["periodo_sugerido"]), obrigatoria=obrig)
            if obrig:
                aux["grade"].setdefault(id_m, {})[id_d] = int(l["periodo_sugerido"])

    for l in ler_csv("pre_requisitos"):
        a, b = ref_id[l["disciplina"]], ref_id[l["requisito"]]
        ctx.add("Pre_Requisito", id_disciplina=a, id_disciplina_requisito=b)
        aux["prereq"].setdefault(a, set()).add(b)
