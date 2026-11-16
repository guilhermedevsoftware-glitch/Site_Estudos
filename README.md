# StudyFlow — Sistema de Gerenciamento de Estudos

Aplicação web para organizar a rotina de estudos: matérias e conteúdos, planejamento em calendário,
tarefas (Kanban), cronômetro com Pomodoro, metas, relatórios com gráficos, anotações e flashcards.

**Tecnologias:** Python · Flask · Flask-SQLAlchemy · SQLite · Jinja2 · HTML5 · CSS3 · Bootstrap 5 · JavaScript · Chart.js

---

## 1. Instalação no Windows

### 1.1 Pré-requisitos
- **Python 3.10 ou superior** — baixe em <https://www.python.org/downloads/windows/>.
  Na instalação, **marque a opção “Add python.exe to PATH”**.
- **Conexão com a internet** ao usar o sistema: Bootstrap, os ícones e o Chart.js são carregados por CDN
  (jsDelivr). Sem internet o sistema funciona, mas sem estilo, ícones e gráficos.

Confirme a instalação abrindo o **PowerShell** e executando:

```powershell
python --version
```

(Se `python` não for reconhecido, tente `py --version` e use `py` no lugar de `python` nos comandos abaixo.)

### 1.2 Preparar o projeto
Abra o PowerShell **dentro da pasta `studyflow`** (no Explorador de Arquivos: clique na barra de endereço,
digite `powershell` e pressione Enter) e execute, um comando por vez:

```powershell
# 1) Criar o ambiente virtual
python -m venv .venv

# 2) Ativar o ambiente virtual
.venv\Scripts\Activate.ps1

# 3) Instalar as dependências
pip install -r requirements.txt
```

> **Erro “a execução de scripts foi desabilitada neste sistema”** ao ativar o ambiente?
> Execute uma vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, responda `S` e repita o passo 2.
> Alternativa: use o **Prompt de Comando (cmd)** e ative com `.venv\Scripts\activate.bat`.

### 1.3 Executar

```powershell
python run.py
```

Abra no navegador: **<http://127.0.0.1:5000>**

O banco de dados (`instance/studyflow.db`) e as tabelas são **criados automaticamente** na primeira execução.
Para encerrar, pressione `Ctrl + C` no terminal.

Nas próximas vezes, basta ativar o ambiente (`.venv\Scripts\Activate.ps1`) e rodar `python run.py`.

### 1.4 Primeiros passos
0. **Crie sua conta.** No primeiro acesso o sistema abre a tela *Crie sua conta* (nome, usuário e senha).
   Em seguida mostra **8 códigos de recuperação**: **guarde-os** (copie, baixe o .txt ou imprima) — eles são a
   forma de redefinir a senha se você esquecê-la. Veja a seção 3.1.
1. No **Dashboard** (ainda vazio), clique em **“Carregar matérias de exemplo”** (opcional) ou cadastre suas
   próprias matérias em **Minhas matérias**. Os exemplos nunca são inseridos sozinhos nem duplicados.
2. Monte a sequência de estudo de cada matéria no botão **Conteúdos** (ícone de lista).
3. Planeje sua semana em **Planejamento semanal**, estude com o **Cronômetro** e acompanhe tudo no Dashboard.

---

## 2. Configuração opcional

Variáveis de ambiente (PowerShell, antes de `python run.py`):

| Variável | Para que serve | Padrão |
|---|---|---|
| `STUDYFLOW_PORT` | Porta do servidor | `5000` |
| `STUDYFLOW_HOST` | Endereço de escuta | `127.0.0.1` |
| `STUDYFLOW_DEBUG` | `1` ativa o modo de depuração (recarrega ao editar o código) | desligado |
| `STUDYFLOW_SECRET_KEY` | Chave de sessão/CSRF | gerada e guardada em `instance/secret.key` |
| `STUDYFLOW_DATABASE_URI` | Outro banco (ex.: `sqlite:///C:/dados/estudos.db`) | `instance/studyflow.db` |

Exemplo: `$env:STUDYFLOW_PORT = "8080"; python run.py`

Preferências dentro do sistema (menu **Configurações**): metas diária e semanal, intervalos do Pomodoro,
tema claro/escuro, itens por página, menu lateral recolhido e informações do sistema.

---

## 3. Módulos

