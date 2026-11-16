from ..choices import CONFIG_PADRAO
from ..extensions import db


class Configuracao(db.Model):
    """Pares chave/valor com as preferências do usuário."""
    __tablename__ = "configuracao"

    chave = db.Column(db.String(60), primary_key=True)
    valor = db.Column(db.String(255), nullable=False, default="")

    @classmethod
    def garantir_padroes(cls):
        """Cria as chaves que ainda não existem (não sobrescreve as existentes)."""
        existentes = {c.chave for c in db.session.scalars(db.select(cls))}
        novas = [cls(chave=k, valor=v) for k, v in CONFIG_PADRAO.items() if k not in existentes]
        if novas:
            db.session.add_all(novas)
            db.session.commit()

    @classmethod
    def todas(cls):
        valores = dict(CONFIG_PADRAO)
        for c in db.session.scalars(db.select(cls)):
            if c.chave in valores:
                valores[c.chave] = c.valor
        return valores

    @classmethod
    def obter(cls, chave):
        return cls.todas().get(chave, CONFIG_PADRAO.get(chave))

    @classmethod
    def obter_numero(cls, chave, tipo=float):
        try:
            return tipo(cls.obter(chave))
        except (TypeError, ValueError):
            return tipo(CONFIG_PADRAO[chave])

    @classmethod
    def definir(cls, valores):
        """Grava vários valores de uma vez (sem commit; quem chama confirma)."""
        for chave, valor in valores.items():
            if chave not in CONFIG_PADRAO:
                continue
            registro = db.session.get(cls, chave)
            if registro is None:
                db.session.add(cls(chave=chave, valor=str(valor)))
            else:
                registro.valor = str(valor)

    def __repr__(self):
        return f"<Configuracao {self.chave}={self.valor}>"
