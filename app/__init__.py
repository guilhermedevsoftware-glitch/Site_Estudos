"""Application factory do StudyFlow."""
import hmac
import secrets
import sys

import flask
from flask import Flask, abort, jsonify, render_template, request, session, url_for

from . import choices
from .extensions import db
from config import INSTANCE_DIR, Config


# ------------------------------------------------------------------ CSRF
def _registrar_csrf(app):
    def gerar_token():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(32)
        return session["_csrf"]

    @app.before_request
    def validar_csrf():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            esperado = session.get("_csrf")
            enviado = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
            if not esperado or not enviado or not hmac.compare_digest(esperado, enviado):
                abort(400, description="Sessão expirada ou token CSRF inválido. "
                                       "Recarregue a página e tente novamente.")

    app.jinja_env.globals["csrf_token"] = gerar_token


# ---------------------------------------------------------- filtros Jinja
def _formatar_duracao(minutos):
    minutos = int(round(minutos or 0))
    h, m = divmod(minutos, 60)
    if h and m:
        return f"{h}h {m:02d}min"
    if h:
        return f"{h}h"
    return f"{m}min"


def _registrar_jinja(app):
    from .models import Configuracao
    from .utils import conteudos_por_materia

    filtros = app.jinja_env.filters
    filtros["duracao"] = _formatar_duracao
    filtros["data_br"] = lambda d: d.strftime("%d/%m/%Y") if d else "—"
    filtros["datahora_br"] = lambda d: d.strftime("%d/%m/%Y %H:%M") if d else "—"
    filtros["hora"] = lambda d: d.strftime("%H:%M") if d else "—"
    filtros["numero"] = lambda n, casas=1: f"{n:.{casas}f}".replace(".", ",")
    filtros["cor"] = lambda rotulo: choices.CORES.get(rotulo, "secondary")

    def url_pagina(pagina):
        args = request.args.to_dict()
        args["page"] = pagina
        return url_for(request.endpoint, **{**(request.view_args or {}), **args})

    app.jinja_env.globals.update(CH=choices, url_pagina=url_pagina,
                                 conteudos_map=conteudos_por_materia)

    @app.context_processor
    def contexto_global():
        try:
            cfg = Configuracao.todas()
        except Exception:  # banco indisponível: usa padrões e não derruba a página de erro
            cfg = dict(choices.CONFIG_PADRAO)
        pomodoro = {
            "foco": _inteiro(cfg["pomodoro_foco"], 25),
            "pausa": _inteiro(cfg["pomodoro_pausa"], 5),
            "longa": _inteiro(cfg["pomodoro_pausa_longa"], 15),
            "ciclos": _inteiro(cfg["pomodoro_ciclos"], 4),
        }
        return {"cfg": cfg, "pomodoro": pomodoro}


def _inteiro(valor, padrao):
    try:
        return max(1, int(valor))
    except (TypeError, ValueError):
        return padrao


# ------------------------------------------------------------ blueprints
def _registrar_blueprints(app):
    from .routes import (anotacoes, auth, cronometro, configuracoes, conteudos, dashboard,
                         flashcards, materias, metas, planejamento, relatorios, tarefas)
    for modulo in (auth, dashboard, materias, conteudos, planejamento, tarefas, cronometro,
                   metas, relatorios, anotacoes, flashcards, configuracoes):
        app.register_blueprint(modulo.bp)


# ----------------------------------------------------------------- erros
def _registrar_erros(app):
    def responder(codigo, titulo, mensagem):
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "mensagem": mensagem, "erros": [mensagem]}), codigo
        return render_template("erro.html", codigo=codigo, titulo=titulo,
                               mensagem=mensagem), codigo

    @app.errorhandler(400)
    def erro_400(e):
        return responder(400, "Requisição inválida", getattr(e, "description", "") or
                         "Não foi possível processar a requisição.")

    @app.errorhandler(404)
    def erro_404(_e):
        return responder(404, "Página não encontrada",
                         "O endereço ou o registro que você procura não existe (talvez já tenha "
                         "sido excluído).")

    @app.errorhandler(413)
    def erro_413(_e):
        return responder(413, "Dados grandes demais", "O conteúdo enviado excede o limite permitido.")

    @app.errorhandler(500)
    def erro_500(_e):
        db.session.rollback()
        return responder(500, "Erro interno",
                         "Ocorreu um erro inesperado. Seus dados anteriores foram preservados.")


# --------------------------------------------------------------- factory
def create_app(config_class=Config):
    app = Flask(__name__, instance_path=INSTANCE_DIR)
    app.config.from_object(config_class)
    app.config["INFO_SISTEMA"] = {"python": sys.version.split()[0], "flask": flask.__version__}

    db.init_app(app)
    _registrar_csrf(app)
    from .security import registrar_auth   # após o CSRF: o token é validado antes do login
    registrar_auth(app)
    _registrar_jinja(app)
    _registrar_blueprints(app)
    _registrar_erros(app)

    with app.app_context():
        from . import models  # noqa: F401  (registra as tabelas)
        from .models import Configuracao
        db.create_all()
        Configuracao.garantir_padroes()

    return app
