"""Listas de opções usadas em formulários, filtros e validações."""

CATEGORIAS = ["Idiomas", "Programação", "Banco de dados", "Análise de dados", "Tecnologia", "Outros"]
NIVEIS = ["Iniciante", "Intermediário", "Avançado"]
STATUS_MATERIA = ["Não iniciado", "Em andamento", "Concluído", "Pausado"]
STATUS_CONTEUDO = ["Não iniciado", "Em andamento", "Concluído"]
STATUS_ATIVIDADE = ["Planejada", "Concluída", "Cancelada"]
PRIORIDADES = ["Baixa", "Média", "Alta"]
STATUS_TAREFA = ["A fazer", "Em andamento", "Concluída"]
TIPOS_META = {
    "horas": "Horas de estudo",
    "dias": "Dias de estudo",
    "conteudos": "Conteúdos concluídos",
    "manual": "Progresso manual (ex.: concluir um curso)",
}
UNIDADES_META = {"horas": "h", "dias": "dias", "conteudos": "conteúdos", "manual": "%"}
STATUS_META = ["Em andamento", "Concluída", "Atrasada"]
DIFICULDADES = ["Não avaliado", "Fácil", "Médio", "Difícil"]
DIFICULDADES_AVALIACAO = ["Fácil", "Médio", "Difícil"]

# Cor (classe "text-bg-*" do Bootstrap) de cada rótulo.
CORES = {
    "Não iniciado": "secondary", "Em andamento": "primary", "Concluído": "success",
    "Pausado": "warning", "Concluída": "success", "A fazer": "secondary",
    "Planejada": "primary", "Cancelada": "dark", "Atrasada": "danger",
    "Alta": "danger", "Média": "warning", "Baixa": "info",
    "Iniciante": "info", "Intermediário": "primary", "Avançado": "dark",
    "Fácil": "success", "Médio": "warning", "Difícil": "danger", "Não avaliado": "secondary",
}

# Chaves de configuração e seus valores padrão (tudo guardado como texto).
CONFIG_PADRAO = {
    "meta_diaria_horas": "2",
    "meta_semanal_horas": "10",
    "pomodoro_foco": "25",
    "pomodoro_pausa": "5",
    "pomodoro_pausa_longa": "15",
    "pomodoro_ciclos": "4",
    "itens_por_pagina": "10",
    "tema": "claro",
    "menu_recolhido": "0",
}
