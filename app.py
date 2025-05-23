
import streamlit as st
import sqlite3
from hashlib import sha256

# ----- BANCO DE DADOS -----
conn = sqlite3.connect("bolao.db", check_same_thread=False)
c = conn.cursor()

# Criação das tabelas
c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    senha TEXT,
    tipo TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS jogos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rodada INTEGER,
    mandante TEXT,
    visitante TEXT,
    placar_mandante INTEGER,
    placar_visitante INTEGER
)''')

c.execute('''CREATE TABLE IF NOT EXISTS palpites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    jogo_id INTEGER,
    palpite_mandante INTEGER,
    palpite_visitante INTEGER,
    pontos INTEGER
)''')

conn.commit()

def hash_senha(senha):
    return sha256(senha.encode()).hexdigest()

def autenticar_usuario(nome, senha):
    senha_hash = hash_senha(senha)
    c.execute("SELECT * FROM usuarios WHERE nome = ? AND senha = ?", (nome, senha_hash))
    return c.fetchone()

def calcular_pontos(real, palpite):
    if real == palpite:
        return 10
    elif (real[0] - real[1]) * (palpite[0] - palpite[1]) > 0 or (real[0] == real[1] and palpite[0] == palpite[1]):
        return 3
    else:
        return 0

st.title("Bolão do Brasileirão 2025")
menu = ["Login", "Cadastro"]
opcao = st.sidebar.selectbox("Menu", menu)

if opcao == "Cadastro":
    st.subheader("Cadastro de Novo Usuário")
    nome = st.text_input("Nome")
    senha = st.text_input("Senha", type="password")
    tipo = st.selectbox("Tipo", ["jogador", "admin"])
    if st.button("Cadastrar"):
        senha_hash = hash_senha(senha)
        c.execute("INSERT INTO usuarios (nome, senha, tipo) VALUES (?, ?, ?)", (nome, senha_hash, tipo))
        conn.commit()
        st.success("Usuário cadastrado com sucesso!")

elif opcao == "Login":
    st.subheader("Login")
    nome = st.text_input("Nome")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        usuario = autenticar_usuario(nome, senha)
        if usuario:
            st.success(f"Bem-vindo, {nome}!")
            tipo = usuario[3]
            st.session_state.usuario_id = usuario[0]
            st.session_state.tipo = tipo

            if tipo == "admin":
                st.header("Cadastrar Jogo")
                rodada = st.number_input("Rodada", min_value=1, step=1)
                mandante = st.text_input("Time Mandante")
                visitante = st.text_input("Time Visitante")
                placar_m = st.number_input("Gols Mandante", step=1)
                placar_v = st.number_input("Gols Visitante", step=1)
                if st.button("Salvar Resultado"):
                    c.execute("INSERT INTO jogos (rodada, mandante, visitante, placar_mandante, placar_visitante) VALUES (?, ?, ?, ?, ?)",
                              (rodada, mandante, visitante, placar_m, placar_v))
                    conn.commit()
                    st.success("Jogo cadastrado!")

            st.header("Meus Palpites")
            jogos = c.execute("SELECT * FROM jogos").fetchall()
            for jogo in jogos:
                st.markdown(f"**{jogo[2]} x {jogo[3]}**")
                palpite_m = st.number_input(f"Placar {jogo[2]}", step=1, key=f"m{jogo[0]}")
                palpite_v = st.number_input(f"Placar {jogo[3]}", step=1, key=f"v{jogo[0]}")
                if st.button(f"Enviar Palpite Jogo {jogo[0]}"):
                    c.execute("SELECT placar_mandante, placar_visitante FROM jogos WHERE id=?", (jogo[0],))
                    real = c.fetchone()
                    if real and None not in real:
                        pontos = calcular_pontos(real, (palpite_m, palpite_v))
                    else:
                        pontos = None
                    c.execute("INSERT INTO palpites (usuario_id, jogo_id, palpite_mandante, palpite_visitante, pontos) VALUES (?, ?, ?, ?, ?)",
                              (st.session_state.usuario_id, jogo[0], palpite_m, palpite_v, pontos))
                    conn.commit()
                    st.success("Palpite registrado!")

            st.header("Ranking")
            ranking = c.execute('''
                SELECT u.nome, SUM(COALESCE(p.pontos, 0)) as total
                FROM usuarios u
                LEFT JOIN palpites p ON u.id = p.usuario_id
                GROUP BY u.nome ORDER BY total DESC
            ''').fetchall()
            for i, (nome_r, total) in enumerate(ranking, 1):
                st.markdown(f"**{i}º {nome_r}** - {total} pontos")
        else:
            st.error("Login inválido")
