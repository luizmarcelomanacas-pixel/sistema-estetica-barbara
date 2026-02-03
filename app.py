import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import time
import os
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Tenta importar FPDF para PDFs
try:
    from fpdf import FPDF
except:
    pass

# --- CONFIGURAÇÃO DE E-MAIL (PREENCHA AQUI SEUS DADOS REAIS) ---
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'
EMAIL_SENHA = 'njyt nrvd vtro jgwi'  # Senha de App de 16 dígitos
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Estética Avançada Bárbara Castro", layout="wide", page_icon="✨")

# --- DESIGN VISUAL PREMIUM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@400;600;700&display=swap');

    .stApp { background: linear-gradient(135deg, #fffcf9 0%, #fcf5f0 50%, #f4eadd 100%); font-family: 'Inter', sans-serif; color: #4a4a4a; }
    h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: #2c2c2c; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #f0e6d2; }

    .stButton>button {
        background: linear-gradient(90deg, #d4af37 0%, #e6c86e 100%); color: white; border: none; border-radius: 8px; font-weight: 500;
        transition: all 0.3s ease; text-transform: uppercase; font-size: 14px; box-shadow: 0 4px 6px rgba(212, 175, 55, 0.2); width: 100%;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(212, 175, 55, 0.3); }
    button[kind="secondary"] { background: linear-gradient(90deg, #ff6b6b 0%, #ff8787 100%) !important; }

    [data-testid="stMetric"] { background-color: rgba(255, 255, 255, 0.8); padding: 15px; border-radius: 12px; border: 1px solid #f5efe6; box-shadow: 0 4px 6px rgba(0,0,0,0.03); }
    [data-testid="stDataFrame"] { background-color: rgba(255, 255, 255, 0.9); border: 1px solid #f0e6d2; border-radius: 15px; padding: 15px; }

    .stTextInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input { background-color: #ffffff; border: 1px solid #e0dacc; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS (ANTI-TRAVAMENTO) ---
DB_FILE = 'clinica_gold.db'


def run_transaction(query, params=()):
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
    try:
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            return pd.read_sql(query, conn)
    except:
        return pd.DataFrame()


def init_db():
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
        cur = conn.cursor()
        if cur.execute("SELECT count(*) FROM procedimentos").fetchone()[0] == 0:
            cur.executemany("INSERT INTO procedimentos (nome, valor, duracao_min, categoria) VALUES (?,?,?,?)",
                            [('Botox', 1200, 45, 'Injetáveis'), ('Preenchimento', 1500, 60, 'Injetáveis'),
                             ('Limpeza', 250, 90, 'Facial')])
            conn.commit()


init_db()


# --- FUNÇÃO DE E-MAIL (AUTOMÁTICA) ---
def enviar_agenda_email():
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

        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg['Subject'] = f"📅 Agenda Bárbara Castro - {hoje.strftime('%d/%m/%Y')}"

        if df.empty:
            corpo_html = f"<h3>Bom dia! ☀️</h3><p>Não há clientes agendados para hoje ({hoje.strftime('%d/%m')}). Aproveite o dia!</p>"
        else:
            tabela_html = """<table style='width:100%; border-collapse: collapse; font-family: Arial;'>
            <tr style='background-color: #d4af37; color: white;'><th style='padding:10px;'>Hora</th><th style='padding:10px;'>Cliente</th><th style='padding:10px;'>Procedimento</th></tr>"""
            for i, row in df.iterrows():
                hora = str(row['hora_agendamento'])[:5]
                tabela_html += f"<tr style='border-bottom: 1px solid #ddd;'><td style='padding:10px; text-align:center'><b>{hora}</b></td><td style='padding:10px;'>{row['nome']}</td><td style='padding:10px;'>{row['proc']}</td></tr>"
            tabela_html += "</table>"
            corpo_html = f"<h3>Bom dia! Aqui está sua agenda de hoje:</h3>{tabela_html}<br><p>Sistema de Gestão Bárbara Castro ✨</p>"

        msg.attach(MIMEText(corpo_html, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.send_message(msg)
        server.quit()
        return "✅ E-mail enviado com sucesso!"
    except Exception as e:
        return f"❌ Erro: {e}"


# --- FUNÇÕES RELATÓRIO PDF ---
def gerar_pdf_fluxo(df_dados, periodo_texto, tot_rec, tot_desp, saldo):
    pdf = FPDF();
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
    pdf.set_font("Arial", 'B', 10)
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


def gerar_historico_pdf(cliente_nome, df_hist, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16);
    pdf.cell(0, 10, f"Historico Financeiro - {cliente_nome}", ln=1, align='C')
    pdf.set_font("Arial", 'I', 10);
    pdf.cell(0, 10, "Estetica Avancada Barbara Castro", ln=1, align='C')
    pdf.line(10, 30, 200, 30);
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Total Investido: R$ {total:,.2f}", ln=1, align='R')
    pdf.ln(5)

    pdf.set_fill_color(212, 175, 55);
    pdf.set_text_color(255, 255, 255);
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 8, "Data", 1, 0, 'C', True)
    pdf.cell(100, 8, "Procedimento", 1, 0, 'C', True)
    pdf.cell(40, 8, "Valor", 1, 1, 'C', True)

    pdf.set_text_color(0, 0, 0);
    pdf.set_font("Arial", '', 10)
    for i, row in df_hist.iterrows():
        try:
            d_fmt = datetime.strptime(str(row['Data']), '%Y-%m-%d').strftime('%d/%m/%Y')
        except:
            d_fmt = str(row['Data'])
        pdf.cell(30, 8, d_fmt, 1)
        pdf.cell(100, 8, row['Procedimento'].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(40, 8, f"R$ {row['Valor']:,.2f}", 1, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')


# --- GATILHO EXTERNO (CRON-JOB/GITHUB ACTIONS) ---
if "rotina" in st.query_params and st.query_params["rotina"] == "disparar_email":
    res = enviar_agenda_email()
    st.write(res);
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists("Barbara.jpeg"):
        st.image("Barbara.jpeg", width=130)
    else:
        st.markdown("### 👑 Bárbara Castro")
    menu = st.radio("NAVEGAÇÃO",
                    ["Dashboard", "Agenda", "Clientes", "Procedimentos", "Financeiro", "Relatórios", "AI Insights"])
    st.markdown("---")
    # Botão de teste removido pois a automação já funciona
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
        st.markdown("### Gerenciar Agendamentos")
        q_ger = """SELECT a.id, c.nome, a.data_agendamento, a.hora_agendamento, p.nome as proc, a.status \
                   FROM agenda a \
                            JOIN clientes c ON a.cliente_id = c.id \
                            JOIN procedimentos p ON a.procedimento_id = p.id \
                   ORDER BY a.data_agendamento DESC, a.hora_agendamento DESC"""
        ag = get_data(q_ger)
        if not ag.empty:
            op = {f"{r['data_agendamento']} - {r['hora_agendamento'][:5]} - {r['nome']} ({r['status']})": r['id'] for
                  i, r in ag.iterrows()}
            aid_key = st.selectbox("Selecione para editar:", list(op.keys()))
            aid = op[aid_key]
            c1, c2 = st.columns(2)
            if c1.button("✅ Concluir"): run_transaction("UPDATE agenda SET status='Concluído' WHERE id=?",
                                                        (aid,)); st.success("Atualizado!"); time.sleep(0.5); st.rerun()
            if c2.button("🗑️ Excluir", type="secondary"): run_transaction("DELETE FROM agenda WHERE id=?",
                                                                          (aid,)); st.success("Excluído!"); time.sleep(
                0.5); st.rerun()
            st.divider();
            st.dataframe(ag, use_container_width=True)
        else:
            st.info("Nenhum agendamento encontrado.")

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
                pass
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
    t1, t2, t3 = st.tabs(["Resumo", "Nova Despesa", "Histórico"])
    q_rec = "SELECT a.data_agendamento as Data, 'Receita: '||p.nome||' ('||c.nome||')' as Descrição, p.valor as Valor, 'Receita' as Tipo FROM agenda a JOIN clientes c ON a.cliente_id=c.id JOIN procedimentos p ON a.procedimento_id=p.id WHERE a.status='Concluído'"
    df_rec = get_data(q_rec)
    df_desp = get_data(
        "SELECT data_despesa as Data, descricao as Descrição, valor as Valor, 'Despesa' as Tipo FROM despesas")
    df_fluxo = pd.concat([df_rec, df_desp], ignore_index=True)
    if not df_fluxo.empty: df_fluxo['Data'] = pd.to_datetime(df_fluxo['Data']).dt.date; df_fluxo = df_fluxo.sort_values(
        'Data', ascending=False)

    tot_r = df_rec['Valor'].sum() if not df_rec.empty else 0
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
            v = st.number_input("Valor");
            dt = st.date_input("Data")
            if st.form_submit_button("Lançar"): run_transaction(
                "INSERT INTO despesas (descricao, valor, data_despesa, categoria) VALUES (?,?,?,?)",
                (d, v, dt, "Geral")); st.rerun()
    with t3:
        dl = get_data("SELECT id, data_despesa, descricao, valor FROM despesas ORDER BY data_despesa DESC")
        if not dl.empty:
            did = st.selectbox("Excluir Despesa", dl['id'].tolist(),
                               format_func=lambda x: f"{x} - {dl[dl['id'] == x].iloc[0]['descricao']}")
            if st.button("Apagar", type="secondary"): run_transaction("DELETE FROM despesas WHERE id=?",
                                                                      (did,)); st.rerun()

elif menu == "Relatórios":
    st.title("📊 Relatórios")
    t1, t2 = st.tabs(["Fluxo de Caixa", "Histórico do Cliente"])

    with t1:
        c1, c2 = st.columns(2);
        d1 = c1.date_input("Início", date.today().replace(day=1));
        d2 = c2.date_input("Fim", date.today())
        q = f"""SELECT a.data_agendamento as Data, 'Receita: '||p.nome||' ('||c.nome||')' as Descrição, 'Receita' as Tipo, p.valor as Valor FROM agenda a JOIN procedimentos p ON a.procedimento_id=p.id JOIN clientes c ON a.cliente_id=c.id WHERE a.status='Concluído' AND a.data_agendamento BETWEEN '{d1}' AND '{d2}' UNION ALL SELECT data_despesa as Data, descricao as Descrição, 'Despesa' as Tipo, valor as Valor FROM despesas WHERE data_despesa BETWEEN '{d1}' AND '{d2}' ORDER BY Data"""
        df_rel = get_data(q)
        if not df_rel.empty:
            rec_p = df_rel[df_rel['Tipo'] == 'Receita']['Valor'].sum();
            desp_p = df_rel[df_rel['Tipo'] == 'Despesa']['Valor'].sum();
            saldo_p = rec_p - desp_p
            st.markdown("---");
            m1, m2, m3 = st.columns(3);
            m1.metric("Receitas", f"R$ {rec_p:,.2f}");
            m2.metric("Despesas", f"R$ {desp_p:,.2f}");
            m3.metric("Saldo", f"R$ {saldo_p:,.2f}")
            st.dataframe(
                df_rel.style.applymap(lambda v: 'color:green' if v == 'Receita' else 'color:red', subset=['Tipo']),
                use_container_width=True)
            ce1, ce2 = st.columns(2);
            b = io.BytesIO()
            with pd.ExcelWriter(b, engine='openpyxl') as w:
                df_rel.to_excel(w, index=False)
            ce1.download_button("📊 Excel", b.getvalue(), "relatorio.xlsx", "application/vnd.ms-excel")
            try:
                pdf = gerar_pdf_fluxo(df_rel, f"{d1} a {d2}", rec_p, desp_p, saldo_p)
                ce2.download_button("📑 PDF", pdf, "relatorio.pdf", "application/pdf")
            except:
                ce2.warning("Instale 'fpdf'")
        else:
            st.info("Sem dados neste período.")

    with t2:
        st.subheader("Histórico por Cliente")
        cli_list = get_data("SELECT id, nome FROM clientes ORDER BY nome")
        if not cli_list.empty:
            c_id = st.selectbox("Selecione o Cliente:", cli_list['id'].tolist(),
                                format_func=lambda x: f"{cli_list[cli_list['id'] == x].iloc[0]['nome']}")
            c_nome = cli_list[cli_list['id'] == c_id].iloc[0]['nome']

            # Query do histórico
            q_hist = f"""
                SELECT a.data_agendamento as Data, p.nome as Procedimento, p.valor as Valor, a.status
                FROM agenda a
                JOIN procedimentos p ON a.procedimento_id = p.id
                WHERE a.cliente_id = {c_id} AND a.status = 'Concluído'
                ORDER BY a.data_agendamento DESC
            """
            df_hist = get_data(q_hist)

            if not df_hist.empty:
                total_investido = df_hist['Valor'].sum()
                st.metric(f"Total Investido por {c_nome}", f"R$ {total_investido:,.2f}")
                st.dataframe(df_hist, use_container_width=True)

                # PDF do Histórico
                try:
                    pdf_h = gerar_historico_pdf(c_nome, df_hist, total_investido)
                    st.download_button(f"📑 Baixar Extrato de {c_nome}", pdf_h, f"extrato_{c_nome}.pdf",
                                       "application/pdf")
                except:
                    pass
            else:
                st.info(f"O cliente {c_nome} ainda não concluiu nenhum procedimento.")
        else:
            st.warning("Cadastre clientes primeiro.")

elif menu == "AI Insights":
    st.title("CRM Inteligente")
    mes = datetime.now().month
    niv = get_data(
        f"SELECT nome, data_nascimento FROM clientes WHERE cast(strftime('%m', data_nascimento) as int) = {mes}")
    if not niv.empty:
        st.success(f"{len(niv)} Aniversariantes este mês!");
        for i, r in niv.iterrows(): st.write(
            f"🎂 {r['nome']} ({datetime.strptime(str(r['data_nascimento']), '%Y-%m-%d').strftime('%d/%m')})")
    else:
        st.info("Sem aniversariantes este mês.")