"""
AGENTE MARIA - TAZMANIA
Flask + OpenRouter + Google Sheets + WhatsApp + Web UI movil
"""
import os, json, requests, tempfile
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
conversaciones = {}

CARTA_1_URL = "https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%201.jpeg"
CARTA_2_URL = "https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%202.jpeg"
QR_BBVA_URL  = "https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/QR_BBVA.jpeg"

PALABRAS_CARTA = ["menu","carta","que tienen","que hay","que venden","productos","ver todo","que ofrecen","que manejan"]
PALABRAS_QR    = ["transferencia","qr","bbva","pagar con","transferir","consignar"]

SYSTEM_PROMPT = """Eres Maria, asistente virtual de Taz, el restaurante de comidas rapidas mas sabroso de Buenaventura. Eres amable, rapida y cercana. Solo tomas pedidos de domicilio.

SALUDO: Al primer mensaje di exactamente: Hola! Soy Maria de Taz. Estoy aqui para ayudarte con tu pedido. Que delicia quieres hoy?

HORARIO: Todos los dias 4PM a 12AM. Fuera de horario: Gracias por escribir a Taz! Estamos descansando, volvemos a las 4PM.

MENU COMPLETO:
HAMBURGUESAS (V/U=unitario, COM=combo con papa francesa + bebida):
TAZ CON MUCHO QUESO V/U $29.900 COM $41.100
TAZ DOBLE RES V/U $35.600 COM $46.800
TAZ POLLO V/U $29.900 COM $41.100
TAZ DOBLE POLLO V/U $35.600 COM $46.800
TAZ MIXTA V/U $35.600 COM $46.800
TAZ CUARTO LIBRA ANGUS V/U $24.500 COM $36.000
TAZ CUARTO LIBRA POLLO V/U $24.500 COM $36.000
TAZ MEDIA LIBRA ANGUS V/U $35.700 COM $47.000
TAZ LIBRA ANGUS V/U $63.000 COM $74.600

PERROS:
PERRO MUCHO QUESO V/U $24.700 COM $34.700
PERRO JUNIOR V/U $20.900 COM $30.900
PERRO RANCHERO V/U $25.400 COM $35.400

ASADOS A LA PARRILLA:
FILETE POLLO $33.500
FILETE GRATINADO $36.600
FILETE LIMON PIMIENTA $34.900
COSTILLA BBQ $45.800
MEDIA COSTILLA $34.600
ALITAS X6 (salsa a elegir: Miel Mostaza/BBQ/Limon Pimienta) $30.800
ALITAS X12 $55.800

OTRAS DELICIAS:
SALCHIPAPA Personal $19.600 Grande $27.400
SALCHIQUESO Personal $26.300 Grande $33.500
SALCHIRANCHERA $22.300
SALCHIRANCHERA CON QUESO $29.000
SALCHICOSTILLA $25.800
SALCHIPOLLO $22.300

ADICIONALES: Pollo 120gr $8.400 | Salchicha $6.500 | Costilla 150gr $9.900 | Tocineta 3un $4.900 | Queso americano $2.800 | Queso fundido 150gr $8.000 | Ensalada $3.400 | Cebolla $2.800 | Salsas $1.700 | Papa francesa 165gr $8.600

BEBIDAS: Gaseosa 2.5L $13.400 | Gaseosa 500ml $4.500 | Jugo hit $4.800 | Mr Tea $4.700 | Agua $3.000 | Cerveza $5.000

ZONAS COMPLETAS: Palo Seco, Iglesia, El Jorge, Inmaculada, Todo Jorge, La Abeja, Km5, Calle 7, Miramar, San Luis, Juan 23, Berberena, Rusbell, Calle Colombia, Las Flores, Chuchofong, Porvenir, El Jardin, El Campin, Eucaristico, 1 de Julio, Rockefeller, Modelo, Maria Eugenia, Bellavista, Olimpico, El Cristal, Transformacion, Cascajal, Independencia.
ZONAS PARCIALES (solo autopista): 12 de Abril, 6 de Enero, El Dorado, Camilo Torres, Ley 69, El Cambio, Alfonso Lopez, Nuevo Horizonte, El Caldas, El Uribe, La Virgen, Cabal Pombo, La Campina, La Libertad, La Frontera, La Dignidad, Floresta, Vista Hermosa, Villa Linda.
Hotel Linea y Via Alterna solo hasta 7PM.

FLUJO: 1-Saluda 2-Toma pedido 3-Confirma (combo/unitario, bebida, salsa, adicionales) 4-Pide nombre y direccion 5-Verifica zona 6-Resumen con total 7-Tiempo semana 30-45min fines 50-60min 8-Metodo pago Efectivo/Datafono/Transferencia QR BBVA Chef Fast llave 0091626861 9-Si transfiere pide comprobante 10-Confirma

Al confirmar completamente pon al FINAL: ##PEDIDO_CONFIRMADO##{"nombre":"X","telefono":"X","direccion":"X","barrio":"X","productos":"X","total":"X","pago":"X"}##

CAMBIOS: Pedido en preparacion, revisamos si alcanzamos. QUEJAS: 316 721 9321. No inventes precios. Calcula bien."""

