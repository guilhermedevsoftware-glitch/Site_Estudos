"""Redefinição de senha pelo terminal (último recurso).

Use quando você esqueceu a senha E perdeu os códigos de recuperação. Como exige acesso ao
computador onde o StudyFlow está instalado, é seguro: quem tem acesso à pasta do sistema já
poderia mexer no banco de dados. Seus dados de estudo NÃO são alterados.

Uso (com o ambiente virtual ativado, na pasta do projeto):

    python redefinir_senha.py
"""
import getpass
import sys

from app import create_app
from app.extensions import db
from app.security import gerar_codigos, limpar_falhas, usuario_unico, validar_senha


def main():
    app = create_app()
    with app.app_context():
        usuario = usuario_unico()
        if usuario is None:
            print("Ainda não existe nenhuma conta. Abra o sistema (python run.py) e crie a sua.")
            return 1

        print(f"Redefinindo a senha da conta “{usuario.login}” ({usuario.nome}).")
        print("(A senha digitada não aparece na tela.)\n")
        senha = getpass.getpass("Nova senha: ")
        confirmacao = getpass.getpass("Repita a nova senha: ")

        erros = validar_senha(senha, usuario.login)
        if senha != confirmacao:
            erros.append("As senhas digitadas não conferem.")
        if erros:
            print("\nNão foi possível redefinir:")
            for erro in erros:
                print(f"  - {erro}")
            return 1

        usuario.definir_senha(senha)      # também desconecta todas as sessões abertas
        limpar_falhas(usuario)
        codigos = gerar_codigos(usuario)  # os códigos antigos deixam de valer
        db.session.commit()

        print("\nSenha redefinida com sucesso!\n")
        print("NOVOS códigos de recuperação (guarde-os; cada um vale uma única vez):\n")
        for numero, codigo in enumerate(codigos, start=1):
            print(f"  {numero}. {codigo}")
        print("\nAgora inicie o sistema com:  python run.py")
        return 0


if __name__ == "__main__":
    sys.exit(main())
