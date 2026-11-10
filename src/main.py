import os
import time

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