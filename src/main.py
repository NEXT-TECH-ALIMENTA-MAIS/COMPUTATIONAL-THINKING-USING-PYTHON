import os
import time
from dotenv import load_dotenv
import oracledb as orcl

def conectar_db():
    load_dotenv()
    conexao = None
    cursor = None

    try:
        host = os.getenv('ORACLE_HOST')
        port = int(os.getenv('ORACLE_PORT', '1521'))
        service = os.getenv('ORACLE_SERVICE')
        user = os.getenv('ORACLE_USER')
        password = os.getenv('ORACLE_PASSWORD')
        str_conexao = orcl.makedsn(host, port, service_name=service)
        conexao = orcl.connect(user=user, password=password, dsn=str_conexao, tcp_connect_timeout=10)
        cursor = conexao.cursor()
    except (orcl.Error, OSError, ValueError) as erro:
        if conexao is not None:
            conexao.close()
        print(f"Erro ao conectar com o banco{erro}")
        return False, None, None
    return True, conexao, cursor

def main():
    while True:
        print("\n" + "="*20)
        print(f"     Acesse sua conta e faça a comida chegar a quem precisa.")
        print("="*20)
        print("\n")
        print("Qual o tipo da sua conta? \n")
        print("1 - Estabelecimento fornecedor")
        print("2 - Instituição receptora")
        print("3 - Administrador")
        print("4 - Ainda não tem uma conta? Crie uma agora!")
        print("5 - Sair \n")

        opcao = int(input("Digite uma opção para entrar: "))

        match opcao:
            case 1:
                print("Validar CNPJ e senha inserida e procurar se existe conta no banco")
            case 2:
                print("Validar CNPJ e senha inserida e procurar se existe conta no banco")
            case 3:
                print("Validar email e senha inserida e procurar se existe conta no banco")
            case 4:
                print("CRUD para criar uma nova conta")
            case 5:
                print("Saindo...")
                time.sleep(2)
                os.system('cls')
                break


def menu_estabelecimento():

    while True:

        print("\n" + "="*20)
        print(f"     Painel de controle da {nome_empresa}")
        print("="*20)
        print("1 - Ver conta")
        print("2 - Buscar doações")
        print("3 - Pesquisar instituições")
        print("4 - Visualizar solicitações de instituições")
        print("5 - Ver publicações de necessidades")
        print("6 - Publicar uma oferta")
        print("7 - Deletar publicação")
        print("8 - Sair")

        opcao = int(input("Digite a opção desejada: "))

        match opcao:
            case 1:
                print("Função para ver a conta")
                time.sleep(2)
                os.system('cls')
            case 2:
                print("Função para buscar doações")
                time.sleep(2)
                os.system('cls')    
            case 3: 
                print("Função para pesquisar por instituições receptoras")
                time.sleep(2)
                os.system('cls')
            case 4:
                print("Função para visualizar as solicitações das instituições")
                time.sleep(2)
                os.system('cls')
            case 5:
                print("Função para ver as publicações de necessidades das instituições")
                time.sleep(2)
                os.system('cls')
            case 6:
                print("Função para publicar uma oferta")
                time.sleep(2)
                os.system('cls')
            case 7:
                print("Função para deletar uma publicação")
                time.sleep(2)
                os.system('cls')
            case 8:
                print("Saindo...")
                time.sleep(2)
                os.system('cls')
                break
            case _:
                print("Opção inválida, tente novamente!")
                time.sleep(2)
                os.system('cls')















if __name__ == "__main__":
    main()