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
        host = os.getenv("ORACLE_HOST")
        port = int(os.getenv("ORACLE_PORT", "1521"))
        service = os.getenv("ORACLE_SERVICE")
        user = os.getenv("ORACLE_USER")
        password = os.getenv("ORACLE_PASSWORD")
        str_conexao = orcl.makedsn(host, port, service_name=service)
        conexao = orcl.connect(
            user=user, password=password, dsn=str_conexao, tcp_connect_timeout=10
        )
        cursor = conexao.cursor()
    except (orcl.Error, OSError, ValueError) as erro:
        if conexao is not None:
            conexao.close()
        print(f"Erro ao conectar com o banco: {erro}")
        return False, None, None
    return True, conexao, cursor


def ler_opcao(pergunta):
    # Se o usuário digitar uma letra, devolve -1 (cai no "opção inválida")
    try:
        return int(input(pergunta))
    except ValueError:
        return -1


def buscar_conta(cursor, cnpj_org):
    # Procura em todas as contas, inclusive as inativas (RN02)
    cursor.execute(
        "SELECT CD_ORGANIZACAO FROM ALIM_TB_ORGANIZACAO WHERE NR_CNPJ = :cnpj_org",
        {"cnpj_org": cnpj_org},
    )
    conta = cursor.fetchone()
    if conta is None:
        return -1
    return conta[0]


def inserir_conta_estab(cursor, conexao):

    try:
        # O CNPJ fica como texto (como número perderia o zero à esquerda).
        # Pede de novo se não tiver 14 números ou se já estiver cadastrado
        cnpj_org = input("Informe o CNPJ do estabelecimento (apenas números): ")
        while (
            len(cnpj_org) != 14
            or not cnpj_org.isdigit()
            or buscar_conta(cursor, cnpj_org) != -1
        ):
            cnpj_org = input(
                "CNPJ inválido ou já cadastrado, informe outro CNPJ (14 números): "
            )

        # Se a API falhar (sem internet, CNPJ não encontrado...), o usuário digita os dados
        try:
            requisicao = requests.get(
                f"https://open.cnpja.com/office/{cnpj_org}", timeout=10
            )
            requisicao.raise_for_status()
            dados_org = requisicao.json()
            nm_razao_social = dados_org["company"]["name"]
            nm_fantasia_estab = dados_org["alias"] or nm_razao_social
            logr_estab = dados_org["address"]["street"]
            nro_estab = dados_org["address"]["number"]
            bairro_estab = dados_org["address"]["district"]
            cidade_estab = dados_org["address"]["city"]
            estado_estab = dados_org["address"]["state"]
            endereco_estab = f"{logr_estab} {nro_estab}, {bairro_estab} - {cidade_estab}/{estado_estab}"
            print(f"Nome empresarial: {nm_razao_social}")
            print(f"Nome fantasia: {nm_fantasia_estab}")
            print(f"Endereço: {endereco_estab}")
        except (requests.RequestException, ValueError, KeyError, TypeError):
            print("Não foi possível consultar o CNPJ. Informe os dados manualmente.")
            nm_razao_social = input("Razão social: ")
            nm_fantasia_estab = input("Nome fantasia: ")
            endereco_estab = input("Endereço completo: ")

        tipo_org = "ESTABELECIMENTO"
        categoria_estab = input(
            "Categoria do estabelecimento (ex.: Padaria, Restaurante, Supermercado): "
        )
        tel_estab = input(
            "Digite o telefone comercial do estabelecimento para contato: "
        )
        email_estab = input("Digite o email do estabelecimento: ")
        nm_login_estab = input("Digite o nome de login do estabelecimento: ")
        senha_org = input("Crie a senha para o acesso da conta: ")

        cursor.execute(
            "INSERT INTO ALIM_TB_ORGANIZACAO (NR_CNPJ, TP_ORGANIZACAO, NM_RAZAO_SOCIAL, NM_FANTASIA, "
            "DS_LOGIN, DS_SENHA_HASH, DS_EMAIL_CONTATO, NR_TELEFONE, DS_ENDERECO) "
            "VALUES (:cnpj, :tipo, :razao, :fantasia, :login, :senha, :email, :tel, :endereco)",
            {
                "cnpj": cnpj_org,
                "tipo": tipo_org,
                "razao": nm_razao_social,
                "fantasia": nm_fantasia_estab,
                "login": nm_login_estab,
                "senha": senha_org,
                "email": email_estab,
                "tel": tel_estab,
                "endereco": endereco_estab,
            },
        )

        cd_organizacao = buscar_conta(cursor, cnpj_org)
        cursor.execute(
            "INSERT INTO ALIM_TB_ESTABELECIMENTO (CD_ORGANIZACAO, TP_ESTABELECIMENTO) "
            "VALUES (:cd, :categoria)",
            {"cd": cd_organizacao, "categoria": categoria_estab},
        )

        conexao.commit()
        print("Cadastro realizado com sucesso! Aguarde a aprovação de um administrador.")

    except orcl.Error as erro:
        conexao.rollback()
        print(
            "Não foi possível concluir o cadastro. Confira se o login já não está em uso e tente novamente!"
        )
        print(f"(Detalhe técnico: {erro})")


