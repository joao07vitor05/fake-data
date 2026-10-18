"""Turmas, horários, aulas, avaliações, vínculos, inscrições, presenças e notas.

A simulação anda semestre a semestre: cada aluno se matricula nas disciplinas da grade, respeitando
pré-requisitos, vagas, choque de horário e professores disponíveis. A nota depende do 'talento' do aluno
e da 'dificuldade' da disciplina; a situação (aprovado/reprovado) sai da frequência e da média."""
from datetime import time, timedelta

from . import config as cfg
from .pessoas import professores_elegiveis

BLOCOS = [(time(8), time(10)), (time(10), time(12)), (time(14), time(16)), (time(16), time(18)), (time(19), time(21))]
SALAS = [f"Sala {n}" for n in list(range(101, 111)) + list(range(201, 211))]
AVALIACOES = [
    [("Prova 1", 0.40), ("Prova 2", 0.40), ("Trabalho", 0.20)],
    [("AV1", 0.30), ("AV2", 0.30), ("AV3", 0.40)],
    [("Prova 1", 0.30), ("Prova 2", 0.30), ("Seminário", 0.20), ("Trabalho prático", 0.20)],
    [("Prova 1", 0.50), ("Prova 2", 0.50)],
]


def _horarios_livres(ctx, n, ocupados, id_campus, id_periodo):
    """Sorteia n (dia, bloco, sala) em dias diferentes, sem conflito com o professor/aluno e com sala livre."""
    rng, ocup_sala = ctx.rng, ctx.aux["ocup_sala"]
    for _ in range(30):
        slots = [(d, rng.randrange(len(BLOCOS))) for d in rng.sample(range(1, 6), n)]
        if any(s in ocupados for s in slots):
            continue
        escolhidos = []
        for d, b in slots:
            livres = [s for s in SALAS if (id_campus, id_periodo, d, b, s) not in ocup_sala]
            if not livres:
                break
            escolhidos.append((d, b, rng.choice(livres)))
        else:
            return escolhidos
    return None


def criar_turma(ctx, id_disc, per, id_campus, evitar):
    rng, aux = ctx.rng, ctx.aux
    n_h = 1 if aux["disc"][id_disc]["ch"] <= 60 else 2
    profs = [p for p in professores_elegiveis(ctx, id_campus, per)
             if aux["carga"].get((p, per["id"]), 0) < cfg.MAX_TURMAS_PROFESSOR]
    rng.shuffle(profs)
    for prof in profs[:8]:
        ocup = aux["ocup_prof"].setdefault((prof, per["id"]), set())
        escolha = _horarios_livres(ctx, n_h, ocup | evitar, id_campus, per["id"])
        if escolha:
            break
    else:
        return None

    lista = aux["turmas"].setdefault((id_disc, per["id"], id_campus), [])
    id_t = ctx.prox_id("Turma")
    vagas = rng.choice([30, 40, 50, 60])
    ctx.add("Turma", id_turma=id_t, id_disciplina=id_disc, id_periodo=per["id"], id_professor=prof,
            id_campus=id_campus, codigo_turma=f"T{len(lista) + 1:02d}", vagas=vagas)
    for dia, b, sala in escolha:
        ctx.add("Horario_Turma", id_horario=ctx.prox_id("Horario_Turma"), id_turma=id_t, dia_semana=dia,
                hora_inicio=BLOCOS[b][0], hora_fim=BLOCOS[b][1], sala=sala)
        ocup.add((dia, b))
        aux["ocup_sala"].add((id_campus, per["id"], dia, b, sala))
    aux["carga"][(prof, per["id"])] = aux["carga"].get((prof, per["id"]), 0) + 1

    datas = sorted(per["inicio"] + timedelta(weeks=w, days=dia - 1)
                   for w in range(cfg.SEMANAS_LETIVAS) for dia, _, _ in escolha)
    aulas = []
    for k, d in enumerate(datas, 1):
        if d > cfg.DATA_REFERENCIA:
            break
        id_a = ctx.prox_id("Aula")
        ctx.add("Aula", id_aula=id_a, id_turma=id_t, data_aula=d, conteudo=f"Aula {k}")
        aulas.append(id_a)

    avals, modelo = [], rng.choice(AVALIACOES)
    for i, (desc, peso) in enumerate(modelo):
        semana = round((i + 1) * (cfg.SEMANAS_LETIVAS - 1) / len(modelo))
        data = per["inicio"] + timedelta(weeks=semana, days=escolha[0][0] - 1)
        id_av = ctx.prox_id("Avaliacao")
        ctx.add("Avaliacao", id_avaliacao=id_av, id_turma=id_t, descricao=desc, peso=peso, data_aplicacao=data)
        avals.append((id_av, peso, data))

    turma = {"id": id_t, "disc": id_disc, "livres": vagas, "slots": {(d, b) for d, b, _ in escolha},
             "aulas": aulas, "avals": avals}
    lista.append(turma)
    return turma


