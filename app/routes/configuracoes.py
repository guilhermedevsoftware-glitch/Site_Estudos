import importlib.metadata as metadados
import os
import sys

from flask import Blueprint, current_app, render_template
from sqlalchemy import func, select

from .. import choices as CH
from ..extensions import db
from ..models import (Anotacao, Atividade, Configuracao, Conteudo, Flashcard, Materia, Meta,
                      SessaoEstudo, Tarefa)
from ..utils import Formulario, confirmar, flash_erros, redirecionar_para

bp = Blueprint("configuracoes", __name__, url_prefix="/configuracoes")

TABELAS = [("Matérias", Materia), ("Conteúdos", Conteudo), ("Atividades planejadas", Atividade),
           ("Tarefas", Tarefa), ("Sessões de estudo", SessaoEstudo), ("Metas", Meta),
           ("Anotações", Anotacao), ("Flashcards", Flashcard)]


def _versao(pacote):
    try:
        return metadados.version(pacote)
    except metadados.PackageNotFoundError:
        return "—"


def _info_sistema():
    arquivo = current_app.config.get("BANCO_ARQUIVO", "")
    tamanho = os.path.getsize(arquivo) if arquivo and os.path.exists(arquivo) else 0
    return {
        "versao": current_app.config.get("VERSAO", ""),
        "python": sys.version.split()[0],
        "flask": _versao("Flask"),
        "flask_sqlalchemy": _versao("Flask-SQLAlchemy"),
        "sqlalchemy": _versao("SQLAlchemy"),
        "banco": arquivo,
        "tamanho_kb": round(tamanho / 1024, 1),
        "contagens": [(nome, db.session.scalar(select(func.count()).select_from(modelo)) or 0)
                      for nome, modelo in TABELAS],
    }


@bp.route("/")
def index():
    return render_template("configuracoes/index.html", info=_info_sistema())


@bp.post("/salvar")
def salvar():
    f = Formulario()
    diaria = f.decimal("meta_diaria_horas", "Meta diária", obrigatorio=True, minimo=0.1, maximo=24)
    semanal = f.decimal("meta_semanal_horas", "Meta semanal", obrigatorio=True, minimo=0.1, maximo=168)
    foco = f.inteiro("pomodoro_foco", "Foco", obrigatorio=True, minimo=1, maximo=180)
    pausa = f.inteiro("pomodoro_pausa", "Descanso curto", obrigatorio=True, minimo=1, maximo=60)
    longa = f.inteiro("pomodoro_pausa_longa", "Descanso longo", obrigatorio=True, minimo=1, maximo=120)
    ciclos = f.inteiro("pomodoro_ciclos", "Focos até o descanso longo", obrigatorio=True,
                       minimo=2, maximo=10)
    itens = f.escolha("itens_por_pagina", "Itens por página", ["5", "10", "20", "50"])
    tema = f.escolha("tema", "Tema", ["claro", "escuro"])
    if diaria is not None and semanal is not None and semanal < diaria:
        f.erros.append("A meta semanal não pode ser menor que a meta diária.")
    if not f.valido:
        flash_erros(f)
        return redirecionar_para("configuracoes.index")

    Configuracao.definir({
        "meta_diaria_horas": f"{diaria:g}", "meta_semanal_horas": f"{semanal:g}",
        "pomodoro_foco": foco, "pomodoro_pausa": pausa, "pomodoro_pausa_longa": longa,
        "pomodoro_ciclos": ciclos, "itens_por_pagina": itens, "tema": tema,
        "menu_recolhido": "1" if f.dados.get("menu_recolhido") else "0",
    })
    confirmar("Configurações salvas.")
    return redirecionar_para("configuracoes.index")
