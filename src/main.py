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

def inserir_conta_estab(cursor, conexao):

        cnpj_org = int(input("Informe o CNPJ do estabelecimento (apenas números): "))
        buscar_conta(cursor, cnpj_org)

        while buscar_conta(cursor, cnpj_org) != -1:
            cnpj_org = int(input(f"O CNPJ {cnpj_org} já está cadastrado no sistema, informe outro CNPJ: "))
            buscar_conta(cursor, cnpj_org)

        str_endpoint = f"https://open.cnpja.com/office/{cnpj_org}"
        requisicao = requests.get(str_endpoint)

        if requisicao.status_code == 200:
            dados_org = requisicao.json()
            nm_fantasia_estab = dados_org["alias"]
            nm_razao_social = dados_org["company"]["name"]
            logr_estab = dados_org["address"]["street"]
            nro_estab = dados_org["address"]["number"]
            bairro_estab = dados_org["address"]["district"]
            cidade_estab = dados_org["address"]["city"]
            estado_estab = dados_org["address"]["state"]
            endereco_estab = f"Endereço do estabelecimento: {logr_estab} {nro_estab}, {bairro_estab} - {cidade_estab}/{estado_estab}"
            print(f"Nome empresarial: {nm_razao_social}")
            print(f"Nome fantasia: {nm_fantasia_estab}")
            print(f"Endereço: {endereco_estab}")
        else:
            print("CNPJ inválido!")

        tipo_org = "estabelecimento fornecedor"
        tel_estab = input("Digite o telefone comercial do estabelecimento para contato: ")
        email_estab = input("Digite o email do estabelecimento: ")
        nm_login_estab = input("Digite o nome de login do estabelecimento: ")
        senha_org = input("Crie a senha para o acesso da conta: ")
        st_cadastro_estab = f"Pendente"
        st_conta_estab = f"Ativa"
        dt_inativacao = ""
        motivo_inativacao = ""


        str_insert = f""" INSERT INTO ALIM_TB_ORGANIZACAO (
            nr_cnpj, nm_fantasia, nm_razao_social, ds_endereco, tp_organizacao, nr_telefone, ds_email_contato, ds_login, ds_senha_hash, st_cadastro, st_conta, dt_inativacao, ds_motivo_inativacao) VALUES ('{cnpj_org}', '{nm_fantasia_estab}', '{nm_razao_social}', '{endereco_estab}', '{tipo_org}', '{tel_estab}', '{email_estab}', '{nm_login_estab}', '{senha_org}', '{st_cadastro_estab}', '{st_conta_estab}', '{dt_inativacao}', '{motivo_inativacao}')"""

        cursor.execute(str_insert)

        conexao.commit()

def alterar_conta_estab(cursor, conexao, estab):

    print(f"Telefone de contato: {estab['nr_telefone']}")
    nv_tel_estab = input("Informe um novo número de telefone para contato: ")

    print(f"Email para contato: {estab['ds_email_contato']}")
    nv_email_estab = input("Digite o novo email para contato: ")

    print(f"Endereço atual: {estab['ds_endereco']}")
    nv_endereco_estab = input("Informe o novo endereço do estabelecimento: ")

    nv_senha_org = input("Digite uma nova senha: ")

    if nv_tel_estab or nv_email_estab or nv_endereco_estab or nv_senha_org != "":

        try:

            cursor.execute(f"""UPDATE ALIM_TB_ORGANIZACAO SET NR_TELEFONE = :tel, DS_EMAIL_CONTATO = :email, DS_ENDERECO = :endereco, DS_SENHA_HASH = :senha_org WHERE CD_ORGANIZACAO = :cd, {"tel": nv_tel_estab, "email": nv_email_estab, "endereco": nv_endereco_estab, "senha_org": nv_senha_org, "cd": estab["cd_organizacao"]}""")

            if cursor.rowcount == 0:
                conexao.rollback()
                print("Nenhuma linha foi alterada!")
            else:
                conexao.commit()
                estab['nr_telefone'] = nv_tel_estab
                estab['ds_email_contato'] = nv_email_estab
                estab['ds_endereco'] = nv_endereco_estab
                estab['ds_senha_hash'] = nv_senha_org

                print("Alterações salvas com sucesso!")

        except orcl.Error:
            conexao.rollback()
            print("Não foi possivel realizar as alterações. Tente novamente!")


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
            nm_fantasia_inst = dados_org["alias"]
            nm_razao_social = dados_org["company"]["name"]
            logr_inst = dados_org["address"]["street"]
            nro_inst = dados_org["address"]["number"]
            bairro_inst = dados_org["address"]["district"]
            cidade_inst = dados_org["address"]["city"]
            estado_inst = dados_org["address"]["state"]
            endereco_inst = (f"Endereço da instituição: {logr_inst} {nro_inst}, {bairro_inst} - {cidade_inst}/{estado_inst}")
            print(f"Nome empresarial: {nm_razao_social}")
            print(f"Nome fantasia: {nm_fantasia_inst}")
            print(f"Endereço: {endereco_inst}")
        else:
            print("CNPJ inválido!")

        tipo_org = "instituição receptora"
        tel_inst = input("Digite o telefone comercial da instituição para contato: ")
        email_inst = input("Digite o email da instituição: ")
        nm_login_inst = input("Digite o nome de login da instituição: ")
        senha_org = input("Crie a senha para o acesso da conta: ")
        st_cadastro_inst = f"Pendente"
        st_conta_inst = f"Ativa"
        dt_inativacao = ""
        motivo_inativacao = ""
        

        str_insert = f""" INSERT INTO ALIM_TB_ORGANIZACAO (
            nr_cnpj, nm_fantasia, nm_razao_social, ds_endereco, tp_organizacao, nr_telefone, ds_email_contato, ds_login, ds_senha_hash, st_cadastro, st_conta, dt_inativacao, ds_motivo_inativacao) VALUES ('{cnpj_org}', '{nm_fantasia_inst}', '{nm_razao_social}', '{endereco_inst}', '{tipo_org}', '{tel_inst}', '{email_inst}', '{nm_login_inst}', '{senha_org}', '{st_cadastro_inst}', '{st_conta_inst}', '{dt_inativacao}', '{motivo_inativacao}')"""

        cursor.execute(str_insert)

        conexao.commit()


