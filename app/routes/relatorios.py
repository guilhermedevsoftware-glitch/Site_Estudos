import csv
import io
from datetime import datetime, time, timedelta

from flask import Blueprint, Response, flash, render_template, request
from sqlalchemy import func, select

from .. import services
from ..extensions import db
from ..models import Conteudo, Materia, Meta, SessaoEstudo, Tarefa
from ..utils import Formulario, hoje, fim_mes, inicio_mes, inicio_semana

bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")

PERIODOS = {"dia": "Dia", "semana": "Semana", "mes": "Mês",
            "personalizado": "Período personalizado", "tudo": "Todo o histórico"}


def _filtros():
    """Lê periodo/ref/inicio/fim/materia da URL e devolve (dict, erros)."""
    f = Formulario(request.args)
    periodo = request.args.get("periodo", "mes")
    if periodo not in PERIODOS:
        periodo = "mes"
    ref = f.data("ref", "Data de referência", padrao=hoje())
    ini_pers = f.data("inicio", "Data inicial", padrao=inicio_mes(hoje()))
    fim_pers = f.data("fim", "Data final", padrao=hoje())

    if periodo == "dia":
        ini = fim = ref
    elif periodo == "semana":
        ini = inicio_semana(ref)
        fim = ini + timedelta(days=6)
    elif periodo == "mes":
        ini, fim = inicio_mes(ref), fim_mes(ref)
    elif periodo == "personalizado":
        ini, fim = ini_pers, fim_pers
        if fim < ini:
            f.erros.append("A data final não pode ser anterior à inicial; as datas foram invertidas.")
            ini, fim = fim, ini
    else:  # tudo
        primeira = db.session.scalar(select(func.min(SessaoEstudo.data)))
        ini, fim = primeira or hoje(), hoje()

    materia_id = request.args.get("materia", type=int)
    return {"periodo": periodo, "ref": ref, "inicio": ini, "fim": fim,
            "ini_pers": ini_pers, "fim_pers": fim_pers, "materia_id": materia_id}, f.erros


def _serie(ini, fim, materia_id):
    """Série para o gráfico principal: diária (até 92 dias) ou mensal."""
    dias = (fim - ini).days + 1
    if dias <= 92:
        por_data = services.minutos_por_data(ini, fim, materia_id)
        datas = [ini + timedelta(days=i) for i in range(dias)]
        return ([d.strftime("%d/%m") for d in datas],
                [services.horas(por_data.get(d, 0)) for d in datas], "dia")
    por_mes = services.minutos_por_mes(ini, fim, materia_id)
    meses, d = [], ini.replace(day=1)
    while d <= fim:
        meses.append(d)
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return ([f"{services.NOMES_MESES[m.month - 1]}/{str(m.year)[2:]}" for m in meses],
            [services.horas(por_mes.get(m.strftime("%Y-%m"), 0)) for m in meses], "mês")


