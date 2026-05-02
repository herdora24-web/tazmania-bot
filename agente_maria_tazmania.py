"""
================================================================
AGENTE MARIA - TAZMANIA
Servidor Flask completo con imagenes, notas de voz y WhatsApp
================================================================
"""

import os
import json
import requests
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
conversaciones = {}

CARTA_1_URL = "https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%201.jpeg"
CARTA_2_URL = "https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%202.jpeg"
QR_BBVA_URL = "https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/QR_BBVA.jpeg"

PALABRAS_CARTA = ["menu", "carta", "que tienen", "que hay", "que venden", "productos", "ver todo", "que ofrecen", "que manejan"]
PALABRAS_QR = ["transferencia", "qr", "bbva", "pagar con", "transferir", "consignar"]

SYSTEM_PROMPT = """Eres Maria, la asistente virtual de Taz, el restaurante de comidas rapidas mas sabroso de Buenaventura. Eres amable, rapida, cercana y hablas con el tono calido y familiar del Pacifico colombiano. Tu unico trabajo es tomar pedidos de domicilio.

SALUDO: Al primer mensaje di exactamente: Hola! Soy Maria de Taz. Estoy aqui para ayudarte con tu pedido. Que delicia quieres hoy?

HORARIO: Todos los dias 4:00 PM a 12:00 AM. Fuera de horario di: Gracias por escribir a Taz! Estamos descansando, volvemos a las 4:00 PM.

MENU:
HAMBURGUESAS: TAZ CON MUCHO QUESO V/U $29.900 COM $41.100 | TAZ DOBLE RES V/U $35.600 COM $46.800 | TAZ POLLO V/U $29.900 COM $41.100 | TAZ DOBLE POLLO V/U $35.600 COM $46.800 | TAZ MIXTA V/U $35.600 COM $46.800 | TAZ CUARTO LIBRA ANGUS V/U $24.500 COM $36.000 | TAZ CUARTO LIBRA POLLO V/U $24.500 COM $36.000 | TAZ MEDIA LIBRA ANGUS V/U $35.700 COM $47.000 | TAZ LIBRA ANGUS V/U $63.000 COM $74.600
PERROS: PERRO MUCHO QUESO V/U $24.700 COM $34.700 | PERRO JUNIOR V/U $20.900 COM $30.900 | PERRO RANCHERO V/U $25.400 COM $35.400
ASADOS: FILETE POLLO $33.500 | FILETE GRATINADO $36.600 | FILETE LIMON PIMIENTA $34.900 | COSTILLA BBQ $45.800 | MEDIA COSTILLA $34.600 | ALITAS X6 $30.800 | ALITAS X12 $55.800
DELICIAS: SALCHIPAPA Personal $19.600 Grande $27.400 | SALCHIQUESO Personal $26.300 Grande $33.500 | SALCHIRANCHERA $22.300 | SALCHIRANCHERA QUESO $29.000 | SALCHICOSTILLA $25.800 | SALCHIPOLLO $22.300
ADICIONALES: Pollo $8.400 | Salchicha $6.500 | Costilla $9.900 | Tocineta $4.900 | Queso americano $2.800 | Queso fundido $8.000 | Ensalada $3.400 | Cebolla $2.800 | Salsas $1.700 | Papa francesa $8.600
BEBIDAS: Gaseosa 2.5L $13.400 | Gaseosa 500ml $4.500 | Jugo hit $4.800 | Mr Tea $4.700 | Agua $3.000 | Cerveza $5.000
COMBO incluye: papa francesa + gaseosa/jugo/te/agua

ZONAS ACCESO COMPLETO: Palo Seco, Iglesia, El Jorge, Inmaculada, Todo Jorge, La Abeja, Km 5, Calle 7, Miramar, San Luis, Juan 23, Berberena, Rusbell, Calle Colombia, Las Flores, Chuchofong, Porvenir, El Jardin, El Campin, Eucaristico, 1 de Julio, Rockefeller, Modelo, Maria Eugenia, Bellavista, Olimpico, El Cristal, Transformacion, Cascajal, Independencia.
ZONAS PARCIALES (solo autopista): 12 de Abril, 6 de Enero, El Dorado, Camilo Torres, Ley 69, El Cambio, Alfonso Lopez, Nuevo Horizonte, El Caldas, El Uribe, La Virgen, Cabal Pombo, La Campina, La Libertad, La Frontera, La Dignidad, Floresta, Vista Hermosa, Villa Linda.
Hotel Linea y Via Alterna solo hasta 7PM.

FLUJO: 1-Saluda 2-Toma el pedido 3-Confirma detalles (combo/unitario, bebida, salsa, adicionales) 4-Pide nombre y direccion 5-Verifica zona 6-Muestra resumen con total 7-Tiempos semana 30-45min fines 50-60min 8-Pregunta metodo pago (Efectivo/Datafono/Transferencia QR BBVA Chef Fast llave 0091626861) 9-Si transfiere pide comprobante 10-Confirma

Al confirmar pedido pon al final: ##PEDIDO_CONFIRMADO##{"nombre":"X","telefono":"X","direccion":"X","barrio":"X","productos":"X","total":"X","pago":"X"}##

CAMBIOS: Ya esta en preparacion, con gusto revisamos. QUEJAS: 316 721 9321. REGLAS: No inventes precios. Calcula bien."""


