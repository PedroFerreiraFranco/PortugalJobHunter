import os

# Cria o diretório templates/ relativo ao diretório do projeto
base_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(base_dir, "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
    print(f"Diretório criado: {templates_dir}")
else:
    print(f"Diretório já existe: {templates_dir}")