def alterar_conta_estab(cursor, conexao, estab):

    print(f"Telefone de contato: {estab['nr_telefone']}")
    nv_tel_estab = input("Informe um novo número de telefone (Enter para manter): ")
    if nv_tel_estab == "":
        nv_tel_estab = estab["nr_telefone"]

    print(f"Email para contato: {estab['ds_email_contato']}")
    nv_email_estab = input("Digite o novo email para contato (Enter para manter): ")
    if nv_email_estab == "":
        nv_email_estab = estab["ds_email_contato"]

    print(f"Endereço atual: {estab['ds_endereco']}")
    nv_endereco_estab = input(
        "Informe o novo endereço do estabelecimento (Enter para manter): "
    )
    if nv_endereco_estab == "":
        nv_endereco_estab = estab["ds_endereco"]

    nv_senha_org = input("Digite uma nova senha (Enter para manter): ")
    if nv_senha_org == "":
        nv_senha_org = estab["ds_senha_hash"]

    try:
        cursor.execute(
            "UPDATE ALIM_TB_ORGANIZACAO SET NR_TELEFONE = :tel, DS_EMAIL_CONTATO = :email, "
            "DS_ENDERECO = :endereco, DS_SENHA_HASH = :senha_org WHERE CD_ORGANIZACAO = :cd",
            {
                "tel": nv_tel_estab,
                "email": nv_email_estab,
                "endereco": nv_endereco_estab,
                "senha_org": nv_senha_org,
                "cd": estab["cd_organizacao"],
            },
        )

        if cursor.rowcount == 0:
            conexao.rollback()
            print("Nenhuma linha foi alterada!")
        else:
            conexao.commit()
            estab["nr_telefone"] = nv_tel_estab
            estab["ds_email_contato"] = nv_email_estab
            estab["ds_endereco"] = nv_endereco_estab
            estab["ds_senha_hash"] = nv_senha_org

            print("Alterações salvas com sucesso!")

    except orcl.Error:
        conexao.rollback()
        print("Não foi possivel realizar as alterações. Tente novamente!")


