from datetime import datetime, time, timedelta

from flask import Blueprint, flash, render_template
from sqlalchemy import func, select

from .. import services
from ..extensions import db
from ..models import Atividade, Materia, Meta, SessaoEstudo, Tarefa
from ..seed import carregar_exemplos
from ..utils import fim_mes, hoje, inicio_mes, inicio_semana, redirecionar_para

bp = Blueprint("dashboard", __name__)


def _dados_graficos(hoje_):
    # Horas por dia da semana atual (segunda a domingo)
    segunda = inicio_semana(hoje_)
    por_data = services.minutos_por_data(segunda, segunda + timedelta(days=6))
    semana = [services.horas(por_data.get(segunda + timedelta(days=i), 0)) for i in range(7)]

    # Horas por matéria (total, 8 maiores)
    materias = services.minutos_por_materia(limite=8)

    # Evolução mensal (12 últimos meses)
    meses = services.meses_ate(hoje_, 12)
    por_mes = services.minutos_por_mes(meses[0], fim_mes(meses[-1]))

    # Distribuição por categoria
    categorias = services.minutos_por_categoria()

    return {
        "semana": {"labels": services.NOMES_DIAS, "valores": semana},
        "materias": {"labels": [m[0] for m in materias],
                     "valores": [services.horas(m[2]) for m in materias]},
        "mensal": {"labels": [f"{services.NOMES_MESES[m.month - 1]}/{str(m.year)[2:]}" for m in meses],
                   "valores": [services.horas(por_mes.get(m.strftime("%Y-%m"), 0)) for m in meses]},
        "categorias": {"labels": [c[0] for c in categorias],
                       "valores": [services.horas(c[1]) for c in categorias]},
    }


@bp.route("/")
def index():
    hoje_ = hoje()
    metas = services.atualizar_metas()

    total_materias = db.session.scalar(select(func.count(Materia.id))) or 0
    pendentes = db.session.scalar(
        select(func.count(Tarefa.id)).where(Tarefa.status != "Concluída")) or 0
    concluidas = db.session.scalar(
        select(func.count(Tarefa.id)).where(Tarefa.status == "Concluída")) or 0
    ativ_total = db.session.scalar(select(func.count(Atividade.id))) or 0
    ativ_concluidas = db.session.scalar(
        select(func.count(Atividade.id)).where(Atividade.status == "Concluída")) or 0
    itens = pendentes + concluidas + ativ_total
    percentual = round((concluidas + ativ_concluidas) / itens * 100) if itens else 0

    indicadores = {
        "hoje": services.soma_minutos(hoje_, hoje_),
        "semana": services.soma_minutos(inicio_semana(hoje_), hoje_),
        "mes": services.soma_minutos(inicio_mes(hoje_), hoje_),
        "materias": total_materias,
        "pendentes": pendentes,
        "concluidas": concluidas,
        "metas_andamento": sum(1 for m in metas if m.status == "Em andamento"),
        "percentual": percentual,
    }

    inicio_dia = datetime.combine(hoje_, time.min)
    fim_dia = inicio_dia + timedelta(days=1)
    atividades_hoje = db.session.scalars(
        select(Atividade).where(Atividade.inicio >= inicio_dia, Atividade.inicio < fim_dia)
        .order_by(Atividade.inicio)).all()
    tarefas_hoje = db.session.scalars(
        select(Tarefa).where(Tarefa.status != "Concluída", Tarefa.prazo.is_not(None),
                             Tarefa.prazo <= hoje_)
        .order_by(Tarefa.prazo, Tarefa.id)).all()

    total_sessoes = db.session.scalar(select(func.count(SessaoEstudo.id))) or 0

    return render_template(
        "dashboard.html",
        ind=indicadores,
        graficos=_dados_graficos(hoje_),
        atividades_hoje=atividades_hoje,
        tarefas_hoje=tarefas_hoje,
        total_sessoes=total_sessoes,
        metas_ativas=[m for m in metas if m.status == "Em andamento"][:4],
        hoje=hoje_,
    )


@bp.post("/exemplos")
def carregar_dados_exemplo():
    criadas = carregar_exemplos()
    if criadas:
        flash(f"{criadas} matéria(s) de exemplo cadastrada(s). Você pode editá-las ou excluí-las.",
              "success")
    else:
        flash("As matérias de exemplo já estão cadastradas; nada foi duplicado.", "info")
    return redirecionar_para("dashboard.index")
