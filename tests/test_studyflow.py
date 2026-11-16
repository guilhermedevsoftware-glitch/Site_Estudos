"""Testes de integração do StudyFlow (rotas + banco SQLite temporário).

Executar:  python -m pytest -q
"""
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app import services
from app.extensions import db
from app.models import (Anotacao, Atividade, Conteudo, Configuracao, Flashcard, Materia, Meta,
                        SessaoEstudo, Tarefa)

MATERIA = {"nome": "Python", "categoria": "Programação", "nivel": "Iniciante",
           "status": "Em andamento", "carga_horaria": "40", "data_inicio": "2026-01-10"}


def contar(modelo):
    return db.session.scalar(select(func.count()).select_from(modelo))


def criar_materia(h, app, **extra):
    dados = {**MATERIA, **extra}
    h.post("/materias/nova", dados)
    with app.app_context():
        return db.session.scalar(select(Materia.id).where(Materia.nome == dados["nome"]))


# ------------------------------------------------------------ páginas e segurança
@pytest.mark.parametrize("url", [
    "/", "/materias/", "/planejamento/", "/tarefas/", "/tarefas/?visao=lista", "/cronometro/",
    "/metas/", "/relatorios/", "/relatorios/?periodo=tudo", "/relatorios/?periodo=semana",
    "/anotacoes/", "/flashcards/", "/flashcards/?aba=cartoes", "/configuracoes/"])
def test_paginas_abrem_com_banco_vazio(client, url):
    assert client.get(url).status_code == 200


def test_pagina_inexistente_da_404(client):
    assert client.get("/nao-existe").status_code == 404


def test_post_sem_token_csrf_e_rejeitado(client, app):
    resposta = client.post("/materias/nova", data=MATERIA)
    assert resposta.status_code == 400
    with app.app_context():
        assert contar(Materia) == 0


# ------------------------------------------------------------ dados de exemplo
def test_exemplos_sao_opcionais_e_nao_duplicam(h, app):
    with app.app_context():
        assert contar(Materia) == 0          # nada é inserido automaticamente
    h.post("/exemplos")
    h.post("/exemplos")
    with app.app_context():
        assert contar(Materia) == 6
        assert contar(Conteudo) == 9         # sequência de Python


# ------------------------------------------------------------ matérias
def test_crud_materia(h, app):
    mid = criar_materia(h, app)
    assert mid
    h.post("/materias/nova", MATERIA)       # duplicada
    h.post(f"/materias/{mid}/editar", {**MATERIA, "nome": "Python Avançado", "nivel": "Avançado"})
    with app.app_context():
        m = db.session.get(Materia, mid)
        assert (contar(Materia), m.nome, m.nivel) == (1, "Python Avançado", "Avançado")
    assert "Python Avançado" in h.client.get("/materias/?q=Python&categoria=Programação"
                                             ).get_data(as_text=True)
    h.post(f"/materias/{mid}/excluir")
    with app.app_context():
        assert contar(Materia) == 0


def test_materia_invalida_nao_grava(h, app):
    h.post("/materias/nova", {**MATERIA, "nome": "", "categoria": "Inexistente"})
    with app.app_context():
        assert contar(Materia) == 0


def test_excluir_materia_remove_dependentes_e_preserva_metas(h, app):
    mid = criar_materia(h, app)
    h.post(f"/conteudos/materia/{mid}/novo", {"nome": "Funções", "status": "Não iniciado"})
    h.post("/tarefas/nova", {"titulo": "Lista 1", "materia_id": mid, "prioridade": "Alta"})
    h.post("/anotacoes/nova", {"titulo": "N", "conteudo": "texto", "materia_id": mid})
    h.post("/flashcards/novo", {"materia_id": mid, "pergunta": "P?", "resposta": "R"})
    h.post("/metas/nova", {"titulo": "Meta", "tipo": "horas", "valor_desejado": "10",
                           "data_inicio": "2026-01-01", "data_limite": "2026-12-31",
                           "materia_id": mid})
    h.post(f"/materias/{mid}/excluir")
    with app.app_context():
        for modelo in (Conteudo, Tarefa, Anotacao, Flashcard, SessaoEstudo, Atividade):
            assert contar(modelo) == 0, modelo
        meta = db.session.scalar(select(Meta))
        assert meta is not None and meta.materia_id is None