def _dados(filtros):
    ini, fim, mid = filtros["inicio"], filtros["fim"], filtros["materia_id"]
    services.atualizar_metas()

    total = services.soma_minutos(ini, fim, mid)
    dias_decorridos = max(1, (min(fim, hoje()) - ini).days + 1)
    media_diaria = total / dias_decorridos
    media_semanal = media_diaria * 7

    materias = services.minutos_por_materia(ini, fim, mid)
    categorias = services.minutos_por_categoria(ini, fim, mid)
    labels, valores, granularidade = _serie(ini, fim, mid)

    por_data = services.minutos_por_data(ini, fim, mid)
    dia_semana = [0] * 7
    for d, m in por_data.items():
        dia_semana[d.weekday()] += m

    conteudos = select(func.count(Conteudo.id)).where(
        Conteudo.status == "Concluído", Conteudo.data_conclusao >= ini, Conteudo.data_conclusao <= fim)
    tarefas = select(func.count(Tarefa.id)).where(
        Tarefa.status == "Concluída",
        Tarefa.concluida_em >= datetime.combine(ini, time.min),
        Tarefa.concluida_em < datetime.combine(fim + timedelta(days=1), time.min))
    metas = select(func.count(Meta.id)).where(
        Meta.status == "Concluída", Meta.data_inicio <= fim, Meta.data_limite >= ini)
    if mid:
        conteudos = conteudos.where(Conteudo.materia_id == mid)
        tarefas = tarefas.where(Tarefa.materia_id == mid)
        metas = metas.where(Meta.materia_id == mid)

    sessoes = db.session.scalar(
        select(func.count(SessaoEstudo.id)).where(
            SessaoEstudo.data >= ini, SessaoEstudo.data <= fim,
            *( [SessaoEstudo.materia_id == mid] if mid else [])))

    return {
        "total": total, "media_diaria": media_diaria, "media_semanal": media_semanal,
        "sessoes": sessoes or 0,
        "conteudos": db.session.scalar(conteudos) or 0,
        "tarefas": db.session.scalar(tarefas) or 0,
        "metas": db.session.scalar(metas) or 0,
        "ranking": [{"nome": n, "categoria": c, "minutos": m,
                     "pct": round(m / total * 100) if total else 0} for n, c, m in materias],
        "graficos": {
            "serie": {"labels": labels, "valores": valores, "granularidade": granularidade},
            "materias": {"labels": [m[0] for m in materias],
                         "valores": [services.horas(m[2]) for m in materias]},
            "categorias": {"labels": [c[0] for c in categorias],
                           "valores": [services.horas(c[1]) for c in categorias]},
            "semana": {"labels": services.NOMES_DIAS,
                       "valores": [services.horas(m) for m in dia_semana]},
        },
    }


@bp.route("/")
def index():
    filtros, erros = _filtros()
    for erro in erros:
        flash(erro, "warning")
    materias = db.session.scalars(select(Materia).order_by(Materia.nome)).all()
    return render_template("relatorios/index.html", f=filtros, d=_dados(filtros),
                           materias=materias, periodos=PERIODOS,
                           args={k: v for k, v in request.args.items() if k not in ("tipo", "page")})


# ---------------------------------------------------------------- CSV
def _celula(valor):
    """Evita injeção de fórmulas ao abrir o CSV no Excel."""
    texto = "" if valor is None else str(valor)
    if texto[:1] in ("=", "+", "-", "@", "\t", "\r"):
        texto = "'" + texto
    return texto


@bp.route("/exportar.csv")
def exportar():
    filtros, _ = _filtros()
    ini, fim, mid = filtros["inicio"], filtros["fim"], filtros["materia_id"]
    tipo = request.args.get("tipo", "sessoes")

    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")  # padrão do Excel pt-BR

    if tipo == "materias":
        escritor.writerow(["Matéria", "Categoria", "Minutos", "Horas", "Percentual do total"])
        dados = _dados(filtros)
        for item in dados["ranking"]:
            escritor.writerow([_celula(item["nome"]), _celula(item["categoria"]), item["minutos"],
                               str(services.horas(item["minutos"])).replace(".", ","),
                               f"{item['pct']}%"])
        nome = "resumo_por_materia"
    else:
        escritor.writerow(["Data", "Início", "Término", "Matéria", "Categoria", "Conteúdo",
                           "Duração (min)", "Observações"])
        consulta = (select(SessaoEstudo).where(SessaoEstudo.data >= ini, SessaoEstudo.data <= fim)
                    .order_by(SessaoEstudo.inicio))
        if mid:
            consulta = consulta.where(SessaoEstudo.materia_id == mid)
        for s in db.session.scalars(consulta):
            escritor.writerow([
                s.data.strftime("%d/%m/%Y"), s.inicio.strftime("%H:%M"), s.fim.strftime("%H:%M"),
                _celula(s.materia.nome), _celula(s.materia.categoria),
                _celula(s.conteudo.nome if s.conteudo else ""), s.duracao_min,
                _celula((s.observacoes or "").replace("\r", " ").replace("\n", " "))])
        nome = "sessoes_de_estudo"

    arquivo = f"studyflow_{nome}_{ini.isoformat()}_{fim.isoformat()}.csv"
    # BOM UTF-8: o Excel reconhece os acentos corretamente.
    return Response("﻿" + saida.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{arquivo}"'})
