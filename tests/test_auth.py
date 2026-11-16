"""Testes de autenticação: cadastro, login, bloqueio, recuperação por código e conta."""
import re
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import CodigoRecuperacao, Usuario
from app.security import hash_codigo, validar_login, validar_senha

from conftest import SENHA, logar

PADRAO_CODIGO = re.compile(r"\b[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}\b")
AJAX = {"X-Requested-With": "XMLHttpRequest"}


def _usuario(app):
    """Lê a conta e a devolve já desanexada (com os códigos carregados)."""
    with app.app_context():
        u = db.session.scalar(select(Usuario))
        if u is not None:
            list(u.codigos)
            db.session.expunge(u)
        return u


def _contar(app, modelo):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(modelo))


def _entrar(h, login="teste", senha=SENHA, **extra):
    return h.post("/entrar", {"login": login, "senha": senha, **extra})


# --------------------------------------------------- regras de validação
@pytest.mark.parametrize("senha, valida", [
    ("Senha1234", True), ("abc12", False), ("somenteletras", False),
    ("12345678", False), ("x" * 129 + "1", False)])
def test_politica_de_senha(senha, valida):
    assert (validar_senha(senha) == []) is valida


def test_senha_igual_ao_usuario_e_recusada():
    assert validar_senha("teste1234", "teste1234")
    assert validar_senha("TESTE1234", "teste1234")


@pytest.mark.parametrize("login, valido", [("ana", True), ("ana.silva-2", True),
                                           ("a", False), ("Ana Silva", False), ("a" * 31, False)])
def test_validar_login(login, valido):
    assert (validar_login(login) == []) is valido


# --------------------------------------------------- primeiro acesso
def test_sem_conta_tudo_leva_ao_cadastro(app):
    c = app.test_client()
    assert c.get("/materias/").headers["Location"].endswith("/cadastro")
    assert c.get("/entrar").headers["Location"].endswith("/cadastro")
    assert c.get("/recuperar").headers["Location"].endswith("/cadastro")
    assert c.get("/cadastro").status_code == 200
    assert c.get("/static/css/style.css").status_code == 200      # estáticos são públicos


def test_cadastro_cria_conta_e_mostra_codigos_uma_vez(app, ajudante):
    c = app.test_client()
    h = ajudante(c)
    r = h.post("/cadastro", {"nome": "Ana Souza", "login": "Ana", "senha": "Estudar2026",
                             "confirmacao": "Estudar2026"})
    assert r.status_code == 200
    codigos = PADRAO_CODIGO.findall(r.get_data(as_text=True))
    assert len(codigos) == 8 and len(set(codigos)) == 8

    u = _usuario(app)
    assert u.login == "ana" and u.nome == "Ana Souza"
    assert "Estudar2026" not in u.senha_hash
    with app.app_context():
        hashes = set(db.session.scalars(select(CodigoRecuperacao.hash)))
    assert hashes == {hash_codigo(x) for x in codigos}             # só hashes no banco
    assert not hashes & set(codigos)
    assert c.get("/").status_code == 200                           # já entrou
    assert c.get("/cadastro").headers["Location"].endswith("/")    # não cria 2ª conta
    h.post("/cadastro", {"nome": "Outro", "login": "outro", "senha": "Estudar2026",
                         "confirmacao": "Estudar2026"})
    assert _contar(app, Usuario) == 1


@pytest.mark.parametrize("campos", [
    {"senha": "abc", "confirmacao": "abc"},
    {"senha": "semnumeros", "confirmacao": "semnumeros"},
    {"senha": "Estudar2026", "confirmacao": "Diferente2026"},
    {"login": "a b", "senha": "Estudar2026", "confirmacao": "Estudar2026"},
    {"nome": "A", "senha": "Estudar2026", "confirmacao": "Estudar2026"}])
def test_cadastro_invalido_nao_cria_conta(app, ajudante, campos):
    h = ajudante(app.test_client())
    h.post("/cadastro", {"nome": "Ana", "login": "ana", **campos})
    assert _contar(app, Usuario) == 0


# ------------------------------------------------------------- login
def test_login_correto_e_logout(app, criar_conta, ajudante):
    criar_conta()
    c = app.test_client()
    h = ajudante(c)
    assert c.get("/").headers["Location"].endswith("/entrar")
    r = _entrar(h, login="TESTE", senha=SENHA, lembrar="1")      # usuário não diferencia maiúsculas
    assert r.status_code == 302
    pagina = c.get("/")
    assert pagina.status_code == 200
    assert "Bem-vindo(a) de volta, Teste!" in pagina.get_data(as_text=True)
    assert h.post("/sair").status_code == 302
    assert c.get("/").status_code == 302


