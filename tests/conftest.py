import re

import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Usuario
from app.security import gerar_codigos
from config import Config

SENHA = "Senha1234"


@pytest.fixture()
def app(tmp_path):
    class TestConfig(Config):
        TESTING = True
        BANCO_ARQUIVO = str(tmp_path / "teste.db")
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + (tmp_path / "teste.db").as_posix()

    aplicacao = create_app(TestConfig)
    yield aplicacao
    with aplicacao.app_context():
        _db.session.remove()
        _db.engine.dispose()


@pytest.fixture()
def criar_conta(app):
    """Devolve uma função que cria a conta única. Resultado: (id, versao_sessao, códigos)."""
    def _criar(login="teste", nome="Teste", senha=SENHA):
        with app.app_context():
            usuario = Usuario(nome=nome, login=login)
            usuario.definir_senha(senha)
            _db.session.add(usuario)
            codigos = gerar_codigos(usuario)
            _db.session.commit()
            return usuario.id, usuario.versao_sessao, codigos
    return _criar


def logar(cliente, uid, versao):
    """Abre a sessão diretamente (sem passar pela tela de login)."""
    with cliente.session_transaction() as sessao:
        sessao["uid"] = uid
        sessao["uv"] = versao


@pytest.fixture()
def client(app, criar_conta):
    """Cliente JÁ autenticado: usado pelos testes dos módulos do sistema."""
    cliente = app.test_client()
    uid, versao, _ = criar_conta()
    logar(cliente, uid, versao)
    return cliente


class Ajudante:
    """Cuida do token CSRF nos testes (funciona logado ou não)."""
    PAGINAS = ("/", "/entrar", "/cadastro", "/recuperar")

    def __init__(self, client):
        self.client = client

    def token(self):
        for pagina in self.PAGINAS:
            resposta = self.client.get(pagina)
            if resposta.status_code == 200:
                achado = re.search(r'name="csrf-token" content="([^"]+)"',
                                   resposta.get_data(as_text=True))
                if achado:
                    return achado.group(1)
        raise AssertionError("não foi possível obter o token CSRF")

    def post(self, url, dados=None, **kw):
        dados = dict(dados or {})
        dados["csrf_token"] = self.token()
        return self.client.post(url, data=dados, **kw)

    def api(self, metodo, url, json=None):
        return self.client.open(
            url, method=metodo, json=json,
            headers={"X-CSRFToken": self.token(), "X-Requested-With": "XMLHttpRequest"})


@pytest.fixture()
def h(client):
    return Ajudante(client)


@pytest.fixture()
def ajudante():
    return Ajudante
