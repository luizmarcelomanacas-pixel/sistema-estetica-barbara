import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import time
import os
import io

# Tenta importar FPDF, se der erro avisa amigavelmente
try:
    from fpdf import FPDF
except ModuleNotFoundError:
    st.error(
        "ERRO CRÍTICO: O arquivo 'requirements.txt' não está configurado corretamente no GitHub. Adicione 'fpdf' lá.")
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Estética Avançada Bárbara Castro", layout="wide", page_icon="✨")

# --- DESIGN VISUAL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@400;600;700&display=swap');
    .stApp { background: linear-gradient(135deg, #fffcf9 0%, #fcf5f0 50%, #f4eadd 100%); font-family: 'Inter', sans-serif; color: #4a4a4a; }
    h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: #2c2c2c; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #f0e6d2; }
    .stButton>button { background: linear-gradient(90deg, #d4af37 0%, #e6c86e 100%); color: white; border: none; border-radius: 8px; font-weight: 500; transition: all 0.3s ease; text-transform: uppercase; font-size: 14px; box-shadow: 0 4px 6px rgba(212, 175, 55, 0.2); width: 100%; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(212, 175, 55, 0.3); }
    button[kind="secondary"] { background: linear-gradient(90deg, #ff6b6b 0%, #ff8787 100%) !important; }
    [data-testid="stMetric"] { background-color: rgba(255, 255, 255, 0.8); padding: 15px; border-radius: 12px; border: 1px solid #f5efe6; box-shadow: 0 4px 6px rgba(0,0,0,0.03); }
    [data-testid="stMetricValue"] { color: #d4af37; font-family: 'Playfair Display', serif; font-weight: 700; }
    [data-testid="stDataFrame"] { background-color: rgba(255, 255, 255, 0.9); border: 1px solid #f0e6d2; border-radius: 15px; padding: 15px; }
    .stTextInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input { background-color: #ffffff; border: 1px solid #e0dacc; border-radius: 8px; }
    .stTextArea textarea { background-color: #fffcf8; border: 1px solid #e0dacc; }
    @media (max-width: 768px) { h1 { font-size: 24px !important; } .block-container { padding-top: 1rem !important; } }
</style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS (TRANSAÇÃO SEGURA) ---
DB_FILE = 'clinica_gold.db'


def get_connection():
    """Cria uma conexão nova para leitura"""
    return sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)


def run_transaction(query, params=()):
    """
    Executa uma escrita no banco (INSERT/UPDATE/DELETE)
    abrindo e fechando a conexão RAPIDAMENTE para evitar travamento.
    """
    try:
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # Modo Turbo
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True
    except Exception as e:
        st.error(f"Erro no Banco de Dados: {e}")
        return False


def init_db():
    """Inicializa as tabelas se não existirem"""
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
        for q in queries:
            conn.execute(q)

        # Migrações (Colunas novas)
        try:
            conn.execute("ALTER TABLE clientes ADD COLUMN data_nascimento DATE")
        except:
            pass
        try:
            conn.execute("ALTER TABLE clientes ADD COLUMN anamnese TEXT")
        except:
            pass

        # Dados iniciais se vazio
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM procedimentos")
        if cursor.fetchone()[0] == 0:
            dados = [('Botox Full Face', 1200.00, 45, 'Injetáveis'),
                     ('Preenchimento Labial', 1500.00, 60, 'Injetáveis'),
                     ('Limpeza de Pele', 250.00, 90, 'Estética Facial'), ('Bioestimulador', 2200.00, 60, 'Injetáveis')]
            cursor.executemany("INSERT INTO procedimentos (nome, valor, duracao_min, categoria) VALUES (?,?,?,?)",
                               dados)
            conn.commit()


# Inicializa o banco ao abrir
init_db()


# --- FUNÇÕES PDF ---
def gerar_pdf_fluxo(df_dados, periodo_texto, tot_rec, tot_desp, saldo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16);
    pdf.cell(0, 10, txt="Relatorio de Fluxo de Caixa", ln=1, align='C')
    pdf.set_font("Arial", 'I', 10);
    pdf.cell(0, 10, txt="Clinica Estetica Barbara Castro", ln=1, align='C')
    pdf.line(10, 30, 200, 30);
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12);
    pdf.cell(0, 10, txt=f"Periodo: {periodo_texto}", ln=1, align='L')
    pdf.set_fill_color(240, 240, 240);
    pdf.rect(10, 50, 190, 25, 'F');
    pdf.set_y(55)
    pdf.set_font("Arial", 'B', 10);
    pdf.cell(63, 5, "Total Receitas", align='C');
    pdf.cell(63, 5, "Total Despesas", align='C');
    pdf.cell(63, 5, "Saldo Liquido", align='C');
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 12);
    pdf.set_text_color(0, 100, 0);
    pdf.cell(63, 5, f"+ R$ {tot_rec:,.2f}", align='C')
    pdf.set_text_color(150, 0, 0);
    pdf.cell(63, 5, f"- R$ {tot_desp:,.2f}", align='C')
    pdf.set_text_color(0, 0, 0) if saldo >= 0 else pdf.set_text_color(255, 0, 0);
    pdf.cell(63, 5, f"R$ {saldo:,.2f}", align='C');
    pdf.set_text_color(0, 0, 0);
    pdf.ln(20)
    pdf.set_font("Arial", 'B', 10);
    pdf.set_fill_color(212, 175, 55);
    pdf.set_text_color(255, 255, 255)
    pdf.cell(25, 8, "Data", 1, 0, 'C', True);
    pdf.cell(95, 8, "Descricao", 1, 0, 'C', True);
    pdf.cell(30, 8, "Tipo", 1, 0, 'C', True);
    pdf.cell(40, 8, "Valor", 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0);
    pdf.set_font("Arial", size=9)
    for i, row in df_dados.iterrows():
        try:
            d_fmt = datetime.strptime(str(row['Data']), '%Y-%m-%d').strftime('%d/%m/%Y')
        except:
            d_fmt = str(row['Data'])
        desc = row['Descrição'].encode('latin-1', 'replace').decode('latin-1')[:45]
        tipo = row['Tipo'];
        val_str = f"R$ {row['Valor']:,.2f}"
        pdf.cell(25, 7, d_fmt, 1);
        pdf.cell(95, 7, desc, 1)
        pdf.set_text_color(0, 100, 0) if tipo == 'Receita' else pdf.set_text_color(150, 0, 0)
        pdf.cell(30, 7, tipo, 1, 0, 'C');
        pdf.set_text_color(0, 0, 0);
        pdf.cell(40, 7, val_str, 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')


def gerar_ficha_pdf(dados_cliente):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 18);
    pdf.cell(0, 10, "Ficha Clinica - Anamnese", ln=1, align='C')
    pdf.set_font("Arial", 'I', 10);
    pdf.cell(0, 10, "Estetica Avancada Barbara Castro", ln=1, align='C')
    pdf.line(10, 30, 200, 30);
    pdf.ln(10)
    nome = dados_cliente['nome'].encode('latin-1', 'replace').decode('latin-1')
    tel = dados_cliente['telefone']
    try:
        dn = datetime.strptime(str(dados_cliente['data_nascimento']), '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        dn = "--/--/----"
    hist = dados_cliente['anamnese'].encode('latin-1', 'replace').decode('latin-1') if dados_cliente[
        'anamnese'] else "Nenhum historico registrado."
    pdf.set_fill_color(240, 240, 240);
    pdf.set_font("Arial", 'B', 12);
    pdf.cell(0, 10, "1. Dados Pessoais", 1, 1, 'L', True)
    pdf.set_font("Arial", '', 11);
    pdf.ln(2)
    pdf.cell(30, 8, "Nome:", 0);
    pdf.cell(0, 8, nome, 0, 1);
    pdf.cell(30, 8, "Telefone:", 0);
    pdf.cell(0, 8, tel, 0, 1);
    pdf.cell(30, 8, "Nascimento:", 0);
    pdf.cell(0, 8, dn, 0, 1);
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12);
    pdf.cell(0, 10, "2. Historico Clinico / Anamnese", 1, 1, 'L', True);
    pdf.ln(3)
    pdf.set_font("Arial", '', 11);
    pdf.multi_cell(0, 7, hist);
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8);
    pdf.cell(0, 10, f"Documento gerado em {date.today().strftime('%d/%m/%Y')}", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')


# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists("Barbara.jpeg"):
        st.image("Barbara.jpeg", width=130)
    else:
        st.image("https://api.dicebear.com/7.x/avataaars/svg?seed=Barbara&backgroundColor=ffdfbf", width=80)
    st.markdown(
        "<div style='text-align:center;margin-bottom:25px;'><h3>Bárbara Castro</h3><p style='color:#d4af37;font-size:11px;font-weight:700;'>ADMIN ESPECIALISTA</p></div>",
        unsafe_allow_html=True)
    menu = st.radio("NAVEGAÇÃO",
                    ["Dashboard", "Agenda", "Clientes", "Procedimentos", "Financeiro", "Relatórios", "AI Insights"])
    st.markdown("---");
    st.markdown("### 🔐 Segurança")
    with open(DB_FILE, "rb") as fp:
        st.download_button("💾 Baixar Backup", fp, f"backup_{date.today()}.db", "application/x-sqlite3")

# --- CONEXÃO LEITURA ---
conn_read = get_connection()

# --- DASHBOARD ---
if menu == "Dashboard":
    st.title("Bem-vinda, Bárbara")
    df_cli = pd.read_sql("SELECT * FROM clientes", conn_read)
    df_fin = pd.read_sql(
        "SELECT SUM(p.valor) as total FROM agenda a JOIN procedimentos p ON a.procedimento_id = p.id WHERE a.status = 'Concluído'",
        conn_read)
    df_hoje_count = pd.read_sql(f"SELECT * FROM agenda WHERE data_agendamento = '{date.today()}'", conn_read)
    rec = df_fin['total'][0] if df_fin['total'][0] else 0.0
    c1, c2, c3 = st.columns(3);
    c1.metric("Faturamento Total", f"R$ {rec:,.2f}");
    c2.metric("Total Clientes", len(df_cli));
    c3.metric("Agendados Hoje", len(df_hoje_count))
    st.markdown("---");
    st.markdown(f"### 📅 Clientes do Dia ({date.today().strftime('%d/%m/%Y')})")
    df_dia = pd.read_sql(
        f"SELECT a.hora_agendamento as Hora, c.nome as Cliente, p.nome as Procedimento, a.status as Status, c.telefone as Telefone FROM agenda a JOIN clientes c ON a.cliente_id = c.id JOIN procedimentos p ON a.procedimento_id = p.id WHERE a.data_agendamento = '{date.today()}' ORDER BY a.hora_agendamento ASC",
        conn_read)
    if not df_dia.empty:
        st.dataframe(df_dia, use_container_width=True, hide_index=True)
    else:
        st.info(f"Nenhum cliente agendado para hoje.")

# --- AGENDA ---
elif menu == "Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Agendar", "Gerenciar"])
    with t1:
        c1, c2 = st.columns([1, 2])
        with c1:
            cli = pd.read_sql("SELECT * FROM clientes", conn_read);
            proc = pd.read_sql("SELECT * FROM procedimentos", conn_read)
            if not cli.empty:
                with st.form("ag"):
                    cd = {f"{r['id']} - {r['nome']}": r['id'] for i, r in cli.iterrows()}
                    pd_dic = {f"{r['id']} - {r['nome']}": r['id'] for i, r in proc.iterrows()}
                    c_s = st.selectbox("Cliente", list(cd.keys()));
                    p_s = st.selectbox("Serviço", list(pd_dic.keys()))
                    dt = st.date_input("Data", format="DD/MM/YYYY");
                    hr = st.time_input("Hora")
                    if st.form_submit_button("Confirmar"):
                        if run_transaction(
                                "INSERT INTO agenda (cliente_id, procedimento_id, data_agendamento, hora_agendamento, status) VALUES (?,?,?,?,?)",
                                (cd[c_s], pd_dic[p_s], dt, str(hr), "Agendado")):
                            st.success("Agendado!");
                            time.sleep(0.5);
                            st.rerun()
            else:
                st.warning("Sem clientes.")
        with c2:
            st.dataframe(pd.read_sql(
                "SELECT a.id, a.data_agendamento as Data, a.hora_agendamento as Hora, c.nome, p.nome as Servico, a.status FROM agenda a JOIN clientes c ON a.cliente_id = c.id JOIN procedimentos p ON a.procedimento_id = p.id ORDER BY a.data_agendamento",
                conn_read), use_container_width=True, hide_index=True)
    with t2:
        df_a = pd.read_sql(
            "SELECT a.id, c.nome, a.data_agendamento FROM agenda a JOIN clientes c ON a.cliente_id = c.id ORDER BY a.data_agendamento DESC",
            conn_read)
        if not df_a.empty:
            op = {f"{r['id']} - {r['nome']} ({r['data_agendamento']})": r['id'] for i, r in df_a.iterrows()}
            aid = op[st.selectbox("Agendamento", list(op.keys()))]
            curr_cursor = conn_read.cursor();
            curr_cursor.execute("SELECT status FROM agenda WHERE id=?", (aid,));
            curr = curr_cursor.fetchone()[0]
            c1, c2 = st.columns(2)
            with c1:
                ns = st.selectbox("Status", ["Agendado", "Concluído", "Cancelado"],
                                  index=["Agendado", "Concluído", "Cancelado"].index(curr))
                if st.button("Atualizar"):
                    if run_transaction("UPDATE agenda SET status=? WHERE id=?", (ns, aid)): st.success(
                        "Atualizado!"); time.sleep(0.5); st.rerun()
            with c2:
                if st.button("Excluir", type="secondary"):
                    if run_transaction("DELETE FROM agenda WHERE id=?", (aid,)): st.success("Excluído!"); time.sleep(
                        0.5); st.rerun()

# --- CLIENTES ---
elif menu == "Clientes":
    st.title("Clientes")
    t1, t2 = st.tabs(["Novo", "Ficha Completa"])
    with t1:
        with st.form("nc"):
            n = st.text_input("Nome");
            t = st.text_input("Tel");
            d = st.date_input("Nasc", min_value=date(1900, 1, 1), format="DD/MM/YYYY");
            a = st.text_area("Anamnese")
            if st.form_submit_button("Salvar"):
                if run_transaction("INSERT INTO clientes (nome, telefone, data_nascimento, anamnese) VALUES (?,?,?,?)",
                                   (n, t, d, a)):
                    st.success("Cliente Salvo!");
                    time.sleep(1);
                    st.rerun()
        st.dataframe(pd.read_sql("SELECT id, nome, telefone FROM clientes ORDER BY id DESC", conn_read),
                     use_container_width=True)
    with t2:
        cli = pd.read_sql("SELECT * FROM clientes", conn_read)
        if not cli.empty:
            cid = st.selectbox("Buscar", cli['id'].tolist(),
                               format_func=lambda x: f"{x} - {cli[cli['id'] == x].iloc[0]['nome']}")
            cdata = cli[cli['id'] == cid].iloc[0]
            with st.form("ec"):
                en = st.text_input("Nome", cdata['nome']);
                et = st.text_input("Tel", cdata['telefone'])
                try:
                    dv = datetime.strptime(str(cdata['data_nascimento']), '%Y-%m-%d').date()
                except:
                    dv = date.today()
                ed = st.date_input("Nasc", dv, min_value=date(1900, 1, 1), format="DD/MM/YYYY");
                ea = st.text_area("Anamnese", cdata['anamnese'] if cdata['anamnese'] else "", height=200)
                if st.form_submit_button("Salvar Alterações"):
                    if run_transaction(
                            "UPDATE clientes SET nome=?, telefone=?, data_nascimento=?, anamnese=? WHERE id=?",
                            (en, et, str(ed), ea, int(cid))):
                        st.success("Atualizado!");
                        time.sleep(1);
                        st.rerun()
            col1, col2 = st.columns(2)
            with col1:
                pdf_bytes = gerar_ficha_pdf(cdata)
                st.download_button("📄 Baixar Ficha PDF", pdf_bytes, f"Ficha_{cdata['nome']}.pdf", "application/pdf")
            with col2:
                if st.button("🗑️ Excluir Cliente", type="secondary"):
                    if run_transaction("DELETE FROM clientes WHERE id=?", (cid,)): st.success("Excluído!"); time.sleep(
                        1); st.rerun()

# --- PROCEDIMENTOS ---
elif menu == "Procedimentos":
    st.title("Serviços")
    t1, t2 = st.tabs(["Novo", "Gerenciar"])
    with t1:
        with st.form("np"):
            n = st.text_input("Nome");
            c = st.selectbox("Categoria", ["Injetáveis", "Facial", "Corporal", "Laser"]);
            v = st.number_input("Valor", min_value=0.0);
            d = st.number_input("Minutos", step=15)
            if st.form_submit_button("Salvar"):
                if run_transaction("INSERT INTO procedimentos (nome, valor, duracao_min, categoria) VALUES (?,?,?,?)",
                                   (n, v, d, c)):
                    st.success("Serviço Salvo!");
                    time.sleep(0.5);
                    st.rerun()
    with t2:
        proc = pd.read_sql("SELECT * FROM procedimentos", conn_read)
        if not proc.empty:
            pid = st.selectbox("Editar", proc['id'].tolist(),
                               format_func=lambda x: f"{x} - {proc[proc['id'] == x].iloc[0]['nome']}")
            pdata = proc[proc['id'] == pid].iloc[0]
            with st.form("ep"):
                pn = st.text_input("Nome", pdata['nome']);
                pv = st.number_input("Valor", value=pdata['valor'])
                if st.form_submit_button("Atualizar"):
                    if run_transaction("UPDATE procedimentos SET nome=?, valor=? WHERE id=?",
                                       (pn, pv, pid)): st.success("Atualizado!"); time.sleep(0.5); st.rerun()
            if st.button("Excluir", type="secondary"):
                if run_transaction("DELETE FROM procedimentos WHERE id=?", (pid,)): st.success("Excluído!"); time.sleep(
                    0.5); st.rerun()

# --- FINANCEIRO ---
elif menu == "Financeiro":
    st.title("Fluxo de Caixa")
    t1, t2, t3 = st.tabs(["Resumo", "Nova Despesa", "Histórico"])
    q_rec = "SELECT a.data_agendamento as Data, 'Receita: '||p.nome||' ('||c.nome||')' as Descrição, p.valor as Valor, 'Receita' as Tipo FROM agenda a JOIN clientes c ON a.cliente_id=c.id JOIN procedimentos p ON a.procedimento_id=p.id WHERE a.status='Concluído'"
    df_rec = pd.read_sql(q_rec, conn_read)
    df_desp = pd.read_sql(
        "SELECT data_despesa as Data, descricao as Descrição, valor as Valor, 'Despesa' as Tipo FROM despesas",
        conn_read)
    df_fluxo = pd.concat([df_rec, df_desp], ignore_index=True)
    if not df_fluxo.empty: df_fluxo['Data'] = pd.to_datetime(df_fluxo['Data']).dt.date; df_fluxo = df_fluxo.sort_values(
        'Data', ascending=False)
    tot_r = df_rec['Valor'].sum() if not df_rec.empty else 0;
    tot_d = df_desp['Valor'].sum() if not df_desp.empty else 0
    with t1:
        c1, c2, c3 = st.columns(3);
        c1.metric("Entradas", f"R$ {tot_r:,.2f}");
        c2.metric("Saídas", f"R$ {tot_d:,.2f}");
        c3.metric("Saldo", f"R$ {tot_r - tot_d:,.2f}")
        st.dataframe(df_fluxo.style.applymap(
            lambda v: 'background-color:#d4edda' if v == 'Receita' else 'background-color:#f8d7da', subset=['Tipo']),
                     use_container_width=True)
    with t2:
        with st.form("fd"):
            d = st.text_input("Descrição");
            v = st.number_input("Valor", min_value=0.0);
            dt = st.date_input("Data", format="DD/MM/YYYY")
            if st.form_submit_button("Lançar"):
                if run_transaction("INSERT INTO despesas (descricao, valor, data_despesa, categoria) VALUES (?,?,?,?)",
                                   (d, v, dt, "Geral")): st.success("Lançado!"); time.sleep(0.5); st.rerun()
    with t3:
        dlist = pd.read_sql("SELECT id, data_despesa, descricao, valor FROM despesas ORDER BY data_despesa DESC",
                            conn_read)
        if not dlist.empty:
            did = st.selectbox("Excluir", dlist['id'].tolist(),
                               format_func=lambda x: f"{x} - {dlist[dlist['id'] == x].iloc[0]['descricao']}")
            if st.button("Apagar", type="secondary"):
                if run_transaction("DELETE FROM despesas WHERE id=?", (did,)): st.success("Apagado!"); time.sleep(
                    0.5); st.rerun()

# --- RELATÓRIOS ---
elif menu == "Relatórios":
    st.title("📊 Relatórios")
    c1, c2 = st.columns(2);
    d1 = c1.date_input("Início", date.today().replace(day=1));
    d2 = c2.date_input("Fim", date.today())
    q = f"""SELECT a.data_agendamento as Data, 'Receita: '||p.nome||' ('||c.nome||')' as Descrição, 'Receita' as Tipo, p.valor as Valor FROM agenda a JOIN procedimentos p ON a.procedimento_id=p.id JOIN clientes c ON a.cliente_id=c.id WHERE a.status='Concluído' AND a.data_agendamento BETWEEN '{d1}' AND '{d2}' UNION ALL SELECT data_despesa as Data, descricao as Descrição, 'Despesa' as Tipo, valor as Valor FROM despesas WHERE data_despesa BETWEEN '{d1}' AND '{d2}' ORDER BY Data"""
    df_rel = pd.read_sql(q, conn_read)
    if not df_rel.empty:
        rec_p = df_rel[df_rel['Tipo'] == 'Receita']['Valor'].sum();
        desp_p = df_rel[df_rel['Tipo'] == 'Despesa']['Valor'].sum();
        saldo_p = rec_p - desp_p
        st.markdown("---");
        m1, m2, m3 = st.columns(3);
        m1.metric("Receitas", f"R$ {rec_p:,.2f}");
        m2.metric("Despesas", f"R$ {desp_p:,.2f}");
        m3.metric("Saldo", f"R$ {saldo_p:,.2f}")
        st.dataframe(df_rel.style.applymap(lambda v: 'color:green' if v == 'Receita' else 'color:red', subset=['Tipo']),
                     use_container_width=True)
        ce1, ce2 = st.columns(2);
        b = io.BytesIO()
        with pd.ExcelWriter(b, engine='openpyxl') as w:
            df_rel.to_excel(w, index=False)
        ce1.download_button("📊 Excel", b.getvalue(), "relatorio.xlsx", "application/vnd.ms-excel")
        pdf = gerar_pdf_fluxo(df_rel, f"{d1} a {d2}", rec_p, desp_p, saldo_p)
        ce2.download_button("📑 PDF", pdf, "relatorio.pdf", "application/pdf")
    else:
        st.info("Sem dados.")

# --- AI INSIGHTS ---
elif menu == "AI Insights":
    st.title("CRM Inteligente")
    mes = datetime.now().month;
    niv = pd.read_sql(
        f"SELECT nome, data_nascimento FROM clientes WHERE cast(strftime('%m', data_nascimento) as int) = {mes}",
        conn_read)
    if not niv.empty:
        st.success(f"{len(niv)} Aniversariantes!");
        for i, r in niv.iterrows(): st.write(f"🎂 {r['nome']}")
    else:
        st.info("Sem aniversariantes.")