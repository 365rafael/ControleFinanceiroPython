# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Criação do banco e tabela
def init_db():
    conn = sqlite3.connect("financeiro.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Função para formatar valores (R$ 1.234,56)
def formatar(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Rota principal com filtro de mês
@app.route("/", methods=["GET", "POST"])
def index():
    # Recebe filtro do usuário no formato MM/AAAA e converte para YYYY-MM
    if request.method == "POST":
        filtro_usuario = request.form.get("mes")  # MM/AAAA
        try:
            mes, ano = filtro_usuario.split("/")
            filtro_mes = f"{ano}-{mes.zfill(2)}"
        except:
            filtro_mes = datetime.today().strftime("%Y-%m")
    else:
        filtro_mes = datetime.today().strftime("%Y-%m")

    conn = sqlite3.connect("financeiro.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transacoes ORDER BY data ASC")  # ordem crescente
    transacoes = cursor.fetchall()
    conn.close()

    saldo = sum([t[3] if t[4] == "entrada" else -t[3] for t in transacoes])

    entradas_mes = 0
    saidas_mes = 0
    transacoes_filtradas = []

    for t in transacoes:
        if t[2].startswith(filtro_mes):
            transacoes_filtradas.append(t)
            if t[4] == "entrada":
                entradas_mes += t[3]
            else:
                saidas_mes += t[3]

    return render_template(
        "index.html",
        transacoes=transacoes_filtradas,
        saldo=formatar(saldo),
        entradas_mes=formatar(entradas_mes),
        saidas_mes=formatar(saidas_mes),
        filtro_mes=f"{filtro_mes[5:7]}/{filtro_mes[0:4]}",  # MM/AAAA
        datetime=datetime
    )

# Rota para adicionar transação
@app.route("/adicionar", methods=["GET", "POST"])
def adicionar():
    if request.method == "POST":
        descricao = request.form["descricao"]
        data = request.form["data"]  # YYYY-MM-DD
        valor = float(request.form["valor"])
        tipo = request.form["tipo"]
        categoria = request.form["categoria"] if request.form["categoria"] else None

        if not data:
            data = datetime.today().strftime("%Y-%m-%d")

        conn = sqlite3.connect("financeiro.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transacoes (descricao, data, valor, tipo, categoria) VALUES (?, ?, ?, ?, ?)",
            (descricao, data, valor, tipo, categoria)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    return render_template("adicionar.html", datetime=datetime)

# Rota para editar transação
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = sqlite3.connect("financeiro.db")
    cursor = conn.cursor()

    if request.method == "POST":
        descricao = request.form["descricao"]
        data = request.form["data"]
        valor = float(request.form["valor"])
        tipo = request.form["tipo"]
        categoria = request.form["categoria"] if request.form["categoria"] else None

        cursor.execute(
            "UPDATE transacoes SET descricao=?, data=?, valor=?, tipo=?, categoria=? WHERE id=?",
            (descricao, data, valor, tipo, categoria, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    cursor.execute("SELECT * FROM transacoes WHERE id=?", (id,))
    transacao = cursor.fetchone()
    conn.close()
    return render_template("editar.html", t=transacao, datetime=datetime)

# Rota para excluir transação
@app.route("/excluir/<int:id>")
def excluir(id):
    conn = sqlite3.connect("financeiro.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transacoes WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
