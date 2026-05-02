"""
================================================================
AGENTE MARIA - TAZMANIA
Servidor Flask con interfaz web + WhatsApp + Google Sheets + Imagenes
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

# URLs publicas de las imagenes en GitHub
CARTA_1_URL = "https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%201.jpeg"
CARTA_2_URL = "https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%202.jpeg"
QR_BBVA_URL = "https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/QR_BBVA.jpeg"

SYSTEM_PROMPT = """Eres Maria, la asistente virtual de Taz, el restaurante de comidas rapidas mas sabroso de Buenaventura. Eres amable, rapida, cercana y hablas con el tono calido y familiar del Pacifico colombiano. Tu unico trabajo es tomar pedidos de domicilio de manera eficiente, verificar zonas de entrega y registrar cada pedido correctamente.

SALUDO INICIAL: Responde SIEMPRE asi al primer mensaje:
Hola! Soy Maria de Taz. Estoy aqui para ayudarte con tu pedido. Que delicia quieres hoy?

HORARIO: Abrimos TODOS LOS DIAS de 4:00 PM a 12:00 AM.
Fuera de horario di: Gracias por escribir a Taz! A esta hora estamos descansando para atenderte mejor. Volvemos a las 4:00 PM.

MENU COMPLETO:
V/U = Valor Unitario | COM = Combo con papa a la francesa y gaseosa/jugo/agua

HAMBURGUESAS:
- TAZ CON MUCHO QUESO: V/U $29.900 | COM $41.100
- TAZ DOBLE DE RES CON MUCHO QUESO: V/U $35.600 | COM $46.800
- TAZ DE POLLO CON MUCHO QUESO: V/U $29.900 | COM $41.100
- TAZ DOBLE DE POLLO CON MUCHO QUESO: V/U $35.600 | COM $46.800
- TAZ MIXTA CON MUCHO QUESO: V/U $35.600 | COM $46.800
- TAZ CUARTO DE LIBRA CARNE ANGUS: V/U $24.500 | COM $36.000
- TAZ CUARTO DE LIBRA POLLO: V/U $24.500 | COM $36.000
- TAZ MEDIA LIBRA CARNE ANGUS: V/U $35.700 | COM $47.000
- TAZ LIBRA CARNE ANGUS: V/U $63.000 | COM $74.600

PERROS:
- PERRO TAZ CON MUCHO QUESO: V/U $24.700 | COM $34.700
- PERRO TAZ JUNIOR: V/U $20.900 | COM $30.900
- PERRO TAZ RANCHERO: V/U $25.400 | COM $35.400

ASADOS A LA PARRILLA:
- FILETE DE POLLO: V/U $33.500
- FILETE DE POLLO GRATINADO: V/U $36.600
- FILETE DE POLLO LIMON-PIMIENTA: V/U $34.900
- COSTILLA AHUMADA CON SALSA BBQ: V/U $45.800
- MEDIA COSTILLA AHUMADA CON SALSA BBQ: V/U $34.600
- ALITAS DE POLLO X 6 (Miel Mostaza/BBQ/Limon Pimienta): V/U $30.800
- ALITAS DE POLLO X 12 (Miel Mostaza/BBQ/Limon Pimienta): V/U $55.800

OTRAS DELICIAS:
- SALCHIPAPA: Personal $19.600 | Grande $27.400
- SALCHIQUESO: Personal $26.300 | Grande $33.500
- SALCHIRANCHERA: $22.300
- SALCHIRANCHERA CON QUESO: $29.000
- SALCHICOSTILLA: $25.800
- SALCHIPOLLO: $22.300

ADICIONALES:
- Trozos de pollo 120 grs: $8.400
- Salchicha ranchera grande: $6.500
- Costilla 150 grs bbq: $9.900
- Tocineta 3 unidades: $4.900
- Queso americano 1 loncha: $2.800
- Queso fundido 150 grs: $8.000
- Ensalada 1 porcion: $3.400
- Cebolla grille: $2.800
- Salsas: $1.700
- Papa a la francesa 165 gr: $8.600

BEBIDAS:
- Gaseosa 2.5 lts: $13.400
- Gaseosa 500 ml: $4.500
- Jugos hit 500 ml: $4.800
- Mr. Tea: $4.700
- Agua en botella 600 ml: $3.000
- Cerveza: $5.000

