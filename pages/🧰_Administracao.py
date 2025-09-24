# pages/🧰_Administracao.py
from __future__ import annotations # Boa prática para typing hints futuros
from datetime import date
import streamlit as st
# Importa as funções auxiliares que você já tem no seu utils.py
from utils import to_brl, fetch_members, fetch_accounts, fetch_categories, fetch_cards, fetch_card_limits

# --- 1. Configuração Inicial e Verificação de Login ---
# Centralizamos a verificação de login no início para garantir que
# nenhuma parte da interface seja carregada antes da autenticação.
if "sb" not in st.session_state or "HOUSEHOLD_ID" not in st.session_state or "user" not in st.session_state:
    st.warning("🔒 Por favor, faça login na página principal para acessar a administração.")
    st.stop() # Interrompe a execução da página se o usuário não estiver logado.

# Acessa os objetos da sessão após a verificação de login
sb = st.session_state.sb
HOUSEHOLD_ID = st.session_state.HOUSEHOLD_ID
user = st.session_state.user

st.title("🧰 Administração do Sistema Financeiro") # Título mais descritivo e alinhado ao contexto

# --- 2. Funções Auxiliares de Tratamento e Feedback ---
# Criamos funções genéricas para evitar repetição de código (DRY - Don't Repeat Yourself).

def _clear_cache_and_rerun():
    """
    Limpa o cache do Streamlit e força uma nova execução da página.
    Essencial após operações de escrita no banco de dados para atualizar a UI.
    """
    st.cache_data.clear() # Limpa o cache para recarregar dados novos
    st.rerun() # Força a re-execução da página

def _show_toast(message: str, icon: str = "✅"):
    """
    Exibe um 'toast' (mensagem temporária) de sucesso ou informação.
    Usado para dar feedback rápido e não intrusivo ao usuário.
    """
    st.toast(message, icon=icon)

def _handle_supabase_operation(operation_func, success_message: str, error_prefix: str):
    """
    Função wrapper para encapsular operações de banco de dados no Supabase,
    tratando exceções, exibindo feedback (toast) e atualizando a interface.

    Args:
        operation_func (callable): Uma função (geralmente uma lambda) que executa
                                  a operação no Supabase (insert, update, upsert).
        success_message (str): Mensagem a ser exibida em caso de sucesso.
        error_prefix (str): Prefixo para a mensagem de erro em caso de falha.
    """
    try:
        operation_func() # Executa a operação no banco de dados
        _show_toast(success_message) # Mostra mensagem de sucesso
        _clear_cache_and_rerun() # Limpa cache e atualiza a UI
    except Exception as e:
        # Exibe uma mensagem de erro detalhada para o desenvolvedor e usuário
        st.error(f"{error_prefix}: {str(e)}")

# --- 3. Funções de Renderização para Cada Aba (Modularidade) ---
# Cada aba agora tem sua própria função, o que torna o código mais organizado e fácil de gerenciar.

