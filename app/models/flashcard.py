from datetime import datetime

from ..extensions import db


class Flashcard(db.Model):
    __tablename__ = "flashcard"

    id = db.Column(db.Integer, primary_key=True)
    materia_id = db.Column(db.Integer, db.ForeignKey("materia.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    pergunta = db.Column(db.Text, nullable=False)
    resposta = db.Column(db.Text, nullable=False)
    dificuldade = db.Column(db.String(20), nullable=False, default="Não avaliado")
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)

    materia = db.relationship("Materia", back_populates="flashcards")

    def para_form(self):
        return {
            "materia_id": self.materia_id,
            "pergunta": self.pergunta,
            "resposta": self.resposta,
        }

    def para_dict(self):
        return {
            "id": self.id,
            "materia_id": self.materia_id,
            "materia": self.materia.nome,
            "pergunta": self.pergunta,
            "resposta": self.resposta,
            "dificuldade": self.dificuldade,
        }

    def __repr__(self):
        return f"<Flashcard {self.id}>"
