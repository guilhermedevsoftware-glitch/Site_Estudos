from datetime import datetime

from ..extensions import db


class Anotacao(db.Model):
    __tablename__ = "anotacao"

    id = db.Column(db.Integer, primary_key=True)
    materia_id = db.Column(db.Integer, db.ForeignKey("materia.id", ondelete="CASCADE"),
                           index=True)  # opcional: anotação geral
    titulo = db.Column(db.String(160), nullable=False)
    conteudo = db.Column(db.Text, nullable=False, default="")
    criada_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    atualizada_em = db.Column(db.DateTime, nullable=False, default=datetime.now,
                              onupdate=datetime.now)

    materia = db.relationship("Materia", back_populates="anotacoes")

    def para_form(self):
        return {
            "titulo": self.titulo,
            "materia_id": self.materia_id or "",
            "conteudo": self.conteudo or "",
        }

    def __repr__(self):
        return f"<Anotacao {self.id} {self.titulo}>"