def alterar_conta_inst(cursor, conexao, inst):

    print(f"Telefone de contato: {inst['nr_telefone']}")
    nv_tel_inst = input("Informe um novo número de telefone para contato: ")

    print(f"Email para contato: {inst['ds_email_contato']}")
    nv_email_inst = input("Digite o novo email para contato: ")

    print(f"Endereço atual: {inst['ds_endereco']}")
    nv_endereco_inst = input("Informe o novo endereço da instituição: ")

    nv_senha_org = input("Digite uma nova senha: ")

    if nv_tel_inst or nv_email_inst or nv_endereco_inst or nv_senha_org != "":

        try:

            cursor.execute(f"""UPDATE ALIM_TB_ORGANIZACAO SET NR_TELEFONE = :tel, DS_EMAIL_CONTATO = :email, DS_ENDERECO = :endereco, DS_SENHA_HASH = :senha_org WHERE CD_ORGANIZACAO = :cd, {"tel": nv_tel_inst, "email": nv_email_inst, "endereco": nv_endereco_inst, "senha_org": nv_senha_org, "cd": inst["cd_organizacao"]}""")

            if cursor.rowcount == 0:
                conexao.rollback()
                print("Nenhuma linha foi alterada!")
            else:
                conexao.commit()
                inst['nr_telefone'] = nv_tel_inst
                inst['ds_email_contato'] = nv_email_inst
                inst['ds_endereco'] = nv_endereco_inst
                inst['ds_senha_hash'] = nv_senha_org

                print("Alterações salvas com sucesso!")

        except orcl.Error:
            conexao.rollback()
            print("Não foi possivel realizar as alterações. Tente novamente!")


def login_estab(cursor, cnpj_estab, senha_estab):

    cursor.execute("SELECT CD_ORGANIZACAO, NR_CNPJ, NM_FANTASIA, DS_ENDERECO, TP_ORGANIZACAO, NR_TELEFONE, DS_EMAIL_CONTATO, NM_RAZAO_SOCIAL, DS_LOGIN, ST_CADASTRO, ST_CONTA, DT_INATIVACAO, DS_MOTIVO_INATIVACAO, DS_SENHA_HASH, CD_USUARIO_ADMIN FROM ALIM_TB_ORGANIZACAO WHERE NR_CNPJ = :cnpj_estab AND DS_SENHA_HASH = :senha_estab", {"cnpj_estab": cnpj_estab, "senha_estab": senha_estab})

    linha = cursor.fetchone()
    if linha is None:
        return None
    return {"cd_organizacao": linha[0], "nr_cnpj": linha[1], "nm_fantasia": linha[2], "ds_endereco": linha[3], "tp_organizacao": linha[4], "nr_telefone": linha[5], "ds_email_contato": linha[6], "nm_razao_social": linha[7], "ds_login": linha[8], "st_cadastro": linha[9], "st_conta": linha[10], "dt_inativacao": linha[11], "ds_motivo_inativacao": linha[12], "ds_senha_hash": linha[13]}

