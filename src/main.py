import os
import time
from datetime import datetime
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
        print(
            "Cadastro realizado com sucesso! Aguarde a aprovação de um administrador."
        )

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
            endereco_inst = (
                f"{logr_inst} {nro_inst}, {bairro_inst} - {cidade_inst}/{estado_inst}"
            )
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
        print(
            "Cadastro realizado com sucesso! Aguarde a aprovação de um administrador."
        )

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


def buscar_publi_estab(cursor, estab):
    cursor.execute(
        """SELECT CD_PUBLICACAO, NM_TITULO, DS_DESCRICAO, DT_PUBLICACAO, ST_PUBLICACAO FROM ALIM_TB_PUBLICACAO WHERE CD_ORGANIZACAO = :cd ORDER BY DT_PUBLICACAO DESC""",
        {"cd": estab["cd_organizacao"]},
    )

    publicacoes = cursor.fetchall()
    if not publicacoes:
        print("\n" + "Nenhuma publicação realizada!")
        return

    print("=== PUBLICAÇÕES ===")

    for publicacao in publicacoes:
        print("=" * 30)
        print(f"Código: {publicacao[0]}")
        print(f"Título: {publicacao[1]}")
        print(f"Descrição: {publicacao[2]}")
        print(f"Data: {publicacao[3]}")
        print(f"Status: {publicacao[4]}")

    print("=" * 30)

    return publicacoes


def ver_instituicoes(cursor):
    cursor.execute(
        """SELECT NM_FANTASIA, NR_CNPJ, DS_EMAIL_CONTATO, NR_TELEFONE, DS_ENDERECO FROM ALIM_TB_ORGANIZACAO WHERE TP_ORGANIZACAO = 'INSTITUICAO' """
    )
    instituicoes = cursor.fetchall()
    if not instituicoes:
        print("\n" + "Nenhuma instituição encontrada!")
        return

    print("=== INSTITUIÇÕES ===")

    for instituicao in instituicoes:
        print("=" * 30)
        print(f"Nome: {instituicao[0]}")
        print(f"CNPJ: {instituicao[1]}")
        print(f"Email: {instituicao[2]}")
        print(f"Telefone: {instituicao[3]}")
        print(f"Endereço: {instituicao[4]}")

    print("=" * 30)

    return instituicoes


def ver_solicitacoes_estab(cursor, estab):
    # Solicitações que as instituições fizeram nas ofertas deste estabelecimento
    cursor.execute(
        "SELECT S.CD_SOLICITACAO, O.NM_FANTASIA, P.NM_TITULO, S.DT_SOLICITACAO, S.ST_SOLICITACAO "
        "FROM ALIM_TB_SOLICITACAO S "
        "JOIN ALIM_TB_PUBLICACAO P ON P.CD_PUBLICACAO = S.CD_OFERTA "
        "JOIN ALIM_TB_ORGANIZACAO O ON O.CD_ORGANIZACAO = S.CD_INSTITUICAO "
        "WHERE P.CD_ORGANIZACAO = :cd ORDER BY S.DT_SOLICITACAO DESC",
        {"cd": estab["cd_organizacao"]},
    )

    solicitacoes = cursor.fetchall()
    if not solicitacoes:
        print("\n" + "Nenhuma solicitação recebida!")
        return

    print("=== SOLICITAÇÕES RECEBIDAS ===")

    for solicitacao in solicitacoes:
        print("=" * 30)
        print(f"Código da solicitação: {solicitacao[0]}")
        print(f"Instituição: {solicitacao[1]}")
        print(f"Oferta: {solicitacao[2]}")
        print(f"Data: {solicitacao[3].strftime('%d/%m/%Y')}")
        print(f"Status: {solicitacao[4]}")

        # Alimentos pedidos nesta solicitação
        cursor.execute(
            "SELECT A.NM_ALIMENTO, I.QT_SOLICITADA_KG, I.QT_ALOCADA_KG "
            "FROM ALIM_TB_ITEM_SOLICITACAO I "
            "JOIN ALIM_TB_ITEM_OFERTA IO ON IO.CD_ITEM_OFERTA = I.CD_ITEM_OFERTA "
            "JOIN ALIM_TB_ALIMENTO A ON A.CD_ALIMENTO = IO.CD_ALIMENTO "
            "WHERE I.CD_SOLICITACAO = :cd",
            {"cd": solicitacao[0]},
        )
        itens = cursor.fetchall()
        for item in itens:
            print(f"     - {item[0]}: pedido {item[1]} kg / reservado {item[2]} kg")

    print("=" * 30)

    return solicitacoes


def responder_solicitacao(cursor, conexao, estab):
    cd_solicitacao = ler_opcao(
        "\nDigite o código da solicitação que deseja responder (0 para voltar): "
    )
    if cd_solicitacao == 0:
        return

    try:
        cursor.execute(
            "SELECT S.ST_SOLICITACAO, S.CD_OFERTA, S.CD_INSTITUICAO, P.ST_PUBLICACAO "
            "FROM ALIM_TB_SOLICITACAO S "
            "JOIN ALIM_TB_PUBLICACAO P ON P.CD_PUBLICACAO = S.CD_OFERTA "
            "WHERE S.CD_SOLICITACAO = :cd AND P.CD_ORGANIZACAO = :org",
            {"cd": cd_solicitacao, "org": estab["cd_organizacao"]},
        )
        solicitacao = cursor.fetchone()

        if solicitacao is None:
            print("Solicitação não encontrada!")
        elif solicitacao[0] != "PENDENTE":
            print("Só é possível responder solicitações com status PENDENTE!")
        else:
            print("\n1 - Aceitar")
            print("2 - Recusar")
            print("3 - Voltar")
            resposta = ler_opcao("Escolha uma opção: ")

            if resposta == 1:
                if solicitacao[3] == "FINALIZADO":
                    # RN42: oferta finalizada não recebe novas solicitações
                    print(
                        "Esta oferta já foi finalizada. Só é possível recusar a solicitação."
                    )
                else:
                    aceitar_solicitacao(
                        cursor, conexao, cd_solicitacao, solicitacao[1], solicitacao[2]
                    )
            elif resposta == 2:
                recusar_solicitacao(cursor, conexao, cd_solicitacao)
            elif resposta != 3:
                print("Opção inválida!")

    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível responder a solicitação. Tente novamente!")
        print(f"(Detalhe técnico: {erro})")


