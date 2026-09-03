<div align="center">

# 🔧 Engenheiro do Código

### Descreva um projeto. Ele constrói pra você. E ainda revisa se ficou bom.

Você escreve **em português** o que quer que o programa faça.
A inteligência artificial **cria todos os arquivos**, mostra uma **prévia
ao vivo** e ainda **revisa** o que foi feito — tudo na sua tela.

**Feito por Vitor** ([@Vitor-AM-IO](https://github.com/Vitor-AM-IO)) · Software livre (MIT)

</div>

---

## 🎬 O que ele faz, em 1 minuto

1. Você escreve: *"uma agenda de contatos que adiciona, lista e apaga"*
2. Escolhe a linguagem (Python, Java, PHP ou site Web)
3. Clica em **Criar projeto**
4. Ele **gera os arquivos**, mostra uma **prévia** (se for site) e você **baixa o `.zip`**
5. Se quiser, clica em **🩺 Revisar** e ele confere se o código ficou bom

Pronto. Sem instalar mil coisas, sem saber programar.

---

## 🚀 Como usar (jeito fácil — Windows)

> Não precisa entender de programação. Siga os passos:

**1.** Baixe este projeto (botão verde **Code → Download ZIP**) e descompacte.

**2.** Dê **dois cliques** em **`Engenheiro-do-Codigo.bat`**.
   - Se você **não tiver o Python**, ele **instala sozinho** — é só confirmar.

**3.** Na primeira vez, ele pergunta **qual IA usar**. Escolha uma:
   | Opção | Custo | Bom pra |
   |-------|-------|---------|
   | 🟢 **Groq** | Grátis (nuvem) | Começar sem gastar e sem pesar no PC |
   | 🔵 **Anthropic** | Centavos por projeto | Melhor qualidade |
   | 🟡 **Ollama** | Grátis (no seu PC) | Quem tem PC forte e quer tudo offline |

**4.** A página abre no navegador. **Escreva o que quer e clique em Criar.** 🎉

> 💡 **Dica:** quer um atalho na Área de Trabalho? Dê dois cliques em
> **`criar-atalho.bat`** (uma vez só). Depois é só clicar no ícone pra abrir.

**No Linux ou Mac?** Rode `./start.sh` no terminal (ele também instala o que falta).

---

## ✨ O que tem dentro

- 🏗️ **Cria projetos do zero** — Python, Java, PHP e sites (HTML/CSS/JS)
- 👁️ **Prévia ao vivo** — vê o site rodando na hora, com botão de tela cheia
- 🩺 **Revisor embutido** — confere erros, bugs e falhas de segurança no que foi criado
- ⚙️ **Troca de IA na tela** — muda de provedor/modelo sem editar nada
- 🔒 **100% no seu PC** — sua chave nunca sai daqui ([veja a segurança](SECURITY.md))
- 💰 **Grátis se quiser** — funciona com Ollama (local) ou Groq (nuvem grátis)

---

## 🎯 Pra que serve (e pra que não serve)

✅ **Funciona muito bem** em projetos pequenos e bem descritos: sites simples,
scripts, programinhas de terminal, APIs pequenas, exercícios.

⚠️ **Não espere milagre** em sistemas grandes e complexos (app completo com banco
de dados, login, pagamento). A IA tenta, mas o resultado precisa de ajuste manual.
E a **qualidade depende da IA escolhida** — Groq/Anthropic geram bem melhor que o
Ollama pequeno.

---

<details>
<summary><b>👨‍💻 É programador? Clique aqui pro modo técnico</b></summary>

### Instalar via pip
```bash
git clone https://github.com/Vitor-AM-IO/Engenheiro-do-Codigo.git
cd Engenheiro-do-Codigo
pip install .
```

### Usar pelo terminal
```bash
# descrição direto no comando
construtor "uma agenda de contatos no terminal" --lang python --out ./agenda

# ou deixe ele perguntar
construtor --lang web
```
Opções: `--lang python|java|php|web`, `--out <pasta>`, `--provider`, `--model`.

### Configurar a IA
Na interface, botão **⚙️ Configurar IA** (grava no `.env` local), ou manualmente:
```
CONSTRUTOR_PROVIDER=groq
GROQ_API_KEY=sua-chave
CONSTRUTOR_MODEL=openai/gpt-oss-120b
```
Provedores: Anthropic, OpenAI, Groq, DeepSeek, Ollama. Cada projeto gera até 12
arquivos (controle de custo). A chave fica só no `.env`, servidor escuta apenas em
`127.0.0.1`. Detalhes em [SECURITY.md](SECURITY.md).

### Estrutura
- `construtor/generator.py` — planeja e gera os arquivos (o cérebro)
- `construtor/revisor.py` — revisor de código embutido
- `construtor/web.py` — interface web (prévia, config, revisão)
- `construtor/providers.py` — camada de IA (multi-provedor, com retry)

</details>

---

<div align="center">

**Gostou? Deixe uma ⭐ no repositório!**

Criado com dedicação por **Vitor** · Licença MIT

</div>
