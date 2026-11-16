"""Dados iniciais OPCIONAIS: só matérias de exemplo (sem sessões, tarefas ou metas
inventadas). A operação é idempotente: nunca duplica uma matéria já existente."""
from sqlalchemy import func, select

from .extensions import db
from .models import Conteudo, Materia
from .utils import hoje

MATERIAS_EXEMPLO = [
    ("Inglês", "Idiomas", "Intermediário", "Vocabulário, gramática e conversação."),
    ("Italiano", "Idiomas", "Iniciante", "Fundamentos do idioma italiano."),
    ("Python", "Programação", "Iniciante", "Lógica de programação e desenvolvimento com Python."),
    ("SQL", "Banco de dados", "Iniciante", "Consultas, modelagem e manipulação de dados."),
    ("Power BI", "Análise de dados", "Iniciante", "Dashboards e relatórios de BI."),
    ("JavaScript", "Programação", "Iniciante", "JavaScript para a web."),
]

CONTEUDOS_PYTHON = [
    "Introdução ao Python", "Variáveis e tipos de dados", "Estruturas condicionais",
    "Estruturas de repetição", "Funções", "Listas e dicionários",
    "Programação orientada a objetos", "Banco de dados", "Desenvolvimento web com Flask",
]


def carregar_exemplos():
    """Cadastra as matérias de exemplo que ainda não existem. Devolve quantas criou."""
    criadas = 0
    for nome, categoria, nivel, descricao in MATERIAS_EXEMPLO:
        existe = db.session.scalar(
            select(Materia.id).where(func.lower(Materia.nome) == nome.lower()))
        if existe:
            continue
        materia = Materia(nome=nome, categoria=categoria, nivel=nivel, descricao=descricao,
                          data_inicio=hoje(), status="Não iniciado", carga_horaria=0)
        if nome == "Python":
            for posicao, titulo in enumerate(CONTEUDOS_PYTHON, start=1):
                materia.conteudos.append(Conteudo(nome=titulo, ordem=posicao))
        db.session.add(materia)
        criadas += 1
    db.session.commit()
    return criadas
