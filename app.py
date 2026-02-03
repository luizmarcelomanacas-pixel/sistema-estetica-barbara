import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO DE E-MAIL ---
EMAIL_REMETENTE = 'luizmarcelomanacas@gmail.com'  # Coloque seu e-mail
EMAIL_SENHA = 'njyt nrvd vtro jgwi'  # Coloque sua senha de app
EMAIL_DESTINATARIO = 'luizmarcelomanacas@gmail.com'

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Estética Avançada", layout="wide", page_icon="✨")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)


def get_data(worksheet):
    try:
        # ttl=0 garante dados frescos
        return conn.read(worksheet=worksheet, ttl=0)
    except Exception:
        return pd.DataFrame()


def add_data(worksheet, new_data_dict):
    try:
        df = get_data(worksheet)
        # Gera ID automático
        if not df.empty and 'id' in df.columns:
            # Garante que o ID é numérico
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0)
            new_id = int(df['id'].max()) + 1
        else:
            new_id = 1

        new_data_dict['id'] = new_id

        # Cria DataFrame da nova linha
        new_row = pd.DataFrame([new_data_dict])

        # Se a planilha estiver vazia, cria com a nova linha
        if df.empty:
            updated_df = new_row
        else:
            updated_df = pd.concat([df, new_row], ignore_index=True)

        conn.update(worksheet=worksheet, data=updated_df)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


def update_data(worksheet, id_to_update, update_dict):
    try:
        df = get_data(worksheet)
        if df.empty: return False

        df['id'] = pd.to_numeric(df['id'], errors='coerce')
        idx = df.index[df['id'] == id_to_update].tolist()

        if not idx: return False

        for key, value in update_dict.items():
            df.at[idx[0], key] = value

        conn.update(worksheet=worksheet, data=df)
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return False


def delete_data(worksheet, id_to_delete):
    try:
        df = get_data(worksheet)
        if df.empty: return False

        df['id'] = pd.to_numeric(df['id'], errors='coerce')
        updated_df = df[df['id'] != id_to_delete]

        conn.update(worksheet=worksheet, data=updated_df)
        return True
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")
        return False


# --- SIDEBAR ---
with st.sidebar:
    st.title("✨ Gestão Estética")
    menu = st.radio("MENU", ["Dashboard", "Insights 🎂", "Agenda", "Clientes", "Procedimentos", "Financeiro"])
    st.markdown("---")
    if st.button("🔄 Atualizar Sistema"): st.rerun()

# --- PÁGINAS ---

# 1. DASHBOARD
if menu == "Dashboard":
    st.title("Visão Geral")
    df_ag = get_data("agenda")

    ag_hoje = 0
    faturamento_est = 0.0

    if not df_ag.empty and 'data_agendamento' in df_ag.columns:
        hoje = str(date.today())
        # Filtra hoje
        df_hoje = df_ag[df_ag['data_agendamento'].astype(str) == hoje]
        ag_hoje = len(df_hoje)

        # Tenta calcular faturamento se houver valores salvos, ou estimativa
        # (Lógica simplificada para não travar se faltar coluna)
        pass

    c1, c2, c3 = st.columns(3)
    c1.metric("Agendamentos Hoje", ag_hoje)
    c2.metric("Data", date.today().strftime('%d/%m/%Y'))
    c3.info("Acesse 'Insights' para ver aniversariantes!")

# 2. INSIGHTS (NOVO!)
elif menu == "Insights 🎂":
    st.title("🧠 Insights Inteligentes")

    df_cli = get_data("clientes")
    if not df_cli.empty and 'data_nascimento' in df_cli.columns:
        # Converte para data
        df_cli['nasc_dt'] = pd.to_datetime(df_cli['data_nascimento'], errors='coerce')

        mes_atual = date.today().month
        nome_mes = date.today().strftime('%B')

        # Filtra aniversariantes
        aniversariantes = df_cli[df_cli['nasc_dt'].dt.month == mes_atual]

        st.subheader(f"🎉 Aniversariantes do Mês ({mes_atual})")
        if not aniversariantes.empty:
            st.success(f"Temos {len(aniversariantes)} clientes fazendo festa este mês! Hora de mandar promoção.")
            st.dataframe(aniversariantes[['nome', 'telefone', 'data_nascimento']], use_container_width=True)
        else:
            st.info("Nenhum aniversariante encontrado neste mês.")

    else:
        st.warning("Cadastre clientes com data de nascimento para ver os insights.")

