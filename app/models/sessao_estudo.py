from ..extensions import db


class SessaoEstudo(db.Model):
    """Tempo efetivamente estudado (vindo do cronômetro ou registrado manualmente)."""
    __tablename__ = "sessao_estudo"

    id = db.Column(db.Integer, primary_key=True)
    materia_id = db.Column(db.Integer, db.ForeignKey("materia.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    conteudo_id = db.Column(db.Integer, db.ForeignKey("conteudo.id", ondelete="SET NULL"),
                            index=True)
    data = db.Column(db.Date, nullable=False, index=True)
    inicio = db.Column(db.DateTime, nullable=False)
    fim = db.Column(db.DateTime, nullable=False)
    duracao_min = db.Column(db.Integer, nullable=False)  # tempo efetivo de estudo
    observacoes = db.Column(db.Text, default="")

    materia = db.relationship("Materia", back_populates="sessoes")
    conteudo = db.relationship("Conteudo", back_populates="sessoes")

    def para_form(self):
        return {
            "materia_id": self.materia_id,
            "conteudo_id": self.conteudo_id or "",
            "data": self.data.isoformat(),
            "hora_inicio": self.inicio.strftime("%H:%M"),
            "hora_fim": self.fim.strftime("%H:%M"),
            "duracao_min": self.duracao_min,
            "observacoes": self.observacoes or "",
        }

    def __repr__(self):
        return f"<SessaoEstudo {self.id} {self.duracao_min}min>"
