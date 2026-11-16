from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import func, select

from .. import choices as CH
from ..extensions import db
from ..models import Flashcard, Materia
from ..utils import (Formulario, confirmar, dados_json, flash_erros, json_erro, obter_ou_404,
                     paginar, redirecionar_para)

bp = Blueprint("flashcards", __name__, url_prefix="/flashcards")

LIMITE_ESTUDO = 500


def _ler_formulario():
    f = Formulario()
    dados = {
        "materia": f.chave("materia_id", "Matéria", Materia),
        "pergunta": f.texto("pergunta", "Pergunta", obrigatorio=True),
        "resposta": f.texto("resposta", "Resposta", obrigatorio=True),
    }
    return f, dados


@bp.route("/")
def index():
    aba = "cartoes" if request.args.get("aba") == "cartoes" else "estudar"
    materia_id = request.args.get("materia", type=int)
    dificuldade = request.args.get("dificuldade", "")

    consulta = select(Flashcard).join(Materia)
    if materia_id:
        consulta = consulta.where(Flashcard.materia_id == materia_id)
    if dificuldade in CH.DIFICULDADES:
        consulta = consulta.where(Flashcard.dificuldade == dificuldade)
    consulta = consulta.order_by(Materia.nome, Flashcard.id)

    materias = db.session.scalars(select(Materia).order_by(Materia.nome)).all()
    por_materia = dict(db.session.execute(
        select(Flashcard.materia_id, func.count(Flashcard.id)).group_by(Flashcard.materia_id)).all())

    contexto = dict(aba=aba, materia_id=materia_id, dificuldade=dificuldade, materias=materias,
                    por_materia=por_materia, total=sum(por_materia.values()),
                    pag=None, cartoes=[])
    if aba == "cartoes":
        contexto["pag"] = paginar(consulta)
    else:
        contexto["cartoes"] = [c.para_dict() for c in
                               db.session.scalars(consulta.limit(LIMITE_ESTUDO))]
    return render_template("flashcards/index.html", **contexto)


@bp.post("/novo")
def criar():
    f, dados = _ler_formulario()
    if not f.valido:
        flash_erros(f)
    else:
        db.session.add(Flashcard(**dados))
        confirmar("Flashcard criado.")
    return redirecionar_para("flashcards.index")


@bp.post("/<int:id>/editar")
def editar(id):
    cartao = obter_ou_404(Flashcard, id)
    f, dados = _ler_formulario()
    if not f.valido:
        flash_erros(f)
    else:
        for campo, valor in dados.items():
            setattr(cartao, campo, valor)
        confirmar("Flashcard atualizado.")
    return redirecionar_para("flashcards.index")


@bp.post("/<int:id>/excluir")
def excluir(id):
    cartao = obter_ou_404(Flashcard, id)
    db.session.delete(cartao)
    confirmar("Flashcard excluído.")
    return redirecionar_para("flashcards.index")


@bp.post("/<int:id>/avaliar")
def avaliar(id):
    """Marca o cartão como Fácil, Médio ou Difícil (modo de estudo, via JavaScript)."""
    cartao = obter_ou_404(Flashcard, id)
    f = Formulario(dados_json())
    dificuldade = f.escolha("dificuldade", "Dificuldade", CH.DIFICULDADES_AVALIACAO)
    if not f.valido:
        return json_erro("Dificuldade inválida.", erros=f.erros)
    cartao.dificuldade = dificuldade
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return json_erro("Não foi possível salvar a avaliação.", 500)
    return jsonify({"ok": True, "dificuldade": dificuldade})
