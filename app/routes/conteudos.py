from flask import Blueprint, jsonify, render_template

from .. import choices as CH
from ..extensions import db
from ..models import Conteudo, Materia
from ..utils import (Formulario, confirmar, dados_json, flash_erros, hoje, json_erro,
                     obter_ou_404, quer_json, redirecionar_para)

bp = Blueprint("conteudos", __name__, url_prefix="/conteudos")


def _aplicar_status(conteudo, status, data_conclusao=None):
    """Mantém a data de conclusão coerente com o status."""
    conteudo.status = status
    if status == "Concluído":
        conteudo.data_conclusao = data_conclusao or conteudo.data_conclusao or hoje()
    else:
        conteudo.data_conclusao = None


def _posicionar(materia, conteudo, posicao):
    """Insere `conteudo` na posição desejada e renumera toda a sequência (1..n)."""
    outros = [c for c in materia.conteudos if c is not conteudo]
    limite = len(outros) + 1
    posicao = limite if not posicao else max(1, min(int(posicao), limite))
    outros.insert(posicao - 1, conteudo)
    for numero, item in enumerate(outros, start=1):
        item.ordem = numero


def _ler_formulario():
    f = Formulario()
    dados = {
        "nome": f.texto("nome", "Nome do conteúdo", obrigatorio=True, max_len=160),
        "descricao": f.texto("descricao", "Descrição"),
        "ordem": f.inteiro("ordem", "Ordem de estudo", minimo=1, maximo=10000),
        "tempo_estimado": f.inteiro("tempo_estimado", "Tempo estimado (min)",
                                    minimo=0, maximo=100000, padrao=0),
        "status": f.escolha("status", "Status", CH.STATUS_CONTEUDO),
        "data_conclusao": f.data("data_conclusao", "Data de conclusão"),
    }
    return f, dados


@bp.route("/materia/<int:materia_id>")
def listar(materia_id):
    materia = obter_ou_404(Materia, materia_id)
    concluidos = sum(1 for c in materia.conteudos if c.status == "Concluído")
    tempo_total = sum(c.tempo_estimado or 0 for c in materia.conteudos)
    return render_template("conteudos/lista.html", materia=materia, concluidos=concluidos,
                           tempo_total=tempo_total, hoje=hoje())


@bp.post("/materia/<int:materia_id>/novo")
def criar(materia_id):
    materia = obter_ou_404(Materia, materia_id)
    f, dados = _ler_formulario()
    if not f.valido:
        flash_erros(f)
        return redirecionar_para("conteudos.listar", materia_id=materia.id)
    posicao = dados.pop("ordem")
    conteudo = Conteudo(materia=materia, ordem=len(materia.conteudos) + 1, **{
        k: v for k, v in dados.items() if k not in ("status", "data_conclusao")})
    _aplicar_status(conteudo, dados["status"], dados["data_conclusao"])
    _posicionar(materia, conteudo, posicao)
    confirmar(f"Conteúdo “{conteudo.nome}” adicionado.")
    return redirecionar_para("conteudos.listar", materia_id=materia.id)


@bp.post("/<int:id>/editar")
def editar(id):
    conteudo = obter_ou_404(Conteudo, id)
    f, dados = _ler_formulario()
    if not f.valido:
        flash_erros(f)
        return redirecionar_para("conteudos.listar", materia_id=conteudo.materia_id)
    posicao = dados.pop("ordem")
    conteudo.nome = dados["nome"]
    conteudo.descricao = dados["descricao"]
    conteudo.tempo_estimado = dados["tempo_estimado"]
    _aplicar_status(conteudo, dados["status"], dados["data_conclusao"])
    _posicionar(conteudo.materia, conteudo, posicao or conteudo.ordem)
    confirmar(f"Conteúdo “{conteudo.nome}” atualizado.")
    return redirecionar_para("conteudos.listar", materia_id=conteudo.materia_id)


@bp.post("/<int:id>/status")
def alterar_status(id):
    """Troca rápida de status pela lista."""
    conteudo = obter_ou_404(Conteudo, id)
    f = Formulario()
    status = f.escolha("status", "Status", CH.STATUS_CONTEUDO)
    if not f.valido:
        flash_erros(f)
    else:
        _aplicar_status(conteudo, status)
        confirmar(f"Status de “{conteudo.nome}” alterado para {status}.")
    return redirecionar_para("conteudos.listar", materia_id=conteudo.materia_id)


@bp.post("/<int:id>/excluir")
def excluir(id):
    conteudo = obter_ou_404(Conteudo, id)
    materia = conteudo.materia
    nome = conteudo.nome
    materia.conteudos.remove(conteudo)  # delete-orphan exclui o registro
    db.session.flush()
    for numero, item in enumerate(materia.conteudos, start=1):  # mantém a sequência 1..n
        item.ordem = numero
    confirmar(f"Conteúdo “{nome}” excluído. Tarefas e sessões ligadas a ele foram mantidas.")
    return redirecionar_para("conteudos.listar", materia_id=materia.id)


@bp.post("/materia/<int:materia_id>/reordenar")
def reordenar(materia_id):
    """Recebe {"ids": [3, 1, 2]} (arrastar e soltar) e grava a nova sequência."""
    materia = obter_ou_404(Materia, materia_id)
    ids = dados_json().get("ids")
    atuais = {c.id: c for c in materia.conteudos}
    if (not isinstance(ids, list) or len(ids) != len(atuais)
            or set(ids) != set(atuais)):
        return json_erro("Lista de conteúdos inválida. Recarregue a página.")
    for numero, id_ in enumerate(ids, start=1):
        atuais[id_].ordem = numero
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return json_erro("Não foi possível salvar a nova ordem.", 500)
    return jsonify({"ok": True})