ZONAS DE DOMICILIO:
ACCESO COMPLETO: Palo Seco Cra 22, Iglesia Cra 21, El Jorge Cra 20 hasta Licores Hebert, Inmaculada, Todo Jorge hasta Casa Blanca, La Abeja, Km 5 Hotel TC Mar, Calle 7 Cancha Sintetica, Miramar, San Luis, Juan 23 Calle La Gaitan, Berberena, Rusbell, Calle Colombia, Calle Las Flores, Chuchofong, Porvenir, El Jardin, El Campin, Eucaristico, 1 de Julio, Rockefeller, Modelo, Maria Eugenia, Bellavista hasta el Topacio, Olimpico hasta CDI, El Cristal, Transformacion hasta anillo vial, Cascajal hasta granero Don Bena, Independencia.

ACCESO PARCIAL solo autopista: 12 de Abril, 6 de Enero, El Dorado Calle 4, Camilo Torres hasta drogueria Los Pinos, Ley 69, El Cambio, Alfonso Lopez, Nuevo Horizonte, El Caldas, El Uribe, La Virgen, Cabal Pombo, La Campina hasta el billar, La Libertad, La Frontera, La Dignidad Calle 4, Floresta hasta panaderia Trocitos Pan, Vista Hermosa, Villa Linda.

RESTRICCION HORARIO: Hotel Linea Buenaventura y Via Alterna solo hasta las 7:00 PM.

ENVIO DE CARTA E IMAGENES:
- Si el cliente pide ver el menu, la carta o los productos, responde con el texto: ##ENVIAR_CARTA##
- Si el cliente confirma que pagara por transferencia o QR, responde con: ##ENVIAR_QR##
- Puedes incluir estos marcadores junto con texto normal. Ejemplo: "Aqui te envio nuestra carta! ##ENVIAR_CARTA## Dime que se te antoja!"

FLUJO DEL PEDIDO:
1. Saluda y pregunta que quiere
2. Si pide ver el menu envia la carta con ##ENVIAR_CARTA##
3. Confirma productos (combo o unitario, bebida, salsa, adicionales)
4. Pide nombre y direccion
5. Verifica zona
6. Presenta resumen con total correcto
7. Tiempos: Entre semana 30-45 min, Fines de semana 50-60 min
8. Metodo de pago: Efectivo, Datafono, o Transferencia QR BBVA Chef Fast llave 0091626861
9. Si elige transferencia envia QR con ##ENVIAR_QR## y pide comprobante
10. Confirma pedido

Al confirmar pedido completamente incluye al final:
##PEDIDO_CONFIRMADO##{"nombre":"NOMBRE","telefono":"TELEFONO","direccion":"DIRECCION","barrio":"BARRIO","productos":"PRODUCTOS","total":"TOTAL","pago":"METODO"}##