def render_members_tab():
    """
    Renderiza a interface para a gestão de membros do agregado familiar.
    Permite ao usuário definir seu nome de exibição.
    """
    st.subheader("�� Gestão de Membros")
    st.markdown("Configure seu nome de exibição para o sistema. O criador do sistema é automaticamente o 'owner'.")

    # Usamos st.form para agrupar entradas e o botão de salvar,
    # o que garante que a lógica só seja executada no submit e isola o estado do formulário.
    with st.form("form_member_name", clear_on_submit=False): # clear_on_submit=False mantém o nome preenchido
        # Buscamos o nome atual do usuário para pré-preencher o campo de texto.
        current_member_name = "Você" # Valor padrão
        mems = fetch_members(sb, HOUSEHOLD_ID) # Busca membros para encontrar o nome do usuário logado
        if mems:
            for m in mems:
                if m["user_id"] == user.id: # <-- Aqui o 'user_id' é necessário!
                    current_member_name = m["display_name"]
                    break

        new_display_name = st.text_input("Seu nome de exibição", value=current_member_name, key="member_display_name_input")
        submit_button = st.form_submit_button("Salvar Meu Nome")

        if submit_button:
            if not new_display_name.strip(): # Validação: O nome não pode estar vazio
                st.error("Por favor, insira um nome de exibição válido.")
                return

            def upsert_member_operation():
                """Lógica para inserir ou atualizar o membro no Supabase."""
                sb.table("members").upsert({
                    "household_id": HOUSEHOLD_ID,
                    "user_id": user.id,
                    "display_name": new_display_name.strip(),
                    "role": "owner" # Para o criador/usuário logado, sempre owner por padrão.
                }, on_conflict="household_id,user_id").execute() # Atualiza se já existir, insere se não.

            _handle_supabase_operation(
                upsert_member_operation,
                "✅ Nome de membro salvo com sucesso!",
                "Erro ao salvar o nome do membro"
            )

    st.markdown("---") # Separador visual
    st.markdown("#### Membros do seu Agregado Familiar Registrados")
    mems = fetch_members(sb, HOUSEHOLD_ID) # Recarrega a lista após uma possível atualização
    if mems:
        # Melhorando a exibição dos membros com um layout mais estruturado usando colunas.
        st.write("Veja quem faz parte do seu agregado familiar:")
        for m in mems:
            col1, col2, col3 = st.columns([4, 3, 2])
            with col1:
                st.markdown(f"**{m['display_name']}**")
            with col2:
                role_text = "✨ Owner" if m["role"] == "owner" else "Membro"
                st.info(role_text, icon="👤") # st.info para destacar a função
            with col3:
                # Aqui poderíamos adicionar botões para editar/remover outros membros,
                # com validações de permissão para garantir que apenas 'owners' possam fazer isso.
                pass
    else:
        st.info("Nenhum membro cadastrado ainda. Seu nome será adicionado automaticamente ao salvar.")


def render_accounts_tab():
    """
    Renderiza a interface para a gestão de contas (bancárias, carteiras, etc.).
    Permite adicionar novas contas e ativar/desativar as existentes.
    """
    st.subheader("💰 Gestão de Contas")
    st.markdown("Cadastre suas contas bancárias, carteiras digitais ou outras fontes de recursos.")

    with st.form("form_new_account", clear_on_submit=True): # clear_on_submit=True limpa o formulário após o envio
        an = st.text_input("Nome da Conta", key="account_name_input")
        at = st.selectbox("Tipo de Conta", ["checking", "savings", "wallet", "credit"],
                          format_func=lambda x: x.capitalize(), key="account_type_select") # Capitaliza para melhor leitura (ex: "Checking")
        ob = st.number_input("Saldo Inicial (R\$)", min_value=0.0, step=50.0, value=0.0, key="account_opening_balance_input")

        submit_button = st.form_submit_button("Salvar Nova Conta")

        if submit_button:
            if not an.strip(): # Validação: Nome da conta é obrigatório
                st.error("Por favor, insira um nome para a conta.")
                return
            if ob < 0: # Embora min_value ajude, é bom ter uma validação explícita.
                st.error("O saldo inicial não pode ser negativo.")
                return

            def insert_account_operation():
                """Lógica para inserir uma nova conta no Supabase."""
                sb.table("accounts").insert({
                    "household_id": HOUSEHOLD_ID,
                    "name": an.strip(),
                    "type": at,
                    "opening_balance": ob,
                    "currency": "BRL", # Moeda padrão, pode ser configurável no futuro
                    "is_active": True
                }).execute()

            _handle_supabase_operation(
                insert_account_operation,
                "✅ Conta salva com sucesso!",
                "Erro ao salvar a conta"
            )

    st.markdown("---")
    st.markdown("#### Suas Contas Cadastradas")
    # Busca todas as contas (ativas e inativas) para permitir a gestão de status.
    accs = fetch_accounts(sb, HOUSEHOLD_ID, False)
    if accs:
        st.write("Visualize e gerencie o status das suas contas:")
        for a in accs:
            status_icon = "🟢" if a["is_active"] else "🔴"
            status_text = "Ativa" if a["is_active"] else "Inativa"
            action_text = "Desativar" if a["is_active"] else "Ativar"
            action_key_prefix = "acc_d_" if a["is_active"] else "acc_a_" # Chave única para os botões

            # Usamos st.columns para um layout mais estruturado e fácil de ler.
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            with col1:
                st.markdown(f"{status_icon} **{a['name']}**")
            with col2:
                st.write(f"Tipo: {a.get('type','').capitalize()}")
            with col3:
                st.write(f"Saldo Inicial: {to_brl(a['opening_balance'])}")
            with col4:
                st.info(status_text) # Exibe o status da conta
            with col5:
                # Botão para ativar/desativar a conta.
                if st.button(action_text, key=f"{action_key_prefix}{a['id']}", help=f"{action_text} a conta {a['name']}"):
                    def update_account_status_operation():
                        """Lógica para atualizar o status (ativo/inativo) da conta."""
                        sb.table("accounts").update({"is_active": not a["is_active"]}).eq("id", a["id"]).execute()
                    _handle_supabase_operation(
                        update_account_status_operation,
                        f"✅ Conta '{a['name']}' {'desativada' if a['is_active'] else 'ativada'}!",
                        f"Erro ao {'desativar' if a['is_active'] else 'ativar'} a conta"
                    )
    else:
        st.info("Nenhuma conta cadastrada ainda. Use o formulário acima para adicionar sua primeira conta!")


