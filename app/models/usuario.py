from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db


class Usuario(db.Model):
    """Conta de acesso. O StudyFlow é de usuário único: existe no máximo uma conta."""
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    login = db.Column(db.String(40), nullable=False, unique=True, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    # Muda a cada troca/redefinição de senha: invalida as demais sessões abertas.
    versao_sessao = db.Column(db.Integer, nullable=False, default=1)
    falhas = db.Column(db.Integer, nullable=False, default=0)
    bloqueado_ate = db.Column(db.DateTime)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    ultimo_acesso = db.Column(db.DateTime)

    codigos = db.relationship("CodigoRecuperacao", back_populates="usuario",
                              cascade="all, delete-orphan")

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
        self.versao_sessao = (self.versao_sessao or 0) + 1

    def conferir_senha(self, senha):
        return check_password_hash(self.senha_hash, senha or "")

    @property
    def segundos_bloqueio(self):
        if not self.bloqueado_ate:
            return 0
        return max(0, int((self.bloqueado_ate - datetime.now()).total_seconds()) + 1)

    @property
    def bloqueado(self):
        return self.segundos_bloqueio > 0

    @property
    def codigos_restantes(self):
        return sum(1 for c in self.codigos if c.usado_em is None)

    def __repr__(self):
        return f"<Usuario {self.id} {self.login}>"


class CodigoRecuperacao(db.Model):
    """Código de uso único para redefinir a senha. Só o hash é guardado."""
    __tablename__ = "codigo_recuperacao"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    hash = db.Column(db.String(64), nullable=False, index=True)
    usado_em = db.Column(db.DateTime)

    usuario = db.relationship("Usuario", back_populates="codigos")
