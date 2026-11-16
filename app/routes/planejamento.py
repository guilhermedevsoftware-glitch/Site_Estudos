from datetime import timedelta

from flask import Blueprint, flash, jsonify, render_template, request
from sqlalchemy import select

from .. import choices as CH
from ..extensions import db
from ..models import Atividade, Materia
from ..utils import (Formulario, confirmar, dados_json, json_erro, obter_ou_404,
                     redirecionar_para)

bp = Blueprint("planejamento", __name__, url_prefix="/planejamento")


@bp.route("/")
def index():
    materias = db.session.scalars(select(Materia).order_by(Materia.nome)).all()
    return render_template("planejamento/calendario.html", materias=materias)


def _validar(dados):
    """Valida os campos de uma atividade (JSON ou formulário). Devolve (f, valores)."""
    f = Formulario(dados)
    valores = {
        "titulo": f.texto("titulo", "Título", obrigatorio=True, max_len=160),
        "descricao": f.texto("descricao", "Descrição"),
        "status": f.escolha("status", "Status", CH.STATUS_ATIVIDADE, obrigatorio=False,
                            padrao="Planejada"),
    }
    materia = f.chave("materia_id", "Matéria", Materia)
    inicio = f.data_hora("inicio", "Início", obrigatorio=True)
    fim = f.data_hora("fim", "Término", obrigatorio=True)
    if inicio and fim:
        if fim <= inicio:
            f.erros.append("O término deve ser depois do início.")
        elif fim.date() != inicio.date():
            f.erros.append("A atividade deve começar e terminar no mesmo dia.")
    valores.update(materia=materia, inicio=inicio, fim=fim)
    return f, valores


def _filtrar_intervalo():
    f = Formulario(request.args)
    ini = f.data_hora("inicio", "Início", obrigatorio=True)
    fim = f.data_hora("fim", "Fim", obrigatorio=True)
    return f, ini, fim


@bp.get("/api/atividades")
def api_listar():
    f, ini, fim = _filtrar_intervalo()
    if not f.valido:
        return json_erro("Intervalo inválido.", erros=f.erros)
    consulta = select(Atividade).where(Atividade.inicio < fim, Atividade.fim > ini)
    materia_id = request.args.get("materia_id", type=int)
    if materia_id:
        consulta = consulta.where(Atividade.materia_id == materia_id)
    atividades = db.session.scalars(consulta.order_by(Atividade.inicio)).all()
    return jsonify([a.para_dict() for a in atividades])


@bp.post("/api/atividades")
def api_criar():
    f, v = _validar(dados_json())
    if not f.valido:
        return json_erro("Verifique os dados informados.", erros=f.erros)
    atividade = Atividade(**v)
    db.session.add(atividade)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return json_erro("Não foi possível salvar a atividade.", 500)
    return jsonify({"ok": True, "mensagem": "Atividade criada.",
                    "atividade": atividade.para_dict()}), 201


@bp.put("/api/atividades/<int:id>")
def api_editar(id):
    atividade = obter_ou_404(Atividade, id)
    f, v = _validar(dados_json())
    if not f.valido:
        return json_erro("Verifique os dados informados.", erros=f.erros)
    for campo, valor in v.items():
        setattr(atividade, campo, valor)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return json_erro("Não foi possível atualizar a atividade.", 500)
    return jsonify({"ok": True, "mensagem": "Atividade atualizada.",
                    "atividade": atividade.para_dict()})


@bp.patch("/api/atividades/<int:id>/mover")
def api_mover(id):
    """Reorganiza a atividade (arrastar/redimensionar): só início e término."""
    atividade = obter_ou_404(Atividade, id)
    f = Formulario(dados_json())
    inicio = f.data_hora("inicio", "Início", obrigatorio=True)
    fim = f.data_hora("fim", "Término", obrigatorio=True)
    if inicio and fim:
        if fim <= inicio:
            f.erros.append("O término deve ser depois do início.")
        elif fim.date() != inicio.date():
            f.erros.append("A atividade deve começar e terminar no mesmo dia.")
    if not f.valido:
        return json_erro("Não foi possível mover a atividade.", erros=f.erros)
    atividade.inicio, atividade.fim = inicio, fim
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return json_erro("Não foi possível mover a atividade.", 500)
    return jsonify({"ok": True, "atividade": atividade.para_dict()})


@bp.delete("/api/atividades/<int:id>")
def api_excluir(id):
    atividade = obter_ou_404(Atividade, id)
    db.session.delete(atividade)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return json_erro("Não foi possível excluir a atividade.", 500)
    return jsonify({"ok": True, "mensagem": "Atividade excluída."})


@bp.post("/atividades/<int:id>/concluir")
def alternar_conclusao(id):
    """Atalho do dashboard: alterna entre Planejada e Concluída."""
    atividade = obter_ou_404(Atividade, id)
    atividade.status = "Planejada" if atividade.status == "Concluída" else "Concluída"
    confirmar("Atividade marcada como concluída." if atividade.status == "Concluída"
              else "Atividade reaberta.")
    return redirecionar_para("dashboard.index")