def inserir_conta_inst(cursor, conexao):

    try:
        cnpj_org = input("Informe o CNPJ da instituição (apenas números): ")
        while (
            len(cnpj_org) != 14
            or not cnpj_org.isdigit()
            or buscar_conta(cursor, cnpj_org) != -1
        ):
            cnpj_org = input(
                "CNPJ inválido ou já cadastrado, informe outro CNPJ (14 números): "
            )

        try:
            requisicao = requests.get(
                f"https://open.cnpja.com/office/{cnpj_org}", timeout=10
            )
            requisicao.raise_for_status()
            dados_org = requisicao.json()
            nm_razao_social = dados_org["company"]["name"]
            nm_fantasia_inst = dados_org["alias"] or nm_razao_social
            logr_inst = dados_org["address"]["street"]
            nro_inst = dados_org["address"]["number"]
            bairro_inst = dados_org["address"]["district"]
            cidade_inst = dados_org["address"]["city"]
            estado_inst = dados_org["address"]["state"]
            endereco_inst = f"{logr_inst} {nro_inst}, {bairro_inst} - {cidade_inst}/{estado_inst}"
            print(f"Nome empresarial: {nm_razao_social}")
            print(f"Nome fantasia: {nm_fantasia_inst}")
            print(f"Endereço: {endereco_inst}")
        except (requests.RequestException, ValueError, KeyError, TypeError):
            print("Não foi possível consultar o CNPJ. Informe os dados manualmente.")
            nm_razao_social = input("Razão social: ")
            nm_fantasia_inst = input("Nome fantasia: ")
            endereco_inst = input("Endereço completo: ")

        tipo_org = "INSTITUICAO"
        categoria_inst = input(
            "Categoria da instituição (ex.: ONG, Igreja, Banco de alimentos): "
        )
        tel_inst = input("Digite o telefone comercial da instituição para contato: ")
        email_inst = input("Digite o email da instituição: ")
        nm_login_inst = input("Digite o nome de login da instituição: ")
        senha_org = input("Crie a senha para o acesso da conta: ")

        cursor.execute(
            "INSERT INTO ALIM_TB_ORGANIZACAO (NR_CNPJ, TP_ORGANIZACAO, NM_RAZAO_SOCIAL, NM_FANTASIA, "
            "DS_LOGIN, DS_SENHA_HASH, DS_EMAIL_CONTATO, NR_TELEFONE, DS_ENDERECO) "
            "VALUES (:cnpj, :tipo, :razao, :fantasia, :login, :senha, :email, :tel, :endereco)",
            {
                "cnpj": cnpj_org,
                "tipo": tipo_org,
                "razao": nm_razao_social,
                "fantasia": nm_fantasia_inst,
                "login": nm_login_inst,
                "senha": senha_org,
                "email": email_inst,
                "tel": tel_inst,
                "endereco": endereco_inst,
            },
        )

        cd_organizacao = buscar_conta(cursor, cnpj_org)
        cursor.execute(
            "INSERT INTO ALIM_TB_INSTITUICAO (CD_ORGANIZACAO, TP_INSTITUICAO) "
            "VALUES (:cd, :categoria)",
            {"cd": cd_organizacao, "categoria": categoria_inst},
        )

        conexao.commit()
        print("Cadastro realizado com sucesso! Aguarde a aprovação de um administrador.")

    except orcl.Error as erro:
        conexao.rollback()
        print(
            "Não foi possível concluir o cadastro. Confira se o login já não está em uso e tente novamente!"
        )
        print(f"(Detalhe técnico: {erro})")  # pode remover antes da apresentação


def alterar_conta_inst(cursor, conexao, inst):

    print(f"Telefone de contato: {inst['nr_telefone']}")
    nv_tel_inst = input("Informe um novo número de telefone (Enter para manter): ")
    if nv_tel_inst == "":
        nv_tel_inst = inst["nr_telefone"]

    print(f"Email para contato: {inst['ds_email_contato']}")
    nv_email_inst = input("Digite o novo email para contato (Enter para manter): ")
    if nv_email_inst == "":
        nv_email_inst = inst["ds_email_contato"]

    print(f"Endereço atual: {inst['ds_endereco']}")
    nv_endereco_inst = input(
        "Informe o novo endereço da instituição (Enter para manter): "
    )
    if nv_endereco_inst == "":
        nv_endereco_inst = inst["ds_endereco"]

    nv_senha_org = input("Digite uma nova senha (Enter para manter): ")
    if nv_senha_org == "":
        nv_senha_org = inst["ds_senha_hash"]

    try:
        cursor.execute(
            "UPDATE ALIM_TB_ORGANIZACAO SET NR_TELEFONE = :tel, DS_EMAIL_CONTATO = :email, "
            "DS_ENDERECO = :endereco, DS_SENHA_HASH = :senha_org WHERE CD_ORGANIZACAO = :cd",
            {
                "tel": nv_tel_inst,
                "email": nv_email_inst,
                "endereco": nv_endereco_inst,
                "senha_org": nv_senha_org,
                "cd": inst["cd_organizacao"],
            },
        )

        if cursor.rowcount == 0:
            conexao.rollback()
            print("Nenhuma linha foi alterada!")
        else:
            conexao.commit()
            inst["nr_telefone"] = nv_tel_inst
            inst["ds_email_contato"] = nv_email_inst
            inst["ds_endereco"] = nv_endereco_inst
            inst["ds_senha_hash"] = nv_senha_org

            print("Alterações salvas com sucesso!")

    except orcl.Error:
        conexao.rollback()
        print("Não foi possivel realizar as alterações. Tente novamente!")


def login_adm(cursor, email, senha):

    cursor.execute(
        "SELECT CD_USUARIO, NM_USUARIO FROM ALIM_TB_USUARIO "
        "WHERE DS_EMAIL = :email AND DS_SENHA_HASH = :senha AND ST_USUARIO = 'ATIVO'",
        {"email": email, "senha": senha},
    )

    linha = cursor.fetchone()
    if linha is None:
        return None
    return {"cd_usuario": linha[0], "nm_usuario": linha[1]}


