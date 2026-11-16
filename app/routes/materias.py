from flask import Blueprint, render_template, request
from sqlalchemy import func, select

from .. import choices as CH
from .. import services
from ..extensions import db
from ..models import Materia
from ..utils import (Formulario, confirmar, flash_erros, hoje, obter_ou_404, paginar,
                     redirecionar_para)

bp = Blueprint("materias", __name__, url_prefix="/materias")


def _ler_formulario(materia_id=None):
    f = Formulario()
    dados = {
        "nome": f.texto("nome", "Nome da matéria", obrigatorio=True, max_len=120),
        "descricao": f.texto("descricao", "Descrição"),
        "categoria": f.escolha("categoria", "Categoria", CH.CATEGORIAS),
        "nivel": f.escolha("nivel", "Nível de conhecimento", CH.NIVEIS),
        "data_inicio": f.data("data_inicio", "Data de início", padrao=hoje()),
        "objetivo": f.texto("objetivo", "Objetivo de aprendizagem"),
        "carga_horaria": f.decimal("carga_horaria", "Carga horária planejada",
                                   minimo=0, maximo=100000, padrao=0),
        "status": f.escolha("status", "Status", CH.STATUS_MATERIA),
    }
    if dados["nome"]:
        duplicada = db.session.scalar(
            select(Materia.id).where(func.lower(Materia.nome) == dados["nome"].lower(),
                                     Materia.id != (materia_id or 0)))
        if duplicada:
            f.erros.append("Já existe uma matéria com esse nome.")
    return f, dados


@bp.route("/")
def listar():
    busca = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "")
    status = request.args.get("status", "")

    consulta = select(Materia)
    if busca:
        consulta = consulta.where(Materia.nome.ilike(f"%{busca}%"))
    if categoria in CH.CATEGORIAS:
        consulta = consulta.where(Materia.categoria == categoria)
    if status in CH.STATUS_MATERIA:
        consulta = consulta.where(Materia.status == status)

    pag = paginar(consulta.order_by(Materia.nome))
    ids = [m.id for m in pag.items]
    return render_template(
        "materias/lista.html", pag=pag, busca=busca, categoria=categoria, status=status,
        minutos=services.minutos_por_materia_ids(ids), conteudos=services.resumo_conteudos(ids),
        hoje=hoje())


@bp.post("/nova")
def criar():
    f, dados = _ler_formulario()
    if not f.valido:
        flash_erros(f)
    else:
        db.session.add(Materia(**dados))
        confirmar(f"Matéria “{dados['nome']}” cadastrada com sucesso.")
    return redirecionar_para("materias.listar")


@bp.post("/<int:id>/editar")
def editar(id):
    materia = obter_ou_404(Materia, id)
    f, dados = _ler_formulario(materia.id)
    if not f.valido:
        flash_erros(f)
    else:
        for campo, valor in dados.items():
            setattr(materia, campo, valor)
        confirmar(f"Matéria “{materia.nome}” atualizada.")
    return redirecionar_para("materias.listar")


@bp.post("/<int:id>/excluir")
def excluir(id):
    materia = obter_ou_404(Materia, id)
    nome = materia.nome
    db.session.delete(materia)  # cascata: conteúdos, atividades, tarefas, sessões, notas, cartões
    confirmar(f"Matéria “{nome}” excluída junto com seus conteúdos, tarefas, sessões, "
              f"anotações e flashcards.")
    return redirecionar_para("materias.listar")