| Módulo | O que faz |
|---|---|
| **Dashboard** | Horas hoje/semana/mês, matérias, tarefas, metas, % de conclusão, 4 gráficos e “Meu Dia de Estudos” |
| **Minhas matérias** | CRUD, busca por nome, filtros por categoria e status, progresso de conteúdos e horas |
| **Conteúdos** | Sequência de aprendizagem por matéria; reordenação por arrastar e soltar; status e data de conclusão |
| **Planejamento semanal** | Calendário em visões dia/semana/mês: clique para criar, arraste para reorganizar, puxe a borda para ajustar a duração |
| **Tarefas e atividades** | Kanban com arrastar e soltar (A fazer / Em andamento / Concluída), visão em lista, filtros e prioridades |
| **Cronômetro** | Cronômetro livre e Pomodoro (25/5/15 personalizáveis); salva a sessão no banco ao finalizar; registro manual |
| **Metas** | Metas por horas, dias, conteúdos concluídos ou progresso manual; progresso e status (em andamento/concluída/atrasada) calculados automaticamente |
| **Relatórios e evolução** | Filtros por dia, semana, mês, período personalizado e matéria; indicadores; gráficos; **exportação CSV** |
| **Anotações** | CRUD, busca e filtro por matéria |
| **Flashcards** | CRUD, modo de estudo (virar, navegar, embaralhar) e marcação Fácil/Médio/Difícil |
| **Configurações** | Metas, Pomodoro, exibição e informações do sistema |

### Como o cronômetro funciona
O estado (matéria, horário de início, tempo acumulado) fica no **`localStorage` do navegador** e o tempo
é sempre **recalculado a partir de horários**, não de uma contagem em memória. Por isso ele segue correto
ao trocar de página, recarregar ou até fechar o navegador. Um mini-relógio aparece no topo de todas as telas
enquanto há uma sessão ativa. No Pomodoro, **apenas o tempo de foco** é contado como estudo.
Observação: o estado é por navegador; abrir o sistema em outro navegador não mostra a sessão em andamento.

### Exclusões seguras
- Excluir uma **matéria** remove também seus conteúdos, atividades, tarefas, sessões, anotações e flashcards
  (a tela pede confirmação e avisa o que será apagado). **Metas** são preservadas, apenas perdem o vínculo.
- Excluir um **conteúdo** mantém as tarefas e sessões que o citavam (apenas sem vínculo), preservando o histórico de horas.
- As chaves estrangeiras do SQLite são ativadas em toda conexão.

### 3.1 Conta, login e recuperação de senha

O StudyFlow é de **usuário único**: o primeiro acesso cria a conta e todas as páginas passam a exigir login.

| Recurso | Como funciona |
|---|---|
| **Login** | Usuário + senha. “Manter conectado” mantém a sessão por 30 dias (use só em computador seu). |
| **Senha** | Mínimo de 8 caracteres, com letras e números. Guardada apenas como *hash* (nunca em texto puro). |
| **Bloqueio** | 5 tentativas incorretas (login, recuperação ou troca de senha) bloqueiam o acesso por 5 minutos. |
| **Esqueci minha senha** | Na tela de login, informe o usuário, **um código de recuperação** e a nova senha. Cada código vale **uma única vez** e só o hash dele fica no banco. |
| **Minha conta** | Menu do usuário (canto superior direito): alterar nome e senha e **gerar novos códigos** (os antigos deixam de valer). Trocar a senha desconecta os outros navegadores. |
| **Perdi senha e códigos** | Com acesso ao computador, feche o sistema e rode `python redefinir_senha.py` (ambiente virtual ativo). O script define uma nova senha e gera novos códigos; **seus dados de estudo não são alterados**. |

Boas práticas: guarde os códigos **fora do computador** (papel ou gerenciador de senhas) e, quando restarem
poucos, gere novos em *Minha conta* (o sistema avisa ao entrar quando restam 2 ou menos).

> Se você já usava o StudyFlow antes do login, nada se perde: as tabelas novas são criadas automaticamente,
> o próximo acesso mostrará a tela de criação de conta e todos os seus dados continuam disponíveis.

---