def aceitar_solicitacao(cursor, conexao, cd_solicitacao, cd_oferta, cd_instituicao):
    try:
        # Alimentos pedidos nesta solicitação
        cursor.execute(
            "SELECT I.CD_ITEM_SOLICITACAO, I.CD_ITEM_OFERTA, A.NM_ALIMENTO, I.QT_SOLICITADA_KG, IO.QT_OFERTADA_KG "
            "FROM ALIM_TB_ITEM_SOLICITACAO I "
            "JOIN ALIM_TB_ITEM_OFERTA IO ON IO.CD_ITEM_OFERTA = I.CD_ITEM_OFERTA "
            "JOIN ALIM_TB_ALIMENTO A ON A.CD_ALIMENTO = IO.CD_ALIMENTO "
            "WHERE I.CD_SOLICITACAO = :cd",
            {"cd": cd_solicitacao},
        )
        itens = cursor.fetchall()
        if not itens:
            print("Esta solicitação não tem alimentos pedidos.")
            return

        print("\n=== RESERVA DE QUANTIDADE ===")
        reservas = []
        total_reservado = 0

        for item in itens:
            # RN31: a soma reservada não pode passar do saldo do alimento.
            # Saldo livre = quantidade ofertada - o que já está reservado (ou entregue) em outras solicitações
            cursor.execute(
                "SELECT NVL(SUM(X.QT_ALOCADA_KG), 0) "
                "FROM ALIM_TB_ITEM_SOLICITACAO X "
                "JOIN ALIM_TB_SOLICITACAO S ON S.CD_SOLICITACAO = X.CD_SOLICITACAO "
                "WHERE X.CD_ITEM_OFERTA = :item AND X.CD_SOLICITACAO <> :sol "
                "AND S.ST_SOLICITACAO IN ('EM_ANDAMENTO', 'CONCLUIDA', 'CONCLUIDA_PARCIAL')",
                {"item": item[1], "sol": cd_solicitacao},
            )
            ja_comprometido = float(cursor.fetchone()[0])
            saldo_livre = round(float(item[4]) - ja_comprometido, 3)

            # Não pode reservar mais do que foi pedido nem mais do que o saldo livre
            limite = round(min(float(item[3]), saldo_livre), 3)
            if limite < 0:
                limite = 0

            print(f"\n{item[2]}: pedido {item[3]} kg | saldo livre {saldo_livre} kg")
            quantidade = -1
            while quantidade < 0 or quantidade > limite:
                try:
                    quantidade = float(
                        input(
                            f"Quanto deseja reservar? (de 0 até {limite} kg): "
                        ).replace(",", ".")
                    )
                except ValueError:
                    quantidade = -1
                if quantidade < 0 or quantidade > limite:
                    print(f"Digite um valor entre 0 e {limite}.")

            reservas.append({"cd_item_solicitacao": item[0], "quantidade": quantidade})
            total_reservado += quantidade

        if total_reservado == 0:
            print(
                "\nNenhuma quantidade foi reservada. Se não puder atender, use a opção de recusar."
            )
            return

        confirmar = ler_opcao(
            f"\nConfirmar a reserva de {round(total_reservado, 3)} kg no total? (1 - Sim / 2 - Não): "
        )
        if confirmar != 1:
            print("Solicitação não aceita.")
            return

        for reserva in reservas:
            cursor.execute(
                "UPDATE ALIM_TB_ITEM_SOLICITACAO SET QT_ALOCADA_KG = :qtd "
                "WHERE CD_ITEM_SOLICITACAO = :cd",
                {"qtd": reserva["quantidade"], "cd": reserva["cd_item_solicitacao"]},
            )

        cursor.execute(
            "UPDATE ALIM_TB_SOLICITACAO SET ST_SOLICITACAO = 'EM_ANDAMENTO' "
            "WHERE CD_SOLICITACAO = :cd AND ST_SOLICITACAO = 'PENDENTE'",
            {"cd": cd_solicitacao},
        )

        # RN28: a oferta passa a mostrar EM_ANDAMENTO enquanto houver negociação em curso
        cursor.execute(
            "UPDATE ALIM_TB_PUBLICACAO SET ST_PUBLICACAO = 'EM_ANDAMENTO' "
            "WHERE CD_PUBLICACAO = :cd AND ST_PUBLICACAO = 'DISPONIVEL'",
            {"cd": cd_oferta},
        )

        # Um commit só no final: tudo vale junto ou nada vale
        conexao.commit()
        print("\nSolicitação aceita!")

        # Não há chat interno: mostramos o contato da instituição para combinar a retirada
        cursor.execute(
            "SELECT NM_FANTASIA, DS_EMAIL_CONTATO, NR_TELEFONE "
            "FROM ALIM_TB_ORGANIZACAO WHERE CD_ORGANIZACAO = :cd",
            {"cd": cd_instituicao},
        )
        contato = cursor.fetchone()
        if contato is not None:
            print(f"Combine a retirada com {contato[0]}:")
            print(f"Email: {contato[1]}")
            print(f"Telefone: {contato[2]}")

    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível aceitar a solicitação. Tente novamente!")
        print(f"(Detalhe técnico: {erro})")  # pode remover antes da apresentação


def recusar_solicitacao(cursor, conexao, cd_solicitacao):
    # O banco exige motivo e data de encerramento para solicitação RECUSADA
    motivo = input("Informe o motivo da recusa: ")
    while motivo == "":
        motivo = input("O motivo é obrigatório. Informe o motivo da recusa: ")

    try:
        cursor.execute(
            "UPDATE ALIM_TB_SOLICITACAO SET ST_SOLICITACAO = 'RECUSADA', "
            "DT_ENCERRAMENTO = SYSDATE, DS_MOTIVO_ENCERRAMENTO = :motivo "
            "WHERE CD_SOLICITACAO = :cd AND ST_SOLICITACAO = 'PENDENTE'",
            {"motivo": motivo, "cd": cd_solicitacao},
        )

        if cursor.rowcount == 0:
            conexao.rollback()
            print("Nenhuma solicitação foi alterada!")
        else:
            conexao.commit()
            print("Solicitação recusada.")

    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível recusar a solicitação. Tente novamente!")
        print(f"(Detalhe técnico: {erro})")  # pode remover antes da apresentação


def ver_necessidades(cursor):
    # Necessidades publicadas pelas instituições que ainda não foram finalizadas
    cursor.execute(
        "SELECT P.CD_PUBLICACAO, O.NM_FANTASIA, P.NM_TITULO, P.DS_DESCRICAO, N.DT_LIMITE, P.ST_PUBLICACAO "
        "FROM ALIM_TB_PUBLICACAO P "
        "JOIN ALIM_TB_NECESSIDADE N ON N.CD_PUBLICACAO = P.CD_PUBLICACAO "
        "JOIN ALIM_TB_ORGANIZACAO O ON O.CD_ORGANIZACAO = P.CD_ORGANIZACAO "
        "WHERE P.ST_PUBLICACAO <> 'FINALIZADO' ORDER BY P.DT_PUBLICACAO DESC"
    )

    necessidades = cursor.fetchall()
    if not necessidades:
        print("\n" + "Nenhuma necessidade publicada!")
        return

    print("=== NECESSIDADES DAS INSTITUIÇÕES ===")

    for necessidade in necessidades:
        print("=" * 30)
        print(f"Código: {necessidade[0]}")
        print(f"Instituição: {necessidade[1]}")
        print(f"Título: {necessidade[2]}")
        print(f"Descrição: {necessidade[3]}")
        if necessidade[4] is None:
            print("Prazo: não informado")
        else:
            print(f"Prazo: {necessidade[4].strftime('%d/%m/%Y')}")
        print(f"Status: {necessidade[5]}")

        # Alimentos que a instituição precisa
        cursor.execute(
            "SELECT A.NM_ALIMENTO, I.QT_DESEJADA_KG "
            "FROM ALIM_TB_ITEM_NECESSIDADE I "
            "JOIN ALIM_TB_ALIMENTO A ON A.CD_ALIMENTO = I.CD_ALIMENTO "
            "WHERE I.CD_PUBLICACAO = :cd",
            {"cd": necessidade[0]},
        )
        itens = cursor.fetchall()
        for item in itens:
            print(f"     - {item[0]}: {item[1]} kg")

    print("=" * 30)

    return necessidades


def ler_itens_oferta(cursor):
    # Mostra o catálogo de alimentos e pede os itens da oferta.
    # Devolve uma lista de dicionários (um por alimento), ou lista vazia se não der para continuar
    cursor.execute(
        "SELECT CD_ALIMENTO, NM_ALIMENTO FROM ALIM_TB_ALIMENTO ORDER BY NM_ALIMENTO"
    )
    alimentos = cursor.fetchall()
    if not alimentos:
        print("\n" + "Nenhum alimento cadastrado no catálogo. Fale com a administração.")
        return []

    print("\n=== ALIMENTOS DISPONÍVEIS ===")
    codigos_validos = []
    for alimento in alimentos:
        print(f"{alimento[0]} - {alimento[1]}")
        codigos_validos.append(alimento[0])

    itens = []
    codigos_escolhidos = []

    while True:
        cd_alimento = ler_opcao("\nDigite o código do alimento: ")

        if cd_alimento not in codigos_validos:
            print("Código inválido. Digite um dos códigos da lista.")
        elif cd_alimento in codigos_escolhidos:
            print("Este alimento já foi adicionado à oferta.")
        else:
            quantidade = 0
            while quantidade <= 0:
                try:
                    quantidade = float(input("Quantidade em kg: ").replace(",", "."))
                except ValueError:
                    quantidade = 0
                if quantidade <= 0:
                    print("Digite uma quantidade maior que zero (ex.: 12.5).")

            validade = None
            texto_validade = input(
                "Data de validade (dd/mm/aaaa) ou Enter se não houver: "
            )
            while texto_validade != "" and validade is None:
                try:
                    validade = datetime.strptime(texto_validade, "%d/%m/%Y")
                    if validade.date() < datetime.now().date():
                        print("A validade não pode ser uma data que já passou.")
                        validade = None
                        texto_validade = input(
                            "Informe outra data (dd/mm/aaaa) ou Enter para pular: "
                        )
                except ValueError:
                    texto_validade = input(
                        "Data inválida. Use dd/mm/aaaa ou Enter para pular: "
                    )

            lote = input("Lote (Enter para pular): ")
            conservacao = input(
                "Condições de conservação (ex.: refrigerado a 4°C, Enter para pular): "
            )

            itens.append(
                {
                    "cd_alimento": cd_alimento,
                    "quantidade": quantidade,
                    "validade": validade,
                    "lote": lote,
                    "conservacao": conservacao,
                }
            )
            codigos_escolhidos.append(cd_alimento)
            print("Alimento adicionado!")

            mais = ler_opcao("Adicionar outro alimento? (1 - Sim / 2 - Não): ")
            if mais != 1:
                break

    return itens