def render_categories_tab():
    """
    Renderiza a interface para a gestão de categorias de transações.
    Permite adicionar novas categorias de receita ou despesa.
    """
    st.subheader("🏷️ Gestão de Categorias")
    st.markdown("Organize suas transações financeiras com categorias personalizadas de receita e despesa.")

    with st.form("form_new_category", clear_on_submit=True):
        col_name, col_kind = st.columns([2, 1]) # Duas colunas para nome e tipo
        with col_name:
            cn = st.text_input("Nome da Categoria", key="category_name_input")
        with col_kind:
            ck = st.selectbox("Tipo", ["income", "expense"],
                              format_func=lambda k: {"income": "Receita", "expense": "Despesa"}[k],
                              key="category_kind_select")
        submit_button = st.form_submit_button("Salvar Nova Categoria")

        if submit_button:
            if not cn.strip(): # Validação: Nome da categoria é obrigatório
                st.error("Por favor, insira um nome para a categoria.")
                return

            def insert_category_operation():
                """Lógica para inserir uma nova categoria no Supabase."""
                sb.table("categories").insert({
                    "household_id": HOUSEHOLD_ID,
                    "name": cn.strip(),
                    "kind": ck
                }).execute()

            _handle_supabase_operation(
                insert_category_operation,
                "✅ Categoria salva com sucesso!",
                "Erro ao salvar a categoria"
            )

    st.markdown("---")
    st.markdown("#### Suas Categorias Cadastradas")
    cats = fetch_categories(sb, HOUSEHOLD_ID) # Busca todas as categorias
    if cats:
        # Exibimos as categorias de receita e despesa em colunas separadas para melhor visualização.
        col_inc, col_exp = st.columns(2)

        with col_inc:
            st.markdown("##### ➕ Receitas")
            income_categories = [c["name"] for c in cats if c["kind"] == "income"]
            if income_categories:
                for cat_name in income_categories:
                    st.success(f"• **{cat_name}**") # Usamos st.success para destacar categorias de receita
            else:
                st.info("Nenhuma categoria de receita cadastrada.")

        with col_exp:
            st.markdown("##### ➖ Despesas")
            expense_categories = [c["name"] for c in cats if c["kind"] == "expense"]
            if expense_categories:
                for cat_name in expense_categories:
                    st.warning(f"• **{cat_name}**") # Usamos st.warning para destacar categorias de despesa
            else:
                st.info("Nenhuma categoria de despesa cadastrada.")
    else:
        st.info("Nenhuma categoria cadastrada ainda. Comece a organizar suas finanças!")


