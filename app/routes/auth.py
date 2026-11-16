"""Cadastro do primeiro acesso, login, recuperação de senha e página "Minha conta"."""
import hmac

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..extensions import db
from ..models import Usuario
from ..security import (QTD_CODIGOS, destino_seguro, encerrar_sessao, gerar_codigos,
                        iniciar_sessao, limpar_falhas, localizar_codigo, mensagem_bloqueio,
                        normalizar_codigo, registrar_falha, tentativas_restantes, usuario_atual,
                        usuario_unico, validar_login, validar_senha)
from ..utils import agora, confirmar

bp = Blueprint("auth", __name__)


def _campo(nome):
    return (request.form.get(nome) or "").strip()


def _igual(a, b):
    """Comparação em tempo constante (aceita acentos, ao contrário de compare_digest com str)."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _avisar_codigos(usuario):
    restantes = usuario.codigos_restantes
    if restantes == 0:
        flash("Você não tem mais códigos de recuperação. Gere novos em Minha conta.", "warning")
    elif restantes <= 2:
        flash(f"Restam apenas {restantes} código(s) de recuperação. "
              f"Gere novos em Minha conta.", "warning")


def _falha(usuario, mensagem):
    """Registra a tentativa errada e avisa quantas restam (ou o bloqueio)."""
    registrar_falha(usuario)
    if usuario.bloqueado:
        flash(mensagem_bloqueio(usuario), "danger")
    else:
        flash(f"{mensagem} Restam {tentativas_restantes(usuario)} tentativa(s).", "danger")


# ------------------------------------------------------------ cadastro
@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    """Só funciona enquanto não existe conta (primeiro acesso)."""
    if usuario_unico() is not None:
        return redirect(url_for("dashboard.index" if usuario_atual() else "auth.entrar"))

    nome = login = ""
    if request.method == "POST":
        nome, login = _campo("nome"), _campo("login").lower()
        senha = request.form.get("senha") or ""
        confirmacao = request.form.get("confirmacao") or ""
        erros = []
        if not 2 <= len(nome) <= 80:
            erros.append("Informe seu nome (de 2 a 80 caracteres).")
        erros += validar_login(login)
        erros += validar_senha(senha, login)
        if senha != confirmacao:
            erros.append("A confirmação não confere com a senha.")
        for erro in erros:
            flash(erro, "danger")
        if not erros:
            usuario = Usuario(nome=nome, login=login)
            usuario.definir_senha(senha)
            db.session.add(usuario)
            codigos = gerar_codigos(usuario)
            if confirmar():
                iniciar_sessao(usuario)
                db.session.commit()
                # Renderiza direto (sem redirecionar): os códigos só existem agora.
                return render_template("auth/codigos.html", codigos=codigos,
                                       primeiro_acesso=True, u=usuario)
    return render_template("auth/cadastro.html", nome=nome, login=login)


# --------------------------------------------------------------- login
@bp.route("/entrar", methods=["GET", "POST"])
def entrar():
    if usuario_atual() is not None:
        return redirect(url_for("dashboard.index"))
    usuario = usuario_unico()
    if usuario is None:
        return redirect(url_for("auth.cadastro"))

    proximo = destino_seguro(request.values.get("next", ""), "")
    login = ""
    if request.method == "POST":
        login = _campo("login").lower()
        senha = request.form.get("senha") or ""
        if usuario.bloqueado:
            flash(mensagem_bloqueio(usuario), "danger")
        elif not login or not senha:
            flash("Informe o usuário e a senha.", "danger")
        else:
            senha_ok = usuario.conferir_senha(senha)          # sempre confere (tempo constante)
            if senha_ok and _igual(login, usuario.login):
                limpar_falhas(usuario)
                iniciar_sessao(usuario, lembrar=bool(request.form.get("lembrar")))
                if confirmar():
                    flash(f"Bem-vindo(a) de volta, {usuario.nome}!", "success")
                    _avisar_codigos(usuario)
                    return redirect(destino_seguro(proximo, url_for("dashboard.index")))
                encerrar_sessao()
            else:
                _falha(usuario, "Usuário ou senha incorretos.")
    return render_template("auth/entrar.html", proximo=proximo, login=login)


@bp.post("/sair")
def sair():
    encerrar_sessao()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.entrar"))


# ------------------------------------------------------- recuperação
@bp.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    """Redefine a senha com o usuário + um código de recuperação (uso único)."""
    if usuario_atual() is not None:
        return redirect(url_for("auth.conta"))
    usuario = usuario_unico()
    if usuario is None:
        return redirect(url_for("auth.cadastro"))

    login = ""
    if request.method == "POST":
        login = _campo("login").lower()
        codigo = _campo("codigo")
        nova = request.form.get("nova_senha") or ""
        confirmacao = request.form.get("confirmacao") or ""
        if usuario.bloqueado:
            flash(mensagem_bloqueio(usuario), "danger")
        else:
            erros = []
            if not login:
                erros.append("Informe o usuário.")
            if not normalizar_codigo(codigo):
                erros.append("Informe um código de recuperação.")
            erros += validar_senha(nova, login)
            if nova != confirmacao:
                erros.append("A confirmação não confere com a nova senha.")
            for erro in erros:
                flash(erro, "danger")
            if not erros:
                registro = localizar_codigo(usuario, codigo)
                if registro is not None and _igual(login, usuario.login):
                    registro.usado_em = agora()
                    usuario.definir_senha(nova)          # também desconecta outras sessões
                    limpar_falhas(usuario)
                    if confirmar():
                        encerrar_sessao()
                        flash("Senha redefinida com sucesso. Entre com a nova senha.", "success")
                        _avisar_codigos(usuario)
                        return redirect(url_for("auth.entrar"))
                else:
                    _falha(usuario, "Usuário ou código de recuperação inválido.")
    return render_template("auth/recuperar.html", login=login)


# --------------------------------------------------------- minha conta
@bp.get("/conta")
def conta():
    return render_template("auth/conta.html", u=usuario_atual(), total_codigos=QTD_CODIGOS)


@bp.post("/conta/perfil")
def alterar_perfil():
    usuario = usuario_atual()
    nome = _campo("nome")
    if not 2 <= len(nome) <= 80:
        flash("Informe seu nome (de 2 a 80 caracteres).", "danger")
    else:
        usuario.nome = nome
        confirmar("Nome atualizado.")
    return redirect(url_for("auth.conta"))


@bp.post("/conta/senha")
def alterar_senha():
    usuario = usuario_atual()
    atual = request.form.get("senha_atual") or ""
    nova = request.form.get("nova_senha") or ""
    confirmacao = request.form.get("confirmacao") or ""
    if usuario.bloqueado:
        flash(mensagem_bloqueio(usuario), "danger")
    elif not usuario.conferir_senha(atual):
        _falha(usuario, "Senha atual incorreta.")
    else:
        erros = validar_senha(nova, usuario.login)
        if nova != confirmacao:
            erros.append("A confirmação não confere com a nova senha.")
        if nova == atual:
            erros.append("A nova senha deve ser diferente da atual.")
        for erro in erros:
            flash(erro, "danger")
        if not erros:
            usuario.definir_senha(nova)
            limpar_falhas(usuario)
            if confirmar("Senha alterada. Os outros dispositivos foram desconectados."):
                session["uv"] = usuario.versao_sessao      # mantém ESTA sessão ativa
    return redirect(url_for("auth.conta"))


@bp.post("/conta/codigos")
def novos_codigos():
    """Gera um novo conjunto de códigos (invalida os anteriores). Exige a senha atual."""
    usuario = usuario_atual()
    if usuario.bloqueado:
        flash(mensagem_bloqueio(usuario), "danger")
    elif not usuario.conferir_senha(request.form.get("senha_atual") or ""):
        _falha(usuario, "Senha incorreta.")
    else:
        limpar_falhas(usuario)
        codigos = gerar_codigos(usuario)
        if confirmar():
            return render_template("auth/codigos.html", codigos=codigos,
                                   primeiro_acesso=False, u=usuario)
    return redirect(url_for("auth.conta"))
