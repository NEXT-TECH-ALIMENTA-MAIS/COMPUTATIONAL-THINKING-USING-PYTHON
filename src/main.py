import os
import time
from dotenv import load_dotenv
import oracledb as orcl
import requests

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

def buscar_conta(cursor, cnpj_org):
    cursor.execute('SELECT CD_ORGANIZACAO FROM ALIM_TB_ORGANIZACAO WHERE NR_CNPJ = :cnpj_org', {'cnpj_org': cnpj_org})
    conta = cursor.fetchone()
    if conta is None:
        return -1
    return conta[0]

def buscar_conta_adm(cursor, cpf):
    cursor.execute('')
    conta_adm = cursor.fetchone()
    if conta_adm is None:
        return -1
    return conta_adm[0]

def inserir_conta_inst(cursor, conexao):

        cnpj_org = int(input("Informe o CNPJ do instelecimento (apenas números): "))
        buscar_conta(cursor, cnpj_org)

        while buscar_conta(cursor, cnpj_org) != -1:
            cnpj_org = int(input(f"O CNPJ {cnpj_org} já está cadastrado no sistema, informe outro CNPJ: "))
            buscar_conta(cursor, cnpj_org)

        str_endpoint = f"https://open.cnpja.com/office/{cnpj_org}"
        requisicao = requests.get(str_endpoint)

        if requisicao.status_code == 200:
            dados_org = requisicao.json()
            nome_inst = dados_org["company"]["name"]
            print(f"Nome fantasia: {nome_inst}")
            logr_inst = dados_org["address"]["street"]
            nro_inst = dados_org["address"]["number"]
            bairro_inst = dados_org["address"]["district"]
            cidade_inst = dados_org["address"]["city"]
            estado_inst = dados_org["address"]["state"]
            endereco_inst = (f"Endereço do instelecimento: {logr_inst} {nro_inst}, {bairro_inst} - {cidade_inst}/{estado_inst}")
        else:
            print("CNPJ inválido!")

        tipo_org = "instelecimento fornecedor"
        tel_inst = input("Digite o telefone comercial do instelecimento para contato: ")
        email_inst = input("Digite o email do instelecimento: ")
        senha_inst = input("Crie a senha para o acesso da conta: ")

        str_insert = f""" INSERT INTO ALIM_TB_ORGANIZACAO (
            nr_cnpj, nm_fantasia, ds_endereco, tp_organizacao, nr_telefone, ds_email_contato, ds_senha_hash) VALUES ('{cnpj_org}', '{nome_inst}', '{endereco_inst}', '{tipo_org}', '{tel_inst}', '{email_inst}', '{senha_inst}')"""

        cursor.execute(str_insert)

        conexao.commit()


def inserir_conta_inst(cursor, conexao):

        cnpj_org = int(input("Informe o CNPJ da instituição (apenas números): "))
        buscar_conta(cursor, cnpj_org)

        while buscar_conta(cursor, cnpj_org) != -1:
            cnpj_org = int(input(f"O CNPJ {cnpj_org} já está cadastrado no sistema, informe outro CNPJ: "))
            buscar_conta(cursor, cnpj_org)

        str_endpoint = f"https://open.cnpja.com/office/{cnpj_org}"
        requisicao = requests.get(str_endpoint)

        if requisicao.status_code == 200:
            dados_org = requisicao.json()
            nome_inst = dados_org["company"]["name"]
            print(f"Nome fantasia: {nome_inst}")
            logr_inst = dados_org["address"]["street"]
            nro_inst = dados_org["address"]["number"]
            bairro_inst = dados_org["address"]["district"]
            cidade_inst = dados_org["address"]["city"]
            estado_inst = dados_org["address"]["state"]
            endereco_inst = (f"Endereço do instelecimento: {logr_inst} {nro_inst}, {bairro_inst} - {cidade_inst}/{estado_inst}")
        else:
            print("CNPJ inválido!")

        tipo_org = "instituição receptora"
        tel_inst = input("Digite o telefone comercial da instituição para contato: ")
        email_inst = input("Digite o email da instituição: ")
        senha_inst = input("Crie a senha para o acesso da conta: ")

        str_insert = f""" INSERT INTO ALIM_TB_ORGANIZACAO (
            nr_cnpj, nm_fantasia, ds_endereco, tp_organizacao, nr_telefone, ds_email_contato, ds_senha_hash) VALUES ('{cnpj_org}', '{nome_inst}', '{endereco_inst}', '{tipo_org}', '{tel_inst}', '{email_inst}', '{senha_inst}')"""

        cursor.execute(str_insert)

        conexao.commit()


def main():
    while True:
        print("\n" + "="*20)
        print(f"     Acesse sua conta e faça a comida chegar a quem precisa.")
        print("="*20)
        print("\n")
        print("Qual o tipo da sua conta? \n")
        print("1 - instelecimento fornecedor")
        print("2 - Instituição receptora")
        print("3 - Administrador")
        print("4 - Ainda não tem uma conta? Crie uma agora!")
        print("5 - Sair \n")

        opcao = int(input("Digite uma opção para entrar: "))

        match opcao:
            case 1:
                print("Realizar função de validar CNPJ")
                time.sleep(2)
                os.system('cls')
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


def menu_instelecimento():

    while True:

        print("\n" + "="*20)
        print(f"     Painel de controle da [nome da empresa]")
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