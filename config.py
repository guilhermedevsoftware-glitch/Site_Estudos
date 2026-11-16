"""Configurações do StudyFlow."""
import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)


def _carregar_chave_secreta():
    """Usa a variável de ambiente, ou gera uma chave aleatória uma única vez
    e a guarda em instance/secret.key (necessária para sessão e CSRF)."""
    chave = os.environ.get("STUDYFLOW_SECRET_KEY")
    if chave:
        return chave
    caminho = os.path.join(INSTANCE_DIR, "secret.key")
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as arq:
            return arq.read().strip()
    chave = secrets.token_hex(32)
    with open(caminho, "w", encoding="utf-8") as arq:
        arq.write(chave)
    return chave


class Config:
    SECRET_KEY = _carregar_chave_secreta()
    # Caminho absoluto, com barras normais (funciona também no Windows).
    BANCO_ARQUIVO = os.path.join(INSTANCE_DIR, "studyflow.db")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "STUDYFLOW_DATABASE_URI",
        "sqlite:///" + BANCO_ARQUIVO.replace("\\", "/"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)   # "Manter conectado"
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    VERSAO = "1.1.0"