def obter_turma(ctx, id_disc, per, id_campus, ocup_aluno):
    lista = ctx.aux["turmas"].get((id_disc, per["id"], id_campus), [])
    for t in lista:
        if t["livres"] > 0 and not (t["slots"] & ocup_aluno):
            return t
    if len(lista) >= cfg.MAX_TURMAS_POR_OFERTA:
        return None
    return criar_turma(ctx, id_disc, per, id_campus, ocup_aluno)


def cursar(ctx, id_vinculo, turma, per, talento, ocup_aluno):
    """Cria inscrição, presenças e notas. Devolve a situação final."""
    rng, aux = ctx.rng, ctx.aux
    turma["livres"] -= 1
    ocup_aluno |= turma["slots"]
    id_i = ctx.prox_id("Inscricao_Turma")
    insc = ctx.add("Inscricao_Turma", id_inscricao=id_i, id_vinculo=id_vinculo, id_turma=turma["id"],
                   situacao="cursando",
                   data_inscricao=aux_data(rng, per["ini_mat"], min(per["fim_mat"], cfg.DATA_REFERENCIA)))
    assiduidade = min(1.0, max(0.35, rng.gauss(0.88 + 0.03 * talento, 0.09)))
    presentes = 0
    for id_a in turma["aulas"]:
        p = rng.random() < assiduidade
        presentes += p
        ctx.add("Presenca", id_aula=id_a, id_inscricao=id_i, id_turma=turma["id"], presente=p)
    alvo = 7.2 + 1.0 * talento - 0.45 * (aux["disc"][turma["disc"]]["dif"] - 3)
    media = 0.0
    for id_av, peso, data in turma["avals"]:
        if data <= cfg.DATA_REFERENCIA:     # prova futura ainda não tem nota
            v = round(min(10, max(0, rng.gauss(alvo, 1.0))), 2)
            ctx.add("Nota", id_inscricao=id_i, id_avaliacao=id_av, id_turma=turma["id"], valor=v)
            media += peso * v
    if per["fim"] <= cfg.DATA_REFERENCIA:   # período encerrado: fecha a situação
        freq = presentes / len(turma["aulas"]) if turma["aulas"] else 1
        insc["situacao"] = ("reprovado_falta" if freq < cfg.MIN_FREQUENCIA
                            else "aprovado" if media >= cfg.MEDIA_APROVACAO else "reprovado_nota")
    return insc["situacao"]


def aux_data(rng, ini, fim):
    return ini + timedelta(days=rng.randint(0, max(0, (fim - ini).days)))


def matricular_alunos(ctx):
    rng, aux = ctx.rng, ctx.aux
    aux.update(turmas={}, ocup_prof={}, ocup_sala=set(), carga={}, status_aluno={}, sem_vaga=0)
    for id_a, plano in aux["plano"].items():
        per0, grade = plano["periodo"], aux["grade"][plano["id_matriz"]]
        ordem = sorted(grade, key=grade.get)
        id_v = ctx.prox_id("Vinculo_Curso")
        aprovadas, sem, status, encerr, ultimo_fim = set(), 0, "ativo", None, None
        for per in aux["periodos"][per0["idx"]:]:
            if per["inicio"] > cfg.DATA_REFERENCIA:
                break
            sem += 1
            if sem > 1:
                r = rng.random()
                if r < cfg.PROB_CANCELAR:
                    status, encerr = "cancelado", ultimo_fim
                    break
                if r < cfg.PROB_CANCELAR + cfg.PROB_TRANCAR:
                    status = "trancado"
                    break
            candidatas = [d for d in ordem if d not in aprovadas and grade[d] <= sem
                          and all(p in aprovadas for p in aux["prereq"].get(d, ()) if p in grade)]
            ocup, resultado = set(), {}
            for d in candidatas[:cfg.MAX_DISCIPLINAS_SEMESTRE]:
                turma = obter_turma(ctx, d, per, plano["campus"], ocup)
                if turma:
                    resultado[d] = cursar(ctx, id_v, turma, per, plano["talento"], ocup)
                else:
                    aux["sem_vaga"] += 1
            aprovadas |= {d for d, s in resultado.items() if s == "aprovado"}
            ultimo_fim = per["fim"]
            if set(grade) <= aprovadas:
                status, encerr = "formado", per["fim"]
                break
        ctx.add("Vinculo_Curso", id_vinculo=id_v, id_aluno=id_a, id_matriz=plano["id_matriz"],
                id_campus=plano["campus"], matricula=f"{per0['codigo'].replace('.', '')}{id_v:05d}",
                data_ingresso=per0["inicio"], status=status, data_encerramento=encerr)
        aux["status_aluno"][id_a] = status
