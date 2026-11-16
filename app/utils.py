"""Funções reutilizáveis: datas, validação de formulários, commits seguros."""
import math
from datetime import date, datetime, time, timedelta

from flask import abort, current_app, flash, jsonify, redirect, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from .extensions import db
from .models import Configuracao


# ---------------------------------------------------------------- datas
def hoje():
    return date.today()


def agora():
    return datetime.now().replace(microsecond=0)


def inicio_semana(d):
    """Segunda-feira da semana de `d`."""
    return d - timedelta(days=d.weekday())


def inicio_mes(d):
    return d.replace(day=1)


def fim_mes(d):
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


# ----------------------------------------------------------- validação
class Formulario:
    """Lê e valida campos de um formulário HTML (ou de um JSON).

    Cada método devolve o valor convertido; os problemas são acumulados em
    `erros` e mostrados de uma vez ao usuário.
    """

    def __init__(self, dados=None):
        self.dados = request.form if dados is None else dados
        self.erros = []

    @property
    def valido(self):
        return not self.erros

    def _bruto(self, campo):
        valor = self.dados.get(campo)
        if valor is None:
            return None
        return str(valor).strip()

    def texto(self, campo, rotulo, obrigatorio=False, max_len=None, padrao=""):
        valor = self._bruto(campo) or ""
        if not valor:
            if obrigatorio:
                self.erros.append(f"{rotulo} é obrigatório.")
            return padrao
        if max_len and len(valor) > max_len:
            self.erros.append(f"{rotulo} deve ter no máximo {max_len} caracteres.")
        return valor

    def escolha(self, campo, rotulo, opcoes, obrigatorio=True, padrao=None):
        valor = self._bruto(campo) or ""
        if not valor:
            if obrigatorio and padrao is None:
                self.erros.append(f"{rotulo} é obrigatório.")
            return padrao
        if valor not in opcoes:
            self.erros.append(f"{rotulo}: valor inválido.")
            return padrao
        return valor

    def inteiro(self, campo, rotulo, obrigatorio=False, minimo=None, maximo=None, padrao=None):
        valor = self._bruto(campo)
        if not valor:
            if obrigatorio:
                self.erros.append(f"{rotulo} é obrigatório.")
            return padrao
        try:
            numero = int(valor)
        except ValueError:
            self.erros.append(f"{rotulo} deve ser um número inteiro.")
            return padrao
        return self._limites(numero, rotulo, minimo, maximo, padrao)

    def decimal(self, campo, rotulo, obrigatorio=False, minimo=None, maximo=None, padrao=None):
        valor = self._bruto(campo)
        if not valor:
            if obrigatorio:
                self.erros.append(f"{rotulo} é obrigatório.")
            return padrao
        try:
            numero = float(valor.replace(",", "."))
            if not math.isfinite(numero):
                raise ValueError
        except ValueError:
            self.erros.append(f"{rotulo} deve ser um número válido.")
            return padrao
        return self._limites(numero, rotulo, minimo, maximo, padrao)

    def _limites(self, numero, rotulo, minimo, maximo, padrao):
        if minimo is not None and numero < minimo:
            self.erros.append(f"{rotulo} deve ser maior ou igual a {minimo:g}.")
            return padrao
        if maximo is not None and numero > maximo:
            self.erros.append(f"{rotulo} deve ser menor ou igual a {maximo:g}.")
            return padrao
        return numero

    def data(self, campo, rotulo, obrigatorio=False, padrao=None):
        valor = self._bruto(campo)
        if not valor:
            if obrigatorio:
                self.erros.append(f"{rotulo} é obrigatória.")
            return padrao
        try:
            return date.fromisoformat(valor)
        except ValueError:
            self.erros.append(f"{rotulo} é inválida.")
            return padrao

    def hora(self, campo, rotulo, obrigatorio=False, padrao=None):
        valor = self._bruto(campo)
        if not valor:
            if obrigatorio:
                self.erros.append(f"{rotulo} é obrigatória.")
            return padrao
        try:
            return time.fromisoformat(valor)
        except ValueError:
            self.erros.append(f"{rotulo} é inválida.")
            return padrao

    def data_hora(self, campo, rotulo, obrigatorio=False, padrao=None):
        valor = self._bruto(campo)
        if not valor:
            if obrigatorio:
                self.erros.append(f"{rotulo} é obrigatório.")
            return padrao
        try:
            return datetime.fromisoformat(valor).replace(tzinfo=None, microsecond=0)
        except ValueError:
            self.erros.append(f"{rotulo} é inválido.")
            return padrao

    def chave(self, campo, rotulo, modelo, obrigatorio=True):
        """Valida uma chave estrangeira e devolve o objeto referenciado."""
        valor = self._bruto(campo)
        if not valor:
            if obrigatorio:
                self.erros.append(f"{rotulo} é obrigatório.")
            return None
        try:
            objeto = db.session.get(modelo, int(valor))
        except ValueError:
            objeto = None
        if objeto is None:
            self.erros.append(f"{rotulo} não encontrado(a).")
        return objeto


def flash_erros(formulario):
    for erro in formulario.erros:
        flash(erro, "danger")


# --------------------------------------------------------- persistência
def confirmar(mensagem_ok=None):
    """Faz commit; em caso de erro desfaz e avisa. Devolve True/False."""
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Erro ao gravar no banco de dados")
        flash("Não foi possível salvar os dados. Nada foi alterado; tente novamente.", "danger")
        return False
    if mensagem_ok:
        flash(mensagem_ok, "success")
    return True


def obter_ou_404(modelo, id_):
    objeto = db.session.get(modelo, id_)
    if objeto is None:
        abort(404)
    return objeto


# ------------------------------------------------------------ navegação
def redirecionar_para(endpoint_padrao, **kwargs):
    """Volta para a URL do campo oculto `next` (se for local) ou para o padrão."""
    destino = request.form.get("next") or ""
    if destino.startswith("/") and not destino.startswith("//") and "\\" not in destino:
        return redirect(destino)
    return redirect(url_for(endpoint_padrao, **kwargs))


def quer_json():
    return request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest"


def json_erro(mensagem, status=400, erros=None):
    return jsonify({"ok": False, "mensagem": mensagem, "erros": erros or [mensagem]}), status


def dados_json():
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


def por_pagina():
    return int(Configuracao.obter_numero("itens_por_pagina", int)) or 10


def paginar(consulta):
    pagina = request.args.get("page", 1, type=int) or 1
    return db.paginate(consulta, page=max(pagina, 1), per_page=por_pagina(), error_out=False)


def conteudos_por_materia():
    """Mapa {materia_id: [{id, nome}]} usado nos seletores dependentes."""
    from .models import Conteudo
    mapa = {}
    consulta = db.select(Conteudo.id, Conteudo.materia_id, Conteudo.nome).order_by(
        Conteudo.materia_id, Conteudo.ordem)
    for id_, materia_id, nome in db.session.execute(consulta):
        mapa.setdefault(str(materia_id), []).append({"id": id_, "nome": nome})
    return mapa