def render_cards_tab():
    """
    Renderiza a interface para a gestão de cartões de crédito.
    Permite adicionar novos cartões e ativar/desativar os existentes.
    """
    st.subheader("💳 Gestão de Cartões de Crédito")
    st.markdown("Cadastre seus cartões de crédito, defina limites e dias de fechamento/vencimento.")

    with st.form("form_new_card", clear_on_submit=True):
        col_nm, col_lim, col_closing, col_due = st.columns(4) # Quatro colunas para as entradas
        with col_nm:
            nm = st.text_input("Nome do Cartão", key="card_name_input")
        with col_lim:
            lim = st.number_input("Limite (R\$)", min_value=0.0, step=100.0, value=0.0, key="card_limit_input")
        with col_closing:
            closing = st.number_input("Dia de Fechamento (1-28)", min_value=1, max_value=28, value=5, key="card_closing_day_input")
        with col_due:
            due = st.number_input("Dia de Vencimento (1-28)", min_value=1, max_value=28, value=15, key="card_due_day_input")

        submit_button = st.form_submit_button("Salvar Novo Cartão")

        if submit_button:
            # Validações dos campos do formulário
            if not nm.strip():
                st.error("Por favor, insira um nome para o cartão.")
                return
            if lim <= 0:
                st.error("O limite do cartão deve ser um valor positivo.")
                return
            if not (1 <= closing <= 28) or not (1 <= due <= 28):
                st.error("Os dias de fechamento e vencimento devem estar entre 1 e 28.")
                return

            def insert_card_operation():
                """Lógica para inserir um novo cartão no Supabase."""
                sb.table("credit_cards").insert({
                    "household_id": HOUSEHOLD_ID,
                    "name": nm.strip(),
                    "limit_amount": lim,
                    "closing_day": int(closing),
                    "due_day": int(due),
                    "is_active": True,
                    "created_by": user.id # Associa o cartão ao usuário que o criou
                }).execute()

            _handle_supabase_operation(
                insert_card_operation,
                "✅ Cartão de crédito salvo com sucesso!",
                "Erro ao salvar o cartão de crédito"
            )

    st.markdown("---")
    st.markdown("#### Seus Cartões Cadastrados")
    # Busca todos os cartões (ativos e inativos) e seus limites.
    cards_all = fetch_cards(sb, HOUSEHOLD_ID, False)
    limits = fetch_card_limits(sb, HOUSEHOLD_ID)
    limap = {x["id"]: x for x in limits} # Cria um mapa para acessar limites disponíveis facilmente pelo ID do cartão.

    if not cards_all:
        st.info("Nenhum cartão de crédito cadastrado ainda. Use o formulário acima para adicionar um!")
        return

    # Iteramos sobre os cartões para exibi-los e permitir ações.
    for c in cards_all:
        status_icon = "🟢" if c["is_active"] else "🔴"
        action_text = "Desativar" if c["is_active"] else "Ativar"
        action_key_prefix = "card_d_" if c["is_active"] else "card_a_"

        available_limit = limap.get(c["id"], {}).get("available_limit", c["limit_amount"])

        # Usamos st.container(border=True) para agrupar visualmente as informações de cada cartão,
        # substituindo o `div class="card"` que você usava e sendo mais idiomático do Streamlit.
        with st.container(border=True):
            colA, colB, colC, colD, colE = st.columns([3, 2, 2, 2, 1])
            with colA:
                st.markdown(f"{status_icon} **{c['name']}**")
            with colB:
                st.write(f"Limite: {to_brl(c['limit_amount'])}")
            with colC:
                st.write(f"Disponível: {to_brl(available_limit)}")
            with colD:
                st.info(f"Fecha dia {c['closing_day']} / Vence dia {c['due_day']}")
            with colE:
                # Botão para ativar/desativar o cartão.
                if st.button(action_text, key=f"{action_key_prefix}{c['id']}", help=f"{action_text} o cartão {c['name']}"):
                    def update_card_status_operation():
                        """Lógica para atualizar o status (ativo/inativo) do cartão."""
                        sb.table("credit_cards").update({"is_active": not c["is_active"]}).eq("id", c["id"]).execute()
                    _handle_supabase_operation(
                        update_card_status_operation,
                        f"✅ Cartão '{c['name']}' {'desativado' if c['is_active'] else 'ativado'}!",
                        f"Erro ao {'desativar' if c['is_active'] else 'ativar'} o cartão"
                    )

# --- 4. Renderização Principal das Abas ---
# Definimos as abas e chamamos as funções de renderização para cada uma.
tabs = st.tabs(["👥 Membros", "💰 Contas", "🏷️ Categorias", "💳 Cartões"])

with tabs[0]:
    with st.container(border=True): # Agrupador visual para a aba Membros
        render_members_tab()
with tabs[1]:
    with st.container(border=True): # Agrupador visual para a aba Contas
        render_accounts_tab()
with tabs[2]:
    with st.container(border=True): # Agrupador visual para a aba Categorias
        render_categories_tab()
with tabs[3]:
    with st.container(border=True): # Agrupador visual para a aba Cartões
        render_cards_tab()
