"""Importar todos os modelos aqui garante que o SQLAlchemy conheça as tabelas
e resolva os relacionamentos declarados por nome (strings)."""
from .anotacao import Anotacao
from .atividade import Atividade
from .configuracao import Configuracao
from .conteudo import Conteudo
from .flashcard import Flashcard
from .materia import Materia
from .meta import Meta
from .sessao_estudo import SessaoEstudo
from .tarefa import Tarefa
from .usuario import CodigoRecuperacao, Usuario

__all__ = ["Anotacao", "Atividade", "CodigoRecuperacao", "Configuracao", "Conteudo",
           "Flashcard", "Materia", "Meta", "SessaoEstudo", "Tarefa", "Usuario"]
