"""Autenticação: senhas, códigos de recuperação, bloqueio por tentativas e sessão."""
import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from flask import flash, g, jsonify, redirect, request, session, url_for
from sqlalchemy import select

from .extensions import db
from .models import CodigoRecuperacao, Usuario
from .utils import agora

MAX_FALHAS = 5
BLOQUEIO_MINUTOS = 5
QTD_CODIGOS = 8
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # sem 0/O e 1/I, que se confundem
LOGIN_RE = re.compile(r"^[a-z0-9_.-]{3,30}$")

# Únicas rotas acessíveis sem estar autenticado.
ROTAS_PUBLICAS = {"auth.entrar", "auth.cadastro", "auth.recuperar", "static"}


# ------------------------------------------------------------- senhas
def validar_senha(senha, login=""):
    erros = []
    if len(senha) < 8:
        erros.append("A senha deve ter pelo menos 8 caracteres.")
    if len(senha) > 128:
        erros.append("A senha deve ter no máximo 128 caracteres.")
    if not re.search(r"[A-Za-z]", senha) or not re.search(r"\d", senha):
        erros.append("A senha deve conter pelo menos uma letra e um número.")
    if login and senha.lower() == login.lower():
        erros.append("A senha não pode ser igual ao nome de usuário.")
    return erros


def validar_login(login):
    if not LOGIN_RE.match(login):
        return ["O usuário deve ter de 3 a 30 caracteres: letras minúsculas, números, ponto, "
                "hífen ou sublinhado."]
    return []


# ------------------------------------------------- códigos de recuperação
def normalizar_codigo(texto):
    return re.sub(r"[^A-Z0-9]", "", (texto or "").upper())


def hash_codigo(texto):
    return hashlib.sha256(normalizar_codigo(texto).encode("utf-8")).hexdigest()


def _novo_codigo():
    bruto = "".join(secrets.choice(ALFABETO) for _ in range(12))   # ~60 bits de entropia
    return "-".join(bruto[i:i + 4] for i in range(0, 12, 4))


def gerar_codigos(usuario, quantidade=QTD_CODIGOS):
    """Substitui todos os códigos do usuário por novos. Devolve os códigos em texto
    puro: esta é a única vez em que eles existem fora do hash."""
    usuario.codigos.clear()
    db.session.flush()
    codigos = []
    while len(codigos) < quantidade:
        codigo = _novo_codigo()
        if codigo not in codigos:
            codigos.append(codigo)
    for codigo in codigos:
        usuario.codigos.append(CodigoRecuperacao(hash=hash_codigo(codigo)))
    return codigos


def localizar_codigo(usuario, texto):
    """Devolve o código não usado que corresponde ao texto digitado (ou None)."""
    alvo = hash_codigo(texto)
    encontrado = None
    for registro in usuario.codigos:
        if registro.usado_em is None and hmac.compare_digest(registro.hash, alvo):
            encontrado = registro
    return encontrado


# ------------------------------------------------------ bloqueio
def registrar_falha(usuario):
    """Conta uma tentativa errada; após MAX_FALHAS bloqueia por alguns minutos."""
    usuario.falhas = (usuario.falhas or 0) + 1
    if usuario.falhas >= MAX_FALHAS:
        usuario.bloqueado_ate = agora() + timedelta(minutes=BLOQUEIO_MINUTOS)
        usuario.falhas = 0
    db.session.commit()


def limpar_falhas(usuario):
    usuario.falhas = 0
    usuario.bloqueado_ate = None


def mensagem_bloqueio(usuario):
    minutos = max(1, -(-usuario.segundos_bloqueio // 60))
    return (f"Muitas tentativas incorretas. Por segurança, o acesso está bloqueado por mais "
            f"{minutos} minuto(s).")


def tentativas_restantes(usuario):
    return MAX_FALHAS - (usuario.falhas or 0)


# --------------------------------------------------------- sessão
def usuario_unico():
    return db.session.scalar(select(Usuario).order_by(Usuario.id).limit(1))


def iniciar_sessao(usuario, lembrar=False):
    session.clear()                                  # evita fixação de sessão
    session["uid"] = usuario.id
    session["uv"] = usuario.versao_sessao
    session.permanent = bool(lembrar)
    usuario.ultimo_acesso = agora()
    g.pop("usuario", None)


def encerrar_sessao():
    session.clear()
    g.pop("usuario", None)


def usuario_atual():
    if "usuario" in g:
        return g.usuario
    usuario = None
    uid = session.get("uid")
    if uid:
        usuario = db.session.get(Usuario, uid)
        if usuario is not None and session.get("uv") != usuario.versao_sessao:
            usuario = None                           # senha mudou em outro lugar
    g.usuario = usuario
    return usuario


def destino_seguro(valor, padrao):
    """Aceita apenas caminhos locais (evita redirecionamento para sites externos)."""
    if valor and valor.startswith("/") and not valor.startswith("//") and "\\" not in valor:
        return valor
    return padrao


# -------------------------------------------------- integração
def registrar_auth(app):
    @app.before_request
    def exigir_login():
        if request.endpoint in ROTAS_PUBLICAS or usuario_atual() is not None:
            return None
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "mensagem": "Sessão expirada. Entre novamente.",
                            "erros": ["Sessão expirada. Entre novamente."]}), 401
        if usuario_unico() is None:
            return redirect(url_for("auth.cadastro"))
        destino = request.full_path.rstrip("?") if request.method == "GET" else ""
        if destino and destino != "/":
            return redirect(url_for("auth.entrar", next=destino))
        return redirect(url_for("auth.entrar"))

    @app.context_processor
    def injetar_usuario():
        try:
            return {"usuario": usuario_atual()}
        except Exception:
            return {"usuario": None}
