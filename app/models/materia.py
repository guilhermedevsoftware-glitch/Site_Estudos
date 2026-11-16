from datetime import date, datetime

from ..extensions import db


class Materia(db.Model):
    __tablename__ = "materia"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, index=True)
    descricao = db.Column(db.Text, default="")
    categoria = db.Column(db.String(40), nullable=False, default="Outros")
    nivel = db.Column(db.String(20), nullable=False, default="Iniciante")
    data_inicio = db.Column(db.Date, default=date.today)
    objetivo = db.Column(db.Text, default="")
    carga_horaria = db.Column(db.Float, nullable=False, default=0)  # em horas
    status = db.Column(db.String(20), nullable=False, default="Não iniciado")
    criada_em = db.Column(db.DateTime, nullable=False, default=datetime.now)

    # Dependentes que NÃO fazem sentido sem a matéria: são excluídos junto com ela.
    conteudos = db.relationship("Conteudo", back_populates="materia",
                                cascade="all, delete-orphan", order_by="Conteudo.ordem")
    atividades = db.relationship("Atividade", back_populates="materia",
                                 cascade="all, delete-orphan")
    tarefas = db.relationship("Tarefa", back_populates="materia",
                              cascade="all, delete-orphan")
    sessoes = db.relationship("SessaoEstudo", back_populates="materia",
                              cascade="all, delete-orphan")
    anotacoes = db.relationship("Anotacao", back_populates="materia",
                                cascade="all, delete-orphan")
    flashcards = db.relationship("Flashcard", back_populates="materia",
                                 cascade="all, delete-orphan")
    # Metas podem existir sem matéria: a chave estrangeira vira NULL.
    metas = db.relationship("Meta", back_populates="materia")

    def para_form(self):
        return {
            "nome": self.nome,
            "descricao": self.descricao or "",
            "categoria": self.categoria,
            "nivel": self.nivel,
            "data_inicio": self.data_inicio.isoformat() if self.data_inicio else "",
            "objetivo": self.objetivo or "",
            "carga_horaria": f"{self.carga_horaria:g}" if self.carga_horaria else "",
            "status": self.status,
        }

    def __repr__(self):
        return f"<Materia {self.id} {self.nome}>"
