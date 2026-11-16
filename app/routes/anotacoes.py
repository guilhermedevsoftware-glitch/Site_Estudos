from flask import Blueprint, render_template, request
from sqlalchemy import or_, select

from ..extensions import db
from ..models import Anotacao, Materia
from ..utils import (Formulario, confirmar, flash_erros, obter_ou_404, paginar,
                     redirecionar_para)

bp = Blueprint("anotacoes", __name__, url_prefix="/anotacoes")


def _ler_formulario():
    f = Formulario()
    dados = {
        "titulo": f.texto("titulo", "Título", obrigatorio=True, max_len=160),
        "materia": f.chave("materia_id", "Matéria", Materia, obrigatorio=False),
        "conteudo": f.texto("conteudo", "Conteúdo da anotação", obrigatorio=True),
    }
    return f, dados


@bp.route("/")
def listar():
    busca = request.args.get("q", "").strip()
    materia_id = request.args.get("materia", type=int)
    consulta = select(Anotacao)
    if busca:
        termo = f"%{busca}%"
        consulta = consulta.where(or_(Anotacao.titulo.ilike(termo), Anotacao.conteudo.ilike(termo)))
    if materia_id:
        consulta = consulta.where(Anotacao.materia_id == materia_id)
    pag = paginar(consulta.order_by(Anotacao.atualizada_em.desc(), Anotacao.id.desc()))
    materias = db.session.scalars(select(Materia).order_by(Materia.nome)).all()
    return render_template("anotacoes/lista.html", pag=pag, busca=busca,
                           materia_id=materia_id, materias=materias)


@bp.post("/nova")
def criar():
    f, dados = _ler_formulario()
    if not f.valido:
        flash_erros(f)
    else:
        db.session.add(Anotacao(**dados))
        confirmar(f"Anotação “{dados['titulo']}” criada.")
    return redirecionar_para("anotacoes.listar")


@bp.post("/<int:id>/editar")
def editar(id):
    nota = obter_ou_404(Anotacao, id)
    f, dados = _ler_formulario()
    if not f.valido:
        flash_erros(f)
    else:
        for campo, valor in dados.items():
            setattr(nota, campo, valor)
        confirmar(f"Anotação “{nota.titulo}” atualizada.")
    return redirecionar_para("anotacoes.listar")


@bp.post("/<int:id>/excluir")
def excluir(id):
    nota = obter_ou_404(Anotacao, id)
    titulo = nota.titulo
    db.session.delete(nota)
    confirmar(f"Anotação “{titulo}” excluída.")
    return redirecionar_para("anotacoes.listar")
