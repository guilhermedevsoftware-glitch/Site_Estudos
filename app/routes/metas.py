from datetime import timedelta

from flask import Blueprint, render_template, request
from sqlalchemy import case, func, select

from .. import choices as CH
from .. import services
from ..extensions import db
from ..models import Materia, Meta
from ..utils import (Formulario, confirmar, flash_erros, hoje, obter_ou_404, paginar,
                     redirecionar_para)

bp = Blueprint("metas", __name__, url_prefix="/metas")

ORDEM_STATUS = case({"Atrasada": 0, "Em andamento": 1, "Concluída": 2}, value=Meta.status, else_=3)


def _ler_formulario():
    f = Formulario()
    tipo = f.escolha("tipo", "Tipo de meta", list(CH.TIPOS_META))
    inicio = f.data("data_inicio", "Data de início", obrigatorio=True)
    limite = f.data("data_limite", "Data limite", obrigatorio=True)
    if inicio and limite and limite < inicio:
        f.erros.append("A data limite não pode ser anterior à data de início.")
    dados = {
        "titulo": f.texto("titulo", "Título da meta", obrigatorio=True, max_len=160),
        "descricao": f.texto("descricao", "Descrição"),
        "materia": f.chave("materia_id", "Matéria", Materia, obrigatorio=False),
        "tipo": tipo,
        "valor_desejado": f.decimal("valor_desejado", "Valor desejado", obrigatorio=True,
                                    minimo=0.01, maximo=1000000),
        "data_inicio": inicio,
        "data_limite": limite,
    }
    progresso = None
    if tipo == "manual":
        progresso = f.decimal("progresso_atual", "Progresso atual", minimo=0,
                              maximo=1000000, padrao=0)
    return f, dados, progresso


def _aplicar(meta, dados, progresso):
    for campo, valor in dados.items():
        setattr(meta, campo, valor)
    if dados["tipo"] == "manual":
        meta.progresso_atual = progresso or 0
    services.atualizar_meta(meta)


@bp.route("/")
def listar():
    services.atualizar_metas()  # recalcula progresso e status antes de exibir
    status = request.args.get("status", "")
    materia_id = request.args.get("materia", type=int)

    consulta = select(Meta)
    if status in CH.STATUS_META:
        consulta = consulta.where(Meta.status == status)
    if materia_id:
        consulta = consulta.where(Meta.materia_id == materia_id)

    contagem = dict(db.session.execute(
        select(Meta.status, func.count(Meta.id)).group_by(Meta.status)).all())
    materias = db.session.scalars(select(Materia).order_by(Materia.nome)).all()
    pag = paginar(consulta.order_by(ORDEM_STATUS, Meta.data_limite, Meta.id))
    return render_template("metas/lista.html", pag=pag, status=status, materia_id=materia_id,
                           materias=materias, contagem=contagem, hoje=hoje(),
                           em_30_dias=hoje() + timedelta(days=30))


@bp.post("/nova")
def criar():
    f, dados, progresso = _ler_formulario()
    if not f.valido:
        flash_erros(f)
    else:
        meta = Meta()
        _aplicar(meta, dados, progresso)
        db.session.add(meta)
        confirmar(f"Meta “{meta.titulo}” criada.")
    return redirecionar_para("metas.listar")


@bp.post("/<int:id>/editar")
def editar(id):
    meta = obter_ou_404(Meta, id)
    f, dados, progresso = _ler_formulario()
    if not f.valido:
        flash_erros(f)
    else:
        _aplicar(meta, dados, progresso)
        confirmar(f"Meta “{meta.titulo}” atualizada.")
    return redirecionar_para("metas.listar")


@bp.post("/<int:id>/excluir")
def excluir(id):
    meta = obter_ou_404(Meta, id)
    titulo = meta.titulo
    db.session.delete(meta)
    confirmar(f"Meta “{titulo}” excluída.")
    return redirecionar_para("metas.listar")
