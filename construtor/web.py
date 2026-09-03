"""Servidor web local do Construtor: descreve o projeto e recebe os arquivos."""

from __future__ import annotations

import base64
import io
import json
import os
import threading
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__, config, generator, providers

_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}


def _provider(name=None, model=None):
    config._load_dotenv()
    try:
        return providers.get_provider(name, config.get_model(model)), None
    except providers.ProviderError as exc:
        return None, str(exc)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _host_ok(self):
        return self.headers.get("Host", "").split(":")[0] in _ALLOWED_HOSTS

    def _origin_ok(self):
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        from urllib.parse import urlparse
        return urlparse(origin).hostname in _ALLOWED_HOSTS

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):
        if not self._host_ok():
            self._json(403, {"error": "host não permitido"}); return
        if self.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/status":
            prov, err = _provider()
            self._json(200, {"has_key": prov is not None, "error": err,
                             "version": __version__, "signature":
                             __import__("construtor", fromlist=["SIGNATURE"]).SIGNATURE,
                             "languages": config.LANGUAGES})
        elif self.path == "/api/config":
            estado = config.estado_atual()
            estado["provedores"] = {k: {"nome": v["nome"],
                                        "precisa_chave": v["precisa_chave"],
                                        "modelo_padrao": v["modelo_padrao"]}
                                    for k, v in config.PROVEDORES_UI.items()}
            estado["ollama_rodando"] = config.ollama_rodando()
            self._json(200, estado)
        else:
            self._json(404, {"error": "não encontrado"})

    def do_POST(self):
        if not self._host_ok() or not self._origin_ok():
            self._json(403, {"error": "requisição não permitida"}); return
        if self.path not in ("/api/build", "/api/config", "/api/revisar"):
            self._json(404, {"error": "não encontrado"}); return

        length = int(self.headers.get("Content-Length", 0) or 0)
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = {}

        # Salvar configuração (provedor/modelo/chave) — grava no .env LOCAL.
        if self.path == "/api/config":
            ok, msg = config.salvar_config(data.get("provider", ""),
                                           data.get("model", ""),
                                           data.get("chave", ""))
            resp = {"ok": ok, "msg": msg}
            if ok:
                resp.update(config.estado_atual())
            self._json(200, resp)
            return

        # Revisar os arquivos gerados (Dr. Código embutido).
        if self.path == "/api/revisar":
            from . import revisor
            provider, err = _provider(data.get("provider"), data.get("model"))
            if provider is None:
                self._json(200, {"error": err or "Provedor não configurado."}); return
            arquivos = [(f.get("path", ""), f.get("content", ""))
                        for f in data.get("files", []) if f.get("path")]
            if not arquivos:
                self._json(200, {"error": "nenhum arquivo para revisar"}); return
            reviews, total = revisor.revisar_arquivos(arquivos, provider)
            self._json(200, {
                "reviews": [{
                    "path": r.path, "summary": r.summary, "error": r.error,
                    "issues": [{"line": i.line, "severity": i.severity,
                                "title": i.title, "description": i.description,
                                "suggestion": i.suggestion} for i in r.issues],
                } for r in reviews],
                "usage": {"input": total.input_tokens, "output": total.output_tokens},
            })
            return

        provider, err = _provider(data.get("provider"), data.get("model"))
        if provider is None:
            self._json(200, {"error": err or "Provedor não configurado."}); return

        descricao = (data.get("descricao") or "").strip()
        lang = data.get("lang", "python")
        if not descricao:
            self._json(200, {"error": "descreva o que o projeto deve fazer"}); return
        if lang not in config.LANGUAGES:
            lang = "python"

        result = generator.build_project(descricao, lang, provider)
        if not result.ok:
            self._json(200, {"error": result.error}); return

        # monta um .zip em memória para download
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for path, content in result.files:
                z.writestr(f"{result.plan.project_name}/{path}", content)
        zip_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        self._json(200, {
            "project_name": result.plan.project_name,
            "run": result.plan.run,
            "files": [{"path": p, "content": c} for p, c in result.files],
            "zip_b64": zip_b64,
            "usage": {"input": result.usage.input_tokens,
                      "output": result.usage.output_tokens},
        })


