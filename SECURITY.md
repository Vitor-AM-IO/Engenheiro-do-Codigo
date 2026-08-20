# Segurança e Privacidade

**Regra de ouro deste projeto: nada sai do computador do usuário, e ninguém de
fora pode acessar.**

- **Só local:** o servidor escuta apenas em `127.0.0.1` (o endereço interno do
  próprio PC). Nenhum computador da internet ou da mesma rede consegue enxergar
  ou acessar — só a própria máquina.
- **Sua chave fica no seu PC:** a chave de API é salva apenas no arquivo `.env`,
  no computador do usuário. Ela **nunca** é enviada para nenhum servidor nosso
  (não existe servidor nosso). É usada só para falar direto com o provedor de IA
  que o próprio usuário escolheu (Anthropic, Groq, etc.).
- **Chave não fica exposta na tela:** depois de salva, a interface mostra apenas
  o começo e o fim da chave (ex.: `gsk_…2345`), nunca ela inteira.
- **Proteção contra sites maliciosos:** mesmo rodando local, o servidor valida o
  cabeçalho `Host` (anti DNS-rebinding) e a `Origin` das requisições (anti-CSRF).
  Assim, nenhum site aberto no navegador consegue usar o Construtor por trás.
- **Sem nuvem, sem banco de dados, sem telemetria:** o Construtor não envia nada
  para lugar nenhum além do provedor de IA configurado pelo usuário.

## Privacidade do código gerado

O que o Construtor gera é feito com base no provedor escolhido. Se o provedor for
na nuvem (Anthropic, Groq…), a **descrição** que você digita é enviada a esse
provedor para gerar o código. Para manter tudo 100% local, use o **Ollama**
(roda no seu PC, não envia nada para a internet).

## Aviso

O código é gerado por IA e pode conter erros — revise antes de usar em produção.