def login_inst(cursor, cnpj_inst, senha_inst):

    cursor.execute("SELECT CD_ORGANIZACAO, NR_CNPJ, NM_FANTASIA, DS_ENDERECO, TP_ORGANIZACAO, NR_TELEFONE, DS_EMAIL_CONTATO, NM_RAZAO_SOCIAL, DS_LOGIN, ST_CADASTRO, ST_CONTA, DT_INATIVACAO, DS_MOTIVO_INATIVACAO, DS_SENHA_HASH, CD_USUARIO_ADMIN FROM ALIM_TB_ORGANIZACAO WHERE NR_CNPJ = :cnpj_inst AND DS_SENHA_HASH = :senha_inst", {"cnpj_inst": cnpj_inst, "senha_inst": senha_inst})

    linha = cursor.fetchone()
    if linha is None:
        return None
    return {"cd_organizacao": linha[0], "nr_cnpj": linha[1], "nm_fantasia": linha[2], "ds_endereco": linha[3], "tp_organizacao": linha[4], "nr_telefone": linha[5], "ds_email_contato": linha[6], "nm_razao_social": linha[7], "ds_login": linha[8], "st_cadastro": linha[9], "st_conta": linha[10], "dt_inativacao": linha[11], "ds_motivo_inativacao": linha[12], "ds_senha_hash": linha[13]}

def main():

    conexao_db, conexao, cursor = conectar_db()


    if conexao_db is True:
        while True:
            print("\n" + "="*20)
            print(f"     Acesse sua conta e faça a comida chegar a quem precisa.")
            print("="*20)
            print("\n")
            print("1 - Entrar como estabelecimento")
            print("2 - Entrar como instituição")
            print("3 - Entrar como administrador")
            print("4 - Ainda não tem uma conta? Crie uma agora!")
            print("5 - Sair \n")

            opcao = int(input("Digite uma opção para entrar: "))

            match opcao:
                case 1:
                    cnpj_estab = input("Insira o CNPJ do estabelecimento: ")
                    senha_estab = input("Digite a senha do estabelecimento: ")
                    estab = login_estab(cursor, cnpj_estab, senha_estab)

                    if estab is None:
                        print("CNPJ ou senha incorretos!")
                        time.sleep(2)
                        os.system('cls')
                    else:
                        print("Entrando...")
                        time.sleep(2)
                        os.system('cls')
                        menu_estab(cursor, conexao, estab)
                case 2:
                    cnpj_inst = input("Insira o CNPJ da instituição: ")
                    senha_inst = input("Digite a senha da instituição: ")
                    inst = login_inst(cursor, cnpj_inst, senha_inst)

                    if inst is None:
                        print("CNPJ ou senha incorretos!")
                        time.sleep(2)
                        os.system('cls')
                    else:
                        time.sleep(2)
                        os.system('cls')
                        menu_inst(cursor, conexao, inst)
                case 3:
                    print("Entrar com CPF e senha")
                case 4:
                    print("Digite o tipo de conta que deseja criar")
                    print("1 - Conta de estabelecimento fornecedor")
                    print("2 - Conta de instituição receptora")
                    print("3 - Conta de administrador")
                    print("4 - Voltar")
                    opcao = int(input("Informe a opção: "))

                    if 1 <= opcao <= 4:
                        if opcao == 1:
                            inserir_conta_estab(cursor, conexao)
                        elif opcao == 2:
                            inserir_conta_inst(cursor, conexao)
                        elif opcao == 3:
                            print("Criar função de inserir conta de adm")
                        elif opcao == 4:
                            break
                        else:
                            print("Opção inválida!")

                case 5:
                    print("Saindo...")
                    time.sleep(2)
                    os.system('cls')
                    break   
    else:
        print("A conexão com o banco de dados não foi estabelecida!")             


def menu_estab(cursor, conexao, estab):

    while True:

        print("\n" + "="*20)
        print(f"     Painel de controle da {estab["nm_fantasia"]}")
        print("="*20)
        print("1 - Alterar dados cadastrais")
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
                alterar_conta_estab(cursor, conexao, estab)
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

def menu_inst(cursor, conexao, inst):

    return print("Menu da Instituição!")













if __name__ == "__main__":
    main()