# ─── HTML ─────────────────────────────────────────────────────────────────────
PAGE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<title>Maria - Taz</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html{height:100%;height:-webkit-fill-available}
body{font-family:Arial,sans-serif;background:#ECE5DD;display:flex;flex-direction:column;height:100vh;height:-webkit-fill-available;overflow:hidden;position:fixed;width:100%;top:0;left:0}
.hdr{background:#075E54;color:#fff;padding:10px 16px;display:flex;align-items:center;gap:10px;flex-shrink:0;z-index:10}
.av{width:40px;height:40px;background:#25D366;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}
.hi h2{font-size:15px;margin:0}
.hi p{font-size:11px;color:#ccc;margin:0}
.badge{background:#FF6B35;color:#fff;font-size:9px;padding:1px 6px;border-radius:8px;margin-left:5px}
.rbtn{margin-left:auto;background:rgba(255,255,255,.2);color:#fff;border:none;border-radius:12px;padding:5px 12px;font-size:11px;cursor:pointer}
.msgs{flex:1;overflow-y:auto;overflow-x:hidden;padding:14px;display:flex;flex-direction:column;gap:7px;-webkit-overflow-scrolling:touch}
.msg{max-width:80%;padding:8px 11px;border-radius:8px;font-size:14px;line-height:1.5;word-wrap:break-word;white-space:pre-wrap}
.bot{background:#fff;align-self:flex-start;border-top-left-radius:0;box-shadow:0 1px 2px rgba(0,0,0,.1)}
.usr{background:#DCF8C6;align-self:flex-end;border-top-right-radius:0}
.typ{background:#fff;align-self:flex-start;color:#999;font-style:italic;padding:9px 13px;border-radius:8px}
.iw{align-self:flex-start;max-width:85%}
.iw img{max-width:100%;border-radius:8px;display:block;box-shadow:0 1px 3px rgba(0,0,0,.2)}
.vm{background:#DCF8C6;align-self:flex-end;border-top-right-radius:0;display:flex;align-items:center;gap:7px;padding:8px 13px;border-radius:8px;font-size:13px;color:#555;max-width:80%}
.bar{background:#F0F0F0;padding:8px 10px;display:flex;gap:7px;align-items:center;flex-shrink:0;border-top:1px solid #ddd;padding-bottom:max(8px,env(safe-area-inset-bottom,8px))}
#inp{flex:1;padding:10px 14px;border-radius:22px;border:none;outline:none;font-size:16px;background:#fff;min-width:0;-webkit-appearance:none;appearance:none}
.btn{background:#075E54;color:#fff;border:none;border-radius:50%;width:42px;height:42px;min-width:42px;cursor:pointer;font-size:17px;flex-shrink:0;display:flex;align-items:center;justify-content:center}
.btn:active{background:#128C7E}
.btn:disabled{background:#aaa}
#mic.rec{background:#e53935;animation:pu 1s infinite}
@keyframes pu{0%,100%{transform:scale(1)}50%{transform:scale(1.1)}}
</style>
</head>
<body>
<div class="hdr">
  <div class="av">&#127828;</div>
  <div class="hi"><h2>Maria <span class="badge">PRUEBAS</span></h2><p>Taz - Buenaventura</p></div>
  <button class="rbtn" id="rst">&#128260; Nueva</button>
</div>
<div class="msgs" id="msgs"></div>
<div class="bar">
  <input type="text" id="inp" placeholder="Escribe tu pedido..." autocomplete="off" autocorrect="off" autocapitalize="sentences">
  <button class="btn" id="mic">&#127908;</button>
  <button class="btn" id="snd">&#10148;</button>
</div>
<script>
var sid='p_'+Math.random().toString(36).substr(2,8);
var mr=null,ac=[],rec=false;
var C1='https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%201.jpeg';
var C2='https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%202.jpeg';
var QR='https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/QR_BBVA.jpeg';

function sb(){var m=document.getElementById('msgs');setTimeout(function(){m.scrollTop=m.scrollHeight;},50);}

function aM(t,x){var m=document.getElementById('msgs'),d=document.createElement('div');d.className='msg '+t;d.textContent=x;m.appendChild(d);sb();return d;}

function aI(u){var m=document.getElementById('msgs'),w=document.createElement('div');w.className='iw';var i=document.createElement('img');i.onload=sb;i.onerror=function(){w.remove();};i.src=u;w.appendChild(i);m.appendChild(w);sb();}

function proc(d){
  if(d.response)aM('bot',d.response);
  if(d.enviar_carta){setTimeout(function(){aI(C1);},200);setTimeout(function(){aI(C2);},500);}
  if(d.enviar_qr){setTimeout(function(){aI(QR);},200);}
}

function send(txt,voz){
  var btn=document.getElementById('snd');
  btn.disabled=true;
  if(voz){var v=document.createElement('div');v.className='vm';v.innerHTML='&#127908; '+txt;document.getElementById('msgs').appendChild(v);sb();}
  else{aM('usr',txt);}
  var t=aM('typ','Maria esta escribiendo...');
  fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:txt,session_id:sid})})
  .then(function(r){return r.json();})
  .then(function(d){t.remove();proc(d);btn.disabled=false;document.getElementById('inp').focus();})
  .catch(function(){t.remove();aM('bot','Error. Intenta de nuevo.');btn.disabled=false;});
}

function go(){var i=document.getElementById('inp'),v=i.value.trim();if(!v)return;i.value='';send(v,false);}

function startRec(){
  if(!navigator.mediaDevices){alert('Usa Chrome para notas de voz');return;}
  navigator.mediaDevices.getUserMedia({audio:true}).then(function(s){
    ac=[];mr=new MediaRecorder(s);
    mr.ondataavailable=function(e){ac.push(e.data);};
    mr.onstop=function(){
      var b=new Blob(ac,{type:'audio/webm'});
      s.getTracks().forEach(function(t){t.stop();});
      sendAudio(b);
    };
    mr.start();rec=true;
    document.getElementById('mic').classList.add('rec');
  }).catch(function(){alert('Permite el acceso al microfono');});
}

function stopRec(){if(mr&&rec){mr.stop();rec=false;document.getElementById('mic').classList.remove('rec');}}

function sendAudio(blob){
  var t=aM('typ','Escuchando nota de voz...');
  var fd=new FormData();fd.append('audio',blob,'voz.webm');fd.append('session_id',sid);
  fetch('/audio',{method:'POST',body:fd})
  .then(function(r){return r.json();})
  .then(function(d){
    t.remove();
    if(d.transcripcion){var v=document.createElement('div');v.className='vm';v.innerHTML='&#127908; '+d.transcripcion;document.getElementById('msgs').appendChild(v);sb();}
    proc(d);
  })
  .catch(function(){t.remove();aM('bot','No pude procesar el audio.');});
}

document.getElementById('snd').onclick=go;
document.getElementById('mic').onclick=function(){if(!rec)startRec();else stopRec();};
document.getElementById('rst').onclick=function(){
  fetch('/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sid})});
  document.getElementById('msgs').innerHTML='';
  aM('bot','Hola! Soy Maria de Taz. Estoy aqui para ayudarte con tu pedido. Que delicia quieres hoy?');
};
document.getElementById('inp').addEventListener('keypress',function(e){if(e.key==='Enter')go();});

// Fix teclado movil
if(window.visualViewport){
  window.visualViewport.addEventListener('resize',function(){
    var bar=document.querySelector('.bar');
    var offset=window.innerHeight-window.visualViewport.height;
    bar.style.marginBottom=offset>0?offset+'px':'0';
    sb();
  });
}

aM('bot','Hola! Soy Maria de Taz. Estoy aqui para ayudarte con tu pedido. Que delicia quieres hoy?');
</script>
</body>
</html>"""

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def call_claude(session_id, mensaje):
    if session_id not in conversaciones:
        conversaciones[session_id] = []
    conversaciones[session_id].append({"role":"user","content":mensaje})
    h = conversaciones[session_id][-20:]
    hdrs = {"Authorization":"Bearer "+os.environ.get("OPENROUTER_API_KEY",""),
            "Content-Type":"application/json","HTTP-Referer":"https://tazmania-bot.com","X-Title":"Maria Taz"}
    body = {"model":"anthropic/claude-sonnet-4-5","max_tokens":1000,
            "messages":[{"role":"system","content":SYSTEM_PROMPT}]+h}
    r = requests.post("https://openrouter.ai/api/v1/chat/completions",headers=hdrs,json=body)
    txt = r.json()["choices"][0]["message"]["content"]
    clean = txt.replace("##ENVIAR_CARTA##","").replace("##ENVIAR_QR##","")
    if "##PEDIDO_CONFIRMADO##" in clean:
        clean = clean[:clean.index("##PEDIDO_CONFIRMADO##")].strip()
    conversaciones[session_id].append({"role":"assistant","content":clean})
    pedido = extraer_pedido(txt)
    if pedido:
        pedido["telefono"] = session_id
        sheets(pedido)
    return txt

def build_resp(msg, txt):
    m = msg.lower()
    carta = "##ENVIAR_CARTA##" in txt or any(p in m for p in PALABRAS_CARTA)
    qr    = "##ENVIAR_QR##"    in txt or any(p in m for p in PALABRAS_QR)
    clean = txt.replace("##ENVIAR_CARTA##","").replace("##ENVIAR_QR##","").strip()
    if "##PEDIDO_CONFIRMADO##" in clean:
        clean = clean[:clean.index("##PEDIDO_CONFIRMADO##")].strip()
    return {"response":clean,"enviar_carta":carta,"enviar_qr":qr}

def extraer_pedido(txt):
    if "##PEDIDO_CONFIRMADO##" in txt:
        try:
            i = txt.index("##PEDIDO_CONFIRMADO##")+len("##PEDIDO_CONFIRMADO##")
            j = txt.index("##",i)
            return json.loads(txt[i:j])
        except: pass
    return None

def gclient():
    j = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not j: return None
    try:
        sc = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
        c = Credentials.from_service_account_info(json.loads(j),scopes=sc)
        return gspread.authorize(c)
    except: return None

def sheets(d):
    try:
        gc = gclient()
        if not gc: return
        ws = gc.open_by_key(os.environ.get("GOOGLE_SHEET_ID")).sheet1
        if ws.row_count==0 or ws.cell(1,1).value!="Fecha":
            ws.append_row(["Fecha","Hora","Nombre","Telefono","Direccion","Barrio","Productos","Total","Pago","Estado"])
        n=datetime.now()
        ws.append_row([n.strftime("%d/%m/%Y"),n.strftime("%H:%M"),d.get("nombre",""),d.get("telefono",""),
                       d.get("direccion",""),d.get("barrio",""),d.get("productos",""),d.get("total",""),d.get("pago",""),"PENDIENTE"])
    except Exception as e: print("Sheets:",e)

def wa_txt(num,msg):
    t=os.environ.get("WHATSAPP_TOKEN"); p=os.environ.get("PHONE_NUMBER_ID")
    r=requests.post(f"https://graph.facebook.com/v18.0/{p}/messages",
        headers={"Authorization":f"Bearer {t}","Content-Type":"application/json"},
        json={"messaging_product":"whatsapp","to":num,"type":"text","text":{"body":msg}})
    print("WA txt:",r.status_code)

def wa_img(num,url,cap=""):
    t=os.environ.get("WHATSAPP_TOKEN"); p=os.environ.get("PHONE_NUMBER_ID")
    r=requests.post(f"https://graph.facebook.com/v18.0/{p}/messages",
        headers={"Authorization":f"Bearer {t}","Content-Type":"application/json"},
        json={"messaging_product":"whatsapp","to":num,"type":"image","image":{"link":url,"caption":cap}})
    print("WA img:",r.status_code)

def wa_send(num, msg_usuario, txt):
    m=msg_usuario.lower()
    carta="##ENVIAR_CARTA##" in txt or any(p in m for p in PALABRAS_CARTA)
    qr="##ENVIAR_QR##" in txt or any(p in m for p in PALABRAS_QR)
    clean=txt.replace("##ENVIAR_CARTA##","").replace("##ENVIAR_QR##","").strip()
    if "##PEDIDO_CONFIRMADO##" in clean: clean=clean[:clean.index("##PEDIDO_CONFIRMADO##")].strip()
    if clean: wa_txt(num,clean)
    if carta: wa_img(num,CARTA_1_URL,"Carta Taz - Hamburguesas"); wa_img(num,CARTA_2_URL,"Carta Taz - Asados")
    if qr: wa_img(num,QR_BBVA_URL,"QR Pago BBVA - Chef Fast")

def whisper(data, ext="webm"):
    try:
        from openai import OpenAI
        oc=OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        with tempfile.NamedTemporaryFile(suffix="."+ext,delete=False) as f:
            f.write(data); tp=f.name
        with open(tp,"rb") as af:
            tr=oc.audio.transcriptions.create(model="whisper-1",file=af,language="es")
        os.unlink(tp); return tr.text
    except Exception as e: print("Whisper:",e); return None

def whisper_wa(aid):
    try:
        t=os.environ.get("WHATSAPP_TOKEN")
        h={"Authorization":f"Bearer {t}"}
        u=requests.get(f"https://graph.facebook.com/v18.0/{aid}",headers=h).json().get("url")
        return whisper(requests.get(u,headers=h).content,"ogg")
    except Exception as e: print("Whisper WA:",e); return None

# ─── RUTAS ────────────────────────────────────────────────────────────────────

@app.route("/")
def index(): return render_template_string(PAGE)

@app.route("/chat", methods=["POST"])
def chat():
    d=request.get_json(); msg=d.get("message",""); sid=d.get("session_id","web")
    return jsonify(build_resp(msg, call_claude(sid,msg)))

@app.route("/audio", methods=["POST"])
def audio():
    sid=request.form.get("session_id","web")
    af=request.files.get("audio")
    if not af: return jsonify({"error":"no audio"}),400
    tr=whisper(af.read(),"webm")
    if not tr: return jsonify({"response":"No pude entender. Escribe tu pedido.","enviar_carta":False,"enviar_qr":False})
    r=build_resp(tr, call_claude(sid,tr)); r["transcripcion"]=tr; return jsonify(r)

@app.route("/reset", methods=["POST"])
def reset():
    d=request.get_json(); sid=d.get("session_id","web")
    conversaciones.pop(sid,None); return jsonify({"ok":True})

@app.route("/webhook", methods=["GET"])
def wh_verify():
    if request.args.get("hub.mode")=="subscribe" and request.args.get("hub.verify_token")==os.environ.get("VERIFY_TOKEN"):
        return request.args.get("hub.challenge"),200
    return "error",403

@app.route("/webhook", methods=["POST"])
def wh_recv():
    try:
        d=request.get_json()
        msgs=d.get("entry",[{}])[0].get("changes",[{}])[0].get("value",{}).get("messages",[])
        if not msgs: return jsonify({"ok":True}),200
        msg=msgs[0]; num=msg.get("from"); tipo=msg.get("type")
        if tipo=="text": txt=msg["text"]["body"]
        elif tipo=="audio":
            txt=whisper_wa(msg["audio"]["id"])
            if not txt: wa_txt(num,"No pude escuchar. Escribe tu pedido."); return jsonify({"ok":True}),200
        elif tipo=="image": txt="[Cliente envio imagen, probablemente comprobante de pago]"
        else: wa_txt(num,"Solo entiendo texto, notas de voz e imagenes."); return jsonify({"ok":True}),200
        wa_send(num, txt, call_claude(num,txt))
        return jsonify({"ok":True}),200
    except Exception as e: print("WH error:",e); return jsonify({"error":str(e)}),500

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)