def login_estab(cursor, cnpj_estab, senha_estab):

    cursor.execute(
        "SELECT CD_ORGANIZACAO, NR_CNPJ, NM_FANTASIA, DS_ENDERECO, TP_ORGANIZACAO, NR_TELEFONE, DS_EMAIL_CONTATO, NM_RAZAO_SOCIAL, DS_LOGIN, ST_CADASTRO, ST_CONTA, DT_INATIVACAO, DS_MOTIVO_INATIVACAO, DS_SENHA_HASH, CD_USUARIO_ADMIN FROM ALIM_TB_ORGANIZACAO WHERE NR_CNPJ = :cnpj_estab AND DS_SENHA_HASH = :senha_estab AND TP_ORGANIZACAO = 'ESTABELECIMENTO'",
        {"cnpj_estab": cnpj_estab, "senha_estab": senha_estab},
    )

    linha = cursor.fetchone()
    if linha is None:
        return None
    return {
        "cd_organizacao": linha[0],
        "nr_cnpj": linha[1],
        "nm_fantasia": linha[2],
        "ds_endereco": linha[3],
        "tp_organizacao": linha[4],
        "nr_telefone": linha[5],
        "ds_email_contato": linha[6],
        "nm_razao_social": linha[7],
        "ds_login": linha[8],
        "st_cadastro": linha[9],
        "st_conta": linha[10],
        "dt_inativacao": linha[11],
        "ds_motivo_inativacao": linha[12],
        "ds_senha_hash": linha[13],
    }


def login_inst(cursor, cnpj_inst, senha_inst):

    cursor.execute(
        "SELECT CD_ORGANIZACAO, NR_CNPJ, NM_FANTASIA, DS_ENDERECO, TP_ORGANIZACAO, NR_TELEFONE, DS_EMAIL_CONTATO, NM_RAZAO_SOCIAL, DS_LOGIN, ST_CADASTRO, ST_CONTA, DT_INATIVACAO, DS_MOTIVO_INATIVACAO, DS_SENHA_HASH, CD_USUARIO_ADMIN FROM ALIM_TB_ORGANIZACAO WHERE NR_CNPJ = :cnpj_inst AND DS_SENHA_HASH = :senha_inst AND TP_ORGANIZACAO = 'INSTITUICAO'",
        {"cnpj_inst": cnpj_inst, "senha_inst": senha_inst},
    )

    linha = cursor.fetchone()
    if linha is None:
        return None
    return {
        "cd_organizacao": linha[0],
        "nr_cnpj": linha[1],
        "nm_fantasia": linha[2],
        "ds_endereco": linha[3],
        "tp_organizacao": linha[4],
        "nr_telefone": linha[5],
        "ds_email_contato": linha[6],
        "nm_razao_social": linha[7],
        "ds_login": linha[8],
        "st_cadastro": linha[9],
        "st_conta": linha[10],
        "dt_inativacao": linha[11],
        "ds_motivo_inativacao": linha[12],
        "ds_senha_hash": linha[13],
    }