def test_login_errado_nao_entra_e_nao_revela_qual_campo(app, criar_conta, ajudante):
    criar_conta()
    c = app.test_client()
    h = ajudante(c)
    r1 = _entrar(h, senha="errada123")
    r2 = _entrar(h, login="outro", senha=SENHA)
    for r in (r1, r2):
        assert r.status_code == 200
        assert "Usuário ou senha incorretos" in r.get_data(as_text=True)
    assert c.get("/").status_code == 302


def test_bloqueio_apos_cinco_falhas_e_liberacao(app, criar_conta, ajudante):
    criar_conta()
    c = app.test_client()
    h = ajudante(c)
    textos = [_entrar(h, senha="errada123").get_data(as_text=True) for _ in range(5)]
    assert "Restam 4" in textos[0] and "Restam 1" in textos[3]
    assert "bloqueado" in textos[4]

    r = _entrar(h, senha=SENHA)                                   # senha certa, mas bloqueado
    assert r.status_code == 200 and "bloqueado" in r.get_data(as_text=True)
    assert c.get("/").status_code == 302

    with app.app_context():                                       # simula o fim do bloqueio
        u = db.session.scalar(select(Usuario))
        u.bloqueado_ate = datetime.now() - timedelta(seconds=1)
        db.session.commit()
    assert _entrar(h, senha=SENHA).status_code == 302
    assert c.get("/").status_code == 200
    assert _usuario(app).falhas == 0


def test_next_seguro(app, criar_conta, ajudante):
    criar_conta()
    c = app.test_client()
    h = ajudante(c)
    assert "next=" in c.get("/metas/").headers["Location"]
    r = _entrar(h, next="/metas/")
    assert r.headers["Location"].endswith("/metas/")
    h.post("/sair")
    for externo in ("//evil.example.com", "https://evil.example.com", "\\\\evil"):
        r = _entrar(h, next=externo)
        assert "evil" not in r.headers["Location"]
        h.post("/sair")


def test_rotas_exigem_login_e_api_devolve_401(app, criar_conta):
    criar_conta()
    c = app.test_client()
    for url in ("/", "/materias/", "/tarefas/", "/cronometro/", "/relatorios/",
                "/relatorios/exportar.csv", "/configuracoes/", "/conta"):
        assert c.get(url).status_code == 302, url
    r = c.get("/planejamento/api/atividades?inicio=2026-01-01T00:00:00&fim=2026-01-02T00:00:00",
              headers=AJAX)
    assert r.status_code == 401 and r.get_json()["ok"] is False
    assert c.get("/nao-existe").status_code == 302                # nem 404 vaza sem login


# ---------------------------------------------------- recuperação
def test_recuperacao_com_codigo_uso_unico(app, criar_conta, ajudante):
    _, _, codigos = criar_conta()
    c = app.test_client()
    h = ajudante(c)
    dados = {"login": "teste", "nova_senha": "NovaSenha77", "confirmacao": "NovaSenha77"}

    # aceita minúsculas e sem hífens
    r = h.post("/recuperar", {**dados, "codigo": codigos[0].replace("-", "").lower()})
    assert r.status_code == 302 and r.headers["Location"].endswith("/entrar")
    assert _entrar(h, senha=SENHA).status_code == 200             # senha antiga não vale
    assert _entrar(h, senha="NovaSenha77").status_code == 302     # a nova vale

    h.post("/sair")
    reuso = h.post("/recuperar", {**dados, "nova_senha": "Outra123456", "confirmacao": "Outra123456",
                                  "codigo": codigos[0]})
    assert reuso.status_code == 200 and "inválido" in reuso.get_data(as_text=True)
    assert h.post("/recuperar", {**dados, "nova_senha": "Outra123456", "confirmacao": "Outra123456",
                                 "codigo": codigos[1]}).status_code == 302