def publicar_oferta(cursor, conexao, estab):
    # RN04 e RN12: só estabelecimento aprovado publica oferta
    if estab["st_cadastro"] != "APROVADO":
        print(
            "\n"
            "Seu cadastro ainda não foi aprovado por um administrador. Você não pode publicar ofertas."
        )
        return

    print("\n=== PUBLICAR OFERTA ===")
    titulo = input("Título da oferta: ")
    while titulo == "":
        titulo = input("O título é obrigatório. Digite o título da oferta: ")

    descricao = input("Descrição da oferta: ")
    while descricao == "":
        descricao = input("A descrição é obrigatória. Digite a descrição da oferta: ")

    tags = ("EXCEDENTE", "PROXIMO_VENCIMENTO", "AMBOS")
    print("\nTag da oferta:")
    for i in range(len(tags)):
        print(f"{i + 1} - {tags[i]}")
    opcao_tag = ler_opcao("Escolha a tag: ")
    while opcao_tag < 1 or opcao_tag > len(tags):
        opcao_tag = ler_opcao("Opção inválida. Escolha a tag (1 a 3): ")
    tp_tag = tags[opcao_tag - 1]

    try:
        itens = ler_itens_oferta(cursor)
        if len(itens) == 0:
            print("Oferta cancelada: nenhum alimento foi informado.")
            return

        # RN19: o estabelecimento precisa aceitar os termos antes de publicar
        print("\n=== TERMOS DE RESPONSABILIDADE ===")
        print("- As informações da oferta são verdadeiras")
        print("- Os alimentos estão em condições adequadas de conservação")
        print("- Os prazos informados serão respeitados")
        print("- Combinarei a retirada com a instituição")
        print("- Seguirei as normas sanitárias aplicáveis")
        aceite = ler_opcao("Você aceita os termos? (1 - Sim / 2 - Não): ")
        if aceite != 1:
            print(
                "Oferta não publicada: é preciso aceitar os termos de responsabilidade."
            )
            return

        # Status (DISPONIVEL) e data de publicação ficam de fora: o banco usa o valor padrão
        codigo_var = cursor.var(orcl.NUMBER)
        cursor.execute(
            "INSERT INTO ALIM_TB_PUBLICACAO (CD_ORGANIZACAO, NM_TITULO, DS_DESCRICAO) "
            "VALUES (:org, :titulo, :descricao) RETURNING CD_PUBLICACAO INTO :codigo",
            {
                "org": estab["cd_organizacao"],
                "titulo": titulo,
                "descricao": descricao,
                "codigo": codigo_var,
            },
        )
        cd_publicacao = int(codigo_var.getvalue())

        cursor.execute(
            "INSERT INTO ALIM_TB_OFERTA (CD_PUBLICACAO, TP_TAG, DT_ACEITE_TERMOS) "
            "VALUES (:cd, :tag, SYSDATE)",
            {"cd": cd_publicacao, "tag": tp_tag},
        )

        for item in itens:
            cursor.execute(
                "INSERT INTO ALIM_TB_ITEM_OFERTA (CD_PUBLICACAO, CD_ALIMENTO, QT_OFERTADA_KG, "
                "DT_VALIDADE, DS_LOTE, DS_CONSERVACAO) "
                "VALUES (:cd, :alimento, :quantidade, :validade, :lote, :conservacao)",
                {
                    "cd": cd_publicacao,
                    "alimento": item["cd_alimento"],
                    "quantidade": item["quantidade"],
                    "validade": item["validade"],
                    "lote": item["lote"],
                    "conservacao": item["conservacao"],
                },
            )

        # Um commit só no final: a oferta e todos os itens valem juntos ou nenhum vale
        conexao.commit()
        print(f"\nOferta publicada com sucesso! Código da publicação: {cd_publicacao}")

    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível publicar a oferta. Tente novamente!")
        print(f"(Detalhe técnico: {erro})")  # pode remover antes da apresentação


def deletar_publicacao(cursor, conexao, estab):
    publicacoes = buscar_publi_estab(cursor, estab)
    if not publicacoes:
        return

    cd_publicacao = ler_opcao(
        "\nDigite o código da publicação que deseja deletar (0 para cancelar): "
    )
    if cd_publicacao == 0:
        print("Exclusão cancelada.")
        return

    try:
        # O filtro por CD_ORGANIZACAO impede deletar publicação de outro estabelecimento
        cursor.execute(
            "SELECT ST_PUBLICACAO FROM ALIM_TB_PUBLICACAO "
            "WHERE CD_PUBLICACAO = :cd AND CD_ORGANIZACAO = :org",
            {"cd": cd_publicacao, "org": estab["cd_organizacao"]},
        )
        publicacao = cursor.fetchone()

        if publicacao is None:
            print("Publicação não encontrada!")
        elif publicacao[0] != "DISPONIVEL":
            # RN41: só publicações DISPONIVEL podem ser deletadas
            print("Só é possível deletar publicações com status DISPONIVEL!")
        else:
            # Se já recebeu solicitação, deletar apagaria o histórico (RN40)
            cursor.execute(
                "SELECT COUNT(*) FROM ALIM_TB_SOLICITACAO WHERE CD_OFERTA = :cd",
                {"cd": cd_publicacao},
            )
            if cursor.fetchone()[0] > 0:
                print(
                    "Esta publicação já recebeu solicitações e não pode ser deletada, para preservar o histórico!"
                )
            else:
                confirmar = ler_opcao(
                    "Tem certeza que deseja deletar esta publicação? (1 - Sim / 2 - Não): "
                )
                if confirmar == 1:
                    # Apaga primeiro as tabelas que dependem da publicação
                    cursor.execute(
                        "DELETE FROM ALIM_TB_ITEM_OFERTA WHERE CD_PUBLICACAO = :cd",
                        {"cd": cd_publicacao},
                    )
                    cursor.execute(
                        "DELETE FROM ALIM_TB_OFERTA WHERE CD_PUBLICACAO = :cd",
                        {"cd": cd_publicacao},
                    )
                    cursor.execute(
                        "DELETE FROM ALIM_TB_PUBLICACAO WHERE CD_PUBLICACAO = :cd AND CD_ORGANIZACAO = :org",
                        {"cd": cd_publicacao, "org": estab["cd_organizacao"]},
                    )
                    conexao.commit()
                    print("Publicação deletada com sucesso!")
                else:
                    print("Exclusão cancelada.")

    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível deletar a publicação. Tente novamente!")
        print(f"(Detalhe técnico: {erro})")


