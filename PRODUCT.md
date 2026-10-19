# Produto — WE TECH SalesOS

## Problema
A WE TECH precisa organizar clientes, oportunidades, propostas, contratos, tarefas e resultados comerciais num sistema próprio, sem depender de um CRM de terceiros.

## Público
O proprietário da WE TECH, como único usuário na primeira versão.

## Escopo por fase
| Fase | Conteúdo | Situação |
|---|---|---|
| 00 | Descoberta e planejamento | Concluída |
| 01 | Fundação técnica | Concluída (este estado) |
| 02 | Clientes e histórico | Planejada |
| 03 | Oportunidades e funil | Planejada |
| 04 | Tarefas e agenda | Planejada |
| 05 | Serviços, propostas, contratos e assinaturas | Planejada |
| 06 | Dashboard e relatórios | Planejada |
| 07 | Segurança e preparação para expansão | Planejada |
| 08 | Validação integral e entrega | Planejada |

## Restrições
- Local, um usuário, servidor só em loopback. Expor na rede exige uma fase própria de segurança.
- Sem Docker, sem IA no produto, sem WhatsApp real, gateway de pagamento ou envio de e-mail na versão inicial.
- Custo adicional zero sempre que viável.
- Dados pessoais tratados conforme a LGPD: mínimo necessário, testes só com dados fictícios.
- Estados comerciais distintos e nunca equivalentes: oportunidade ganha, contrato assinado, cobrança registrada, valor recebido.

## Critérios de aceite da Fase 01
Ver `docs/phases.md` (Fase 01) e as evidências em `docs/setup.md`.