def serve(host="127.0.0.1", port=8770, open_browser=True):
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"Construtor Web rodando em {url}")
    print("Pressione Ctrl+C para parar.")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando…")
        server.shutdown()


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Engenheiro do Código</title>
<style>
  :root{--bg:#0f1115;--panel:#171a21;--panel2:#1e222b;--line:#2a2f3a;--text:#e7e9ee;
    --muted:#9aa3b2;--accent:#5b9dff;--accent2:#7ee0a2;--radius:14px}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font:15px/1.55 -apple-system,Segoe UI,Roboto,Arial,sans-serif}
  header{padding:20px 24px;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center}
  header h1{font-size:18px;margin:0}
  header .ver{color:var(--muted);font-size:12px;margin-left:auto}
  .wrap{max-width:900px;margin:0 auto;padding:24px}
  label{display:block;font-size:13px;color:var(--muted);margin:14px 0 6px}
  textarea,select,input{width:100%;background:var(--panel2);border:1px solid var(--line);
    color:var(--text);border-radius:10px;padding:11px 12px;font-size:14px}
  textarea{min-height:150px;font-family:inherit}
  .btn{margin-top:16px;background:var(--accent);color:#07101f;border:none;padding:12px 22px;
    border-radius:10px;font-weight:700;cursor:pointer;font-size:15px}
  .btn:disabled{opacity:.6;cursor:progress}
  .hint{color:var(--muted);font-size:12px;margin-top:6px}
  .banner{background:#3a2020;border:1px solid #5c2b2b;color:#ffb4b4;padding:12px 14px;
    border-radius:10px;margin-bottom:16px;display:none}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);
    padding:16px;margin-bottom:14px}
  .file{margin-bottom:10px}
  .file summary{cursor:pointer;font-weight:600}
  pre{background:#0b0d11;border:1px solid var(--line);border-radius:10px;padding:12px;
    overflow:auto;font-size:12.5px;margin:8px 0 0}
  .result{display:none;margin-top:20px}
  .dl{display:inline-block;margin-top:8px;background:var(--accent2);color:#07101f;
    padding:10px 18px;border-radius:10px;font-weight:700;text-decoration:none}
  a{color:var(--accent)}
</style></head><body>
<header><span style="font-size:22px">🔧</span><h1>Engenheiro do Código</h1>
<button id="cfgbtn" style="margin-left:auto;background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:7px 12px;cursor:pointer">⚙️ Configurar IA</button>
<span class="ver" id="ver"></span></header>
<div class="wrap">
  <div class="banner" id="banner"></div>

  <div id="cfgpanel" class="card" style="display:none">
    <b>⚙️ De onde vem a inteligência artificial</b>
    <div class="hint" style="margin:6px 0 12px">Tudo fica salvo só no seu computador (arquivo .env). Sua chave nunca sai daqui e ninguém de fora acessa.</div>
    <label>Provedor</label>
    <select id="cfg-prov"></select>
    <div id="cfg-chave-box">
      <label>Chave da API <span id="cfg-chave-atual" class="hint"></span></label>
      <input type="password" id="cfg-chave" placeholder="cole a chave aqui (fica só no seu PC)">
      <div class="hint" id="cfg-chave-ajuda"></div>
    </div>
    <label>Modelo</label>
    <input type="text" id="cfg-model" placeholder="nome do modelo">
    <div id="cfg-ollama-aviso" class="hint" style="display:none"></div>
    <button class="btn" id="cfg-salvar" style="margin-top:14px">💾 Salvar</button>
    <span id="cfg-msg" class="hint" style="margin-left:10px"></span>
  </div>

  <label>Descreva o que o projeto deve fazer (uma lista, quanto mais detalhe melhor)</label>
  <textarea id="descricao" placeholder="Ex.:&#10;- uma agenda de contatos no terminal&#10;- adicionar, listar e apagar contatos&#10;- salvar num arquivo"></textarea>
  <div class="row" style="display:flex;gap:12px;flex-wrap:wrap">
    <div style="flex:1;min-width:180px">
      <label>Linguagem / tipo</label>
      <select id="lang">
        <option value="python">Python</option>
        <option value="java">Java</option>
        <option value="php">PHP</option>
        <option value="web">Web (HTML/CSS/JS)</option>
      </select>
    </div>
  </div>
  <button class="btn" id="btn">🏗️ Criar projeto</button>
  <div class="hint">O agente planeja os arquivos e gera cada um. Custa tokens (use um
    provedor local como o Ollama pra não gastar). Cria até 12 arquivos por projeto.</div>
  <div class="result" id="result"></div>
