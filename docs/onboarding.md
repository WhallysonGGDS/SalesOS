# Onboarding (Windows)

> **Validação no Windows pendente.** Tudo abaixo foi testado só no Linux. Antes de cadastrar dados reais, execute a checklist de `docs/setup.md` (seção "Antes de usar dados reais") no seu computador.

## Instalar

1. Instale o Git for Windows e o uv (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`. Esse é o instalador oficial; leia-o antes de executar, se preferir.
2. Baixe o repositório pelo GitHub Desktop (branch `claude/practical-bell-w2zwqp`) numa pasta **dentro do seu usuário** (por exemplo, `C:\Users\<você>\Projetos\SalesOS`), fora de pastas sincronizadas pelo OneDrive se possível. Abra o terminal nessa pasta.
3. `uv sync --locked`: o uv baixa o Python 3.15 e instala as versões exatas do `uv.lock` em `.venv`.
4. `uv run alembic upgrade head`: cria ou atualiza `data\salesos.db`. Rode de novo sempre que atualizar o código.
5. Opcional: copie `.env.example` para `.env` para fixar a porta, o segredo dos formulários ou a pasta de backups.

Rode todos os comandos a partir da raiz do projeto: os caminhos `data\...` são relativos a ela.

## Usar

- `uv run salesos` e abra http://127.0.0.1:8000. Para encerrar, Ctrl+C no terminal.
- **Clientes**: cadastrar, buscar por nome ou e-mail, editar, arquivar e restaurar.
- **Na tela do cliente**: contatos, registro de interações (ligação, reunião, mensagem, e-mail, nota) e a linha do tempo. Interações não podem ser editadas nem apagadas depois.
- **Anonimizar** é irreversível: leia `docs/privacy.md` antes.
- Ainda não existem CPF, CNPJ e telefone (aguardam a validação das regras oficiais).

## Backup

**Não copie a pasta `data\` com o servidor ligado**: o banco usa WAL e a cópia pode sair inconsistente. Use o comando, que funciona com o servidor ligado ou desligado:

```
uv run salesos backup
```

- Cria `data\backups\salesos-<data>.db` e o manifesto `.db.json` (SHA-256, revisão), depois de conferir a integridade.
- Nada é apagado automaticamente: os backups se acumulam e contêm dados pessoais. Guarde uma cópia fora do computador (pendrive criptografado, por exemplo) e veja a limpeza em `docs/privacy.md`.
- Para mudar a pasta: `SALESOS_BACKUP_DIR` no `.env`.

## Restaurar um backup

1. Encerre o servidor (Ctrl+C) e feche qualquer programa que esteja com o banco aberto (DB Browser, por exemplo).
2. `uv run salesos restore data\backups\salesos-<data>.db`
3. Se der certo, a mensagem informa onde ficou o banco anterior (`data\salesos.db.pre-restore-<data>`); também é feito um backup de segurança em `data\backups\pre-restore-<data>.db`.

A restauração **recusa** (sem alterar nada) quando:

- o servidor do SalesOS ou outro programa está usando o banco;
- o backup está corrompido, sem manifesto, com SHA-256 diferente, de outra versão do esquema ou com estrutura inesperada;
- o backup traria de volta dados de um cliente anonimizado depois dele. Se for isso mesmo, repita com `--aceitar-reintroducao`.

## Se a restauração for interrompida

Queda de energia ou janela fechada no meio da restauração deixam um registro pendente, e o servidor não inicia até ele ser resolvido. Rode:

```
uv run salesos recover
```

O comando termina com segurança: antes da troca concluída, volta o banco anterior (o novo fica guardado como `.failed-<data>`); depois, mantém o restaurado. Pode ser rodado mais de uma vez. Ele nunca apaga arquivos e avisa se houver sobras temporárias de backup.

## Verificar a instalação

```
uv run ruff check . ; uv run ruff format --check . ; uv run mypy ; uv run pytest
```

No Windows, o resultado esperado do pytest é `227 passed, 4 skipped, 1 warning`: os 4 testes de permissões POSIX não se aplicam ao Windows e o teste exclusivo do Windows (troca recusada com o arquivo aberto) precisa **rodar e passar**. Detalhes em `docs/quality.md`.