def analisar_cad_pendentes(cursor, conexao):
    cursor.execute("""
        SELECT CD_ORGANIZACAO, NR_CNPJ, TP_ORGANIZACAO,
               NM_RAZAO_SOCIAL, NM_FANTASIA, DS_LOGIN,
               DS_EMAIL_CONTATO, NR_TELEFONE, DS_ENDERECO,
               ST_CADASTRO, ST_CONTA
        FROM ALIM_TB_ORGANIZACAO
        WHERE ST_CADASTRO = 'PENDENTE'
        ORDER BY CD_ORGANIZACAO
    """)

    cad_pendentes = cursor.fetchall()
    if not cad_pendentes:
        print("\n" + "Não há cadastros pendentes!")
        input("\n" + "Pressione Enter para voltar: ")
        os.system("cls")
        return

    print("=== CADASTROS PENDENTES ===")

    for cad_pendente in cad_pendentes:
        if not cad_pendentes:
            print("Não há cadastros pendentes!")
            break

        print("=" * 30)
        print(f"CNPJ: {cad_pendente[1]}")
        print(f"Tipo de organização: {cad_pendente[2]}")
        print(f"Razão Social: {cad_pendente[3]}")
        print(f"Nome fantasia: {cad_pendente[4]}")
        print(f"Login: {cad_pendente[5]}")
        print(f"Email: {cad_pendente[6]}")
        print(f"Telefone: {cad_pendente[7]}")
        print(f"Endereço: {cad_pendente[8]}")
        print(f"Situação do cadastro: {cad_pendente[9]}")
        print(f"Situação da conta: {cad_pendente[10]}")

        print("\n1 - Aprovar cadastro")
        print("2 - Reprovar cadastro")
        print("3 - Voltar")

        resposta = ler_opcao("Escolha uma opção: ")

        # APROVAR CADASTRO
        if resposta == 1:
            try:
                cursor.execute(
                    """
                    UPDATE ALIM_TB_ORGANIZACAO
                    SET ST_CADASTRO = 'APROVADO'
                    WHERE CD_ORGANIZACAO = :cd
                    AND ST_CADASTRO = 'PENDENTE'
                """,
                    {"cd": cad_pendente[0]},
                )

                if cursor.rowcount > 0:
                    conexao.commit()
                    print("\nCadastro aprovado com sucesso!")
                    input("Aperte Enter para avançar: ")
                    os.system("cls")
                else:
                    conexao.rollback()
                    print("\nCadastro não encontrado ou já analisado!")
                    input("Aperte Enter para avançar: ")
                    os.system("cls")
            except orcl.Error as erro:
                conexao.rollback()
                print(f"Erro ao aprovar cadastro: {erro}")

        # REPROVAR CADASTRO
        elif resposta == 2:
            try:
                cursor.execute(
                    """
                    UPDATE ALIM_TB_ORGANIZACAO
                    SET ST_CADASTRO = 'REPROVADO'
                    WHERE CD_ORGANIZACAO = :cd
                    AND ST_CADASTRO = 'PENDENTE'
                """,
                    {"cd": cad_pendente[0]},
                )

                if cursor.rowcount > 0:
                    conexao.commit()
                    print("\nCadastro reprovado com sucesso!")
                    input("Aperte Enter para avançar: ")
                    os.system("cls")
                else:
                    conexao.rollback()
                    print("\nCadastro não encontrado ou já analisado!")
                    input("Aperte Enter para avançar: ")
                    os.system("cls")
            except orcl.Error as erro:
                conexao.rollback()
                print(f"Erro ao reprovar cadastro: {erro}")

        elif resposta == 3:
            return
        else:
            print("Opção inválida!")


def listar_organizacoes(cursor):
    print("\n=== LISTAR ORGANIZAÇÕES ===")
    print("1 - Todas as organizações")
    print("2 - Filtrar por tipo")
    print("3 - Filtrar por situação do cadastro")

    opcao = ler_opcao("Escolha uma opção: ")
    os.system("cls")

    if opcao == 1:
        cursor.execute("""
            SELECT CD_ORGANIZACAO, NM_FANTASIA, NR_CNPJ,
                   TP_ORGANIZACAO, ST_CADASTRO, ST_CONTA
            FROM ALIM_TB_ORGANIZACAO
            ORDER BY NM_FANTASIA
        """)
    elif opcao == 2:
        print("\n1 - Estabelecimento")
        print("2 - Instituição")

        tipo = ler_opcao("Escolha o tipo: ")

        if tipo == 1:
            tipo_org = "ESTABELECIMENTO"
        elif tipo == 2:
            tipo_org = "INSTITUICAO"
        else:
            print("Opção inválida!")
            return

        cursor.execute(
            """
            SELECT CD_ORGANIZACAO, NM_FANTASIA, NR_CNPJ,
                   TP_ORGANIZACAO, ST_CADASTRO, ST_CONTA
            FROM ALIM_TB_ORGANIZACAO
            WHERE TP_ORGANIZACAO = :tipo
            ORDER BY NM_FANTASIA
        """,
            {"tipo": tipo_org},
        )
    elif opcao == 3:
        print("\n1 - Pendente")
        print("2 - Aprovado")
        print("3 - Reprovado")

        situacao = ler_opcao("Escolha a situação: ")

        if situacao == 1:
            st_cadastro = "PENDENTE"
        elif situacao == 2:
            st_cadastro = "APROVADO"
        elif situacao == 3:
            st_cadastro = "REPROVADO"
        else:
            print("Opção inválida!")
            return

        cursor.execute(
            """
            SELECT CD_ORGANIZACAO, NM_FANTASIA, NR_CNPJ,
                   TP_ORGANIZACAO, ST_CADASTRO, ST_CONTA
            FROM ALIM_TB_ORGANIZACAO
            WHERE ST_CADASTRO = :situacao
            ORDER BY NM_FANTASIA
        """,
            {"situacao": st_cadastro},
        )
    else:
        print("Opção inválida!")
        return

    organizacoes = cursor.fetchall()
    if not organizacoes:
        os.system("cls")
        print("\nNenhuma organização encontrada!")
        input("Pressione Enter para voltar: ")
        os.system("cls")
        return

    os.system("cls")
    print("\n=== ORGANIZAÇÕES ENCONTRADAS ===")

    for organizacao in organizacoes:
        print("=" * 30)
        print(f"Código: {organizacao[0]}")
        print(f"Nome: {organizacao[1]}")
        print(f"CNPJ: {organizacao[2]}")
        print(f"Tipo: {organizacao[3]}")
        print(f"Situação do cadastro: {organizacao[4]}")
        print(f"Situação da conta: {organizacao[5]}")

    print("=" * 30)
    print("\n" f"Total de organizações encontradas: {len(organizacoes)}")


def inativar_organizacao(cursor, conexao, adm):
    cursor.execute("""
        SELECT CD_ORGANIZACAO, NM_FANTASIA, TP_ORGANIZACAO, ST_CONTA
        FROM ALIM_TB_ORGANIZACAO
        ORDER BY NM_FANTASIA
    """)

    organizacoes = cursor.fetchall()
    if not organizacoes:
        print("Nenhuma organização encontrada!")
        return

    print("\n=== ORGANIZAÇÕES ===")
    for organizacao in organizacoes:
        print("=" * 30)
        print(f"Código: {organizacao[0]}")
        print(f"Nome: {organizacao[1]}")
        print(f"Tipo: {organizacao[2]}")
        print(f"Situação da conta: {organizacao[3]}")

    cd_organizacao = ler_opcao(
        "Código da organização que deseja inativar (0 para voltar): "
    )
    if cd_organizacao == 0:
        return

    try:
        cursor.execute(
            "SELECT NM_FANTASIA, ST_CONTA FROM ALIM_TB_ORGANIZACAO WHERE CD_ORGANIZACAO = :cd",
            {"cd": cd_organizacao},
        )
        organizacao = cursor.fetchone()

        if organizacao is None:
            print("Organização não encontrada!")
            return
        if organizacao[1] == "INATIVA":
            print("Esta organização já está inativa!")
            return

        # Impede a inativação enquanto houver solicitação em andamento,
        # seja a organização o estabelecimento ou a instituição.
        cursor.execute(
            "SELECT COUNT(*) FROM ALIM_TB_SOLICITACAO S "
            "LEFT JOIN ALIM_TB_PUBLICACAO P ON P.CD_PUBLICACAO = S.CD_OFERTA "
            "WHERE S.ST_SOLICITACAO = 'EM_ANDAMENTO' "
            "AND (S.CD_INSTITUICAO = :cd_inst OR P.CD_ORGANIZACAO = :cd_estab)",
            {"cd_inst": cd_organizacao, "cd_estab": cd_organizacao},
        )
        em_andamento = cursor.fetchone()[0]

        if em_andamento > 0:
            print("Não é possível inativar: existe doação/solicitação em andamento!")
            return

        motivo = input("Informe a justificativa da inativação: ").strip()
        while motivo == "":
            motivo = input("A justificativa é obrigatória: ").strip()

        confirmar = ler_opcao(
            f"Confirma a inativação de {organizacao[0]}? (1-Sim / 2-Não): "
        )
        if confirmar != 1:
            print("Operação cancelada.")
            return

        cursor.execute(
            "UPDATE ALIM_TB_ORGANIZACAO "
            "SET ST_CONTA = 'INATIVA', DT_INATIVACAO = SYSDATE, "
            "DS_MOTIVO_INATIVACAO = :motivo, CD_USUARIO_ADMIN = :adm "
            "WHERE CD_ORGANIZACAO = :cd AND ST_CONTA = 'ATIVA'",
            {"motivo": motivo, "adm": adm["cd_usuario"], "cd": cd_organizacao},
        )

        if cursor.rowcount > 0:
            conexao.commit()
            print("Organização inativada com sucesso!")
        else:
            conexao.rollback()
            print("Não foi possível inativar. Verifique a situação da conta.")

    except orcl.Error as erro:
        conexao.rollback()
        print("Erro ao inativar organização:", erro)


