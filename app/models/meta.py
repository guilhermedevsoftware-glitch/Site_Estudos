from ..extensions import db


class Meta(db.Model):
    """Meta de estudos. `progresso_atual` e `status` são recalculados a partir
    das sessões/conteúdos (exceto no tipo "manual", em que o usuário informa o progresso)."""
    __tablename__ = "meta"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.Text, default="")
    materia_id = db.Column(db.Integer, db.ForeignKey("materia.id", ondelete="SET NULL"),
                           index=True)
    tipo = db.Column(db.String(20), nullable=False, default="horas")
    valor_desejado = db.Column(db.Float, nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_limite = db.Column(db.Date, nullable=False)
    progresso_atual = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="Em andamento")

    materia = db.relationship("Materia", back_populates="metas")

    @property
    def percentual(self):
        if not self.valor_desejado:
            return 0
        return max(0, min(100, round(self.progresso_atual / self.valor_desejado * 100)))

    def para_form(self):
        return {
            "titulo": self.titulo,
            "descricao": self.descricao or "",
            "materia_id": self.materia_id or "",
            "tipo": self.tipo,
            "valor_desejado": f"{self.valor_desejado:g}",
            "data_inicio": self.data_inicio.isoformat(),
            "data_limite": self.data_limite.isoformat(),
            "progresso_atual": f"{self.progresso_atual:g}" if self.tipo == "manual" else "",
        }

    def __repr__(self):
        return f"<Meta {self.id} {self.titulo}>"
