"""Endereços, campus, professores, alunos e usuários."""
import string
from datetime import datetime, time, timedelta

from . import config as cfg
from .utils import (data_aleatoria, data_por_ano, escolher, gerar_cpf, gerar_telefone, ler_coluna, ler_csv,
                    trocar_dominio)


def carregar_bases(ctx):
    ctx.aux["nomes"] = ler_coluna("nomes", "nome")
    ctx.aux["sobrenomes"] = ler_coluna("sobrenomes", "sobrenome")
    bairros = {}
    for l in ler_csv("localidades"):
        bairros.setdefault(l["cidade"], []).append(l["bairro"])
    ctx.aux["bairros"] = bairros


def novo_endereco(ctx, logradouro, numero, complemento, bairro, cidade, uf, cep):
    id_ = ctx.prox_id("Endereco")
    ctx.add("Endereco", id_endereco=id_, logradouro=logradouro, numero=numero, complemento=complemento,
            bairro=bairro, cidade=cidade, estado=uf, cep=cep)
    return id_


def endereco_proximo(ctx, id_campus):
    """Só UF, cidade e bairro são reais; logradouro, número e CEP são inventados."""
    rng, c = ctx.rng, ctx.aux["campus"][id_campus]
    comp = rng.choice([None, None, None, f"Apto {rng.randint(11, 1204)}", f"Casa {rng.randint(1, 9)}"])
    while True:
        cep = f"{rng.randrange(10 ** 8):08d}"
        if cep not in ctx.aux["ceps_reais"]:
            break
    return novo_endereco(ctx, f"Rua Fictícia {rng.randint(1, 999)}", str(rng.randint(1, 2500)), comp,
                         rng.choice(ctx.aux["bairros"][c["cidade"]]), c["cidade"], c["uf"], cep)


def gerar_campus(ctx):
    ctx.aux["campus"], ctx.aux["ceps_reais"] = {}, set()
    for l in ler_csv("campus"):
        id_c = ctx.prox_id("Campus")
        id_end = novo_endereco(ctx, l["logradouro"], l["numero"], l["complemento"] or None, l["bairro"],
                               l["cidade"], l["uf"], l["cep"])
        ctx.aux["ceps_reais"].add(l["cep"])
        ctx.add("Campus", id_campus=id_c, nome=l["nome"], email=l["email"], id_endereco=id_end,
                telefone=gerar_telefone(ctx.rng, ctx.telefones, l["ddd"], fixo=True))
        ctx.aux["campus"][id_c] = {"cidade": l["cidade"], "uf": l["uf"], "ddd": l["ddd"],
                                   "regiao": l["regiao"], "peso": float(l["peso"])}


def _pessoa(ctx, id_campus):
    """Campos comuns a professor e aluno (nome, cpf, e-mail, telefone, endereço próximo ao campus)."""
    rng, aux = ctx.rng, ctx.aux
    n, s = rng.choice(aux["nomes"]), rng.choice(aux["sobrenomes"])
    tel = gerar_telefone(rng, ctx.telefones, aux["campus"][id_campus]["ddd"]) if rng.random() < 0.9 else None
    return dict(nome=f"{n} {s}", cpf=gerar_cpf(rng, ctx.cpfs), email=ctx.emails.novo(n, s, cfg.DOMINIO_PESSOAS),
                telefone=tel, id_endereco=endereco_proximo(ctx, id_campus))


def _sortear_campus(ctx):
    ids = list(ctx.aux["campus"])
    return ctx.rng.choices(ids, [ctx.aux["campus"][i]["peso"] for i in ids])[0]


def gerar_professores(ctx):
    rng, aux = ctx.rng, ctx.aux
    aux["prof"], aux["pc"] = {}, {i: [] for i in aux["campus"]}
    for _ in range(cfg.N_PROFESSORES):
        id_p, campus = ctx.prox_id("Professor"), _sortear_campus(ctx)
        status = escolher(rng, cfg.STATUS_PROFESSOR)
        contr = data_por_ano(rng, cfg.PESO_ANO_CONTRATACAO, cfg.DATA_REFERENCIA)
        deslig = None
        if status == "desligado":
            limite = cfg.DATA_REFERENCIA - timedelta(days=200)
            if contr > limite:
                contr = data_aleatoria(rng, contr.replace(month=1, day=1, year=cfg.ANO_INICIAL), limite)
            deslig = data_aleatoria(rng, contr + timedelta(days=180), cfg.DATA_REFERENCIA)
        ctx.add("Professor", id_professor=id_p, titulacao=escolher(rng, cfg.TITULACOES), data_contratacao=contr,
                status=status, data_desligamento=deslig, **_pessoa(ctx, campus))
        aux["prof"][id_p] = {"campus": campus, "status": status}
        _professor_campus(ctx, id_p, campus, contr, deslig)
        outros = [c for c, v in aux["campus"].items()
                  if c != campus and v["regiao"] == aux["campus"][campus]["regiao"]]
        if outros and rng.random() < cfg.PROB_SEGUNDO_CAMPUS:   # só entre campi da mesma região metropolitana
            fim_max = deslig or cfg.DATA_REFERENCIA
            _professor_campus(ctx, id_p, rng.choice(outros), data_aleatoria(rng, contr, fim_max), deslig)