# ------------------------------------------------------------ conteúdos
def test_conteudos_ordem_reordenar_e_excluir(h, app):
    mid = criar_materia(h, app)
    for nome in ("A", "B", "C"):
        h.post(f"/conteudos/materia/{mid}/novo", {"nome": nome, "status": "Não iniciado"})
    h.post(f"/conteudos/materia/{mid}/novo", {"nome": "Z", "status": "Não iniciado", "ordem": "1"})
    with app.app_context():
        nomes = [c.nome for c in db.session.scalars(select(Conteudo).order_by(Conteudo.ordem))]
        assert nomes == ["Z", "A", "B", "C"]
        ids = {c.nome: c.id for c in db.session.scalars(select(Conteudo))}

    nova = [ids["C"], ids["B"], ids["A"], ids["Z"]]
    assert h.api("POST", f"/conteudos/materia/{mid}/reordenar", {"ids": nova}).status_code == 200
    assert h.api("POST", f"/conteudos/materia/{mid}/reordenar", {"ids": [1]}).status_code == 400
    h.post(f"/conteudos/{ids['B']}/excluir")
    with app.app_context():
        restantes = db.session.scalars(select(Conteudo).order_by(Conteudo.ordem)).all()
        assert [(c.nome, c.ordem) for c in restantes] == [("C", 1), ("A", 2), ("Z", 3)]


def test_conteudo_concluido_recebe_data(h, app):
    mid = criar_materia(h, app)
    h.post(f"/conteudos/materia/{mid}/novo", {"nome": "X", "status": "Concluído"})
    with app.app_context():
        c = db.session.scalar(select(Conteudo))
        assert c.data_conclusao == date.today()
        cid = c.id
    h.post(f"/conteudos/{cid}/status", {"status": "Em andamento"})
    with app.app_context():
        assert db.session.get(Conteudo, cid).data_conclusao is None


# ------------------------------------------------------------ tarefas
def test_tarefas_kanban_e_conclusao(h, app):
    mid = criar_materia(h, app)
    h.post("/tarefas/nova", {"titulo": "T1", "materia_id": mid, "prioridade": "Média",
                             "prazo": "2026-12-01", "tempo_estimado": "30"})
    with app.app_context():
        tid = db.session.scalar(select(Tarefa.id))
        assert db.session.get(Tarefa, tid).status == "A fazer"
    assert h.api("POST", f"/tarefas/{tid}/status", {"status": "Concluída"}).status_code == 200
    with app.app_context():
        t = db.session.get(Tarefa, tid)
        assert t.status == "Concluída" and t.concluida_em is not None
    assert h.api("POST", f"/tarefas/{tid}/status", {"status": "Em andamento"}).status_code == 200
    assert h.api("POST", f"/tarefas/{tid}/status", {"status": "Inválido"}).status_code == 400
    with app.app_context():
        assert db.session.get(Tarefa, tid).concluida_em is None
    h.post(f"/tarefas/{tid}/editar", {"titulo": "T1b", "materia_id": mid, "prioridade": "Alta"})
    h.post(f"/tarefas/{tid}/excluir")
    with app.app_context():
        assert contar(Tarefa) == 0


def test_tarefa_rejeita_conteudo_de_outra_materia(h, app):
    m1 = criar_materia(h, app)
    m2 = criar_materia(h, app, nome="SQL")
    h.post(f"/conteudos/materia/{m2}/novo", {"nome": "Joins", "status": "Não iniciado"})
    with app.app_context():
        cid = db.session.scalar(select(Conteudo.id))
    h.post("/tarefas/nova", {"titulo": "X", "materia_id": m1, "conteudo_id": cid,
                             "prioridade": "Baixa"})
    with app.app_context():
        assert contar(Tarefa) == 0


# ------------------------------------------------------------ planejamento
def test_atividades_api(h, app):
    mid = criar_materia(h, app)
    amanha = date.today() + timedelta(days=1)
    corpo = {"titulo": "Estudar", "materia_id": mid, "status": "Planejada",
             "inicio": f"{amanha}T09:00:00", "fim": f"{amanha}T10:30:00"}
    r = h.api("POST", "/planejamento/api/atividades", corpo)
    assert r.status_code == 201
    aid = r.get_json()["atividade"]["id"]
    assert r.get_json()["atividade"]["duracao_min"] == 90

    assert h.api("POST", "/planejamento/api/atividades",
                 {**corpo, "fim": f"{amanha}T08:00:00"}).status_code == 400
    assert h.api("POST", "/planejamento/api/atividades",
                 {**corpo, "fim": f"{amanha + timedelta(days=1)}T08:00:00"}).status_code == 400

    r = h.api("PATCH", f"/planejamento/api/atividades/{aid}/mover",
              {"inicio": f"{amanha}T14:00:00", "fim": f"{amanha}T15:00:00"})
    assert r.status_code == 200
    r = h.client.get(f"/planejamento/api/atividades?inicio={amanha}T00:00:00&fim={amanha}T23:59:59")
    assert [a["inicio"] for a in r.get_json()] == [f"{amanha}T14:00"]

    assert h.api("PUT", f"/planejamento/api/atividades/{aid}", {**corpo, "titulo": "Novo"}
                 ).get_json()["atividade"]["titulo"] == "Novo"
    assert h.api("DELETE", f"/planejamento/api/atividades/{aid}").status_code == 200
    with app.app_context():
        assert contar(Atividade) == 0


