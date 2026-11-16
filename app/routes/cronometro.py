from datetime import timedelta

from flask import Blueprint, flash, jsonify, render_template, request
from sqlalchemy import select

from ..extensions import db
from ..models import Conteudo, Configuracao, Materia, SessaoEstudo
from ..utils import (Formulario, agora, confirmar, dados_json, flash_erros, hoje, json_erro,
                     obter_ou_404, paginar, redirecionar_para)

bp = Blueprint("cronometro", __name__, url_prefix="/cronometro")


@bp.route("/")
def index():
    materias = db.session.scalars(select(Materia).order_by(Materia.nome)).all()
    pag = paginar(select(SessaoEstudo).order_by(SessaoEstudo.inicio.desc()))
    return render_template(
        "cronometro/index.html", materias=materias, pag=pag, hoje=hoje(),
        materia_inicial=request.args.get("materia", type=int),
        conteudo_inicial=request.args.get("conteudo", type=int))


def _validar_sessao(dados, exigir_inicio_fim=True):
    """Valida os dados de uma sessão (JSON do cronômetro ou formulário manual)."""
    f = Formulario(dados)
    materia = f.chave("materia_id", "Matéria", Materia)
    conteudo = f.chave("conteudo_id", "Conteúdo", Conteudo, obrigatorio=False)
    if materia and conteudo and conteudo.materia_id != materia.id:
        f.erros.append("O conteúdo escolhido não pertence à matéria selecionada.")
    duracao = f.inteiro("duracao_min", "Duração", obrigatorio=True, minimo=1, maximo=1440)
    inicio = f.data_hora("inicio", "Início", obrigatorio=exigir_inicio_fim)
    fim = f.data_hora("fim", "Término", obrigatorio=exigir_inicio_fim)
    if inicio and fim and fim < inicio:
        f.erros.append("O término não pode ser anterior ao início.")
    if fim and fim > agora() + timedelta(minutes=5):
        f.erros.append("O término não pode estar no futuro.")
    observacoes = f.texto("observacoes", "Observações")
    return f, dict(materia=materia, conteudo=conteudo, duracao_min=duracao, inicio=inicio,
                   fim=fim, observacoes=observacoes)


@bp.post("/sessoes")
def salvar_sessao():
    """Chamado pelo cronômetro ao finalizar: grava a sessão automaticamente."""
    f, v = _validar_sessao(dados_json())
    if not f.valido:
        return json_erro("Não foi possível salvar a sessão.", erros=f.erros)
    sessao = SessaoEstudo(data=v["inicio"].date(), **v)
    db.session.add(sessao)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return json_erro("Não foi possível salvar a sessão.", 500)
    flash(f"Sessão salva: {sessao.duracao_min} min de {sessao.materia.nome}.", "success")
    return jsonify({"ok": True, "id": sessao.id}), 201


def _ler_manual():
    """Registro/edição manual (formulário): data + hora de início e de término."""
    f = Formulario()
    dia = f.data("data", "Data", obrigatorio=True)
    h_ini = f.hora("hora_inicio", "Horário de início", obrigatorio=True)
    h_fim = f.hora("hora_fim", "Horário de término", obrigatorio=True)
    dados = {}
    if dia and h_ini and h_fim:
        from datetime import datetime
        dados["inicio"] = datetime.combine(dia, h_ini).replace(microsecond=0)
        dados["fim"] = datetime.combine(dia, h_fim).replace(microsecond=0)
        if dados["fim"] <= dados["inicio"]:
            f.erros.append("O horário de término deve ser depois do início.")
        dados["duracao_min"] = f.inteiro("duracao_min", "Duração (min)", minimo=1, maximo=1440,
                                         padrao=max(1, int((dados["fim"] - dados["inicio"])
                                                           .total_seconds() // 60)))
    materia = f.chave("materia_id", "Matéria", Materia)
    conteudo = f.chave("conteudo_id", "Conteúdo", Conteudo, obrigatorio=False)
    if materia and conteudo and conteudo.materia_id != materia.id:
        f.erros.append("O conteúdo escolhido não pertence à matéria selecionada.")
    if dados.get("fim") and dados["fim"] > agora() + timedelta(minutes=5):
        f.erros.append("O término não pode estar no futuro.")
    dados.update(materia=materia, conteudo=conteudo, observacoes=f.texto("observacoes", "Observações"))
    return f, dados


@bp.post("/sessoes/nova")
def criar_manual():
    f, dados = _ler_manual()
    if not f.valido:
        flash_erros(f)
    else:
        db.session.add(SessaoEstudo(data=dados["inicio"].date(), **dados))
        confirmar("Sessão registrada manualmente.")
    return redirecionar_para("cronometro.index")


@bp.post("/sessoes/<int:id>/editar")
def editar_sessao(id):
    sessao = obter_ou_404(SessaoEstudo, id)
    f, dados = _ler_manual()
    if not f.valido:
        flash_erros(f)
    else:
        for campo, valor in dados.items():
            setattr(sessao, campo, valor)
        sessao.data = dados["inicio"].date()
        confirmar("Sessão atualizada.")
    return redirecionar_para("cronometro.index")


@bp.post("/sessoes/<int:id>/excluir")
def excluir_sessao(id):
    sessao = obter_ou_404(SessaoEstudo, id)
    db.session.delete(sessao)
    confirmar("Sessão excluída.")
    return redirecionar_para("cronometro.index")


@bp.post("/intervalos")
def salvar_intervalos():
    """Personaliza os intervalos do Pomodoro (chamado por JavaScript)."""
    f = Formulario(dados_json())
    foco = f.inteiro("foco", "Foco", obrigatorio=True, minimo=1, maximo=180)
    pausa = f.inteiro("pausa", "Descanso curto", obrigatorio=True, minimo=1, maximo=60)
    longa = f.inteiro("longa", "Descanso longo", obrigatorio=True, minimo=1, maximo=120)
    ciclos = f.inteiro("ciclos", "Ciclos até a pausa longa", obrigatorio=True, minimo=2, maximo=10)
    if not f.valido:
        return json_erro("Intervalos inválidos.", erros=f.erros)
    Configuracao.definir({"pomodoro_foco": foco, "pomodoro_pausa": pausa,
                          "pomodoro_pausa_longa": longa, "pomodoro_ciclos": ciclos})
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return json_erro("Não foi possível salvar os intervalos.", 500)
    return jsonify({"ok": True, "pomodoro": {"foco": foco, "pausa": pausa,
                                              "longa": longa, "ciclos": ciclos}})
