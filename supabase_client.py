# supabase_client.py
import os
from supabase import create_client, Client

def get_supabase() -> Client:
    """
    Retorna uma instância do cliente Supabase, utilizando variáveis de ambiente
    para a URL e a chave de API.
    """
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        # Quando rodando localmente, você pode definir estas variáveis de ambiente
        # ou criar um arquivo .env e carregá-lo, ou configurar diretamente no Streamlit Cloud
        raise ValueError("SUPABASE_URL e SUPABASE_KEY devem ser configuradas como variáveis de ambiente.")

    return create_client(url, key)