def _professor_campus(ctx, id_p, id_c, inicio, fim):
    ctx.add("Professor_Campus", id_professor=id_p, id_campus=id_c, data_inicio=inicio, data_fim=fim)
    ctx.aux["pc"][id_c].append((id_p, inicio, fim))


def professores_elegiveis(ctx, id_campus, per):
    """Professores que cobrem o período inteiro no campus (afastados não lecionam no período corrente)."""
    atual = per["inicio"] <= cfg.DATA_REFERENCIA <= per["fim"]
    return [p for p, ini, fim in ctx.aux["pc"][id_campus]
            if ini <= per["inicio"] and (fim is None or fim >= per["fim"])
            and not (atual and ctx.aux["prof"][p]["status"] == "afastado")]


def gerar_alunos(ctx):
    """Cria os alunos e o 'plano' de cada um (campus, curso, semestre de ingresso, talento).
    Os vínculos e inscrições nascem depois, em vida.py."""
    rng, aux = ctx.rng, ctx.aux
    campi = list(aux["campus"])
    validos = {c: [p for p in aux["periodos"] if p["inicio"] <= cfg.DATA_REFERENCIA
                   and len(professores_elegiveis(ctx, c, p)) >= cfg.MIN_PROF_ELEGIVEIS] for c in campi}
    ids_m = list(aux["matriz_peso"])
    aux["plano"] = {}
    for _ in range(cfg.N_ALUNOS):
        id_a, campus = ctx.prox_id("Aluno"), _sortear_campus(ctx)
        if not validos[campus]:
            raise RuntimeError(f"Campus {campus} sem professores suficientes: aumente N_PROFESSORES.")
        per = rng.choice(validos[campus])
        idade = int(rng.triangular(cfg.IDADE_MINIMA_INGRESSO, 45, 21))
        nasc = per["inicio"] - timedelta(days=int(idade * 365.25) + 2 + rng.randint(0, 364))
        ctx.add("Aluno", id_aluno=id_a, data_nascimento=nasc, **_pessoa(ctx, campus))
        aux["plano"][id_a] = {"campus": campus, "periodo": per, "talento": rng.gauss(0, 1),
                              "id_matriz": rng.choices(ids_m, [aux["matriz_peso"][m] for m in ids_m])[0]}


def _senha_hash(rng):
    alfabeto = string.ascii_letters + string.digits + "./"
    return "$2b$12$" + "".join(rng.choices(alfabeto, k=53))   # formato bcrypt, mas aleatório (não é senha de ninguém)


def gerar_usuarios(ctx):
    """Roda depois das matrículas: 'ativo' e 'criado_em' dependem da vida acadêmica da pessoa."""
    rng, aux = ctx.rng, ctx.aux
    hora = lambda d: datetime.combine(d, time(rng.randint(7, 20), rng.randint(0, 59), rng.randint(0, 59)))
    for p in ctx.t["Professor"]:
        if rng.random() < cfg.PROB_TER_USUARIO:
            ctx.add("Usuario", id_usuario=ctx.prox_id("Usuario"), email=trocar_dominio(p["email"], cfg.DOMINIO_UNIVERSIDADE),
                    senha_hash=_senha_hash(rng), perfil="professor", ativo=p["status"] != "desligado",
                    id_aluno=None, id_professor=p["id_professor"], criado_em=hora(p["data_contratacao"]))
    for a in ctx.t["Aluno"]:
        if rng.random() < cfg.PROB_TER_USUARIO:
            per = aux["plano"][a["id_aluno"]]["periodo"]
            criado = data_aleatoria(rng, per["ini_mat"], per["inicio"])
            ctx.add("Usuario", id_usuario=ctx.prox_id("Usuario"), email=trocar_dominio(a["email"], cfg.DOMINIO_UNIVERSIDADE),
                    senha_hash=_senha_hash(rng), perfil="aluno", ativo=aux["status_aluno"][a["id_aluno"]] != "cancelado",
                    id_aluno=a["id_aluno"], id_professor=None, criado_em=hora(criado))
