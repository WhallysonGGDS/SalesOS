# 0004 — Modelo de clientes, contatos e interações

**Status:** aceita (Fase 02)

**Contexto:** a Fase 02 precisa guardar clientes, as pessoas que falam por eles e o histórico de contato, com dados pessoais mínimos e sem campos cuja regra oficial ainda não foi validada.

**Decisão:**
- Três tabelas (migração `0002`): `clientes`, `contatos` e `interacoes`.
- `clientes`: tipo `PF`/`PJ`; origem numa lista fixa (D1); e-mail único entre clientes; `busca` com nome, nome fantasia e e-mail sem acentos e em casefold (usada na busca e na ordenação); `archived_at` e `anonimizado_em`.
- `contatos`: e-mail único dentro do mesmo cliente e repetível entre clientes (D2, restrição `uq_contatos_cliente_id_email`). Remover contato é permitido (D3).
- `interacoes`: só acréscimo (D5): não existe função nem rota para editar ou excluir. Tipo `sistema` é reservado para os eventos que o serviço grava, só com ação e nomes de campos (D4).
- Chaves estrangeiras: cliente com filhos não pode ser apagado (`RESTRICT`); remover contato deixa `interacoes.contato_id` nulo (`SET NULL`), preservando o histórico.
- Sem telefone (D12). A coluna `documento` existe, mas fica vazia até CPF e CNPJ terem fonte oficial (D6, D11).
- Anonimização em vez de exclusão física (D9): mantém o ID e as referências; detalhes em `docs/privacy.md`.
- Datas em UTC no banco; a interface mostra no fuso do computador.
- `PRAGMA secure_delete=ON` em toda conexão.

**Consequências:**
- A busca usa `LIKE '%termo%'` sobre `busca` e percorre a tabela: adequado para um usuário; rever se o volume crescer muito.
- O SQLite grava datas sem fuso; a aplicação garante UTC.
- Liberar CPF, CNPJ ou telefone exige fonte oficial, aprovação e uma migração nova.
