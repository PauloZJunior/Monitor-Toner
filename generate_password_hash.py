#!/usr/bin/env python3
"""
generate_password_hash.py — Utilitário para gerar hash bcrypt seguro

Uso:
    python3 generate_password_hash.py
    python3 generate_password_hash.py "minha_senha"

Exemplo:
    $ python3 generate_password_hash.py "Toner@2024Segura"
    Hash bcrypt:
    $2b$12$YourHashHereFullHash...
    
    Copie o hash acima para a variável ADMIN_PASSWORD_HASH no arquivo .env
"""
import sys
import bcrypt
import getpass


def main():
    if len(sys.argv) > 1:
        # Senha passada como argumento
        senha = sys.argv[1]
    else:
        # Solicita senha de forma segura (sem ecoar)
        senha = getpass.getpass("Digite a senha do administrador: ")
        confirma = getpass.getpass("Confirme a senha: ")
        
        if senha != confirma:
            print("❌ Erro: As senhas não conferem!")
            sys.exit(1)
    
    if not senha or len(senha) < 8:
        print("❌ Erro: Senha muito curta (mínimo 8 caracteres)")
        sys.exit(1)
    
    # Gera hash bcrypt com 12 rounds (mais seguro)
    hash_bcrypt = bcrypt.hashpw(senha.encode(), bcrypt.gensalt(rounds=12)).decode()
    
    print("\n" + "="*80)
    print("✓ Hash bcrypt gerado com sucesso!")
    print("="*80)
    print(f"\nHash:\n{hash_bcrypt}\n")
    print("="*80)
    print("\nInstruções:")
    print("  1. Copie o hash acima")
    print("  2. Abra o arquivo .env")
    print("  3. Cole o valor em: ADMIN_PASSWORD_HASH=<hash>")
    print("  4. Salve o arquivo")
    print("  5. Execute: docker-compose up -d")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