def listar_alimentos(cursor):
    cursor.execute("""
        SELECT CD_ALIMENTO, NM_ALIMENTO, TP_CLASSIFICACAO
        FROM ALIM_TB_ALIMENTO
        ORDER BY NM_ALIMENTO
    """)
    alimentos = cursor.fetchall()

    if not alimentos:
        print("Nenhum alimento cadastrado!")
        return

    print("\n=== CATÁLOGO DE ALIMENTOS ===")
    for alimento in alimentos:
        print("=" * 30)
        print(f"Código: {alimento[0]}")
        print(f"Alimento: {alimento[1]}")
        print(f"Classificação: {alimento[2]}")
    print("=" * 30)


def cadastrar_alimento(cursor, conexao):
    nome = input("Nome do alimento: ").strip()
    while nome == "":
        nome = input("O nome é obrigatório: ").strip()

    print("1 - Perecível")
    print("2 - Não perecível")
    opcao = ler_opcao("Classificação: ")

    if opcao == 1:
        classificacao = "PERECIVEL"
    elif opcao == 2:
        classificacao = "NAO_PERECIVEL"
    else:
        print("Opção inválida!")
        return

    try:
        cursor.execute(
            "INSERT INTO ALIM_TB_ALIMENTO (NM_ALIMENTO, TP_CLASSIFICACAO) "
            "VALUES (:nome, :classificacao)",
            {"nome": nome, "classificacao": classificacao},
        )
        conexao.commit()
        print("Alimento cadastrado com sucesso!")
    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível cadastrar o alimento:", erro)


def alterar_alimento(cursor, conexao):
    listar_alimentos(cursor)
    cd_alimento = ler_opcao("Código do alimento que deseja alterar (0 para voltar): ")
    if cd_alimento == 0:
        return

    cursor.execute(
        "SELECT NM_ALIMENTO, TP_CLASSIFICACAO FROM ALIM_TB_ALIMENTO WHERE CD_ALIMENTO = :cd",
        {"cd": cd_alimento},
    )
    alimento = cursor.fetchone()

    if alimento is None:
        print("Alimento não encontrado!")
        return

    nome = input(f"Novo nome (Enter para manter {alimento[0]}): ").strip()
    if nome == "":
        nome = alimento[0]

    print("1 - Perecível")
    print("2 - Não perecível")
    print("3 - Manter classificação atual")
    opcao = ler_opcao("Nova classificação: ")

    if opcao == 1:
        classificacao = "PERECIVEL"
    elif opcao == 2:
        classificacao = "NAO_PERECIVEL"
    elif opcao == 3:
        classificacao = alimento[1]
    else:
        print("Opção inválida!")
        return

    try:
        cursor.execute(
            "UPDATE ALIM_TB_ALIMENTO SET NM_ALIMENTO = :nome, "
            "TP_CLASSIFICACAO = :classificacao WHERE CD_ALIMENTO = :cd",
            {"nome": nome, "classificacao": classificacao, "cd": cd_alimento},
        )
        conexao.commit()
        print("Alimento alterado com sucesso!")
    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível alterar o alimento:", erro)


def menu_catalogo_alimentos(cursor, conexao):
    while True:
        print("\n=== CATÁLOGO DE ALIMENTOS ===")
        print("1 - Cadastrar alimento")
        print("2 - Listar alimentos")
        print("3 - Alterar alimento")
        print("4 - Voltar")

        opcao = ler_opcao("Escolha uma opção: ")

        if opcao == 1:
            cadastrar_alimento(cursor, conexao)
        elif opcao == 2:
            listar_alimentos(cursor)
        elif opcao == 3:
            alterar_alimento(cursor, conexao)
        elif opcao == 4:
            return
        else:
            print("Opção inválida!")

        input("\nPressione Enter para continuar...")


def ver_ofertas_disponiveis(cursor):
    print("\n=== VER OFERTAS DISPONÍVEIS ===")
    print("1 - Todas as ofertas")
    print("2 - Filtrar por tag")
    print("3 - Filtrar por classificação do alimento")
    opcao = ler_opcao("Escolha uma opção: ")

    sql = """
        SELECT P.CD_PUBLICACAO, P.NM_TITULO, P.DS_DESCRICAO,
               P.DT_PUBLICACAO, O.NM_FANTASIA, F.TP_TAG,
               I.CD_ITEM_OFERTA, A.NM_ALIMENTO, A.TP_CLASSIFICACAO,
               I.QT_OFERTADA_KG, I.DT_VALIDADE
        FROM ALIM_TB_PUBLICACAO P
        JOIN ALIM_TB_OFERTA F ON F.CD_PUBLICACAO = P.CD_PUBLICACAO
        JOIN ALIM_TB_ITEM_OFERTA I ON I.CD_PUBLICACAO = P.CD_PUBLICACAO
        JOIN ALIM_TB_ALIMENTO A ON A.CD_ALIMENTO = I.CD_ALIMENTO
        JOIN ALIM_TB_ORGANIZACAO O ON O.CD_ORGANIZACAO = P.CD_ORGANIZACAO
        WHERE P.ST_PUBLICACAO = 'DISPONIVEL'
          AND O.ST_CADASTRO = 'APROVADO'
          AND O.ST_CONTA = 'ATIVA'
    """
    parametros = {}

    if opcao == 2:
        print("1 - EXCEDENTE")
        print("2 - PROXIMO_VENCIMENTO")
        print("3 - AMBOS")
        tag_opcao = ler_opcao("Escolha a tag: ")
        tags = {1: "EXCEDENTE", 2: "PROXIMO_VENCIMENTO", 3: "AMBOS"}
        if tag_opcao not in tags:
            print("Opção inválida!")
            return
        sql += " AND F.TP_TAG = :tag"
        parametros["tag"] = tags[tag_opcao]

    elif opcao == 3:
        print("1 - PERECIVEL")
        print("2 - NAO_PERECIVEL")
        tipo = ler_opcao("Escolha a classificação: ")
        classificacoes = {1: "PERECIVEL", 2: "NAO_PERECIVEL"}
        if tipo not in classificacoes:
            print("Opção inválida!")
            return
        sql += " AND A.TP_CLASSIFICACAO = :classificacao"
        parametros["classificacao"] = classificacoes[tipo]

    elif opcao != 1:
        print("Opção inválida!")
        return

    sql += " ORDER BY P.DT_PUBLICACAO DESC, P.CD_PUBLICACAO"
    cursor.execute(sql, parametros)
    ofertas = cursor.fetchall()

    if not ofertas:
        print("Nenhuma oferta disponível encontrada!")
        return []

    print("\n=== OFERTAS DISPONÍVEIS ===")
    codigos_exibidos = []
    for oferta in ofertas:
        if oferta[0] not in codigos_exibidos:
            print("=" * 35)
            print(f"Código da oferta: {oferta[0]}")
            print(f"Título: {oferta[1]}")
            print(f"Descrição: {oferta[2]}")
            print(f"Data: {oferta[3]}")
            print(f"Estabelecimento: {oferta[4]}")
            print(f"Tag: {oferta[5]}")
            codigos_exibidos.append(oferta[0])

        print(f"  Item {oferta[6]} - {oferta[7]} ({oferta[8]}): {oferta[9]} kg")
        if oferta[10] is not None:
            print(f"    Validade: {oferta[10].strftime('%d/%m/%Y')}")

    print("=" * 35)
    return codigos_exibidos