# ------------------------------------------------------------ cronômetro, metas e relatórios
def _sessao(h, mid, minutos=30):
    fim = datetime.now().replace(microsecond=0) - timedelta(minutes=1)
    inicio = fim - timedelta(minutes=minutos)
    return h.api("POST", "/cronometro/sessoes", {
        "materia_id": mid, "conteudo_id": "", "duracao_min": minutos,
        "inicio": inicio.isoformat(), "fim": fim.isoformat(), "observacoes": "teste"}), inicio


def test_sessao_alimenta_dashboard_metas_e_relatorios(h, app):
    mid = criar_materia(h, app)
    r, inicio = _sessao(h, mid, 45)
    assert r.status_code == 201
    assert _sessao(h, mid, 0)[0].status_code == 400            # duração inválida

    h.post("/metas/nova", {"titulo": "1h", "tipo": "horas", "valor_desejado": "1",
                           "data_inicio": (date.today() - timedelta(days=1)).isoformat(),
                           "data_limite": (date.today() + timedelta(days=5)).isoformat(),
                           "materia_id": mid})
    with app.app_context():
        assert services.soma_minutos(inicio.date(), inicio.date()) == 45
        assert services.minutos_por_materia()[0][0] == "Python"
        assert services.minutos_por_categoria()[0][0] == "Programação"
        meta = db.session.scalar(select(Meta))
        assert meta.progresso_atual == pytest.approx(0.75) and meta.status == "Em andamento"
        assert meta.percentual == 75

    r, _ = _sessao(h, mid, 30)                                  # total 75 min > 1 h
    h.client.get("/metas/")                                     # recalcula
    with app.app_context():
        assert db.session.scalar(select(Meta)).status == "Concluída"

    assert h.client.get("/").status_code == 200
    assert h.client.get("/relatorios/?periodo=mes").status_code == 200

    csv = h.client.get("/relatorios/exportar.csv?periodo=tudo")
    texto = csv.get_data(as_text=True)
    assert csv.mimetype == "text/csv" and texto.startswith("﻿")
    assert "Python" in texto and ";45;" in texto
    resumo = h.client.get("/relatorios/exportar.csv?periodo=tudo&tipo=materias").get_data(as_text=True)
    assert "Python" in resumo and "75" in resumo


def test_meta_atrasada_e_validacoes(h, app):
    h.post("/metas/nova", {"titulo": "Velha", "tipo": "dias", "valor_desejado": "5",
                           "data_inicio": "2020-01-01", "data_limite": "2020-02-01"})
    h.post("/metas/nova", {"titulo": "Datas ruins", "tipo": "horas", "valor_desejado": "5",
                           "data_inicio": "2026-05-01", "data_limite": "2026-04-01"})
    h.client.get("/metas/")
    with app.app_context():
        assert contar(Meta) == 1
        assert db.session.scalar(select(Meta)).status == "Atrasada"


def test_meta_manual_e_exclusao(h, app):
    h.post("/metas/nova", {"titulo": "Curso", "tipo": "manual", "valor_desejado": "100",
                           "progresso_atual": "40", "data_inicio": "2026-01-01",
                           "data_limite": "2099-01-01"})
    with app.app_context():
        meta = db.session.scalar(select(Meta))
        assert meta.progresso_atual == 40 and meta.status == "Em andamento"
        mid = meta.id
    h.post(f"/metas/{mid}/editar", {"titulo": "Curso", "tipo": "manual", "valor_desejado": "100",
                                    "progresso_atual": "100", "data_inicio": "2026-01-01",
                                    "data_limite": "2099-01-01"})
    with app.app_context():
        assert db.session.get(Meta, mid).status == "Concluída"
    h.post(f"/metas/{mid}/excluir")
    with app.app_context():
        assert contar(Meta) == 0


def test_csv_neutraliza_formulas(h, app):
    mid = criar_materia(h, app)
    fim = datetime.now().replace(microsecond=0) - timedelta(minutes=1)
    h.api("POST", "/cronometro/sessoes", {
        "materia_id": mid, "duracao_min": 10, "inicio": (fim - timedelta(minutes=10)).isoformat(),
        "fim": fim.isoformat(), "observacoes": "=HYPERLINK(\"http://x\")"})
    texto = h.client.get("/relatorios/exportar.csv?periodo=tudo").get_data(as_text=True)
    assert "'=HYPERLINK" in texto