CAMBIOS: Di que el pedido esta en preparacion y pregunta que desea modificar.
QUEJAS: Transfiere al 316 721 9321.
REGLAS: No inventes productos ni precios. Calcula totales correctamente. Solo habla del restaurante."""


HTML_CHAT = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Maria - Taz Bot Pruebas</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Arial, sans-serif; background: #ECE5DD; height: 100vh; display: flex; flex-direction: column; }
.header { background: #075E54; color: white; padding: 12px 20px; display: flex; align-items: center; gap: 12px; }
.avatar { width: 42px; height: 42px; background: #25D366; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 22px; }
.hinfo h2 { font-size: 16px; }
.hinfo p { font-size: 12px; color: #ccc; }
.badge { background: #FF6B35; color: white; font-size: 10px; padding: 2px 8px; border-radius: 10px; margin-left: 6px; }
.rbtn { margin-left: auto; background: rgba(255,255,255,0.2); color: white; border: none; border-radius: 15px; padding: 6px 14px; font-size: 12px; cursor: pointer; }
.msgs { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 6px; }
.msg { max-width: 75%; padding: 8px 12px; border-radius: 8px; font-size: 14px; line-height: 1.5; word-wrap: break-word; white-space: pre-wrap; }
.bot { background: white; align-self: flex-start; border-top-left-radius: 0; }
.user { background: #DCF8C6; align-self: flex-end; border-top-right-radius: 0; }
.typing { background: white; align-self: flex-start; color: #999; font-style: italic; }
.img-msg { background: white; align-self: flex-start; border-top-left-radius: 0; padding: 4px; border-radius: 8px; max-width: 75%; }
.img-msg img { max-width: 100%; border-radius: 6px; display: block; }
.iarea { background: #F0F0F0; padding: 10px 15px; display: flex; gap: 10px; align-items: center; }
#inp { flex: 1; padding: 10px 15px; border-radius: 25px; border: none; outline: none; font-size: 14px; }
#sbtn { background: #075E54; color: white; border: none; border-radius: 50%; width: 44px; height: 44px; cursor: pointer; font-size: 18px; }
#sbtn:disabled { background: #ccc; }
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
  <input type="text" id="inp" placeholder="Escribe como si fueras un cliente...">
  <button id="sbtn">&#10148;</button>
</div>
<script>
var sid = 'prueba_' + Math.random().toString(36).substr(2, 9);

var CARTA_1 = 'https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%201.jpeg';
var CARTA_2 = 'https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/CARTA%202.jpeg';
var QR_BBVA = 'https://raw.githubusercontent.com/herdora24-web/tazmania-bot/main/QR_BBVA.jpeg';

function addMsg(tipo, txt) {
  var m = document.getElementById('msgs');
  var d = document.createElement('div');
  d.className = 'msg ' + tipo;
  d.textContent = txt;
  m.appendChild(d);
  m.scrollTop = m.scrollHeight;
  return d;
}

function addImg(url) {
  var m = document.getElementById('msgs');
  var d = document.createElement('div');
  d.className = 'img-msg';
  var img = document.createElement('img');
  img.src = url;
  img.alt = 'Imagen';
  d.appendChild(img);
  m.appendChild(d);
  m.scrollTop = m.scrollHeight;
}

function procesarRespuesta(texto) {
  var enviarCarta = texto.indexOf('##ENVIAR_CARTA##') !== -1;
  var enviarQR = texto.indexOf('##ENVIAR_QR##') !== -1;
  var textoLimpio = texto.replace(/##ENVIAR_CARTA##/g, '').replace(/##ENVIAR_QR##/g, '').trim();
  if (textoLimpio) addMsg('bot', textoLimpio);
  if (enviarCarta) {
    addImg(CARTA_1);
    addImg(CARTA_2);
  }
  if (enviarQR) {
    addImg(QR_BBVA);
  }
}

function enviar() {
  var inp = document.getElementById('inp');
  var btn = document.getElementById('sbtn');
  var txt = inp.value.trim();
  if (!txt) return;
  inp.value = '';
  btn.disabled = true;
  addMsg('user', txt);
  var typing = addMsg('typing', 'Maria esta escribiendo...');
  fetch('/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: txt, session_id: sid})
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    typing.remove();
    if (d.response) addMsg('bot', d.response);
    if (d.enviar_carta) { addImg(CARTA_1); addImg(CARTA_2); }
    if (d.enviar_qr) { addImg(QR_BBVA); }
    btn.disabled = false;
    inp.focus();
  })
  .catch(function() {
    typing.remove();
    addMsg('bot', 'Error de conexion. Intenta de nuevo.');
    btn.disabled = false;
  });
}

function reset() {
  fetch('/reset', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({session_id: sid})
  });
  document.getElementById('msgs').innerHTML = '';
  addMsg('bot', 'Hola! Soy Maria de Taz. Estoy aqui para ayudarte con tu pedido. Que delicia quieres hoy?');
}

document.getElementById('sbtn').onclick = enviar;
document.getElementById('resetbtn').onclick = reset;
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
    texto_limpio = limpiar_respuesta(texto)
    conversaciones[session_id].append({"role": "assistant", "content": texto_limpio})
    pedido = extraer_pedido_confirmado(texto)
    if pedido:
        pedido["telefono"] = session_id
        registrar_en_sheets(pedido)
    return texto


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
        if ws.row_count == 0 or ws.cell(1, 1).value != "Fecha":
            ws.append_row(["Fecha","Hora","Nombre","Telefono","Direccion","Barrio","Productos","Total","Metodo Pago","Estado"])
        ahora = datetime.now()
        ws.append_row([
            ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M"),
            datos_pedido.get("nombre",""), datos_pedido.get("telefono",""),
            datos_pedido.get("direccion",""), datos_pedido.get("barrio",""),
            datos_pedido.get("productos",""), datos_pedido.get("total",""),
            datos_pedido.get("pago",""), "PENDIENTE"
        ])
        print("Pedido registrado: " + str(datos_pedido.get("nombre")))
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


def limpiar_respuesta(texto):
    if "##PEDIDO_CONFIRMADO##" in texto:
        texto = texto[:texto.index("##PEDIDO_CONFIRMADO##")].strip()
    return texto


def enviar_imagen_whatsapp(numero, url, caption=""):
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("PHONE_NUMBER_ID")
    url_api = "https://graph.facebook.com/v18.0/" + phone_id + "/messages"
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "image",
        "image": {"link": url, "caption": caption}
    }
    resp = requests.post(url_api, headers=headers, json=data)
    print("Imagen WhatsApp: " + str(resp.status_code))


def enviar_texto_whatsapp(numero, mensaje):
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("PHONE_NUMBER_ID")
    url = "https://graph.facebook.com/v18.0/" + phone_id + "/messages"
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": mensaje}}
    resp = requests.post(url, headers=headers, json=data)
    print("Texto WhatsApp: " + str(resp.status_code))


def procesar_y_enviar_whatsapp(numero, texto_respuesta):
    enviar_carta = "##ENVIAR_CARTA##" in texto_respuesta
    enviar_qr = "##ENVIAR_QR##" in texto_respuesta
    texto_limpio = limpiar_respuesta(
        texto_respuesta.replace("##ENVIAR_CARTA##", "").replace("##ENVIAR_QR##", "").strip()
    )
    if texto_limpio:
        enviar_texto_whatsapp(numero, texto_limpio)
    if enviar_carta:
        enviar_imagen_whatsapp(numero, CARTA_1_URL, "Carta Taz - Hamburguesas y Perros")
        enviar_imagen_whatsapp(numero, CARTA_2_URL, "Carta Taz - Asados, Delicias y Bebidas")
    if enviar_qr:
        enviar_imagen_whatsapp(numero, QR_BBVA_URL, "QR de pago - BBVA Chef Fast")


def transcribir_audio(audio_id):
    try:
        token = os.environ.get("WHATSAPP_TOKEN")
        headers = {"Authorization": "Bearer " + token}
        url_info = requests.get("https://graph.facebook.com/v18.0/" + audio_id, headers=headers).json()
        audio_url = url_info.get("url")
        audio_resp = requests.get(audio_url, headers=headers)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio_resp.content)
            temp_path = f.name
        from openai import OpenAI
        oc = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        with open(temp_path, "rb") as af:
            transcript = oc.audio.transcriptions.create(model="whisper-1", file=af, language="es")
        os.unlink(temp_path)
        return transcript.text
    except Exception as e:
        print("Audio error: " + str(e))
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
    msg_lower = mensaje.lower()
    palabras_carta = ["menu", "carta", "que tienen", "que hay", "que venden", "productos", "ver todo"]
    palabras_qr = ["transferencia", "qr", "bbva", "pagar con", "transferir"]
    enviar_carta = "##ENVIAR_CARTA##" in respuesta or any(p in msg_lower for p in palabras_carta)
    enviar_qr = "##ENVIAR_QR##" in respuesta or any(p in msg_lower for p in palabras_qr)
    texto_limpio = respuesta.replace("##ENVIAR_CARTA##", "").replace("##ENVIAR_QR##", "").strip()
    if "##PEDIDO_CONFIRMADO##" in texto_limpio:
        texto_limpio = texto_limpio[:texto_limpio.index("##PEDIDO_CONFIRMADO##")].strip()
    return jsonify({"response": texto_limpio, "enviar_carta": enviar_carta, "enviar_qr": enviar_qr})


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
            texto_cliente = transcribir_audio(msg["audio"]["id"])
            if not texto_cliente:
                enviar_texto_whatsapp(numero, "No pude escuchar bien. Puedes escribirlo?")
                return jsonify({"status": "ok"}), 200
        elif tipo == "image":
            texto_cliente = "[El cliente envio una imagen, probablemente comprobante de pago]"
        else:
            enviar_texto_whatsapp(numero, "Solo puedo leer mensajes de texto, notas de voz e imagenes.")
            return jsonify({"status": "ok"}), 200
        respuesta = procesar_con_claude(numero, texto_cliente)
        procesar_y_enviar_whatsapp(numero, respuesta)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print("Error: " + str(e))
        return jsonify({"status": "error", "detail": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
