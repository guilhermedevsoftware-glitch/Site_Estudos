from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import case, or_, select

from .. import choices as CH
from ..extensions import db
from ..models import Conteudo, Materia, Tarefa
from ..utils import (Formulario, confirmar, dados_json, flash_erros, hoje, json_erro,
                     obter_ou_404, paginar, quer_json, redirecionar_para)

bp = Blueprint("tarefas", __name__, url_prefix="/tarefas")

ORDEM_PRIORIDADE = case({"Alta": 0, "Média": 1, "Baixa": 2}, value=Tarefa.prioridade, else_=3)


def _ler_formulario():
    f = Formulario()
    materia = f.chave("materia_id", "Matéria", Materia)
    conteudo = f.chave("conteudo_id", "Conteúdo", Conteudo, obrigatorio=False)
    if materia and conteudo and conteudo.materia_id != materia.id:
        f.erros.append("O conteúdo escolhido não pertence à matéria selecionada.")
    dados = {
        "titulo": f.texto("titulo", "Título", obrigatorio=True, max_len=160),
        "descricao": f.texto("descricao", "Descrição"),
        "materia": materia,
        "conteudo": conteudo,
        "prioridade": f.escolha("prioridade", "Prioridade", CH.PRIORIDADES),
        "prazo": f.data("prazo", "Prazo"),
        "tempo_estimado": f.inteiro("tempo_estimado", "Tempo estimado (min)",
                                    minimo=0, maximo=100000, padrao=0),
    }
    status = f.escolha("status", "Status", CH.STATUS_TAREFA, obrigatorio=False, padrao="A fazer")
    return f, dados, status


def _filtros():
    return {
        "q": request.args.get("q", "").strip(),
        "materia": request.args.get("materia", type=int),
        "prioridade": request.args.get("prioridade", ""),
        "status": request.args.get("status", ""),
    }


def _consulta(filtros, com_status=True):
    consulta = select(Tarefa)
    if filtros["q"]:
        termo = f"%{filtros['q']}%"
        consulta = consulta.where(or_(Tarefa.titulo.ilike(termo), Tarefa.descricao.ilike(termo)))
    if filtros["materia"]:
        consulta = consulta.where(Tarefa.materia_id == filtros["materia"])
    if filtros["prioridade"] in CH.PRIORIDADES:
        consulta = consulta.where(Tarefa.prioridade == filtros["prioridade"])
    if com_status and filtros["status"] in CH.STATUS_TAREFA:
        consulta = consulta.where(Tarefa.status == filtros["status"])
    return consulta


@bp.route("/")
def index():
    filtros = _filtros()
    visao = "lista" if request.args.get("visao") == "lista" else "quadro"
    materias = db.session.scalars(select(Materia).order_by(Materia.nome)).all()
    contexto = dict(filtros=filtros, visao=visao, materias=materias, hoje=hoje())

    if visao == "lista":
        consulta = _consulta(filtros).order_by(Tarefa.prazo.is_(None), Tarefa.prazo,
                                               ORDEM_PRIORIDADE, Tarefa.id)
        return render_template("tarefas/index.html", pag=paginar(consulta), colunas=None, **contexto)

    colunas = {}
    base = _consulta(filtros, com_status=False)
    for status in CH.STATUS_TAREFA:
        ordem = (Tarefa.concluida_em.desc(),) if status == "Concluída" else (
            Tarefa.prazo.is_(None), Tarefa.prazo, ORDEM_PRIORIDADE, Tarefa.id)
        colunas[status] = db.session.scalars(
            base.where(Tarefa.status == status).order_by(*ordem)).all()
    return render_template("tarefas/index.html", pag=None, colunas=colunas, **contexto)


def _aplicar(tarefa, dados, status):
    for campo, valor in dados.items():
        setattr(tarefa, campo, valor)
    tarefa.definir_status(status)


@bp.post("/nova")
def criar():
    f, dados, status = _ler_formulario()
    if not f.valido:
        flash_erros(f)
    else:
        tarefa = Tarefa()
        _aplicar(tarefa, dados, status)
        db.session.add(tarefa)
        confirmar(f"Tarefa “{tarefa.titulo}” criada.")
    return redirecionar_para("tarefas.index")


@bp.post("/<int:id>/editar")
def editar(id):
    tarefa = obter_ou_404(Tarefa, id)
    f, dados, status = _ler_formulario()
    if not f.valido:
        flash_erros(f)
    else:
        _aplicar(tarefa, dados, status)
        confirmar(f"Tarefa “{tarefa.titulo}” atualizada.")
    return redirecionar_para("tarefas.index")


@bp.post("/<int:id>/status")
def alterar_status(id):
    """Muda o status (arrastar e soltar no Kanban, menu "mover para" ou atalhos)."""
    tarefa = obter_ou_404(Tarefa, id)
    dados = dados_json() if request.is_json else request.form
    f = Formulario(dados)
    status = f.escolha("status", "Status", CH.STATUS_TAREFA)
    if not f.valido:
        if quer_json():
            return json_erro("Status inválido.", erros=f.erros)
        flash_erros(f)
        return redirecionar_para("tarefas.index")
    tarefa.definir_status(status)
    if quer_json():
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return json_erro("Não foi possível atualizar a tarefa.", 500)
        return jsonify({"ok": True, "status": tarefa.status})
    confirmar("Tarefa concluída. Bom trabalho!" if status == "Concluída"
              else f"Tarefa movida para “{status}”.")
    return redirecionar_para("tarefas.index")


@bp.post("/<int:id>/excluir")
def excluir(id):
    tarefa = obter_ou_404(Tarefa, id)
    titulo = tarefa.titulo
    db.session.delete(tarefa)
    confirmar(f"Tarefa “{titulo}” excluída.")
    return redirecionar_para("tarefas.index")
