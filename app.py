import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import time
import os
import requests  # Necessário para a Z-API
from urllib.parse import quote

# Tenta importar FPDF, se der erro ignora para não quebrar o app
try:
    from fpdf import FPDF
except:
    pass

# --- CONFIGURAÇÃO DA Z-API (OPÇÃO PAGA/PROFISSIONAL) ---
# Substitua pelos dados do seu painel Z-API
ZAPI_INSTANCE_ID = "3EE0C802EF9F42C7CA3512E352C1CFB5"  # Ex: 3A2F3D...
ZAPI_TOKEN = "E22495F303A338BA9B19D1D3"  # Ex: 4b8c9d...
SEU_CELULAR = "5521985554643"  # Seu número (55 + DDD + Numero)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Estética Avançada Bárbara Castro", layout="wide", page_icon="✨")

# --- DESIGN VISUAL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@400;600;700&display=swap');
    .stApp { background: linear-gradient(135deg, #fffcf9 0%, #fcf5f0 50%, #f4eadd 100%); font-family: 'Inter', sans-serif; color: #4a4a4a; }
    h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: #2c2c2c; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #f0e6d2; }
    .stButton>button { background: linear-gradient(90deg, #d4af37 0%, #e6c86e 100%); color: white; border: none; border-radius: 8px; font-weight: 500; width: 100%; transition: all 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(212, 175, 55, 0.3); }
    [data-testid="stMetric"] { background-color: rgba(255,255,255,0.8); border-radius: 12px; border: 1px solid #f5efe6; padding: 10px; }
    [data-testid="stDataFrame"] { background-color: rgba(255,255,255,0.9); border-radius: 15px; padding: 10px; }
    .zap-btn { display: inline-block; text-decoration: none; background-color: #25D366; color: white !important; padding: 10px 20px; border-radius: 8px; font-weight: bold; text-align: center; width: 100%; margin-top: 10px; }
    .zap-btn:hover { background-color: #128C7E; }
</style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS (ANTI-TRAVAMENTO) ---
DB_FILE = 'clinica_gold.db'


def run_transaction(query, params=()):
    """Executa escrita no banco de forma rápida e segura"""
    try:
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True
    except Exception as e:
        st.error(f"Erro no Banco: {e}")
        return False


def get_data(query):
    """Lê dados do banco"""
    try:
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            return pd.read_sql(query, conn)
    except:
        return pd.DataFrame()


def init_db():
    """Cria tabelas e colunas se não existirem"""
    queries = [
        '''CREATE TABLE IF NOT EXISTS clientes
           (
               id
               INTEGER
               PRIMARY
               KEY
               AUTOINCREMENT,
               nome
               TEXT,
               telefone
               TEXT,
               email
               TEXT,
               data_nascimento
               DATE,
               anamnese
               TEXT,
               created_at
               DATETIME
               DEFAULT
               CURRENT_TIMESTAMP
           )''',
        '''CREATE TABLE IF NOT EXISTS procedimentos
           (
               id
               INTEGER
               PRIMARY
               KEY
               AUTOINCREMENT,
               nome
               TEXT,
               valor
               REAL,
               duracao_min
               INTEGER,
               categoria
               TEXT
           )''',
        '''CREATE TABLE IF NOT EXISTS agenda
        (
            id
            INTEGER
            PRIMARY
            KEY
            AUTOINCREMENT,
            cliente_id
            INTEGER,
            procedimento_id
            INTEGER,
            data_agendamento
            DATE,
            hora_agendamento
            TIME,
            status
            TEXT,
            FOREIGN
            KEY
           (
            cliente_id
           ) REFERENCES clientes
           (
               id
           ), FOREIGN KEY
           (
               procedimento_id
           ) REFERENCES procedimentos
           (
               id
           ))''',
        '''CREATE TABLE IF NOT EXISTS despesas
           (
               id
               INTEGER
               PRIMARY
               KEY
               AUTOINCREMENT,
               descricao
               TEXT,
               valor
               REAL,
               data_despesa
               DATE,
               categoria
               TEXT,
               created_at
               DATETIME
               DEFAULT
               CURRENT_TIMESTAMP
           )'''
    ]
    with sqlite3.connect(DB_FILE) as conn:
        for q in queries: conn.execute(q)
        try:
            conn.execute("ALTER TABLE clientes ADD COLUMN data_nascimento DATE");
        except:
            pass
        try:
            conn.execute("ALTER TABLE clientes ADD COLUMN anamnese TEXT")
        except:
            pass
        # Dados iniciais
        cur = conn.cursor()
        if cur.execute("SELECT count(*) FROM procedimentos").fetchone()[0] == 0:
            cur.executemany("INSERT INTO procedimentos (nome, valor, duracao_min, categoria) VALUES (?,?,?,?)",
                            [('Botox', 1200, 45, 'Injetáveis'), ('Preenchimento', 1500, 60, 'Injetáveis'),
                             ('Limpeza', 250, 90, 'Facial')])
            conn.commit()


init_db()


# --- FUNÇÃO Z-API (AUTOMÁTICA) ---
def enviar_agenda_zapi():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        hoje = date.today()
        query = f"""
            SELECT a.hora_agendamento, c.nome, p.nome as proc 
            FROM agenda a 
            JOIN clientes c ON a.cliente_id = c.id 
            JOIN procedimentos p ON a.procedimento_id = p.id 
            WHERE a.data_agendamento = '{hoje}' AND a.status = 'Agendado'
            ORDER BY a.hora_agendamento
        """
        df = pd.read_sql(query, conn)
        conn.close()
    except Exception as e:
        return f"Erro ao ler banco: {e}"

    if df.empty:
        mensagem = f"Bom dia, Bárbara! ☀️\n\n📅 *Agenda ({hoje.strftime('%d/%m')}):*\nNenhum cliente agendado."
    else:
        mensagem = f"Bom dia, Bárbara! ☀️\n\n📅 *Agenda ({hoje.strftime('%d/%m')}):*\n-------------------\n"
        for i, row in df.iterrows():
            hora = str(row['hora_agendamento'])[:5]
            mensagem += f"⏰ *{hora}* - {row['nome']}\n   └ _{row['proc']}_\n\n"
        mensagem += "-------------------\nBom trabalho! 🚀"

    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
    try:
        response = requests.post(url, json={"phone": SEU_CELULAR, "message": mensagem},
                                 headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            return "✅ Enviado via Z-API!"
        else:
            return f"❌ Erro Z-API: {response.text}"
    except Exception as e:
        return f"❌ Erro Conexão: {e}"


# --- FUNÇÕES PDF ---
def gerar_ficha_pdf(dados):
    pdf = FPDF();
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16);
    pdf.cell(0, 10, "Ficha Clinica", ln=1, align='C')
    pdf.set_font("Arial", '', 12);
    pdf.ln(10)
    pdf.cell(0, 10, f"Nome: {dados['nome']}", ln=1)
    pdf.cell(0, 10, f"Telefone: {dados['telefone']}", ln=1)
    pdf.ln(5);
    pdf.cell(0, 10, "Anamnese:", ln=1)
    pdf.multi_cell(0, 7, dados['anamnese'] if dados['anamnese'] else "Sem registro.")
    return pdf.output(dest='S').encode('latin-1')


# --- GATILHO EXTERNO (CRON-JOB) ---
if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_zapi":
    res = enviar_agenda_zapi()
    st.write(res);
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists("Barbara.jpeg"):
        st.image("Barbara.jpeg", width=130)
    else:
        st.markdown("### 👑 Bárbara Castro")
    st.markdown("<p style='color:#d4af37;font-size:12px;font-weight:700;text-align:center'>ADMIN ESPECIALISTA</p>",
                unsafe_allow_html=True)
    menu = st.radio("NAVEGAÇÃO", ["Dashboard", "Agenda", "Clientes", "Procedimentos", "Financeiro", "Relatórios"])
    st.markdown("---")

    # Botão Manual (Caso a Z-API não esteja paga ainda)
    if st.button("📲 Gerar Zap Manual"):
        hoje = date.today()
        df_zap = get_data(
            f"SELECT a.hora_agendamento, c.nome, p.nome as proc FROM agenda a JOIN clientes c ON a.cliente_id=c.id JOIN procedimentos p ON a.procedimento_id=p.id WHERE a.data_agendamento='{hoje}' AND a.status='Agendado' ORDER BY a.hora_agendamento")
        txt = f"📅 *Agenda ({hoje.strftime('%d/%m')}):*\n\n"
        if df_zap.empty:
            txt += "Livre!"
        else:
            for i, r in df_zap.iterrows(): txt += f"⏰ {str(r['hora_agendamento'])[:5]} - {r['nome']}\n"
        lnk = f"https://wa.me//?text={quote(txt)}"
        st.markdown(f'<a href="{lnk}" target="_blank" class="zap-btn">Abrir WhatsApp</a>', unsafe_allow_html=True)

    st.markdown("---")
    with open(DB_FILE, "rb") as fp:
        st.download_button("💾 Backup Completo", fp, f"backup_{date.today()}.db")

# --- PÁGINAS ---
if menu == "Dashboard":
    st.title("Bem-vinda, Bárbara")
    df_hj = get_data(f"SELECT * FROM agenda WHERE data_agendamento='{date.today()}'")
    rec = get_data(
        "SELECT SUM(valor) as t FROM agenda a JOIN procedimentos p ON a.procedimento_id=p.id WHERE a.status='Concluído'")
    total = rec['t'][0] if not rec.empty and rec['t'][0] else 0.0
    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento", f"R$ {total:,.2f}");
    c2.metric("Agendados Hoje", len(df_hj));
    c3.metric("Dia", date.today().strftime('%d/%m'))
    st.markdown(f"### 📅 Clientes de Hoje")
    q_dia = f"SELECT a.hora_agendamento as Hora, c.nome as Cliente, p.nome as Procedimento, a.status FROM agenda a JOIN clientes c ON a.cliente_id=c.id JOIN procedimentos p ON a.procedimento_id=p.id WHERE a.data_agendamento='{date.today()}' ORDER BY Hora"
    df_dia = get_data(q_dia)
    if not df_dia.empty:
        st.dataframe(df_dia, use_container_width=True, hide_index=True)
    else:
        st.info("Agenda livre hoje.")

elif menu == "Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Agendar", "Gerenciar"])
    with t1:
        c1, c2 = st.columns([1, 2])
        with c1:
            cli = get_data("SELECT * FROM clientes");
            proc = get_data("SELECT * FROM procedimentos")
            if not cli.empty:
                with st.form("new_ag"):
                    cd = {f"{r['id']} - {r['nome']}": r['id'] for i, r in cli.iterrows()}
                    pd_dic = {f"{r['id']} - {r['nome']}": r['id'] for i, r in proc.iterrows()}
                    c = st.selectbox("Cliente", list(cd.keys()));
                    p = st.selectbox("Serviço", list(pd_dic.keys()))
                    d = st.date_input("Data", format="DD/MM/YYYY");
                    h = st.time_input("Hora")
                    if st.form_submit_button("Agendar"):
                        if run_transaction(
                            "INSERT INTO agenda (cliente_id, procedimento_id, data_agendamento, hora_agendamento, status) VALUES (?,?,?,?,?)",
                            (cd[c], pd_dic[p], d, str(h), "Agendado")): st.success("Agendado!"); time.sleep(
                            0.5); st.rerun()
            else:
                st.warning("Cadastre clientes antes.")
        with c2:
            st.dataframe(get_data(
                "SELECT a.data_agendamento as Data, a.hora_agendamento as Hora, c.nome, p.nome as Servico, a.status FROM agenda a JOIN clientes c ON a.cliente_id=c.id JOIN procedimentos p ON a.procedimento_id=p.id ORDER BY Data DESC"),
                         use_container_width=True)
    with t2:
        ag = get_data(
            "SELECT a.id, c.nome, a.data_agendamento FROM agenda a JOIN clientes c ON a.cliente_id=c.id ORDER BY Data DESC")
        if not ag.empty:
            op = {f"{r['id']} - {r['nome']} ({r['data_agendamento']})": r['id'] for i, r in ag.iterrows()}
            aid = op[st.selectbox("Selecione para Editar", list(op.keys()))]
            col1, col2 = st.columns(2)
            if col1.button("✅ Concluir Atendimento"): run_transaction("UPDATE agenda SET status='Concluído' WHERE id=?",
                                                                      (aid,)); st.rerun()
            if col2.button("🗑️ Excluir Agendamento", type="secondary"): run_transaction("DELETE FROM agenda WHERE id=?",
                                                                                        (aid,)); st.rerun()

elif menu == "Clientes":
    st.title("Clientes")
    t1, t2 = st.tabs(["Novo", "Editar/Ficha"])
    with t1:
        with st.form("nc"):
            n = st.text_input("Nome");
            t = st.text_input("Tel");
            d = st.date_input("Nasc", min_value=date(1900, 1, 1));
            a = st.text_area("Anamnese")
            if st.form_submit_button("Salvar"):
                if run_transaction("INSERT INTO clientes (nome, telefone, data_nascimento, anamnese) VALUES (?,?,?,?)",
                                   (n, t, d, a)): st.success("Salvo!"); st.rerun()
        st.dataframe(get_data("SELECT id, nome, telefone FROM clientes ORDER BY id DESC"), use_container_width=True)
    with t2:
        cli = get_data("SELECT * FROM clientes")
        if not cli.empty:
            cid = st.selectbox("Buscar Cliente", cli['id'].tolist(),
                               format_func=lambda x: f"{x} - {cli[cli['id'] == x].iloc[0]['nome']}")
            cd = cli[cli['id'] == cid].iloc[0]
            with st.form("ec"):
                nn = st.text_input("Nome", cd['nome']);
                nt = st.text_input("Tel", cd['telefone']);
                na = st.text_area("Anamnese", cd['anamnese'] if cd['anamnese'] else "", height=150)
                if st.form_submit_button("Atualizar"): run_transaction(
                    "UPDATE clientes SET nome=?, telefone=?, anamnese=? WHERE id=?", (nn, nt, na, cid)); st.rerun()
            c1, c2 = st.columns(2)
            try:
                c1.download_button("📄 Baixar PDF", gerar_ficha_pdf(cd), f"ficha_{cd['nome']}.pdf", "application/pdf")
            except:
                c1.warning("Instale 'fpdf' no requirements.txt")
            if c2.button("Excluir Cliente", type="secondary"): run_transaction("DELETE FROM clientes WHERE id=?",
                                                                               (cid,)); st.rerun()

elif menu == "Procedimentos":
    st.title("Serviços")
    with st.form("np"):
        n = st.text_input("Nome");
        v = st.number_input("Valor");
        d = st.number_input("Minutos", step=15)
        if st.form_submit_button("Salvar"): run_transaction(
            "INSERT INTO procedimentos (nome, valor, duracao_min, categoria) VALUES (?,?,?,?)",
            (n, v, d, "Geral")); st.rerun()
    st.dataframe(get_data("SELECT * FROM procedimentos"), use_container_width=True)

elif menu == "Financeiro":
    st.title("Fluxo de Caixa")
    t1, t2 = st.tabs(["Resumo", "Lançar Despesa"])
    with t1:
        rec = get_data(
            "SELECT SUM(p.valor) FROM agenda a JOIN procedimentos p ON a.procedimento_id=p.id WHERE a.status='Concluído'").iloc[
                  0, 0] or 0
        desp = get_data("SELECT SUM(valor) FROM despesas").iloc[0, 0] or 0
        st.metric("Saldo Líquido", f"R$ {rec - desp:,.2f}")
    with t2:
        with st.form("nd"):
            d = st.text_input("Descrição");
            v = st.number_input("Valor");
            dt = st.date_input("Data")
            if st.form_submit_button("Lançar"): run_transaction(
                "INSERT INTO despesas (descricao, valor, data_despesa, categoria) VALUES (?,?,?,?)",
                (d, v, dt, "Geral")); st.rerun()

elif menu == "Relatórios":
    st.title("Relatórios")
    df = get_data("SELECT * FROM agenda")
    st.dataframe(df)