def solicitar_oferta(cursor, conexao, inst):
    ofertas = ver_ofertas_disponiveis(cursor)
    if not ofertas:
        return

    cd_oferta = ler_opcao(
        "\nDigite o código da oferta que deseja solicitar (0 para voltar): "
    )
    if cd_oferta == 0:
        return
    if cd_oferta not in ofertas:
        print("Código de oferta inválido!")
        return

    cursor.execute(
        """
        SELECT I.CD_ITEM_OFERTA, A.NM_ALIMENTO, I.QT_OFERTADA_KG
        FROM ALIM_TB_ITEM_OFERTA I
        JOIN ALIM_TB_ALIMENTO A ON A.CD_ALIMENTO = I.CD_ALIMENTO
        WHERE I.CD_PUBLICACAO = :cd
        ORDER BY A.NM_ALIMENTO
    """,
        {"cd": cd_oferta},
    )
    itens_oferta = cursor.fetchall()

    itens_escolhidos = []
    print("\n=== ESCOLHA OS ALIMENTOS ===")
    for item in itens_oferta:
        print(
            f"Código do item: {item[0]} | {item[1]} | Disponível na oferta: {item[2]} kg"
        )
        resposta = ler_opcao("Deseja solicitar este alimento? (1-Sim / 2-Não): ")
        if resposta == 1:
            quantidade = 0
            while quantidade <= 0 or quantidade > float(item[2]):
                try:
                    quantidade = float(
                        input(
                            f"Quantidade desejada em kg (máximo {item[2]}): "
                        ).replace(",", ".")
                    )
                except ValueError:
                    quantidade = 0
                if quantidade <= 0 or quantidade > float(item[2]):
                    print(f"Digite uma quantidade entre 0 e {item[2]} kg.")
            itens_escolhidos.append((item[0], quantidade))

    if not itens_escolhidos:
        print("Nenhum alimento foi selecionado. Solicitação cancelada.")
        return

    try:
        codigo_var = cursor.var(orcl.NUMBER)
        cursor.execute(
            """
            INSERT INTO ALIM_TB_SOLICITACAO
                (CD_OFERTA, CD_INSTITUICAO)
            VALUES (:oferta, :instituicao)
            RETURNING CD_SOLICITACAO INTO :codigo
        """,
            {
                "oferta": cd_oferta,
                "instituicao": inst["cd_organizacao"],
                "codigo": codigo_var,
            },
        )
        cd_solicitacao = int(codigo_var.getvalue())

        for cd_item, quantidade in itens_escolhidos:
            cursor.execute(
                """
                INSERT INTO ALIM_TB_ITEM_SOLICITACAO
                    (CD_SOLICITACAO, CD_ITEM_OFERTA, QT_SOLICITADA_KG)
                VALUES (:solicitacao, :item, :quantidade)
            """,
                {
                    "solicitacao": cd_solicitacao,
                    "item": cd_item,
                    "quantidade": quantidade,
                },
            )

        conexao.commit()
        print(f"Solicitação registrada com sucesso! Código: {cd_solicitacao}")
    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível registrar a solicitação:", erro)


