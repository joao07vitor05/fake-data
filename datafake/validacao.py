"""Confere integridade (PK, UNIQUE, FK) e regras de negócio. Devolve a lista de problemas encontrados."""
from datetime import date

from . import config as cfg
from .esquema import FKS, PKS, UNICOS


def _chaves(linhas, cols):
    return [tuple(l[c] for c in cols) for l in linhas]


def _idade(nasc, ref):
    return ref.year - nasc.year - ((ref.month, ref.day) < (nasc.month, nasc.day))


def validar(ctx):
    t, erros = ctx.t, []
    erro = lambda msg: erros.append(msg) if len(erros) < 40 else None

    for tab, cols in PKS.items():
        ks = _chaves(t[tab], cols)
        if len(ks) != len(set(ks)):
            erro(f"PK duplicada em {tab}")
    for tab, lista in UNICOS.items():
        for cols in lista:
            ks = [k for k in _chaves(t[tab], cols) if None not in k]
            if len(ks) != len(set(ks)):
                erro(f"UNIQUE {cols} duplicado em {tab}")
    for tab, cols, ref, rcols in FKS:
        existentes = set(_chaves(t[ref], rcols))
        if any(None not in k and k not in existentes for k in _chaves(t[tab], cols)):
            erro(f"FK órfã: {tab}{cols} -> {ref}")

    ref, ini = cfg.DATA_REFERENCIA, date(cfg.ANO_INICIAL, 1, 1)
    prof = {p["id_professor"]: p for p in t["Professor"]}
    for p in prof.values():
        if p["titulacao"] not in ("especialista", "mestre", "doutor"):
            erro(f"titulação inválida: {p['id_professor']}")
        if not (ini <= p["data_contratacao"] <= ref):
            erro(f"contratação fora do intervalo: {p['id_professor']}")
        if (p["status"] == "desligado") != (p["data_desligamento"] is not None):
            erro(f"status x desligamento incoerente: {p['id_professor']}")
        if p["data_desligamento"] and not (p["data_contratacao"] <= p["data_desligamento"] <= ref):
            erro(f"desligamento antes da contratação: {p['id_professor']}")
    for pc in t["Professor_Campus"]:
        p = prof[pc["id_professor"]]
        if pc["data_inicio"] < p["data_contratacao"] or (pc["data_fim"] and pc["data_fim"] < pc["data_inicio"]):
            erro(f"datas de Professor_Campus incoerentes: {pc['id_professor']}")
    for tab in ("Professor", "Aluno"):
        for p in t[tab]:
            if len(p["cpf"]) != 11 or not p["email"].endswith("@" + cfg.DOMINIO_PESSOAS):
                erro(f"cpf/e-mail inválido em {tab}")
    for u in t["Usuario"]:
        if not u["email"].endswith("@" + cfg.DOMINIO_UNIVERSIDADE) or (u["id_aluno"] is None) == (u["id_professor"] is None):
            erro("Usuario com e-mail/vínculo inválido")

    alunos = {a["id_aluno"]: a for a in t["Aluno"]}
    cidade = {e["id_endereco"]: e["cidade"] for e in t["Endereco"]}
    cidade_campus = {c["id_campus"]: cidade[c["id_endereco"]] for c in t["Campus"]}
    for v in t["Vinculo_Curso"]:
        a = alunos[v["id_aluno"]]
        if _idade(a["data_nascimento"], v["data_ingresso"]) < cfg.IDADE_MINIMA_INGRESSO:
            erro(f"aluno {a['id_aluno']} ingressou com menos de {cfg.IDADE_MINIMA_INGRESSO} anos")
        if cidade[a["id_endereco"]] != cidade_campus[v["id_campus"]]:
            erro(f"aluno {a['id_aluno']} mora fora da cidade do campus")
    for p in t["Professor"]:
        cidades = {cidade_campus[c] for pid, c in ((x["id_professor"], x["id_campus"]) for x in t["Professor_Campus"]) if pid == p["id_professor"]}
        if cidade[p["id_endereco"]] not in cidades:
            erro(f"professor {p['id_professor']} mora fora da cidade de seus campi")

    pcs = {(x["id_professor"], x["id_campus"]): x for x in t["Professor_Campus"]}
    per = {x["id_periodo"]: x for x in t["Periodo_Letivo"]}
    turmas = {x["id_turma"]: x for x in t["Turma"]}
    for tu in turmas.values():
        pc, pe = pcs[(tu["id_professor"], tu["id_campus"])], per[tu["id_periodo"]]
        if pc["data_inicio"] > pe["data_inicio"] or (pc["data_fim"] and pc["data_fim"] < pe["data_fim"]):
            erro(f"turma {tu['id_turma']} com professor fora do vínculo")
    soma = {}
    for a in t["Avaliacao"]:
        soma[a["id_turma"]] = round(soma.get(a["id_turma"], 0) + a["peso"], 2)
    if any(s != 1.0 for s in soma.values()):
        erro("pesos das avaliações não somam 1")

    vinc = {v["id_vinculo"]: v for v in t["Vinculo_Curso"]}
    ocupadas = {}
    por_vinculo = {}
    for i in t["Inscricao_Turma"]:
        tu, v = turmas[i["id_turma"]], vinc[i["id_vinculo"]]
        if tu["id_campus"] != v["id_campus"]:
            erro("inscrição em turma de outro campus")
        ocupadas[tu["id_turma"]] = ocupadas.get(tu["id_turma"], 0) + 1
        por_vinculo.setdefault(i["id_vinculo"], []).append((per[tu["id_periodo"]]["data_inicio"], tu["id_disciplina"], i["situacao"]))
    if any(n > turmas[k]["vagas"] for k, n in ocupadas.items()):
        erro("turma com mais inscritos que vagas")
    prereq, grade = {}, {}
    for r in t["Pre_Requisito"]:
        prereq.setdefault(r["id_disciplina"], set()).add(r["id_disciplina_requisito"])
    for g in t["Grade_Curricular"]:
        grade.setdefault(g["id_matriz"], set()).add(g["id_disciplina"])
    for idv, itens in por_vinculo.items():
        aprovou = {}
        for ini_p, d, s in itens:
            if s == "aprovado":
                aprovou[d] = min(aprovou.get(d, ini_p), ini_p)
        for ini_p, d, _ in itens:
            for req in prereq.get(d, ()):
                if req in grade[vinc[idv]["id_matriz"]] and not (req in aprovou and aprovou[req] < ini_p):
                    erro(f"pré-requisito não cumprido (vínculo {idv}, disciplina {d})")
    if any(not (0 <= n["valor"] <= 10) for n in t["Nota"]):
        erro("nota fora de 0..10")
    return erros