# 3. AGENDA
elif menu == "Agenda":
    st.title("Agenda")
    t1, t2 = st.tabs(["Novo Agendamento", "Visualizar"])

    df_cli = get_data("clientes")
    df_proc = get_data("procedimentos")

    with t1:
        if not df_cli.empty and not df_proc.empty:
            with st.form("form_agenda"):
                c_nome = st.selectbox("Cliente", df_cli['nome'].unique())
                p_nome = st.selectbox("Procedimento", df_proc['nome'].unique())
                d_ag = st.date_input("Data")
                h_ag = st.time_input("Hora")

                if st.form_submit_button("Agendar"):
                    # Busca IDs
                    c_id = df_cli[df_cli['nome'] == c_nome]['id'].values[0]
                    p_id = df_proc[df_proc['nome'] == p_nome]['id'].values[0]

                    dados = {
                        "cliente_id": int(c_id), "cliente_nome": c_nome,
                        "procedimento_id": int(p_id), "procedimento_nome": p_nome,
                        "data_agendamento": str(d_ag), "hora_agendamento": str(h_ag),
                        "status": "Agendado"
                    }
                    if add_data("agenda", dados):
                        st.success("Agendado com sucesso!")
                        time.sleep(1);
                        st.rerun()
        else:
            st.warning("Cadastre clientes e procedimentos antes de agendar.")

    with t2:
        df_ag = get_data("agenda")
        if not df_ag.empty:
            st.dataframe(df_ag)
        else:
            st.info("Agenda vazia.")

# 4. CLIENTES
elif menu == "Clientes":
    st.title("Gestão de Clientes")
    t1, t2 = st.tabs(["Cadastrar", "Lista Completa"])

    with t1:
        with st.form("form_cliente"):
            nome = st.text_input("Nome Completo")
            tel = st.text_input("Telefone (Whatsapp)")
            email = st.text_input("E-mail")
            nasc = st.date_input("Data de Nascimento", min_value=date(1920, 1, 1))
            anamnese = st.text_area("Ficha de Anamnese (Alergias, histórico...)")

            if st.form_submit_button("Salvar Cliente"):
                if nome:
                    dados = {
                        "nome": nome,
                        "telefone": tel,
                        "email": email,
                        "data_nascimento": str(nasc),
                        "anamnese": anamnese,
                        "created_at": str(datetime.now())
                    }
                    if add_data("clientes", dados):
                        st.success(f"Cliente {nome} salvo!")
                        time.sleep(1);
                        st.rerun()
                else:
                    st.error("O nome é obrigatório.")

    with t2:
        df = get_data("clientes")
        if not df.empty:
            st.dataframe(df)
        else:
            st.info("Nenhum cliente cadastrado.")

# 5. PROCEDIMENTOS
elif menu == "Procedimentos":
    st.title("Catálogo de Serviços")
    with st.form("form_proc"):
        n = st.text_input("Nome do Procedimento")
        v = st.number_input("Valor (R$)", min_value=0.0)
        d = st.number_input("Duração (minutos)", min_value=15, step=15)

        if st.form_submit_button("Salvar Serviço"):
            if n:
                if add_data("procedimentos", {"nome": n, "valor": v, "duracao_min": d, "categoria": "Geral"}):
                    st.success("Serviço salvo!")
                    time.sleep(1);
                    st.rerun()

    st.dataframe(get_data("procedimentos"))

# 6. FINANCEIRO
elif menu == "Financeiro":
    st.title("Controle Financeiro")
    with st.form("form_fin"):
        desc = st.text_input("Descrição da Despesa")
        val = st.number_input("Valor", min_value=0.0)
        dt = st.date_input("Data")
        cat = st.selectbox("Categoria", ["Produtos", "Aluguel", "Luz/Água", "Marketing", "Outros"])

        if st.form_submit_button("Lançar Despesa"):
            if desc:
                dados = {
                    "descricao": desc, "valor": val,
                    "data_despesa": str(dt), "categoria": cat,
                    "created_at": str(datetime.now())
                }
                if add_data("despesas", dados):
                    st.success("Lançado!")
                    time.sleep(1);
                    st.rerun()

    st.subheader("Histórico de Despesas")
    st.dataframe(get_data("despesas"))