def test_recuperacao_codigo_errado_conta_falhas_e_bloqueia(app, criar_conta, ajudante):
    _, _, codigos = criar_conta()
    h = ajudante(app.test_client())
    dados = {"login": "teste", "nova_senha": "NovaSenha77", "confirmacao": "NovaSenha77"}
    for _ in range(5):
        h.post("/recuperar", {**dados, "codigo": "AAAA-BBBB-CCCC"})
    r = h.post("/recuperar", {**dados, "codigo": codigos[0]})     # código certo, porém bloqueado
    assert r.status_code == 200 and "bloqueado" in r.get_data(as_text=True)
    assert _usuario(app).conferir_senha(SENHA)                    # senha não mudou


def test_senha_fraca_nao_consome_o_codigo(app, criar_conta, ajudante):
    _, _, codigos = criar_conta()
    h = ajudante(app.test_client())
    r = h.post("/recuperar", {"login": "teste", "codigo": codigos[0], "nova_senha": "fraca",
                              "confirmacao": "fraca"})
    assert r.status_code == 200
    u = _usuario(app)
    assert u.codigos_restantes == 8 and u.falhas == 0


def test_recuperacao_desconecta_outras_sessoes(app, criar_conta, ajudante):
    uid, versao, codigos = criar_conta()
    aberta = app.test_client()
    logar(aberta, uid, versao)
    assert aberta.get("/").status_code == 200

    h = ajudante(app.test_client())
    h.post("/recuperar", {"login": "teste", "codigo": codigos[2], "nova_senha": "NovaSenha77",
                          "confirmacao": "NovaSenha77"})
    assert aberta.get("/").status_code == 302


# ------------------------------------------------------ minha conta
def test_alterar_senha(app, client, ajudante, criar_conta):
    h = ajudante(client)
    outra = app.test_client()
    with app.app_context():
        u = db.session.scalar(select(Usuario))
        logar(outra, u.id, u.versao_sessao)

    h.post("/conta/senha", {"senha_atual": "errada123", "nova_senha": "Nova123456",
                            "confirmacao": "Nova123456"})
    assert _usuario(app).conferir_senha(SENHA) and _usuario(app).falhas == 1
    h.post("/conta/senha", {"senha_atual": SENHA, "nova_senha": SENHA, "confirmacao": SENHA})
    assert _usuario(app).conferir_senha(SENHA)                    # igual à atual: recusada
    h.post("/conta/senha", {"senha_atual": SENHA, "nova_senha": "Nova123456",
                            "confirmacao": "Nova123456"})
    assert _usuario(app).conferir_senha("Nova123456")
    assert client.get("/conta").status_code == 200                # esta sessão continua ativa
    assert outra.get("/").status_code == 302                      # as outras caem


def test_novos_codigos_invalidam_os_antigos(app, client, ajudante, criar_conta):
    h = ajudante(client)
    with app.app_context():
        antigos = [c.hash for c in db.session.scalars(select(CodigoRecuperacao))]
    assert len(antigos) == 8

    h.post("/conta/codigos", {"senha_atual": "errada123"})
    with app.app_context():
        assert [c.hash for c in db.session.scalars(select(CodigoRecuperacao))] == antigos

    r = h.post("/conta/codigos", {"senha_atual": SENHA})
    novos = PADRAO_CODIGO.findall(r.get_data(as_text=True))
    assert len(novos) == 8
    with app.app_context():
        atuais = {c.hash for c in db.session.scalars(select(CodigoRecuperacao))}
    assert atuais == {hash_codigo(x) for x in novos} and not atuais & set(antigos)


def test_alterar_nome_e_pagina_da_conta(app, client, ajudante, criar_conta):
    h = ajudante(client)
    assert client.get("/conta").status_code == 200
    h.post("/conta/perfil", {"nome": "Novo Nome"})
    assert _usuario(app).nome == "Novo Nome"
    h.post("/conta/perfil", {"nome": "x"})
    assert _usuario(app).nome == "Novo Nome"


def test_script_de_redefinicao_pelo_terminal(app, criar_conta, ajudante, monkeypatch, capsys):
    criar_conta()
    import redefinir_senha
    monkeypatch.setattr(redefinir_senha, "create_app", lambda: app)
    entradas = iter(["Terminal2026", "Terminal2026"])
    monkeypatch.setattr(redefinir_senha.getpass, "getpass", lambda _msg: next(entradas))
    assert redefinir_senha.main() == 0
    novos = PADRAO_CODIGO.findall(capsys.readouterr().out)
    assert len(novos) == 8
    assert _usuario(app).conferir_senha("Terminal2026")

    h = ajudante(app.test_client())
    assert _entrar(h, senha="Terminal2026").status_code == 302
