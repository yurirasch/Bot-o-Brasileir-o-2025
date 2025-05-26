import streamlit as st
import sqlite3
from hashlib import sha256

st.set_page_config(page_title="FUTELEX 2025", layout="centered")

# Inicializar variáveis de sessão
if 'usuario_id' not in st.session_state:
    st.session_state.usuario_id = None
if 'tipo' not in st.session_state:
    st.session_state.tipo = None

# Exibir logo no topo
st.image("futelex2025.png", use_column_width=True)

# Conexão com banco de dados
conn = sqlite3.connect("bolao.db", check_same_thread=False)
c = conn.cursor()

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

# Se não está logado, mostrar login e cadastro
if st.session_state.usuario_id is None:
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
            if nome and senha:
                usuario = autenticar_usuario(nome, senha)
                if usuario:
                    st.session_state.usuario_id = usuario[0]
                    st.session_state.tipo = usuario[3]
                    st.experimental_rerun()
                else:
                    st.error("Login inválido")
            else:
                st.warning("Por favor, preencha nome e senha!")
else:
    st.success("Login ativo!")

    # Área do admin
    if st.session_state.tipo == "admin":
        st.header("Adicionar Resultado de Jogo")
        jogos = c.execute("SELECT id, mandante, visitante FROM jogos WHERE placar_mandante IS NULL").fetchall()
        for jogo in jogos:
            st.markdown(f"**{jogo[1]} x {jogo[2]}**")
            g1 = st.number_input(f"Gols {jogo[1]}", step=1, key=f"adm_m{jogo[0]}")
            g2 = st.number_input(f"Gols {jogo[2]}", step=1, key=f"adm_v{jogo[0]}")
            if st.button(f"Salvar Resultado {jogo[0]}", key=f"btn_adm_{jogo[0]}"):
                c.execute("UPDATE jogos SET placar_mandante=?, placar_visitante=? WHERE id=?", (g1, g2, jogo[0]))
                palpites = c.execute("SELECT id, palpite_mandante, palpite_visitante FROM palpites WHERE jogo_id=?", (jogo[0],)).fetchall()
                for palpite in palpites:
                    pontos = calcular_pontos((g1, g2), (palpite[1], palpite[2]))
                    c.execute("UPDATE palpites SET pontos=? WHERE id=?", (pontos, palpite[0]))
                conn.commit()
                st.success("Resultado salvo e pontuação atualizada.")

    # Área de palpites para todos
    st.header("Meus Palpites")
    jogos = c.execute("SELECT id, rodada, mandante, visitante, datahora FROM jogos ORDER BY datahora").fetchall()
    for jogo in jogos:
        st.markdown(f"**{jogo[1]}** - {jogo[2]} x {jogo[3]} - {jogo[4]}")
        palpite_m = st.number_input(f"Palpite {jogo[2]}", step=1, key=f"m{jogo[0]}")
        palpite_v = st.number_input(f"Palpite {jogo[3]}", step=1, key=f"v{jogo[0]}")
        if st.button(f"Enviar Palpite {jogo[0]}", key=f"btn_jogador_{jogo[0]}"):
            c.execute("SELECT id FROM palpites WHERE usuario_id=? AND jogo_id=?", (st.session_state.usuario_id, jogo[0]))
            if c.fetchone() is None:
                c.execute("INSERT INTO palpites (usuario_id, jogo_id, palpite_mandante, palpite_visitante, pontos) VALUES (?, ?, ?, ?, ?)",
                          (st.session_state.usuario_id, jogo[0], palpite_m, palpite_v, None))
                conn.commit()
                st.success("Palpite enviado!")
            else:
                st.warning("Você já enviou um palpite para esse jogo.")

    # Ranking final
    st.header("Ranking")
    ranking = c.execute('''
        SELECT u.nome, SUM(COALESCE(p.pontos, 0)) as total
        FROM usuarios u
        LEFT JOIN palpites p ON u.id = p.usuario_id
        GROUP BY u.nome ORDER BY total DESC
    ''').fetchall()
    for i, (nome_r, total) in enumerate(ranking, 1):
        st.markdown(f"**{i}º {nome_r}** - {total} pontos")