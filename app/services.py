"""Consultas agregadas (indicadores, gráficos e metas), reaproveitadas por várias telas."""
from datetime import date, timedelta

from sqlalchemy import and_, case, func, or_, select

from .extensions import db
from .models import Conteudo, Materia, Meta, SessaoEstudo
from .utils import hoje


# ------------------------------------------------------- horas estudadas
def _filtrar(consulta, ini=None, fim=None, materia_id=None):
    if ini:
        consulta = consulta.where(SessaoEstudo.data >= ini)
    if fim:
        consulta = consulta.where(SessaoEstudo.data <= fim)
    if materia_id:
        consulta = consulta.where(SessaoEstudo.materia_id == materia_id)
    return consulta


def soma_minutos(ini=None, fim=None, materia_id=None):
    consulta = _filtrar(select(func.coalesce(func.sum(SessaoEstudo.duracao_min), 0)),
                        ini, fim, materia_id)
    return int(db.session.scalar(consulta) or 0)


def minutos_por_data(ini, fim, materia_id=None):
    """{date: minutos} para o intervalo."""
    consulta = _filtrar(
        select(SessaoEstudo.data, func.sum(SessaoEstudo.duracao_min)).group_by(SessaoEstudo.data),
        ini, fim, materia_id)
    return {d: int(m or 0) for d, m in db.session.execute(consulta)}


def minutos_por_mes(ini, fim, materia_id=None):
    """{'AAAA-MM': minutos} para o intervalo."""
    mes = func.strftime("%Y-%m", SessaoEstudo.data)
    consulta = _filtrar(select(mes, func.sum(SessaoEstudo.duracao_min)).group_by(mes),
                        ini, fim, materia_id)
    return {m: int(v or 0) for m, v in db.session.execute(consulta)}


def minutos_por_materia(ini=None, fim=None, materia_id=None, limite=None):
    """Lista de (nome, categoria, minutos), do maior para o menor."""
    total = func.sum(SessaoEstudo.duracao_min)
    consulta = (select(Materia.nome, Materia.categoria, total)
                .select_from(SessaoEstudo)
                .join(Materia, Materia.id == SessaoEstudo.materia_id)
                .group_by(Materia.id, Materia.nome, Materia.categoria)
                .order_by(total.desc()))
    consulta = _filtrar(consulta, ini, fim, materia_id)
    if limite:
        consulta = consulta.limit(limite)
    return [(n, c, int(m or 0)) for n, c, m in db.session.execute(consulta)]


def minutos_por_categoria(ini=None, fim=None, materia_id=None):
    total = func.sum(SessaoEstudo.duracao_min)
    consulta = (select(Materia.categoria, total)
                .select_from(SessaoEstudo)
                .join(Materia, Materia.id == SessaoEstudo.materia_id)
                .group_by(Materia.categoria)
                .order_by(total.desc()))
    consulta = _filtrar(consulta, ini, fim, materia_id)
    return [(c, int(m or 0)) for c, m in db.session.execute(consulta)]


def horas(minutos):
    return round(minutos / 60, 2)


def meses_ate(data_final, quantidade):
    """Lista dos últimos `quantidade` meses (primeiro dia de cada um), em ordem."""
    meses = []
    ano, mes = data_final.year, data_final.month
    for _ in range(quantidade):
        meses.append(date(ano, mes, 1))
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return list(reversed(meses))


NOMES_MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
NOMES_DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


# -------------------------------------------------- progresso das matérias
def resumo_conteudos(ids_materia):
    """{materia_id: (concluidos, total)}"""
    concluidos = func.sum(case((Conteudo.status == "Concluído", 1), else_=0))
    consulta = (select(Conteudo.materia_id, concluidos, func.count(Conteudo.id))
                .where(Conteudo.materia_id.in_(ids_materia))
                .group_by(Conteudo.materia_id))
    return {mid: (int(c or 0), int(t or 0)) for mid, c, t in db.session.execute(consulta)}


def minutos_por_materia_ids(ids_materia):
    consulta = (select(SessaoEstudo.materia_id, func.sum(SessaoEstudo.duracao_min))
                .where(SessaoEstudo.materia_id.in_(ids_materia))
                .group_by(SessaoEstudo.materia_id))
    return {mid: int(m or 0) for mid, m in db.session.execute(consulta)}


# ------------------------------------------------------------------ metas
def calcular_progresso(meta):
    ini, fim = meta.data_inicio, meta.data_limite
    if meta.tipo == "horas":
        return horas(soma_minutos(ini, fim, meta.materia_id))
    if meta.tipo == "dias":
        consulta = _filtrar(select(func.count(func.distinct(SessaoEstudo.data))),
                            ini, fim, meta.materia_id)
        return float(db.session.scalar(consulta) or 0)
    if meta.tipo == "conteudos":
        consulta = select(func.count(Conteudo.id)).where(
            Conteudo.status == "Concluído",
            or_(Conteudo.data_conclusao.is_(None),
                and_(Conteudo.data_conclusao >= ini, Conteudo.data_conclusao <= fim)))
        if meta.materia_id:
            consulta = consulta.where(Conteudo.materia_id == meta.materia_id)
        return float(db.session.scalar(consulta) or 0)
    return float(meta.progresso_atual or 0)  # manual


def atualizar_meta(meta):
    meta.progresso_atual = calcular_progresso(meta)
    if meta.progresso_atual >= meta.valor_desejado:
        meta.status = "Concluída"
    elif hoje() > meta.data_limite:
        meta.status = "Atrasada"
    else:
        meta.status = "Em andamento"
    return meta


def atualizar_metas():
    """Recalcula todas as metas e grava o resultado."""
    metas = db.session.scalars(select(Meta)).all()
    for meta in metas:
        atualizar_meta(meta)
    db.session.commit()
    return metas


def proxima_data(d, dias):
    return d + timedelta(days=dias)
