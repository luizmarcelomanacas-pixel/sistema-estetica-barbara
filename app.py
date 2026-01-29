import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import time
import os
import io
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Estética Avançada Bárbara Castro", layout="wide", page_icon="✨")

# --- DESIGN VISUAL PREMIUM (Tema Porcelana & Ouro) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@400;600;700&display=swap');

    .stApp {
        background: linear-gradient(135deg, #fffcf9 0%, #fcf5f0 50%, #f4eadd 100%);
        font-family: 'Inter', sans-serif;
        color: #4a4a4a;
    }

    h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: #2c2c2c; }

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #f0e6d2;
    }

    .stButton>button {
        background: linear-gradient(90deg, #d4af37 0%, #e6c86e 100%);
        color: white; border: none; border-radius: 8px; font-weight: 500;
        transition: all 0.3s ease; text-transform: uppercase; font-size: 14px;
        box-shadow: 0 4px 6px rgba(212, 175, 55, 0.2);
        width: 100%;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(212, 175, 55, 0.3); }
    button[kind="secondary"] { background: linear-gradient(90deg, #ff6b6b 0%, #ff8787 100%) !important; }

    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.8);
        padding: 15px; border-radius: 12px; border: 1px solid #f5efe6;
        box-shadow: 0 4px 6px rgba(0,0,0,0.03);
    }
    [data-testid="stMetricValue"] { color: #d4af37; font-family: 'Playfair Display', serif; font-weight: 700; }

    [data-testid="stDataFrame"] {
        background-color: rgba(255, 255, 255, 0.9);
        border: 1px solid #f0e6d2; border-radius: 15px; padding: 15px;
    }

    .stTextInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #ffffff; border: 1px solid #e0dacc; border-radius: 8px;
    }
    .stTextArea textarea { background-color: #fffcf8; border: 1px solid #e0dacc; }

    @media (max-width: 768px) {
        h1 { font-size: 24px !important; }
        .block-container { padding-top: 1rem !important; }
    }
</style>
""", unsafe_allow_html=True)


# --- BANCO DE DADOS ---
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect('clinica_gold.db', check_same_thread=False)
    return conn


def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes
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
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS procedimentos
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
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS agenda
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
                 ))''')
    c.execute('''CREATE TABLE IF NOT EXISTS despesas
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
                 )''')

    try:
        c.execute("ALTER TABLE clientes ADD COLUMN data_nascimento DATE")
    except:
        pass
    try:
        c.execute("ALTER TABLE clientes ADD COLUMN anamnese TEXT")
    except:
        pass

    c.execute("SELECT count(*) FROM procedimentos")
    if c.fetchone()[0] == 0:
        dados = [('Botox Full Face', 1200.00, 45, 'Injetáveis'), ('Preenchimento Labial', 1500.00, 60, 'Injetáveis'),
                 ('Limpeza de Pele', 250.00, 90, 'Estética Facial'), ('Bioestimulador', 2200.00, 60, 'Injetáveis')]
        c.executemany("INSERT INTO procedimentos (nome, valor, duracao_min, categoria) VALUES (?,?,?,?)", dados)
        conn.commit()
    return conn


try:
    conn = init_db()
except:
    st.stop()


# --- FUNÇÃO PDF ---
def gerar_pdf_fluxo(df_dados, periodo_texto, tot_rec, tot_desp, saldo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="Relatorio de Fluxo de Caixa", ln=1, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, txt="Clinica Estetica Barbara Castro", ln=1, align='C')
    pdf.line(10, 30, 200, 30)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt=f"Periodo: {periodo_texto}", ln=1, align='L')

    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, 50, 190, 25, 'F')
    pdf.set_y(55)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(63, 5, "Total Receitas", align='C')
    pdf.cell(63, 5, "Total Despesas", align='C')
    pdf.cell(63, 5, "Saldo Liquido", align='C')
    pdf.ln(8)

    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 100, 0)
    pdf.cell(63, 5, f"+ R$ {tot_rec:,.2f}", align='C')
    pdf.set_text_color(150, 0, 0)
    pdf.cell(63, 5, f"- R$ {tot_desp:,.2f}", align='C')
    if saldo >= 0:
        pdf.set_text_color(0, 0, 0)
    else:
        pdf.set_text_color(255, 0, 0)
    pdf.cell(63, 5, f"R$ {saldo:,.2f}", align='C')
    pdf.set_text_color(0, 0, 0)

    pdf.ln(20)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(212, 175, 55)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(25, 8, "Data", 1, 0, 'C', True)
    pdf.cell(95, 8, "Descricao", 1, 0, 'C', True)
    pdf.cell(30, 8, "Tipo", 1, 0, 'C', True)
    pdf.cell(40, 8, "Valor", 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=9)

    for i, row in df_dados.iterrows():
        try:
            d_fmt = datetime.strptime(str(row['Data']), '%Y-%m-%d').strftime('%d/%m/%Y')
        except:
            d_fmt = str(row['Data'])
        desc = row['Descrição'].encode('latin-1', 'replace').decode('latin-1')[:45]
        tipo = row['Tipo']
        val_str = f"R$ {row['Valor']:,.2f}"

        pdf.cell(25, 7, d_fmt, 1)
        pdf.cell(95, 7, desc, 1)
        if tipo == 'Receita':
            pdf.set_text_color(0, 100, 0)
        else:
            pdf.set_text_color(150, 0, 0)
        pdf.cell(30, 7, tipo, 1, 0, 'C')
        pdf.set_text_color(0, 0, 0)
        pdf.cell(40, 7, val_str, 1, 1, 'R')

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

    # --- ÁREA DE BACKUP NA SIDEBAR ---
    st.markdown("---")
    st.markdown("### 🔐 Segurança")
    st.markdown("<span style='font-size:12px; color:gray;'>Baixe o backup diariamente!</span>", unsafe_allow_html=True)

    # Botão de Download do Banco de Dados (.db)
    with open("clinica_gold.db", "rb") as fp:
        btn = st.download_button(
            label="💾 Baixar Backup (Banco de Dados)",
            data=fp,
            file_name=f"backup_clinica_{date.today()}.db",
            mime="application/x-sqlite3",
            help="Clique aqui para salvar todos os dados da clínica no seu computador."
        )

# --- DASHBOARD ---
if menu == "Dashboard":
    st.title("Bem-vinda, Bárbara")
    df_ag = pd.read_sql("SELECT * FROM agenda", conn)
    df_cli = pd.read_sql("SELECT * FROM clientes", conn)
    df_receita = pd.read_sql(
        "SELECT SUM(p.valor) as total FROM agenda a JOIN procedimentos p ON a.procedimento_id = p.id WHERE a.status = 'Concluído'",
        conn)
    rec = df_receita['total'][0] if df_receita['total'][0] else 0.0
    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento", f"R$ {rec:,.2f}");
    c2.metric("Clientes", len(df_cli));
    c3.metric("Hoje", len(df_ag[df_ag['data_agendamento'] == str(date.today())]))
    if not df_ag.empty:
        st.markdown("### 📅 Agenda Recente")
        st.dataframe(pd.read_sql(
            "SELECT a.data_agendamento as Data, a.hora_agendamento as Hora, c.nome, p.nome as Servico, a.status FROM agenda a JOIN clientes c ON a.cliente_id = c.id JOIN procedimentos p ON a.procedimento_id = p.id WHERE a.status = 'Agendado' ORDER BY a.data_agendamento LIMIT 5",
            conn), use_container_width=True, hide_index=True)

# --- AGENDA ---
elif menu == "Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Agendar", "Gerenciar"])
    with t1:
        c1, c2 = st.columns([1, 2])
        with c1:
            cli = pd.read_sql("SELECT * FROM clientes", conn);
            proc = pd.read_sql("SELECT * FROM procedimentos", conn)
            if not cli.empty:
                with st.form("ag"):
                    cd = {f"{r['id']} - {r['nome']}": r['id'] for i, r in cli.iterrows()}
                    pd_dic = {f"{r['id']} - {r['nome']}": r['id'] for i, r in proc.iterrows()}
                    c_s = st.selectbox("Cliente", list(cd.keys()));
                    p_s = st.selectbox("Serviço", list(pd_dic.keys()))
                    dt = st.date_input("Data", format="DD/MM/YYYY");
                    hr = st.time_input("Hora")
                    if st.form_submit_button("Confirmar"):
                        conn.execute(
                            "INSERT INTO agenda (cliente_id, procedimento_id, data_agendamento, hora_agendamento, status) VALUES (?,?,?,?,?)",
                            (cd[c_s], pd_dic[p_s], dt, str(hr), "Agendado"));
                        conn.commit();
                        st.success("Agendado!");
                        time.sleep(0.5);
                        st.rerun()
            else:
                st.warning("Sem clientes.")
        with c2:
            st.dataframe(pd.read_sql(
                "SELECT a.id, a.data_agendamento as Data, a.hora_agendamento as Hora, c.nome, p.nome as Servico, a.status FROM agenda a JOIN clientes c ON a.cliente_id = c.id JOIN procedimentos p ON a.procedimento_id = p.id ORDER BY a.data_agendamento",
                conn), use_container_width=True, hide_index=True)
    with t2:
        df_a = pd.read_sql(
            "SELECT a.id, c.nome, a.data_agendamento FROM agenda a JOIN clientes c ON a.cliente_id = c.id ORDER BY a.data_agendamento DESC",
            conn)
        if not df_a.empty:
            op = {f"{r['id']} - {r['nome']} ({r['data_agendamento']})": r['id'] for i, r in df_a.iterrows()}
            aid = op[st.selectbox("Agendamento", list(op.keys()))]
            curr = conn.execute("SELECT status FROM agenda WHERE id=?", (aid,)).fetchone()[0]
            c1, c2 = st.columns(2)
            with c1:
                ns = st.selectbox("Status", ["Agendado", "Concluído", "Cancelado"],
                                  index=["Agendado", "Concluído", "Cancelado"].index(curr))
                if st.button("Atualizar"): conn.execute("UPDATE agenda SET status=? WHERE id=?",
                                                        (ns, aid)); conn.commit(); st.rerun()
            with c2:
                st.write("");
                st.write("")
                if st.button("Excluir", type="secondary"): conn.execute("DELETE FROM agenda WHERE id=?",
                                                                        (aid,)); conn.commit(); st.rerun()

# --- CLIENTES ---
elif menu == "Clientes":
    st.title("Clientes")
    t1, t2 = st.tabs(["Novo", "Ficha"])
    with t1:
        with st.form("nc"):
            n = st.text_input("Nome");
            t = st.text_input("Tel");
            d = st.date_input("Nasc", min_value=date(1900, 1, 1), format="DD/MM/YYYY");
            a = st.text_area("Anamnese")
            if st.form_submit_button("Salvar"): conn.execute(
                "INSERT INTO clientes (nome, telefone, data_nascimento, anamnese) VALUES (?,?,?,?)",
                (n, t, d, a)); conn.commit(); st.rerun()
        st.dataframe(pd.read_sql("SELECT id, nome, telefone FROM clientes ORDER BY id DESC", conn),
                     use_container_width=True)
    with t2:
        cli = pd.read_sql("SELECT * FROM clientes", conn)
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
                ea = st.text_area("Anamnese", cdata['anamnese'] if cdata['anamnese'] else "")
                if st.form_submit_button("Salvar"): conn.execute(
                    "UPDATE clientes SET nome=?, telefone=?, data_nascimento=?, anamnese=? WHERE id=?",
                    (en, et, str(ed), ea, cid)); conn.commit(); st.rerun()
            if st.button("Excluir", type="secondary"): conn.execute("DELETE FROM clientes WHERE id=?",
                                                                    (cid,)); conn.commit(); st.rerun()

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
            if st.form_submit_button("Salvar"): conn.execute(
                "INSERT INTO procedimentos (nome, valor, duracao_min, categoria) VALUES (?,?,?,?)",
                (n, v, d, c)); conn.commit(); st.rerun()
        st.dataframe(pd.read_sql("SELECT * FROM procedimentos", conn), use_container_width=True)
    with t2:
        proc = pd.read_sql("SELECT * FROM procedimentos", conn)
        if not proc.empty:
            pid = st.selectbox("Editar", proc['id'].tolist(),
                               format_func=lambda x: f"{x} - {proc[proc['id'] == x].iloc[0]['nome']}")
            pdata = proc[proc['id'] == pid].iloc[0]
            with st.form("ep"):
                pn = st.text_input("Nome", pdata['nome']);
                pv = st.number_input("Valor", value=pdata['valor'])
                if st.form_submit_button("Atualizar"): conn.execute(
                    "UPDATE procedimentos SET nome=?, valor=? WHERE id=?", (pn, pv, pid)); conn.commit(); st.rerun()
            if st.button("Excluir", type="secondary"): conn.execute("DELETE FROM procedimentos WHERE id=?",
                                                                    (pid,)); conn.commit(); st.rerun()

# --- FINANCEIRO ---
elif menu == "Financeiro":
    st.title("Fluxo de Caixa")
    t1, t2, t3 = st.tabs(["Resumo", "Nova Despesa", "Histórico Despesas"])

    q_rec = "SELECT a.data_agendamento as Data, 'Receita: '||p.nome||' ('||c.nome||')' as Descrição, p.valor as Valor, 'Receita' as Tipo FROM agenda a JOIN clientes c ON a.cliente_id=c.id JOIN procedimentos p ON a.procedimento_id=p.id WHERE a.status='Concluído'"
    df_rec = pd.read_sql(q_rec, conn)
    df_desp = pd.read_sql(
        "SELECT data_despesa as Data, descricao as Descrição, valor as Valor, 'Despesa' as Tipo FROM despesas", conn)
    df_fluxo = pd.concat([df_rec, df_desp], ignore_index=True)
    if not df_fluxo.empty:
        df_fluxo['Data'] = pd.to_datetime(df_fluxo['Data']).dt.date
        df_fluxo = df_fluxo.sort_values('Data', ascending=False)

    tot_r = df_rec['Valor'].sum() if not df_rec.empty else 0
    tot_d = df_desp['Valor'].sum() if not df_desp.empty else 0

    with t1:
        c1, c2, c3 = st.columns(3)
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
            if st.form_submit_button("Lançar"): conn.execute(
                "INSERT INTO despesas (descricao, valor, data_despesa, categoria) VALUES (?,?,?,?)",
                (d, v, dt, "Geral")); conn.commit(); st.rerun()
    with t3:
        dlist = pd.read_sql("SELECT id, data_despesa, descricao, valor FROM despesas ORDER BY data_despesa DESC", conn)
        if not dlist.empty:
            did = st.selectbox("Excluir", dlist['id'].tolist(),
                               format_func=lambda x: f"{x} - {dlist[dlist['id'] == x].iloc[0]['descricao']}")
            if st.button("Apagar Despesa", type="secondary"): conn.execute("DELETE FROM despesas WHERE id=?",
                                                                           (did,)); conn.commit(); st.rerun()
            st.dataframe(dlist, use_container_width=True)

# --- RELATÓRIOS ---
elif menu == "Relatórios":
    st.title("📊 Relatório de Fluxo de Caixa")
    c1, c2 = st.columns(2)
    d1 = c1.date_input("Início", date.today().replace(day=1), format="DD/MM/YYYY")
    d2 = c2.date_input("Fim", date.today(), format="DD/MM/YYYY")

    q_unificada = f"""
        SELECT a.data_agendamento as Data, 'Receita: '||p.nome||' ('||c.nome||')' as Descrição, 'Receita' as Tipo, p.valor as Valor 
        FROM agenda a JOIN procedimentos p ON a.procedimento_id=p.id JOIN clientes c ON a.cliente_id=c.id
        WHERE a.status='Concluído' AND a.data_agendamento BETWEEN '{d1}' AND '{d2}'
        UNION ALL
        SELECT data_despesa as Data, descricao as Descrição, 'Despesa' as Tipo, valor as Valor 
        FROM despesas WHERE data_despesa BETWEEN '{d1}' AND '{d2}' ORDER BY Data
    """
    df_rel = pd.read_sql(q_unificada, conn)

    if not df_rel.empty:
        rec_p = df_rel[df_rel['Tipo'] == 'Receita']['Valor'].sum()
        desp_p = df_rel[df_rel['Tipo'] == 'Despesa']['Valor'].sum()
        saldo_p = rec_p - desp_p

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Receitas", f"R$ {rec_p:,.2f}");
        m2.metric("Despesas", f"R$ {desp_p:,.2f}");
        m3.metric("Saldo", f"R$ {saldo_p:,.2f}", delta_color="normal" if saldo_p >= 0 else "inverse")
        st.dataframe(df_rel.style.applymap(lambda v: 'color:green' if v == 'Receita' else 'color:red', subset=['Tipo']),
                     use_container_width=True)

        st.subheader("📥 Exportar")
        ce1, ce2 = st.columns(2)
        b = io.BytesIO()
        with pd.ExcelWriter(b, engine='openpyxl') as writer:
            pd.DataFrame({'Item': ['Receitas', 'Despesas', 'Saldo'], 'Valor': [rec_p, desp_p, saldo_p]}).to_excel(
                writer, sheet_name='Resumo', index=False)
            df_rel.to_excel(writer, sheet_name='Lancamentos', index=False)
        ce1.download_button("📊 Excel", b.getvalue(), f"fluxo_{d1}_{d2}.xlsx", "application/vnd.ms-excel")
        pdf_bytes = gerar_pdf_fluxo(df_rel, f"{d1.strftime('%d/%m/%Y')} a {d2.strftime('%d/%m/%Y')}", rec_p, desp_p,
                                    saldo_p)
        ce2.download_button("📑 PDF", pdf_bytes, f"fluxo_{d1}_{d2}.pdf", "application/pdf")
    else:
        st.info("Sem dados no período.")

# --- AI INSIGHTS ---
elif menu == "AI Insights":
    st.title("CRM Inteligente")
    mes = datetime.now().month
    niv = pd.read_sql(
        f"SELECT nome, data_nascimento FROM clientes WHERE cast(strftime('%m', data_nascimento) as int) = {mes}", conn)
    if not niv.empty:
        st.success(f"{len(niv)} Aniversariantes!")
        for i, r in niv.iterrows(): st.write(f"🎂 {r['nome']}")
    else:
        st.info("Sem aniversariantes.")