HTML_CHAT = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, interactive-widget=resizes-content">
<title>Maria - Taz Bot Pruebas</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Arial, sans-serif; background: #ECE5DD; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
.header { background: #075E54; color: white; padding: 12px 20px; display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.avatar { width: 42px; height: 42px; background: #25D366; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; }
.hinfo h2 { font-size: 16px; }
.hinfo p { font-size: 12px; color: #ccc; }
.badge { background: #FF6B35; color: white; font-size: 10px; padding: 2px 8px; border-radius: 10px; margin-left: 6px; }
.rbtn { margin-left: auto; background: rgba(255,255,255,0.2); color: white; border: none; border-radius: 15px; padding: 6px 14px; font-size: 12px; cursor: pointer; white-space: nowrap; }
.msgs { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
.msg { max-width: 78%; padding: 8px 12px; border-radius: 8px; font-size: 14px; line-height: 1.5; word-wrap: break-word; white-space: pre-wrap; }
.bot { background: white; align-self: flex-start; border-top-left-radius: 0; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
.user { background: #DCF8C6; align-self: flex-end; border-top-right-radius: 0; }
.typing { background: white; align-self: flex-start; color: #999; font-style: italic; padding: 10px 14px; }
.img-wrap { align-self: flex-start; max-width: 78%; }
.img-wrap img { max-width: 100%; border-radius: 8px; display: block; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
.voice-msg { background: #DCF8C6; align-self: flex-end; border-top-right-radius: 0; display: flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 8px; font-size: 13px; color: #555; }
.iarea { background: #F0F0F0; padding: 10px 12px; display: flex; gap: 8px; align-items: center; flex-shrink: 0; border-top: 1px solid #ddd; }
#inp { flex: 1; padding: 10px 15px; border-radius: 25px; border: none; outline: none; font-size: 14px; background: white; }
.sbtn { background: #075E54; color: white; border: none; border-radius: 50%; width: 44px; height: 44px; cursor: pointer; font-size: 18px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; transition: background 0.2s; }
.sbtn:hover { background: #128C7E; }
.sbtn:disabled { background: #ccc; cursor: not-allowed; }
#micbtn { background: #075E54; }
#micbtn.grabando { background: #e53935; animation: pulse 1s infinite; }
@keyframes pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.1)} }
</style>
</head>
<body>
<div class="header">
  <div class="avatar">&#127828;</div>
  <div class="hinfo">
    <h2>Maria <span class="badge">PRUEBAS</span></h2>
    <p>Taz Comidas Rapidas - Buenaventura</p>
  </div>
  <button class="rbtn" id="resetbtn">&#128260; Nueva conv.</button>
</div>
<div class="msgs" id="msgs"></div>
<div class="iarea">
  <input type="text" id="inp" placeholder="Escribe como cliente o usa el microfono...">
  <button class="sbtn" id="micbtn" title="Nota de voz">&#127908;</button>
  <button class="sbtn" id="sbtn">&#10148;</button>
</div>

<script>
var sid = 'prueba_' + Math.random().toString(36).substr(2, 9);
var mediaRecorder = null;
var audioChunks = [];
var grabando = false;

var CARTA_1 = 'https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%201.jpeg';
var CARTA_2 = 'https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%202.jpeg';
var QR_BBVA = 'https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/QR_BBVA.jpeg';

function scrollBottom() {
  var m = document.getElementById('msgs');
  m.scrollTop = m.scrollHeight;
}

function addMsg(tipo, txt) {
  var m = document.getElementById('msgs');
  var d = document.createElement('div');
  d.className = 'msg ' + tipo;
  d.textContent = txt;
  m.appendChild(d);
  scrollBottom();
  return d;
}

function addImg(url) {
  var m = document.getElementById('msgs');
  var w = document.createElement('div');
  w.className = 'img-wrap';
  var img = document.createElement('img');
  img.onload = scrollBottom;
  img.onerror = function() { w.remove(); };
  img.src = url;
  w.appendChild(img);
  m.appendChild(w);
  scrollBottom();
}

function procesarRespuesta(data) {
  if (data.response) addMsg('bot', data.response);
  if (data.enviar_carta) {
    setTimeout(function() { addImg(CARTA_1); }, 300);
    setTimeout(function() { addImg(CARTA_2); }, 600);
  }
  if (data.enviar_qr) {
    setTimeout(function() { addImg(QR_BBVA); }, 300);
  }
}

function enviarMensaje(texto, esVoz) {
  var btn = document.getElementById('sbtn');
  btn.disabled = true;
  if (esVoz) {
    var vm = document.createElement('div');
    vm.className = 'voice-msg';
    vm.innerHTML = '&#127908; Nota de voz';
    document.getElementById('msgs').appendChild(vm);
    scrollBottom();
  } else {
    addMsg('user', texto);
  }
  var typing = addMsg('typing', 'Maria esta escribiendo...');
  fetch('/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: texto, session_id: sid})
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    typing.remove();
    procesarRespuesta(d);
    btn.disabled = false;
    document.getElementById('inp').focus();
  })
  .catch(function(e) {
    typing.remove();
    addMsg('bot', 'Error de conexion. Intenta de nuevo.');
    btn.disabled = false;
  });
}

function enviar() {
  var inp = document.getElementById('inp');
  var txt = inp.value.trim();
  if (!txt) return;
  inp.value = '';
  enviarMensaje(txt, false);
}

// Notas de voz
function iniciarGrabacion() {
  if (!navigator.mediaDevices) {
    alert('Tu navegador no soporta grabacion de audio. Usa Chrome.');
    return;
  }
  navigator.mediaDevices.getUserMedia({audio: true}).then(function(stream) {
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = function(e) { audioChunks.push(e.data); };
    mediaRecorder.onstop = function() {
      var blob = new Blob(audioChunks, {type: 'audio/webm'});
      stream.getTracks().forEach(function(t) { t.stop(); });
      enviarAudio(blob);
    };
    mediaRecorder.start();
    grabando = true;
    document.getElementById('micbtn').classList.add('grabando');
    document.getElementById('micbtn').title = 'Toca para detener';
  }).catch(function() {
    alert('No se pudo acceder al microfono. Permite el acceso en tu navegador.');
  });
}

function detenerGrabacion() {
  if (mediaRecorder && grabando) {
    mediaRecorder.stop();
    grabando = false;
    document.getElementById('micbtn').classList.remove('grabando');
    document.getElementById('micbtn').title = 'Nota de voz';
  }
}

function enviarAudio(blob) {
  var typing = addMsg('typing', 'Transcribiendo nota de voz...');
  var formData = new FormData();
  formData.append('audio', blob, 'nota_voz.webm');
  formData.append('session_id', sid);
  fetch('/audio', {method: 'POST', body: formData})
  .then(function(r) { return r.json(); })
  .then(function(d) {
    typing.remove();
    if (d.transcripcion) {
      var vm = document.createElement('div');
      vm.className = 'voice-msg';
      vm.innerHTML = '&#127908; ' + d.transcripcion;
      document.getElementById('msgs').appendChild(vm);
      scrollBottom();
    }
    procesarRespuesta(d);
  })
  .catch(function() {
    typing.remove();
    addMsg('bot', 'No pude procesar el audio. Intenta de nuevo.');
  });
}

document.getElementById('sbtn').onclick = enviar;
document.getElementById('resetbtn').onclick = function() {
  fetch('/reset', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({session_id: sid})});
  document.getElementById('msgs').innerHTML = '';
  addMsg('bot', 'Hola! Soy Maria de Taz. Estoy aqui para ayudarte con tu pedido. Que delicia quieres hoy?');
};
document.getElementById('micbtn').onclick = function() {
  if (!grabando) iniciarGrabacion(); else detenerGrabacion();
};
document.getElementById('inp').onkeypress = function(e) {
  if (e.key === 'Enter') enviar();
};

addMsg('bot', 'Hola! Soy Maria de Taz. Estoy aqui para ayudarte con tu pedido. Que delicia quieres hoy?');
</script>
</body>
</html>"""


def procesar_con_claude(session_id, mensaje_usuario):
    if session_id not in conversaciones:
        conversaciones[session_id] = []
    conversaciones[session_id].append({"role": "user", "content": mensaje_usuario})
    historial = conversaciones[session_id][-20:]
    headers = {
        "Authorization": "Bearer " + os.environ.get("OPENROUTER_API_KEY", ""),
        "Content-Type": "application/json",
        "HTTP-Referer": "https://tazmania-bot.com",
        "X-Title": "Maria Tazmania Bot"
    }
    data = {
        "model": "anthropic/claude-sonnet-4-5",
        "max_tokens": 1000,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + historial
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    result = response.json()
    texto = result["choices"][0]["message"]["content"]
    texto_guardado = texto.replace("##ENVIAR_CARTA##","").replace("##ENVIAR_QR##","")
    if "##PEDIDO_CONFIRMADO##" in texto_guardado:
        texto_guardado = texto_guardado[:texto_guardado.index("##PEDIDO_CONFIRMADO##")].strip()
    conversaciones[session_id].append({"role": "assistant", "content": texto_guardado})
    pedido = extraer_pedido_confirmado(texto)
    if pedido:
        pedido["telefono"] = session_id
        registrar_en_sheets(pedido)
    return texto


def construir_respuesta(mensaje_usuario, respuesta_claude):
    msg = mensaje_usuario.lower()
    enviar_carta = "##ENVIAR_CARTA##" in respuesta_claude or any(p in msg for p in PALABRAS_CARTA)
    enviar_qr = "##ENVIAR_QR##" in respuesta_claude or any(p in msg for p in PALABRAS_QR)
    texto = respuesta_claude.replace("##ENVIAR_CARTA##","").replace("##ENVIAR_QR##","").strip()
    if "##PEDIDO_CONFIRMADO##" in texto:
        texto = texto[:texto.index("##PEDIDO_CONFIRMADO##")].strip()
    return {"response": texto, "enviar_carta": enviar_carta, "enviar_qr": enviar_qr}


def get_google_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        return None
    try:
        creds_dict = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        print("Error Google: " + str(e))
        return None


def registrar_en_sheets(datos_pedido):
    try:
        gc = get_google_client()
        if not gc:
            return
        sheet = gc.open_by_key(os.environ.get("GOOGLE_SHEET_ID"))
        ws = sheet.sheet1
        if ws.row_count == 0 or ws.cell(1,1).value != "Fecha":
            ws.append_row(["Fecha","Hora","Nombre","Telefono","Direccion","Barrio","Productos","Total","Metodo Pago","Estado"])
        ahora = datetime.now()
        ws.append_row([ahora.strftime("%d/%m/%Y"),ahora.strftime("%H:%M"),datos_pedido.get("nombre",""),datos_pedido.get("telefono",""),datos_pedido.get("direccion",""),datos_pedido.get("barrio",""),datos_pedido.get("productos",""),datos_pedido.get("total",""),datos_pedido.get("pago",""),"PENDIENTE"])
        print("Pedido: " + str(datos_pedido.get("nombre")))
    except Exception as e:
        print("Error Sheets: " + str(e))


def extraer_pedido_confirmado(texto):
    if "##PEDIDO_CONFIRMADO##" in texto:
        try:
            inicio = texto.index("##PEDIDO_CONFIRMADO##") + len("##PEDIDO_CONFIRMADO##")
            fin = texto.index("##", inicio)
            return json.loads(texto[inicio:fin])
        except:
            pass
    return None


def enviar_imagen_whatsapp(numero, url, caption=""):
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("PHONE_NUMBER_ID")
    url_api = "https://graph.facebook.com/v18.0/" + phone_id + "/messages"
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    data = {"messaging_product":"whatsapp","to":numero,"type":"image","image":{"link":url,"caption":caption}}
    resp = requests.post(url_api, headers=headers, json=data)
    print("Img WA: " + str(resp.status_code))


def enviar_texto_whatsapp(numero, mensaje):
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("PHONE_NUMBER_ID")
    url = "https://graph.facebook.com/v18.0/" + phone_id + "/messages"
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    data = {"messaging_product":"whatsapp","to":numero,"type":"text","text":{"body":mensaje}}
    resp = requests.post(url, headers=headers, json=data)
    print("Txt WA: " + str(resp.status_code))


def procesar_y_enviar_whatsapp(numero, mensaje_usuario, texto_respuesta):
    msg = mensaje_usuario.lower()
    enviar_carta = "##ENVIAR_CARTA##" in texto_respuesta or any(p in msg for p in PALABRAS_CARTA)
    enviar_qr = "##ENVIAR_QR##" in texto_respuesta or any(p in msg for p in PALABRAS_QR)
    texto = texto_respuesta.replace("##ENVIAR_CARTA##","").replace("##ENVIAR_QR##","").strip()
    if "##PEDIDO_CONFIRMADO##" in texto:
        texto = texto[:texto.index("##PEDIDO_CONFIRMADO##")].strip()
    if texto:
        enviar_texto_whatsapp(numero, texto)
    if enviar_carta:
        enviar_imagen_whatsapp(numero, CARTA_1_URL, "Carta Taz - Hamburguesas y Perros")
        enviar_imagen_whatsapp(numero, CARTA_2_URL, "Carta Taz - Asados, Delicias y Bebidas")
    if enviar_qr:
        enviar_imagen_whatsapp(numero, QR_BBVA_URL, "QR pago BBVA - Chef Fast")


def transcribir_audio_bytes(audio_bytes, extension="webm"):
    try:
        from openai import OpenAI
        oc = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        with tempfile.NamedTemporaryFile(suffix="." + extension, delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        with open(temp_path, "rb") as af:
            transcript = oc.audio.transcriptions.create(model="whisper-1", file=af, language="es")
        os.unlink(temp_path)
        return transcript.text
    except Exception as e:
        print("Audio error: " + str(e))
        return None


def transcribir_audio_whatsapp(audio_id):
    try:
        token = os.environ.get("WHATSAPP_TOKEN")
        headers = {"Authorization": "Bearer " + token}
        url_info = requests.get("https://graph.facebook.com/v18.0/" + audio_id, headers=headers).json()
        audio_url = url_info.get("url")
        audio_resp = requests.get(audio_url, headers=headers)
        return transcribir_audio_bytes(audio_resp.content, "ogg")
    except Exception as e:
        print("Audio WA error: " + str(e))
        return None


@app.route("/", methods=["GET"])
def chat_web():
    return render_template_string(HTML_CHAT)


@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.get_json()
    mensaje = data.get("message", "")
    session_id = data.get("session_id", "web_user")
    respuesta = procesar_con_claude(session_id, mensaje)
    return jsonify(construir_respuesta(mensaje, respuesta))


@app.route("/audio", methods=["POST"])
def audio_api():
    session_id = request.form.get("session_id", "web_user")
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "no audio"}), 400
    audio_bytes = audio_file.read()
    transcripcion = transcribir_audio_bytes(audio_bytes, "webm")
    if not transcripcion:
        return jsonify({"response": "No pude entender el audio. Puedes escribirlo?", "enviar_carta": False, "enviar_qr": False})
    respuesta = procesar_con_claude(session_id, transcripcion)
    resultado = construir_respuesta(transcripcion, respuesta)
    resultado["transcripcion"] = transcripcion
    return jsonify(resultado)


@app.route("/reset", methods=["POST"])
def reset_chat():
    data = request.get_json()
    session_id = data.get("session_id", "web_user")
    if session_id in conversaciones:
        del conversaciones[session_id]
    return jsonify({"status": "ok"})


@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == os.environ.get("VERIFY_TOKEN"):
        return challenge, 200
    return "Token incorrecto", 403


@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    try:
        data = request.get_json()
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return jsonify({"status": "ok"}), 200
        msg = messages[0]
        numero = msg.get("from")
        tipo = msg.get("type")
        if tipo == "text":
            texto_cliente = msg["text"]["body"]
        elif tipo == "audio":
            texto_cliente = transcribir_audio_whatsapp(msg["audio"]["id"])
            if not texto_cliente:
                enviar_texto_whatsapp(numero, "No pude escuchar bien. Puedes escribirlo?")
                return jsonify({"status": "ok"}), 200
        elif tipo == "image":
            texto_cliente = "[El cliente envio una imagen, probablemente comprobante de pago]"
        else:
            enviar_texto_whatsapp(numero, "Solo entiendo texto, notas de voz e imagenes.")
            return jsonify({"status": "ok"}), 200
        respuesta = procesar_con_claude(numero, texto_cliente)
        procesar_y_enviar_whatsapp(numero, texto_cliente, respuesta)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print("Error webhook: " + str(e))
        return jsonify({"status": "error", "detail": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
