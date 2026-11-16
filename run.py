"""Ponto de entrada do StudyFlow.

Uso:  python run.py
Variáveis opcionais: STUDYFLOW_HOST, STUDYFLOW_PORT, STUDYFLOW_DEBUG=1
"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("STUDYFLOW_HOST", "127.0.0.1"),
        port=int(os.environ.get("STUDYFLOW_PORT", "5000")),
        debug=os.environ.get("STUDYFLOW_DEBUG") == "1",
    )
