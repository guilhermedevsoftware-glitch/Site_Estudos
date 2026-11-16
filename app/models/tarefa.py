from datetime import date, datetime

from ..extensions import db


class Tarefa(db.Model):
    __tablename__ = "tarefa"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.Text, default="")
    materia_id = db.Column(db.Integer, db.ForeignKey("materia.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    conteudo_id = db.Column(db.Integer, db.ForeignKey("conteudo.id", ondelete="SET NULL"),
                            index=True)
    prioridade = db.Column(db.String(10), nullable=False, default="Média")
    criada_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    prazo = db.Column(db.Date)
    tempo_estimado = db.Column(db.Integer, nullable=False, default=0)  # minutos
    status = db.Column(db.String(20), nullable=False, default="A fazer", index=True)
    concluida_em = db.Column(db.DateTime)

    materia = db.relationship("Materia", back_populates="tarefas")
    conteudo = db.relationship("Conteudo", back_populates="tarefas")

    @property
    def atrasada(self):
        return bool(self.prazo and self.prazo < date.today() and self.status != "Concluída")

    def definir_status(self, status):
        """Muda o status mantendo a data de conclusão coerente."""
        if status == "Concluída" and self.status != "Concluída":
            self.concluida_em = datetime.now().replace(microsecond=0)
        elif status != "Concluída":
            self.concluida_em = None
        self.status = status

    def para_form(self):
        return {
            "titulo": self.titulo,
            "descricao": self.descricao or "",
            "materia_id": self.materia_id,
            "conteudo_id": self.conteudo_id or "",
            "prioridade": self.prioridade,
            "prazo": self.prazo.isoformat() if self.prazo else "",
            "tempo_estimado": self.tempo_estimado or "",
            "status": self.status,
        }

    def __repr__(self):
        return f"<Tarefa {self.id} {self.titulo}>"