</div>
<script>
let CFG={provedores:{}};
async function carregarConfig(){
  try{
    const c=await (await fetch('/api/config')).json();
    CFG=c;
    const sel=document.getElementById('cfg-prov');
    sel.innerHTML='';
    for(const [id,p] of Object.entries(c.provedores)){
      const label = id==='ollama'
        ? p.nome + (c.ollama_rodando ? ' — ✓ detectado!' : ' — (não está rodando)')
        : p.nome;
      sel.innerHTML+='<option value="'+id+'">'+label+'</option>';
    }
    sel.value=c.provider;
    document.getElementById('cfg-model').value=c.model||'';
    atualizarCampos();
    if(c.tem_chave){
      document.getElementById('cfg-chave-atual').textContent='(salva: '+c.chave_mascarada+' — deixe em branco pra manter)';
    }
  }catch(e){}
}
function atualizarCampos(){
  const id=document.getElementById('cfg-prov').value;
  const p=CFG.provedores[id]||{};
  document.getElementById('cfg-chave-box').style.display = p.precisa_chave ? '' : 'none';
  const aviso=document.getElementById('cfg-ollama-aviso');
  if(id==='ollama'){
    aviso.style.display='';
    aviso.textContent = CFG.ollama_rodando
      ? '✓ Ollama detectado no seu PC. É grátis e local.'
      : '⚠ O Ollama não está rodando. Abra o app do Ollama antes de usar.';
  } else { aviso.style.display='none'; }
  const ajuda={anthropic:'Pegue em platform.claude.com/settings/keys (começa com sk-ant-)',
    groq:'Grátis em console.groq.com (começa com gsk_)',
    openai:'Pegue em platform.openai.com (começa com sk-)'}[id]||'';
  document.getElementById('cfg-chave-ajuda').textContent=ajuda;
  if(!document.getElementById('cfg-model').value && p.modelo_padrao)
    document.getElementById('cfg-model').value=p.modelo_padrao;
}
document.getElementById('cfg-prov').onchange=()=>{
  const id=document.getElementById('cfg-prov').value;
  document.getElementById('cfg-model').value=(CFG.provedores[id]||{}).modelo_padrao||'';
  document.getElementById('cfg-chave').value='';
  document.getElementById('cfg-chave-atual').textContent='';
  atualizarCampos();
};
document.getElementById('cfgbtn').onclick=()=>{
  const pnl=document.getElementById('cfgpanel');
  pnl.style.display = pnl.style.display==='none' ? '' : 'none';
};
document.getElementById('cfg-salvar').onclick=async ()=>{
  const body={provider:document.getElementById('cfg-prov').value,
    model:document.getElementById('cfg-model').value,
    chave:document.getElementById('cfg-chave').value};
  const msg=document.getElementById('cfg-msg');
  msg.textContent='salvando…';
  try{
    const r=await (await fetch('/api/config',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
    msg.textContent = r.ok ? '✓ salvo!' : ('⚠ '+r.msg);
    if(r.ok){ document.getElementById('cfg-chave').value='';
      if(r.chave_mascarada) document.getElementById('cfg-chave-atual').textContent='(salva: '+r.chave_mascarada+')';
      document.getElementById('banner').style.display='none'; }
  }catch(e){ msg.textContent='⚠ falha ao salvar'; }
};

async function status(){
  try{const s=await (await fetch('/api/status')).json();
    document.getElementById('ver').textContent='v'+s.version;
    if(!s.has_key){const b=document.getElementById('banner');b.style.display='block';
      b.textContent='⚠ '+(s.error||'Provedor não configurado')+' — configure o .env e reinicie.';}
  }catch(e){}
}
status();
carregarConfig();
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

async function build(){
  const descricao=document.getElementById('descricao').value.trim();
  if(!descricao){alert('Descreva o projeto primeiro.');return;}
  const lang=document.getElementById('lang').value;
  const btn=document.getElementById('btn');
  btn.disabled=true; btn.textContent='Criando… (pode levar um tempo)';
  const r=document.getElementById('result'); r.style.display='none';
  try{
    const res=await fetch('/api/build',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({descricao,lang})});
    const d=await res.json();
    if(d.error){ r.style.display='block'; r.innerHTML='<div class="card" style="color:#ffb4b4">'+esc(d.error)+'</div>'; return; }
    render(d);
  }catch(e){ r.style.display='block'; r.innerHTML='<div class="card" style="color:#ffb4b4">Falha ao gerar.</div>'; }
  finally{ btn.disabled=false; btn.textContent='🏗️ Criar projeto'; }
}

function render(d){
  window._ultimosArquivos = d.files;  // guarda pra revisão
  const r=document.getElementById('result'); r.style.display='block';
  let html='<div class="card"><b>Projeto: '+esc(d.project_name)+'</b> — '+d.files.length+' arquivo(s)';
  const zipUrl='data:application/zip;base64,'+d.zip_b64;
  html+='<br><a class="dl" download="'+esc(d.project_name)+'.zip" href="'+zipUrl+'">⬇ Baixar projeto (.zip)</a>';
  html+=' <button class="btn" id="btn-revisar" style="margin-top:8px">🩺 Revisar o que foi criado</button>';
  html+='<div id="revisao"></div>';
  if(d.run) html+='<div class="hint" style="margin-top:10px">Como rodar: '+esc(d.run)+'</div>';
  html+='</div>';

  // Prévia ao vivo — só para projetos web (quando há um index.html)
  const paginaHtml = montarPreview(d.files);
  if(paginaHtml){
    html+='<div class="card"><div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">'
      +'<b>👁️ Prévia ao vivo</b>'
      +'<button class="btn" id="btn-fullscreen" style="margin-left:auto;padding:7px 14px">⛶ Tela cheia</button>'
      +'</div>'
      +'<iframe id="preview-frame" style="width:100%;height:420px;border:1px solid var(--line);'
      +'border-radius:10px;background:#fff" sandbox="allow-scripts allow-forms allow-modals"></iframe>'
      +'<div class="hint" style="margin-top:8px">É só uma amostra rodando aqui dentro. Baixe o .zip para usar de verdade.</div>'
      +'</div>';
  }

  for(const f of d.files){
    html+='<details class="card file"><summary>'+esc(f.path)+'</summary>'
      +'<pre>'+esc(f.content)+'</pre></details>';
  }
  if(d.usage) html+='<div class="hint">Tokens: '+d.usage.input+' entrada / '+d.usage.output+' saída</div>';
  r.innerHTML=html;
  document.getElementById('btn-revisar').onclick=revisarProjeto;

  // injeta a página na prévia (via srcdoc, isolado)
  if(paginaHtml){
    const frame=document.getElementById('preview-frame');
    frame.srcdoc=paginaHtml;
    window._paginaPreview=paginaHtml;
    document.getElementById('btn-fullscreen').onclick=abrirTelaCheia;
  }
}

// Junta os arquivos web num único HTML (embute CSS e JS inline) para a prévia.
function montarPreview(files){
  const byPath={};
  for(const f of files) byPath[f.path.replace(/^\.\//,'')]=f.content;
  // acha o index.html (ou qualquer .html)
  let htmlPath=Object.keys(byPath).find(p=>/(^|\/)index\.html$/i.test(p))
            || Object.keys(byPath).find(p=>/\.html$/i.test(p));
  if(!htmlPath) return null;  // não é projeto web → sem prévia
  let doc=byPath[htmlPath];

  // embute os <link rel=stylesheet href="..."> como <style>
  doc=doc.replace(/<link[^>]*href=["']([^"']+\.css)["'][^>]*>/gi,(m,href)=>{
    const css=acharArquivo(byPath,href); return css!=null?('<style>\n'+css+'\n</style>'):m;
  });
  // embute os <script src="..."> como <script>inline</script>
  doc=doc.replace(/<script[^>]*src=["']([^"']+\.js)["'][^>]*><\/script>/gi,(m,src)=>{
    const js=acharArquivo(byPath,src); return js!=null?('<script>\n'+js+'\n<\/script>'):m;
  });
  return doc;
}
function acharArquivo(byPath,ref){
  ref=ref.replace(/^\.\//,'').replace(/^\//,'');
  if(byPath[ref]!=null) return byPath[ref];
  // tenta casar só pelo nome do arquivo (caso o caminho tenha pasta)
  const nome=ref.split('/').pop();
  const k=Object.keys(byPath).find(p=>p.split('/').pop()===nome);
  return k!=null?byPath[k]:null;
}
function abrirTelaCheia(){
  const w=window.open('','_blank');
  if(w){ w.document.open(); w.document.write(window._paginaPreview||''); w.document.close(); }
}

async function revisarProjeto(){
  const btn=document.getElementById('btn-revisar');
  const alvo=document.getElementById('revisao');
  btn.disabled=true; btn.textContent='Revisando… (pode levar um tempo)';
  try{
    const res=await fetch('/api/revisar',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({files:window._ultimosArquivos})});
    const d=await res.json();
    if(d.error){ alvo.innerHTML='<div class="hint" style="color:#ffb4b4">'+esc(d.error)+'</div>'; return; }
    renderRevisao(d, alvo);
  }catch(e){ alvo.innerHTML='<div class="hint" style="color:#ffb4b4">Falha ao revisar.</div>'; }
  finally{ btn.disabled=false; btn.textContent='🩺 Revisar o que foi criado'; }
}

function renderRevisao(d, alvo){
  const cor={critical:'#ff6b6b',high:'#ffa94d',medium:'#ffd43b',low:'#8ce99a'};
  const lbl={critical:'CRÍTICO',high:'ALTO',medium:'MÉDIO',low:'BAIXO'};
  let total=0; d.reviews.forEach(r=>total+=(r.issues||[]).length);
  let html='<div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--line)">';
  html+='<b>🩺 Resultado da revisão</b> — '+(total===0?'nenhum problema encontrado! ✓':total+' ponto(s) de atenção');
  for(const r of d.reviews){
    const n=(r.issues||[]).length;
    const status = r.error ? '⚠ erro' : (n===0 ? '✓ OK' : '⚠ '+n);
    html+='<div style="margin-top:10px"><b>'+esc(r.path)+'</b> <span class="hint">'+status+'</span>';
    if(r.error){ html+='<div class="hint" style="color:#ffb4b4">'+esc(r.error)+'</div>'; }
    for(const i of (r.issues||[])){
      const c=cor[i.severity]||'#ccc';
      html+='<div style="margin:6px 0;padding:8px 10px;background:var(--panel2);border-left:3px solid '+c+';border-radius:6px">'
        +'<span style="color:'+c+';font-weight:700;font-size:11px">'+(lbl[i.severity]||i.severity)+'</span> '
        +'<b>'+esc(i.title)+'</b> <span class="hint">('+(i.line?'linha '+i.line:'geral')+')</span>'
        +'<div class="hint" style="margin-top:2px">'+esc(i.description)+'</div>'
        +(i.suggestion?'<div class="hint" style="color:var(--accent2);margin-top:2px">→ '+esc(i.suggestion)+'</div>':'')
        +'</div>';
    }
    html+='</div>';
  }
  if(d.usage) html+='<div class="hint" style="margin-top:8px">Revisão: '+d.usage.input+' entrada / '+d.usage.output+' saída (tokens)</div>';
  html+='</div>';
  alvo.innerHTML=html;
}
document.getElementById('btn').onclick=build;
</script></body></html>"""