## 4. Testes automatizados

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```

Os testes usam um banco temporário (não tocam em `instance/studyflow.db`) e cobrem páginas, CSRF, CRUD de todos os
módulos, exclusão em cascata, reordenação de conteúdos, Kanban, API do calendário, sessões/metas/relatórios,
exportação CSV e configurações — além de **cadastro, login, bloqueio por tentativas, redirecionamento seguro,
recuperação por código (uso único), troca de senha, novos códigos e o script `redefinir_senha.py`**.

---

## 5. Estrutura do projeto

```
studyflow/
├── app/
│   ├── __init__.py          # create_app: configuração, CSRF, filtros Jinja, tratamento de erros
│   ├── extensions.py        # db (SQLAlchemy) + ativação das chaves estrangeiras do SQLite
│   ├── choices.py           # listas de opções (categorias, status, prioridades…)
│   ├── utils.py             # validação de formulários, datas, commit seguro, paginação
│   ├── security.py          # senhas, códigos de recuperação, bloqueio, sessão e proteção das rotas
│   ├── services.py          # consultas agregadas (horas, gráficos, progresso das metas)
│   ├── seed.py              # matérias de exemplo (opcionais e idempotentes)
│   ├── models/              # Materia, Conteudo, Atividade, Tarefa, SessaoEstudo, Meta,
│   │                        # Anotacao, Flashcard, Configuracao, Usuario, CodigoRecuperacao
│   ├── routes/              # um Blueprint por módulo
│   ├── templates/           # base.html, _macros.html e uma pasta por módulo
│   └── static/ css/ js/ img/
├── instance/                # studyflow.db e secret.key (criados automaticamente)
├── tests/
├── config.py
├── run.py
├── redefinir_senha.py       # último recurso: nova senha pelo terminal
├── requirements.txt
└── README.md
```

### Banco de dados
`materia` 1—N `conteudo`, `atividade`, `tarefa`, `sessao_estudo`, `anotacao`, `flashcard` (exclusão em cascata);
`materia` 1—N `meta` (opcional; `NULL` ao excluir a matéria); `conteudo` 1—N `tarefa` e `sessao_estudo`
(opcional; `NULL` ao excluir o conteúdo); `configuracao` guarda pares chave/valor.
Datas e horários são gravados no horário local do computador, sem fuso.

---

## 6. Solução de problemas

| Problema | Solução |
|---|---|
| `python` não é reconhecido | Reinstale o Python marcando “Add python.exe to PATH”, ou use `py` |
| `Address already in use` / porta ocupada | `$env:STUDYFLOW_PORT = "5001"` e rode de novo |
| Página sem estilo, ícones ou gráficos | Verifique a internet (os recursos vêm de CDN) |
| “Sessão expirada ou token CSRF inválido” | Recarregue a página (F5) e repita a ação |
| Esqueci a senha | Tela de login → “Esqueci minha senha” → use um código de recuperação |
| Esqueci a senha e perdi os códigos | Feche o sistema e rode `python redefinir_senha.py` |
| “Acesso bloqueado por tentativas” | Aguarde 5 minutos (ou, com o sistema fechado, rode `python redefinir_senha.py`, que também libera o bloqueio) |
| Fui desconectado do nada | Apagar `instance\secret.key` ou trocar a senha em outro navegador encerra as sessões abertas; basta entrar de novo |
| Quero zerar tudo | Feche o sistema e apague `instance\studyflow.db` (um novo banco vazio é criado) |
| Quero fazer backup | Copie `instance\studyflow.db` com o sistema fechado |

## 7. Observações de segurança
O StudyFlow foi pensado para **uso pessoal em um único computador**. O login protege o acesso pelo navegador,
mas o servidor embutido do Flask é de desenvolvimento e **não usa HTTPS**: mantenha o padrão `127.0.0.1` e
**não exponha o sistema à rede ou à internet**. Para uso compartilhado seria preciso, no mínimo, HTTPS e um
servidor de produção.

O arquivo `instance/studyflow.db` não é criptografado: quem tem acesso à pasta do sistema tem acesso aos dados
(e pode redefinir a senha com `redefinir_senha.py`). Proteja o computador/usuário do Windows e faça backups.
Detalhes: senhas guardadas com *hash* (Werkzeug), códigos de recuperação guardados apenas como SHA-256,
proteção CSRF em todos os formulários, sessão invalidada ao trocar a senha e redirecionamentos pós-login
restritos a endereços locais.