def minhas_solicitacoes(cursor, conexao, inst):
    cursor.execute(
        """
        SELECT S.CD_SOLICITACAO, S.CD_OFERTA, P.NM_TITULO,
               E.NM_FANTASIA, E.DS_EMAIL_CONTATO, E.NR_TELEFONE,
               S.DT_SOLICITACAO, S.ST_SOLICITACAO,
               S.DS_MOTIVO_ENCERRAMENTO
        FROM ALIM_TB_SOLICITACAO S
        JOIN ALIM_TB_PUBLICACAO P ON P.CD_PUBLICACAO = S.CD_OFERTA
        JOIN ALIM_TB_ORGANIZACAO E ON E.CD_ORGANIZACAO = P.CD_ORGANIZACAO
        WHERE S.CD_INSTITUICAO = :inst
        ORDER BY S.DT_SOLICITACAO DESC
    """,
        {"inst": inst["cd_organizacao"]},
    )
    solicitacoes = cursor.fetchall()

    if not solicitacoes:
        print("Você ainda não possui solicitações!")
        return

    print("\n=== MINHAS SOLICITAÇÕES ===")
    for sol in solicitacoes:
        print("=" * 35)
        print(f"Código: {sol[0]}")
        print(f"Oferta: {sol[2]} (código {sol[1]})")
        print(f"Estabelecimento: {sol[3]}")
        print(f"E-mail: {sol[4]}")
        print(f"Telefone: {sol[5]}")
        print(f"Data: {sol[6]}")
        print(f"Status: {sol[7]}")
        if sol[8]:
            print(f"Motivo de encerramento: {sol[8]}")

        cursor.execute(
            """
            SELECT A.NM_ALIMENTO, I.QT_SOLICITADA_KG, I.QT_ALOCADA_KG
            FROM ALIM_TB_ITEM_SOLICITACAO I
            JOIN ALIM_TB_ITEM_OFERTA IO ON IO.CD_ITEM_OFERTA = I.CD_ITEM_OFERTA
            JOIN ALIM_TB_ALIMENTO A ON A.CD_ALIMENTO = IO.CD_ALIMENTO
            WHERE I.CD_SOLICITACAO = :cd
        """,
            {"cd": sol[0]},
        )
        for item in cursor.fetchall():
            print(f"  - {item[0]}: solicitada {item[1]} kg / reservada {item[2]} kg")

    cd_cancelar = ler_opcao(
        "\nDigite o código da solicitação para cancelar (0 para voltar): "
    )
    if cd_cancelar == 0:
        return

    cursor.execute(
        """
        SELECT ST_SOLICITACAO, CD_OFERTA
        FROM ALIM_TB_SOLICITACAO
        WHERE CD_SOLICITACAO = :cd AND CD_INSTITUICAO = :inst
    """,
        {"cd": cd_cancelar, "inst": inst["cd_organizacao"]},
    )
    solicitacao = cursor.fetchone()

    if solicitacao is None:
        print("Solicitação não encontrada!")
        return
    if solicitacao[0] not in ("PENDENTE", "EM_ANDAMENTO"):
        print("Só é possível cancelar solicitações pendentes ou em andamento.")
        return

    motivo = input("Informe o motivo do cancelamento: ").strip()
    while motivo == "":
        motivo = input("O motivo é obrigatório: ").strip()

    try:
        cursor.execute(
            """
            UPDATE ALIM_TB_SOLICITACAO
            SET ST_SOLICITACAO = 'CANCELADA',
                DT_ENCERRAMENTO = SYSDATE,
                DS_MOTIVO_ENCERRAMENTO = :motivo
            WHERE CD_SOLICITACAO = :cd
              AND CD_INSTITUICAO = :inst
              AND ST_SOLICITACAO IN ('PENDENTE', 'EM_ANDAMENTO')
        """,
            {"motivo": motivo, "cd": cd_cancelar, "inst": inst["cd_organizacao"]},
        )

        cursor.execute(
            """
            UPDATE ALIM_TB_ITEM_SOLICITACAO
            SET QT_ALOCADA_KG = 0
            WHERE CD_SOLICITACAO = :cd
        """,
            {"cd": cd_cancelar},
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM ALIM_TB_SOLICITACAO
            WHERE CD_OFERTA = :oferta AND ST_SOLICITACAO = 'EM_ANDAMENTO'
        """,
            {"oferta": solicitacao[1]},
        )
        outras_em_andamento = cursor.fetchone()[0]

        if outras_em_andamento == 0:
            cursor.execute(
                """
                UPDATE ALIM_TB_PUBLICACAO
                SET ST_PUBLICACAO = 'DISPONIVEL'
                WHERE CD_PUBLICACAO = :oferta
                  AND ST_PUBLICACAO = 'EM_ANDAMENTO'
            """,
                {"oferta": solicitacao[1]},
            )

        conexao.commit()
        print("Solicitação cancelada com sucesso!")
    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível cancelar a solicitação:", erro)


def publicar_necessidade(cursor, conexao, inst):
    if inst["st_cadastro"] != "APROVADO":
        print(
            "Seu cadastro ainda não foi aprovado. Não é possível publicar necessidades."
        )
        return

    print("\n=== PUBLICAR NECESSIDADE ===")
    titulo = input("Título da necessidade: ").strip()
    while titulo == "":
        titulo = input("O título é obrigatório: ").strip()
    descricao = input("Descrição: ").strip()
    while descricao == "":
        descricao = input("A descrição é obrigatória: ").strip()

    texto_limite = input(
        "Data limite (dd/mm/aaaa) ou Enter para não informar: "
    ).strip()
    dt_limite = None
    if texto_limite:
        try:
            dt_limite = datetime.strptime(texto_limite, "%d/%m/%Y")
        except ValueError:
            print("Data inválida. Use dd/mm/aaaa.")
            return

    cursor.execute(
        "SELECT CD_ALIMENTO, NM_ALIMENTO FROM ALIM_TB_ALIMENTO ORDER BY NM_ALIMENTO"
    )
    alimentos = cursor.fetchall()
    if not alimentos:
        print("Não há alimentos cadastrados no catálogo.")
        return

    print("\n=== CATÁLOGO DE ALIMENTOS ===")
    for alimento in alimentos:
        print(f"{alimento[0]} - {alimento[1]}")

    itens = []
    codigos = []
    while True:
        cd_alimento = ler_opcao("Código do alimento (0 para finalizar): ")
        if cd_alimento == 0:
            break
        if cd_alimento not in [a[0] for a in alimentos] or cd_alimento in codigos:
            print("Código inválido ou alimento já adicionado.")
            continue
        quantidade = 0
        while quantidade <= 0:
            try:
                quantidade = float(
                    input("Quantidade desejada em kg: ").replace(",", ".")
                )
            except ValueError:
                quantidade = 0
            if quantidade <= 0:
                print("Informe uma quantidade maior que zero.")
        itens.append((cd_alimento, quantidade))
        codigos.append(cd_alimento)
        mais = ler_opcao("Adicionar outro alimento? (1-Sim / 2-Não): ")
        if mais != 1:
            break

    if not itens:
        print("Publicação cancelada: nenhum alimento informado.")
        return

    try:
        codigo_var = cursor.var(orcl.NUMBER)
        cursor.execute(
            """
            INSERT INTO ALIM_TB_PUBLICACAO
                (CD_ORGANIZACAO, NM_TITULO, DS_DESCRICAO)
            VALUES (:org, :titulo, :descricao)
            RETURNING CD_PUBLICACAO INTO :codigo
        """,
            {
                "org": inst["cd_organizacao"],
                "titulo": titulo,
                "descricao": descricao,
                "codigo": codigo_var,
            },
        )
        cd_publicacao = int(codigo_var.getvalue())

        cursor.execute(
            """
            INSERT INTO ALIM_TB_NECESSIDADE (CD_PUBLICACAO, DT_LIMITE)
            VALUES (:cd, :limite)
        """,
            {"cd": cd_publicacao, "limite": dt_limite},
        )

        for cd_alimento, quantidade in itens:
            cursor.execute(
                """
                INSERT INTO ALIM_TB_ITEM_NECESSIDADE
                    (CD_PUBLICACAO, CD_ALIMENTO, QT_DESEJADA_KG)
                VALUES (:publicacao, :alimento, :quantidade)
            """,
                {
                    "publicacao": cd_publicacao,
                    "alimento": cd_alimento,
                    "quantidade": quantidade,
                },
            )

        conexao.commit()
        print(f"Necessidade publicada com sucesso! Código: {cd_publicacao}")
    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível publicar a necessidade:", erro)


def minhas_necessidades(cursor, conexao, inst):
    cursor.execute(
        """
        SELECT P.CD_PUBLICACAO, P.NM_TITULO, P.DS_DESCRICAO,
               P.DT_PUBLICACAO, P.ST_PUBLICACAO, N.DT_LIMITE
        FROM ALIM_TB_PUBLICACAO P
        JOIN ALIM_TB_NECESSIDADE N ON N.CD_PUBLICACAO = P.CD_PUBLICACAO
        WHERE P.CD_ORGANIZACAO = :org
        ORDER BY P.DT_PUBLICACAO DESC
    """,
        {"org": inst["cd_organizacao"]},
    )
    necessidades = cursor.fetchall()

    if not necessidades:
        print("Você ainda não publicou necessidades!")
        return

    print("\n=== MINHAS NECESSIDADES ===")
    for necessidade in necessidades:
        print("=" * 35)
        print(f"Código: {necessidade[0]}")
        print(f"Título: {necessidade[1]}")
        print(f"Descrição: {necessidade[2]}")
        print(f"Data: {necessidade[3]}")
        print(f"Status: {necessidade[4]}")
        print(f"Data limite: {necessidade[5]}")
        cursor.execute(
            """
            SELECT A.NM_ALIMENTO, I.QT_DESEJADA_KG
            FROM ALIM_TB_ITEM_NECESSIDADE I
            JOIN ALIM_TB_ALIMENTO A ON A.CD_ALIMENTO = I.CD_ALIMENTO
            WHERE I.CD_PUBLICACAO = :cd
        """,
            {"cd": necessidade[0]},
        )
        for item in cursor.fetchall():
            print(f"  - {item[0]}: {item[1]} kg")

    cd_publicacao = ler_opcao("\nCódigo da necessidade para excluir (0 para voltar): ")
    if cd_publicacao == 0:
        return

    cursor.execute(
        """
        SELECT ST_PUBLICACAO
        FROM ALIM_TB_PUBLICACAO
        WHERE CD_PUBLICACAO = :cd AND CD_ORGANIZACAO = :org
    """,
        {"cd": cd_publicacao, "org": inst["cd_organizacao"]},
    )
    publicacao = cursor.fetchone()

    if publicacao is None:
        print("Necessidade não encontrada!")
        return
    if publicacao[0] != "DISPONIVEL":
        print("Só é possível excluir necessidades com status DISPONIVEL.")
        return

    cursor.execute(
        """
        SELECT COUNT(*) FROM ALIM_TB_SOLICITACAO
        WHERE CD_NECESSIDADE = :cd
    """,
        {"cd": cd_publicacao},
    )
    if cursor.fetchone()[0] > 0:
        print(
            "Esta necessidade já possui solicitações vinculadas e não pode ser excluída."
        )
        return

    confirmar = ler_opcao("Confirma a exclusão? (1-Sim / 2-Não): ")
    if confirmar != 1:
        print("Exclusão cancelada.")
        return

    try:
        cursor.execute(
            "DELETE FROM ALIM_TB_ITEM_NECESSIDADE WHERE CD_PUBLICACAO = :cd",
            {"cd": cd_publicacao},
        )
        cursor.execute(
            "DELETE FROM ALIM_TB_NECESSIDADE WHERE CD_PUBLICACAO = :cd",
            {"cd": cd_publicacao},
        )
        cursor.execute(
            """
            DELETE FROM ALIM_TB_PUBLICACAO
            WHERE CD_PUBLICACAO = :cd AND CD_ORGANIZACAO = :org
        """,
            {"cd": cd_publicacao, "org": inst["cd_organizacao"]},
        )
        conexao.commit()
        print("Necessidade excluída com sucesso!")
    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível excluir a necessidade:", erro)


def pesquisar_estabelecimentos(cursor):
    cursor.execute("""
        SELECT NM_FANTASIA, NR_CNPJ, DS_EMAIL_CONTATO,
               NR_TELEFONE, DS_ENDERECO
        FROM ALIM_TB_ORGANIZACAO
        WHERE TP_ORGANIZACAO = 'ESTABELECIMENTO'
          AND ST_CADASTRO = 'APROVADO'
          AND ST_CONTA = 'ATIVA'
        ORDER BY NM_FANTASIA
    """)
    estabelecimentos = cursor.fetchall()

    if not estabelecimentos:
        print("Nenhum estabelecimento encontrado!")
        return

    print("\n=== ESTABELECIMENTOS ===")
    for estabelecimento in estabelecimentos:
        print("=" * 35)
        print(f"Nome: {estabelecimento[0]}")
        print(f"CNPJ: {estabelecimento[1]}")
        print(f"E-mail: {estabelecimento[2]}")
        print(f"Telefone: {estabelecimento[3]}")
        print(f"Endereço: {estabelecimento[4]}")


def confirmar_recebimento(cursor, conexao, inst):
    cursor.execute(
        """
        SELECT S.CD_SOLICITACAO, S.CD_OFERTA, P.NM_TITULO,
               E.NM_FANTASIA, S.ST_SOLICITACAO
        FROM ALIM_TB_SOLICITACAO S
        JOIN ALIM_TB_PUBLICACAO P ON P.CD_PUBLICACAO = S.CD_OFERTA
        JOIN ALIM_TB_ORGANIZACAO E ON E.CD_ORGANIZACAO = P.CD_ORGANIZACAO
        WHERE S.CD_INSTITUICAO = :inst
          AND S.ST_SOLICITACAO IN ('EM_ANDAMENTO', 'CONCLUIDA_PARCIAL')
        ORDER BY S.DT_SOLICITACAO DESC
    """,
        {"inst": inst["cd_organizacao"]},
    )
    solicitacoes = cursor.fetchall()

    if not solicitacoes:
        print("Não há solicitações aguardando confirmação de recebimento.")
        return

    print("\n=== SOLICITAÇÕES PARA CONFIRMAR RECEBIMENTO ===")
    for sol in solicitacoes:
        print("=" * 35)
        print(f"Código: {sol[0]}")
        print(f"Oferta: {sol[2]}")
        print(f"Estabelecimento: {sol[3]}")
        print(f"Status: {sol[4]}")

    cd_solicitacao = ler_opcao("Código da solicitação recebida (0 para voltar): ")
    if cd_solicitacao == 0:
        return
    if cd_solicitacao not in [s[0] for s in solicitacoes]:
        print("Solicitação inválida!")
        return

    try:
        cursor.execute(
            """
            SELECT I.CD_ITEM_SOLICITACAO, A.NM_ALIMENTO,
                   I.QT_ALOCADA_KG
            FROM ALIM_TB_ITEM_SOLICITACAO I
            JOIN ALIM_TB_ITEM_OFERTA IO ON IO.CD_ITEM_OFERTA = I.CD_ITEM_OFERTA
            JOIN ALIM_TB_ALIMENTO A ON A.CD_ALIMENTO = IO.CD_ALIMENTO
            WHERE I.CD_SOLICITACAO = :cd
        """,
            {"cd": cd_solicitacao},
        )
        itens = cursor.fetchall()

        cursor.execute(
            """
            SELECT CD_RETIRADA
            FROM ALIM_TB_RETIRADA
            WHERE CD_SOLICITACAO = :cd
        """,
            {"cd": cd_solicitacao},
        )
        retirada = cursor.fetchone()

        if retirada is None:
            codigo_var = cursor.var(orcl.NUMBER)
            cursor.execute(
                """
                INSERT INTO ALIM_TB_RETIRADA (CD_SOLICITACAO, DT_RETIRADA)
                VALUES (:cd, SYSDATE)
                RETURNING CD_RETIRADA INTO :codigo
            """,
                {"cd": cd_solicitacao, "codigo": codigo_var},
            )
            cd_retirada = int(codigo_var.getvalue())
        else:
            cd_retirada = retirada[0]

        total_alocado = 0
        total_confirmado = 0
        for item in itens:
            print(f"\n{item[1]} - reservado: {item[2]} kg")
            quantidade = -1
            while quantidade < 0 or quantidade > float(item[2]):
                try:
                    quantidade = float(
                        input("Quantidade recebida em kg: ").replace(",", ".")
                    )
                except ValueError:
                    quantidade = -1
                if quantidade < 0 or quantidade > float(item[2]):
                    print(f"Informe um valor entre 0 e {item[2]} kg.")

            total_alocado += float(item[2])
            total_confirmado += quantidade

            cursor.execute(
                """
                SELECT CD_ITEM_RETIRADA
                FROM ALIM_TB_ITEM_RETIRADA
                WHERE CD_RETIRADA = :retirada
                  AND CD_ITEM_SOLICITACAO = :item
            """,
                {"retirada": cd_retirada, "item": item[0]},
            )
            item_retirada = cursor.fetchone()

            if item_retirada is None:
                cursor.execute(
                    """
                    INSERT INTO ALIM_TB_ITEM_RETIRADA
                        (CD_RETIRADA, CD_ITEM_SOLICITACAO,
                         QT_CONFIRMADA_INST, DT_CONF_INST)
                    VALUES (:retirada, :item, :quantidade, SYSDATE)
                """,
                    {
                        "retirada": cd_retirada,
                        "item": item[0],
                        "quantidade": quantidade,
                    },
                )
            else:
                cursor.execute(
                    """
                    UPDATE ALIM_TB_ITEM_RETIRADA
                    SET QT_CONFIRMADA_INST = :quantidade,
                        DT_CONF_INST = SYSDATE
                    WHERE CD_ITEM_RETIRADA = :cd
                """,
                    {"quantidade": quantidade, "cd": item_retirada[0]},
                )

        if total_confirmado == total_alocado:
            status_final = "CONCLUIDA"
        else:
            motivo = input("Informe o motivo do recebimento parcial: ").strip()
            while motivo == "":
                motivo = input("O motivo é obrigatório: ").strip()
            cursor.execute(
                """
                UPDATE ALIM_TB_RETIRADA
                SET DS_MOTIVO_PARCIAL = :motivo
                WHERE CD_RETIRADA = :cd
            """,
                {"motivo": motivo, "cd": cd_retirada},
            )
            status_final = "CONCLUIDA_PARCIAL"

        cursor.execute(
            """
            UPDATE ALIM_TB_SOLICITACAO
            SET ST_SOLICITACAO = :status,
                DT_ENCERRAMENTO = SYSDATE
            WHERE CD_SOLICITACAO = :cd
        """,
            {"status": status_final, "cd": cd_solicitacao},
        )

        conexao.commit()
        print(f"Recebimento registrado! Situação: {status_final}")
    except orcl.Error as erro:
        conexao.rollback()
        print("Não foi possível confirmar o recebimento:", erro)


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
            print("           Acesse sua conta e faça a comida chegar a quem precisa.")
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
        print(f"           Painel de controle da {estab['nm_fantasia']}")
        print("=" * 20)
        print("1 - Alterar dados cadastrais")
        print("2 - Visualizar minhas doações")
        print("3 - Pesquisar instituições")
        print("4 - Solicitações recebidas (ver, aceitar ou recusar)")
        print("5 - Ver publicações de necessidades")
        print("6 - Publicar uma oferta")
        print("7 - Deletar publicação")
        print("8 - Sair")

        opcao = ler_opcao("Digite a opção desejada: ")

        match opcao:
            case 1:
                alterar_conta_estab(cursor, conexao, estab)
            case 2:
                buscar_publi_estab(cursor, estab)
                input("\nPressione Enter para voltar ao menu ")
                os.system("cls")
            case 3:
                print("\n" + "Buscando instituições...")
                time.sleep(3)
                os.system("cls")
                ver_instituicoes(cursor)
                input("\nPressione Enter para voltar ao menu ")
                os.system("cls")
            case 4:
                solicitacoes = ver_solicitacoes_estab(cursor, estab)
                if solicitacoes:
                    responder_solicitacao(cursor, conexao, estab)
                input("\nPressione Enter para voltar ao menu ")
                os.system("cls")
            case 5:
                ver_necessidades(cursor)
                input("\nPressione Enter para voltar ao menu ")
                os.system("cls")
            case 6:
                publicar_oferta(cursor, conexao, estab)
                input("\nPressione Enter para voltar ao menu ")
                os.system("cls")
            case 7:
                deletar_publicacao(cursor, conexao, estab)
                input("\nPressione Enter para voltar ao menu ")
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
        print(f"           Painel de controle da {inst['nm_fantasia']}")
        print("=" * 20)
        print("1 - Alterar dados cadastrais")
        print("2 - Ver ofertas disponíveis")
        print("3 - Solicitar uma oferta")
        print("4 - Minhas solicitações")
        print("5 - Publicar necessidade")
        print("6 - Minhas necessidades")
        print("7 - Pesquisar estabelecimentos")
        print("8 - Confirmar recebimento")
        print("9 - Sair")

        opcao = ler_opcao("Digite a opção desejada: ")

        match opcao:
            case 1:
                alterar_conta_inst(cursor, conexao, inst)
            case 2:
                ver_ofertas_disponiveis(cursor)
                input("\nPressione Enter para voltar ao menu ")
            case 3:
                solicitar_oferta(cursor, conexao, inst)
                input("\nPressione Enter para voltar ao menu ")
            case 4:
                minhas_solicitacoes(cursor, conexao, inst)
                input("\nPressione Enter para voltar ao menu ")
            case 5:
                publicar_necessidade(cursor, conexao, inst)
                input("\nPressione Enter para voltar ao menu ")
            case 6:
                minhas_necessidades(cursor, conexao, inst)
                input("\nPressione Enter para voltar ao menu ")
            case 7:
                pesquisar_estabelecimentos(cursor)
                input("\nPressione Enter para voltar ao menu ")
            case 8:
                confirmar_recebimento(cursor, conexao, inst)
                input("\nPressione Enter para voltar ao menu ")
            case 9:
                print("Saindo...")
                time.sleep(2)
                os.system("cls")
                break
            case _:
                print("Opção inválida, tente novamente!")
                time.sleep(2)
                os.system("cls")


def menu_adm(cursor, conexao, adm):
    while True:
        print("\n" + "=" * 20)
        print(f"Bem-vindo, {adm['nm_usuario']}! Qual a tarefa de hoje?")
        print("=" * 20)
        print("1 - Analisar cadastros pendentes")
        print("2 - Listar organizações")
        print("3 - Inativar organização")
        print("4 - Catálogo de alimentos")
        print("5 - Sair")

        opcao = ler_opcao("Digite a opção desejada: ")

        match opcao:
            case 1:
                analisar_cad_pendentes(cursor, conexao)
            case 2:
                listar_organizacoes(cursor)
                input("\nPressione Enter para voltar ao menu ")
                os.system("cls")
            case 3:
                inativar_organizacao(cursor, conexao, adm)
                input("\nPressione Enter para voltar ao menu ")
                os.system("cls")
            case 4:
                menu_catalogo_alimentos(cursor, conexao)
            case 5:
                print("Saindo...")
                time.sleep(2)
                os.system("cls")
                break
            case _:
                print("Opção inválida, tente novamente!")
                time.sleep(2)
                os.system("cls")


if __name__ == "__main__":
    main()