def main():

    conexao_db, conexao, cursor = conectar_db()

    if conexao_db is True:
        while True:
            print("\n" + "=" * 20)
            print("     Acesse sua conta e faça a comida chegar a quem precisa.")
            print("=" * 20)
            print("\n")
            print("1 - Entrar como estabelecimento")
            print("2 - Entrar como instituição")
            print("3 - Entrar como administrador")
            print("4 - Ainda não tem uma conta? Crie uma agora!")
            print("5 - Sair \n")

            opcao = ler_opcao("Digite uma opção para entrar: ")

            try:
                match opcao:
                    case 1:
                        cnpj_estab = input(
                            "Insira o CNPJ do estabelecimento (apenas números): "
                        )
                        senha_estab = input("Digite a senha do estabelecimento: ")
                        estab = login_estab(cursor, cnpj_estab, senha_estab)

                        if estab is None:
                            print("CNPJ ou senha incorretos!")
                            time.sleep(2)
                            os.system("cls")
                        elif estab["st_conta"] == "INATIVA":
                            print("Esta conta está inativa. Fale com a administração.")
                            time.sleep(2)
                            os.system("cls")
                        else:
                            print("Entrando...")
                            time.sleep(2)
                            os.system("cls")
                            menu_estab(cursor, conexao, estab)
                    case 2:
                        cnpj_inst = input(
                            "Insira o CNPJ da instituição (apenas números): "
                        )
                        senha_inst = input("Digite a senha da instituição: ")
                        inst = login_inst(cursor, cnpj_inst, senha_inst)

                        if inst is None:
                            print("CNPJ ou senha incorretos!")
                            time.sleep(2)
                            os.system("cls")
                        elif inst["st_conta"] == "INATIVA":
                            print("Esta conta está inativa. Fale com a administração.")
                            time.sleep(2)
                            os.system("cls")
                        else:
                            print("Entrando...")
                            time.sleep(2)
                            os.system("cls")
                            menu_inst(cursor, conexao, inst)
                    case 3:
                        email_adm = input("Digite o e-mail do administrador: ")
                        senha_adm = input("Digite a senha: ")
                        adm = login_adm(cursor, email_adm, senha_adm)

                        if adm is None:
                            print("E-mail ou senha incorretos!")
                            time.sleep(2)
                            os.system("cls")
                        else:
                            print("Entrando...")
                            time.sleep(2)
                            os.system("cls")
                            menu_adm(cursor, conexao, adm)
                    case 4:
                        print("Digite o tipo de conta que deseja criar")
                        print("1 - Conta de estabelecimento fornecedor")
                        print("2 - Conta de instituição receptora")
                        print("3 - Voltar")
                        opcao_conta = ler_opcao("Informe a opção: ")

                        if opcao_conta == 1:
                            inserir_conta_estab(cursor, conexao)
                        elif opcao_conta == 2:
                            inserir_conta_inst(cursor, conexao)
                        elif opcao_conta != 3:
                            print("Opção inválida!")
                    case 5:
                        print("Saindo...")
                        time.sleep(2)
                        os.system("cls")
                        break
                    case _:
                        print("Opção inválida, tente novamente!")
                        time.sleep(2)
                        os.system("cls")
            except orcl.Error as erro:
                conexao.rollback()
                print("Erro ao acessar o banco de dados. Tente novamente!")
                print(f"(Detalhe técnico: {erro})")

        # Fecha a conexão ao sair do programa
        cursor.close()
        conexao.close()
    else:
        print("A conexão com o banco de dados não foi estabelecida!")


def menu_estab(cursor, conexao, estab):

    while True:

        print("\n" + "=" * 20)
        print(f"     Painel de controle da {estab['nm_fantasia']}")
        print("=" * 20)
        print("1 - Alterar dados cadastrais")
        print("2 - Buscar doações")
        print("3 - Pesquisar instituições")
        print("4 - Visualizar solicitações de instituições")
        print("5 - Ver publicações de necessidades")
        print("6 - Publicar uma oferta")
        print("7 - Deletar publicação")
        print("8 - Sair")

        opcao = ler_opcao("Digite a opção desejada: ")

        match opcao:
            case 1:
                alterar_conta_estab(cursor, conexao, estab)
            case 2:
                print("Função para buscar doações")
                time.sleep(2)
                os.system("cls")
            case 3:
                print("Função para pesquisar por instituições receptoras")
                time.sleep(2)
                os.system("cls")
            case 4:
                print("Função para visualizar as solicitações das instituições")
                time.sleep(2)
                os.system("cls")
            case 5:
                print("Função para ver as publicações de necessidades das instituições")
                time.sleep(2)
                os.system("cls")
            case 6:
                print("Função para publicar uma oferta")
                time.sleep(2)
                os.system("cls")
            case 7:
                print("Função para deletar uma publicação")
                time.sleep(2)
                os.system("cls")
            case 8:
                print("Saindo...")
                time.sleep(2)
                os.system("cls")
                break
            case _:
                print("Opção inválida, tente novamente!")
                time.sleep(2)
                os.system("cls")


def menu_inst(cursor, conexao, inst):

    while True:

        print("\n" + "=" * 20)
        print(f"     Painel de controle da {inst['nm_fantasia']}")
        print("=" * 20)
        print("1 - Alterar dados cadastrais")
        print("2 - Sair")

        opcao = ler_opcao("Digite a opção desejada: ")

        match opcao:
            case 1:
                alterar_conta_inst(cursor, conexao, inst)
            case 2:
                print("Saindo...")
                time.sleep(2)
                os.system("cls")
                break
            case _:
                print("Opção inválida, tente novamente!")
                time.sleep(2)
                os.system("cls")


def menu_adm(cursor, conexao, adm):

    print(f"Bem-vindo, {adm['nm_usuario']}! Menu do administrador em construção.")
    time.sleep(2)
    os.system("cls")


if __name__ == "__main__":
    main()