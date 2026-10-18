# data-fake — gerador de dados fictícios (Universidade Hogwarts)

    python main.py                       # gera CSVs + popular.sql em ./saida
    python main.py --alunos 1000 --professores 120 --semente 7

- Python 3.10+, sem dependências externas.
- `data/` = CSVs-base de entrada (nomes.csv e sobrenomes.csv são exemplos: troque pelos seus).
- `datafake/config.py` = todos os parâmetros. `saida/` = resultado (apague e gere de novo quando quiser).
- A validação (PK, UNIQUE, FK e regras de negócio) roda antes de gravar; se falhar, nada é escrito.
