# Onboarding (Windows)

> **Validação no Windows pendente.** Tudo abaixo foi testado só no Linux. Antes de cadastrar dados reais, execute a checklist de `docs/setup.md` (seção "Antes de usar dados reais") no seu computador.

## Instalar

1. Instale o Git for Windows e o uv (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`. Esse é o instalador oficial; leia-o antes de executar, se preferir.
2. Baixe o repositório pelo GitHub Desktop (branch `claude/practical-bell-w2zwqp`) numa pasta **dentro do seu usuário** (por exemplo, `C:\Users\<você>\Projetos\SalesOS`), fora de pastas sincronizadas pelo OneDrive se possível. Abra o terminal nessa pasta.
3. `uv sync --locked`: o uv baixa o Python 3.15 e instala as versões exatas do `uv.lock` em `.venv`.
4. `uv run alembic upgrade head`: cria ou atualiza `data\salesos.db`. Rode de novo sempre que atualizar o código. Depois de atualizar para a Fase 03 (revisão `0003`), `salesos restore` recusa backups feitos antes da atualização (B1).
5. Opcional: copie `.env.example` para `.env` para fixar a porta, o segredo dos formulários ou a pasta de backups.

Rode todos os comandos a partir da raiz do projeto: os caminhos `data\...` são relativos a ela.

## Usar

- `uv run salesos` e abra http://127.0.0.1:8000. Para encerrar, Ctrl+C no terminal.
- **Clientes**: cadastrar, buscar por nome ou e-mail, editar, arquivar e restaurar.
- **Na tela do cliente**: contatos, registro de interações (ligação, reunião, mensagem, e-mail, nota) e a linha do tempo. Interações não podem ser editadas nem apagadas depois.
- **Funil** (Fase 03): na página do cliente, **Nova oportunidade**. O valor é em reais no formato `1.234,56`. A oportunidade começa em *Novo lead* e muda de etapa pelo formulário **Mudar etapa**: livre entre as etapas em andamento; *Venda ganha* exige valor; *Venda perdida* exige o motivo. Para trocar ganha por perdida (ou o contrário), reabra antes numa etapa em andamento. O histórico de etapas nunca é apagado. Venda ganha **não** significa contrato assinado nem pagamento recebido.
- **Anonimizar** é irreversível: leia `docs/privacy.md` antes. As oportunidades do cliente perdem título, observações e detalhe do motivo; valor, etapa e datas ficam.
- Ainda não existem CPF, CNPJ e telefone (aguardam a validação das regras oficiais).

## Backup

**Não copie a pasta `data\` com o servidor ligado**: o banco usa WAL e a cópia pode sair inconsistente. Use o comando, que funciona com o servidor ligado ou desligado:

```
uv run salesos backup
```

- Cria `data\backups\salesos-<data>.db` e o manifesto `.db.json` (SHA-256, revisão), depois de conferir a integridade.
- Nada é apagado automaticamente: os backups se acumulam e contêm dados pessoais. Guarde uma cópia fora do computador (pendrive criptografado, por exemplo) e veja a limpeza em `docs/privacy.md`.
- Para mudar a pasta: `SALESOS_BACKUP_DIR` no `.env`.
- Se aparecer "bloqueado por outro programa", algum programa (por exemplo, o DB Browser no meio de uma alteração) está segurando o banco: feche-o e rode de novo.

## Restaurar um backup

1. Encerre o servidor (Ctrl+C) e feche qualquer programa que esteja com o banco aberto (DB Browser, por exemplo).
2. `uv run salesos restore data\backups\salesos-<data>.db`
3. Se der certo, a mensagem informa onde ficou o banco anterior (`data\salesos.db.pre-restore-<data>`); também é feito um backup de segurança em `data\backups\pre-restore-<data>.db`.

A restauração **recusa** (sem alterar nada) quando:

- o servidor do SalesOS ou outro programa está usando o banco;
- o banco atual não pode ser lido (por exemplo, não foi migrado): a mensagem mostra o erro do SQLite, e o caminho é rodar `uv run alembic upgrade head` antes;
- o backup está corrompido, sem manifesto, com SHA-256 diferente, de outra versão do esquema ou com estrutura inesperada;
- o backup traria de volta dados de um cliente anonimizado depois dele. Se for isso mesmo, repita com `--aceitar-reintroducao`.

### Backup de uma versão anterior do SalesOS

Depois de uma atualização com migração (por exemplo, da Fase 02 para a Fase 03), o restore recusa backups antigos com "revisão do esquema ... difere da atual". Nesse caso, use `--migrar`. Ele migra **uma cópia** do backup para a versão atual e restaura o resultado; o backup original não é alterado:

```
uv run salesos restore data\backups\salesos-<data>.db --migrar
```

- A mensagem informa o backup migrado, que fica guardado como `data\backups\migrado-<data>.db` (com manifesto). Ele contém os dados do backup **antigo**, embora a data no nome seja a de hoje.
- Valem as mesmas recusas acima (inclusive a de anonimização, com `--aceitar-reintroducao` se for isso mesmo).
- Se aparecer "Backup não migrado", nada foi alterado: o backup está corrompido, é de uma versão desconhecida ou mais nova, ou a migração falhou.
- **Este comando foi testado no Linux; no Windows ainda não.** Os comandos acima foram revisados, não executados no PowerShell.

## Se a restauração for interrompida

Queda de energia ou janela fechada no meio da restauração deixam um registro pendente, e o servidor não inicia até ele ser resolvido. Rode:

```
uv run salesos recover
```

O comando termina com segurança: antes da troca concluída, volta o banco anterior (o novo fica guardado como `.failed-<data>`); depois, mantém o restaurado. Pode ser rodado mais de uma vez. Ele nunca apaga arquivos e avisa se houver sobras temporárias de backup, inclusive pastas `data\backups\.migracao-*` deixadas por um `restore --migrar` interrompido (contêm uma cópia dos dados: apague-as depois de conferir).

Se o comando responder "Diário de restauração inválido", o registro pendente foi corrompido ou alterado: nada foi movido. Não apague o arquivo `data\salesos.db.restore.json` sem antes conferir a pasta `data\` (o banco atual e as cópias `.pre-restore-*`).

## Verificar a instalação

```
uv run ruff check . ; uv run ruff format --check . ; uv run mypy ; uv run pytest
```

No Windows, o resultado esperado do pytest é `437 passed, 14 skipped, 1 warning` (estimativa): os 5 testes de permissões POSIX e os 9 de fuso com `tzset` não se aplicam ao Windows e o teste exclusivo do Windows (troca recusada com o arquivo aberto) precisa **rodar e passar**. Detalhes em `docs/quality.md`.
