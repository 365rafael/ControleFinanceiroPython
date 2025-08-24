# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import functools
import hashlib  # para senha simples

app = Flask(__name__)
app.secret_key = "uma_chave_secreta_qualquer"

# ----------------------
# Banco de dados
# ----------------------
def init_db():
    conn = sqlite3.connect("financeiro.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT,
            usuario_id INTEGER NOT NULL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ----------------------
# Funções auxiliares
# ----------------------
def formatar(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("usuario_id"):
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# ----------------------
# Rotas de cadastro/login
# ----------------------
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        usuario = request.form["usuario"].strip()  # remove espaços
        senha = hash_senha(request.form["senha"])

        if not usuario or not senha:
            flash("Preencha usuário e senha!", "danger")
            return render_template("cadastro.html")

        conn = sqlite3.connect("financeiro.db")
        cursor = conn.cursor()

        # Verifica se usuário já existe
        cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,))
        existente = cursor.fetchone()

        if existente:
            flash("Usuário já existe!", "danger")
        else:
            cursor.execute(
                "INSERT INTO usuarios (usuario, senha) VALUES (?, ?)",
                (usuario, senha)
            )
            conn.commit()
            flash("Cadastro realizado com sucesso! Faça login.", "success")
            conn.close()
            return redirect(url_for("login"))

        conn.close()

    return render_template("cadastro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = hash_senha(request.form["senha"])

        conn = sqlite3.connect("financeiro.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE usuario=? AND senha=?", (usuario, senha))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["usuario_id"] = user[0]
            session["usuario"] = usuario
            return redirect(url_for("index"))
        else:
            flash("Usuário ou senha incorretos!", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ----------------------
# Rotas principais
# ----------------------
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    filtro_mes = datetime.today().strftime("%Y-%m")
    if request.method == "POST":
        filtro_usuario = request.form.get("mes")  # MM/AAAA
        try:
            mes, ano = filtro_usuario.split("/")
            filtro_mes = f"{ano}-{mes.zfill(2)}"
        except:
            filtro_mes = datetime.today().strftime("%Y-%m")

    conn = sqlite3.connect("financeiro.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transacoes WHERE usuario_id=? ORDER BY data ASC", (session["usuario_id"],))
    transacoes = cursor.fetchall()
    conn.close()

    saldo = sum([t[3] if t[4]=="entrada" else -t[3] for t in transacoes])
    entradas_mes = saidas_mes = 0
    transacoes_filtradas = []
    entradas_mes = 0
    saidas_mes = 0

    for t in transacoes:
        if t[2].startswith(filtro_mes):  # compara YYYY-MM
            # Converte a data de YYYY-MM-DD para DD/MM/AAAA
            data_formatada = datetime.strptime(t[2], "%Y-%m-%d").strftime("%d/%m/%Y")
            transacoes_filtradas.append((
                t[0],       # id
                t[1],       # descricao
                data_formatada,  # data formatada
                t[3],       # valor
                t[4],       # tipo
                t[5]        # categoria
            ))
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
        filtro_mes=f"{filtro_mes[5:7]}/{filtro_mes[0:4]}"
    )

@app.route("/adicionar", methods=["GET", "POST"])
@login_required
def adicionar():
    if request.method=="POST":
        descricao = request.form["descricao"]
        data = request.form["data"]
        valor = float(request.form["valor"])
        tipo = request.form["tipo"]
        categoria = request.form["categoria"] if request.form["categoria"] else None

        conn = sqlite3.connect("financeiro.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transacoes (descricao, data, valor, tipo, categoria, usuario_id) VALUES (?, ?, ?, ?, ?, ?)",
            (descricao, data, valor, tipo, categoria, session["usuario_id"])
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    return render_template("adicionar.html")

@app.route("/editar/<int:id>", methods=["GET","POST"])
@login_required
def editar(id):
    conn = sqlite3.connect("financeiro.db")
    cursor = conn.cursor()

    if request.method=="POST":
        descricao = request.form["descricao"]
        data = request.form["data"]
        valor = float(request.form["valor"])
        tipo = request.form["tipo"]
        categoria = request.form["categoria"] if request.form["categoria"] else None

        cursor.execute(
            "UPDATE transacoes SET descricao=?, data=?, valor=?, tipo=?, categoria=? WHERE id=? AND usuario_id=?",
            (descricao, data, valor, tipo, categoria, id, session["usuario_id"])
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    cursor.execute("SELECT * FROM transacoes WHERE id=? AND usuario_id=?", (id, session["usuario_id"]))
    transacao = cursor.fetchone()
    conn.close()
    return render_template("editar.html", t=transacao)

@app.route("/excluir/<int:id>")
@login_required
def excluir(id):
    conn = sqlite3.connect("financeiro.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transacoes WHERE id=? AND usuario_id=?", (id, session["usuario_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# ----------------------
# Rodar app
# ----------------------
if __name__=="__main__":
    app.run(debug=True)
