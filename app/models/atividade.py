from ..extensions import db

# Cores usadas no calendário para diferenciar as matérias.
PALETA = ["#2563eb", "#0ea5e9", "#6366f1", "#14b8a6", "#f59e0b",
          "#ef4444", "#8b5cf6", "#22c55e", "#ec4899", "#64748b"]


class Atividade(db.Model):
    """Atividade programada no planejamento semanal (início e fim no mesmo dia)."""
    __tablename__ = "atividade"

    id = db.Column(db.Integer, primary_key=True)
    materia_id = db.Column(db.Integer, db.ForeignKey("materia.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    titulo = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.Text, default="")
    inicio = db.Column(db.DateTime, nullable=False, index=True)
    fim = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Planejada")

    materia = db.relationship("Materia", back_populates="atividades")

    @property
    def duracao_min(self):
        return int((self.fim - self.inicio).total_seconds() // 60)

    def para_dict(self):
        return {
            "id": self.id,
            "titulo": self.titulo,
            "descricao": self.descricao or "",
            "materia_id": self.materia_id,
            "materia": self.materia.nome,
            "cor": PALETA[self.materia_id % len(PALETA)],
            "inicio": self.inicio.strftime("%Y-%m-%dT%H:%M"),
            "fim": self.fim.strftime("%Y-%m-%dT%H:%M"),
            "status": self.status,
            "duracao_min": self.duracao_min,
        }

    def __repr__(self):
        return f"<Atividade {self.id} {self.titulo}>"
