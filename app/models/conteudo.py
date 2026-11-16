from ..extensions import db


class Conteudo(db.Model):
    __tablename__ = "conteudo"

    id = db.Column(db.Integer, primary_key=True)
    materia_id = db.Column(db.Integer, db.ForeignKey("materia.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    nome = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.Text, default="")
    ordem = db.Column(db.Integer, nullable=False, default=1)
    tempo_estimado = db.Column(db.Integer, nullable=False, default=0)  # minutos
    status = db.Column(db.String(20), nullable=False, default="Não iniciado")
    data_conclusao = db.Column(db.Date)

    materia = db.relationship("Materia", back_populates="conteudos")
    # Tarefas e sessões sobrevivem à exclusão do conteúdo (FK vira NULL).
    tarefas = db.relationship("Tarefa", back_populates="conteudo")
    sessoes = db.relationship("SessaoEstudo", back_populates="conteudo")

    def para_form(self):
        return {
            "nome": self.nome,
            "descricao": self.descricao or "",
            "ordem": self.ordem,
            "tempo_estimado": self.tempo_estimado or "",
            "status": self.status,
            "data_conclusao": self.data_conclusao.isoformat() if self.data_conclusao else "",
        }

    def __repr__(self):
        return f"<Conteudo {self.id} {self.nome}>"
