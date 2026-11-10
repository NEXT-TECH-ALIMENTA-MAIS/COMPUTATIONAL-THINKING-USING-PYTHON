import os
import time

def exibir_menu_empresa():
    print("\n" + "="*20)
    print("     DESTAQUES")
    print("="*20)
    print("1 - Ver conta")
    print("2 - Buscar doações")
    print("3 - Pesquisar instituições")
    print("4 - Visualizar solicitações de instituições")
    print("5 - Ver publicações de necessidades")
    print("6 - Publicar uma oferta")
    print("7 - Deletar publicação")
    print("8 - Sair")
    

def main():

    while True:
        exibir_menu_empresa()

        try:
            opcao = int(input("Digite a opção desejada: "))

            match opcao:
                case 1:
                    print("Função para ver a conta")
                    time.sleep(3)
                    os.system('cls')
                case 2:
                    print("Função para buscar doações")    
                case 3: 
                    print("Função para pesquisar por instituições receptoras")
                case 4:
                    print("Função para visualizar as solicitações das instituições")
                case 5:
                    print("Função para ver as publicações de necessidades das instituições")
                case 6:
                    print("Função para publicar uma oferta")
                case 7:
                    print("Função para deletar uma publicação")
                case 8:
                    print("Sair")
                    break
                case _:
                    print("Opção inválida, tente novamente!")
        except ValueError as erro:
            print(f"Erro: {erro}")














if __name__ == "__main__":
    main()