def test_sessao_manual_edicao_exclusao_e_intervalos(h, app):
    mid = criar_materia(h, app)
    hoje = date.today().isoformat()
    h.post("/cronometro/sessoes/nova", {"materia_id": mid, "data": hoje, "hora_inicio": "01:00",
                                        "hora_fim": "02:00", "observacoes": "manual"})
    with app.app_context():
        s = db.session.scalar(select(SessaoEstudo))
        assert s.duracao_min == 60
        sid = s.id
    h.post(f"/cronometro/sessoes/{sid}/editar", {"materia_id": mid, "data": hoje,
           "hora_inicio": "01:00", "hora_fim": "01:30", "duracao_min": "20"})
    with app.app_context():
        assert db.session.get(SessaoEstudo, sid).duracao_min == 20
    h.post(f"/cronometro/sessoes/{sid}/excluir")
    with app.app_context():
        assert contar(SessaoEstudo) == 0

    r = h.api("POST", "/cronometro/intervalos", {"foco": 50, "pausa": 10, "longa": 30, "ciclos": 3})
    assert r.status_code == 200
    assert h.api("POST", "/cronometro/intervalos", {"foco": 0, "pausa": 1, "longa": 1, "ciclos": 4}
                 ).status_code == 400
    with app.app_context():
        assert Configuracao.obter("pomodoro_foco") == "50"


# ------------------------------------------------------------ anotações, flashcards e configurações
def test_anotacoes_crud_e_busca(h, app):
    mid = criar_materia(h, app)
    h.post("/anotacoes/nova", {"titulo": "Decoradores", "conteudo": "funções de ordem superior",
                               "materia_id": mid})
    h.post("/anotacoes/nova", {"titulo": "", "conteudo": "x"})        # inválida
    with app.app_context():
        assert contar(Anotacao) == 1
        nid = db.session.scalar(select(Anotacao.id))
    assert "Decoradores" in h.client.get("/anotacoes/?q=ordem+superior").get_data(as_text=True)
    assert "Decoradores" not in h.client.get("/anotacoes/?q=zzzz").get_data(as_text=True)
    h.post(f"/anotacoes/{nid}/editar", {"titulo": "Decoradores 2", "conteudo": "novo"})
    with app.app_context():
        assert db.session.get(Anotacao, nid).titulo == "Decoradores 2"
    h.post(f"/anotacoes/{nid}/excluir")
    with app.app_context():
        assert contar(Anotacao) == 0


def test_flashcards_crud_e_avaliacao(h, app):
    mid = criar_materia(h, app)
    h.post("/flashcards/novo", {"materia_id": mid, "pergunta": "O que é uma lista?",
                                "resposta": "Sequência mutável"})
    with app.app_context():
        fid = db.session.scalar(select(Flashcard.id))
        assert db.session.get(Flashcard, fid).dificuldade == "Não avaliado"
    assert "O que é uma lista?" in h.client.get("/flashcards/").get_data(as_text=True)
    assert h.api("POST", f"/flashcards/{fid}/avaliar", {"dificuldade": "Difícil"}).status_code == 200
    assert h.api("POST", f"/flashcards/{fid}/avaliar", {"dificuldade": "Nada"}).status_code == 400
    h.post(f"/flashcards/{fid}/editar", {"materia_id": mid, "pergunta": "P", "resposta": "R"})
    with app.app_context():
        assert db.session.get(Flashcard, fid).dificuldade == "Difícil"
    h.post(f"/flashcards/{fid}/excluir")
    with app.app_context():
        assert contar(Flashcard) == 0


def test_configuracoes(h, app):
    base = {"meta_diaria_horas": "3", "meta_semanal_horas": "15", "pomodoro_foco": "30",
            "pomodoro_pausa": "7", "pomodoro_pausa_longa": "20", "pomodoro_ciclos": "4",
            "itens_por_pagina": "20", "tema": "escuro", "menu_recolhido": "1"}
    h.post("/configuracoes/salvar", base)
    with app.app_context():
        cfg = Configuracao.todas()
        assert (cfg["tema"], cfg["pomodoro_foco"], cfg["menu_recolhido"]) == ("escuro", "30", "1")
    h.post("/configuracoes/salvar", {**base, "tema": "neon", "pomodoro_foco": "99"})  # inválido
    with app.app_context():
        assert Configuracao.todas()["tema"] == "escuro"
    h.post("/configuracoes/salvar", {**base, "meta_semanal_horas": "1"})              # semanal < diária
    with app.app_context():
        assert Configuracao.todas()["meta_semanal_horas"] == "15"
    assert 'data-bs-theme="dark"' in h.client.get("/").get_data(as_text=True)
