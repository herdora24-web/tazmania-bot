"""
================================================================
AGENTE MARIA - TAZMANIA
Servidor Flask con interfaz web de pruebas + WhatsApp + Google Sheets
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

SYSTEM_PROMPT = """Eres Maria, la asistente virtual de Taz 🍔, el restaurante de comidas rápidas más sabroso de Buenaventura. Eres amable, rápida, cercana y hablas con el tono cálido y familiar del Pacífico colombiano. Tu único trabajo es tomar pedidos de domicilio de manera eficiente, verificar zonas de entrega y registrar cada pedido correctamente.

SALUDO INICIAL: Responde SIEMPRE así al primer mensaje:
"¡Hola! Soy Maria de Taz 🍔
Estoy aquí para ayudarte con tu pedido.
¿Qué delicia quieres hoy? 😄"

HORARIO: Abrimos TODOS LOS DÍAS de 4:00 PM a 12:00 AM.
Fuera de horario: "¡Gracias por escribir a Taz! 🍔 A esta hora estamos descansando para atenderte mejor. Volvemos a las 4:00 PM, ¡te esperamos con todo el sabor!"

MENÚ COMPLETO:
V/U = Valor Unitario | COM = Combo (papa a la francesa + gaseosa 500ml / jugo hit / Mr. Tea / agua)

HAMBURGUESAS:
- TAZ CON MUCHO QUESO: V/U $29.900 | COM $41.100
- TAZ DOBLE DE RES CON MUCHO QUESO: V/U $35.600 | COM $46.800
- TAZ DE POLLO CON MUCHO QUESO: V/U $29.900 | COM $41.100
- TAZ DOBLE DE POLLO CON MUCHO QUESO: V/U $35.600 | COM $46.800
- TAZ MIXTA CON MUCHO QUESO: V/U $35.600 | COM $46.800
- TAZ CUARTO DE LIBRA (CARNE ANGUS): V/U $24.500 | COM $36.000
- TAZ CUARTO DE LIBRA (POLLO): V/U $24.500 | COM $36.000
- TAZ MEDIA LIBRA (CARNE ANGUS): V/U $35.700 | COM $47.000
- TAZ LIBRA (CARNE ANGUS): V/U $63.000 | COM $74.600

PERROS:
- PERRO TAZ CON MUCHO QUESO: V/U $24.700 | COM $34.700
- PERRO TAZ JUNIOR: V/U $20.900 | COM $30.900
- PERRO TAZ RANCHERO: V/U $25.400 | COM $35.400

ASADOS A LA PARRILLA:
- FILETE DE POLLO: V/U $33.500
- FILETE DE POLLO GRATINADO: V/U $36.600
- FILETE DE POLLO LIMÓN-PIMIENTA: V/U $34.900
- COSTILLA AHUMADA CON SALSA BBQ: V/U $45.800
- 1/2 COSTILLA AHUMADA CON SALSA BBQ: V/U $34.600
- ALITAS DE POLLO X 6 (Miel Mostaza/BBQ/Limón Pimienta): V/U $30.800
- ALITAS DE POLLO X 12 (Miel Mostaza/BBQ/Limón Pimienta): V/U $55.800

OTRAS DELICIAS:
- SALCHIPAPA: Personal $19.600 | Grande $27.400
- SALCHIQUESO: Personal $26.300 | Grande $33.500
- SALCHIRANCHERA: $22.300
- SALCHIRANCHERA CON QUESO: $29.000
- SALCHICOSTILLA: $25.800
- SALCHIPOLLO: $22.300

ADICIONALES:
- Trozos de pollo (120 grs): $8.400
- Salchicha ranchera grande: $6.500
- Costilla 150 grs bbq: $9.900
- Tocineta (3 unidades): $4.900
- Queso americano (1 loncha): $2.800
- Queso fundido 150 grs: $8.000
- Ensalada (1 porción): $3.400
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
ACCESO COMPLETO: Palo Seco (Cra 22), Iglesia (Cra 21), El Jorge (Cra 20 hasta Licores Hebert), Inmaculada, Todo Jorge (hasta Casa Blanca), La Abeja, Km 5 (Hotel TC Mar), Calle 7 (Cancha Sintética), Miramar, San Luis, Juan 23 (Calle La Gaitán), Berberena, Rusbell, Calle Colombia, Calle Las Flores, Chuchofong, Porvenir, El Jardín, El Campín, Eucarístico, 1° de Julio, Rockefeller, Modelo, María Eugenia, Bellavista (hasta el Topacio), Olímpico (hasta CDI), El Cristal, Transformación (hasta anillo vial), Cascajal (hasta granero Don Bena), Independencia.

ACCESO PARCIAL (solo autopista/principal): 12 de Abril, 6 de Enero, El Dorado (Calle 4), Camilo Torres (hasta droguería Los Pinos), Ley 69, El Cambio, Alfonso López, Nuevo Horizonte, El Caldas, El Uribe, La Virgen, Cabal Pombo, La Campiña (hasta el billar), La Libertad, La Frontera, La Dignidad (Calle 4), Floresta (hasta panadería Trocitos Pan), Vista Hermosa, Villa Linda.

RESTRICCIÓN HORARIO: Hotel Línea Buenaventura y Vía Alterna solo hasta las 7:00 PM.

FLUJO DEL PEDIDO:
1. Saluda y pregunta qué quiere
2. Confirma productos (combo o unitario, bebida, salsa, adicionales)
3. Pide nombre y dirección
4. Verifica zona
5. Presenta resumen con total correcto
6. Tiempos: Entre semana 30-45 min | Fines de semana 50-60 min
7. Método de pago: Efectivo / Datáfono / QR BBVA Chef Fast llave: 0091626861
8. Si transfiere: pide comprobante
9. Confirma pedido

Al confirmar pedido completamente incluye:
##PEDIDO_CONFIRMADO##{"nombre":"[nombre]","telefono":"[numero]","direccion":"[direccion]","barrio":"[barrio]","productos":"[lista]","total":"[total]","pago":"[metodo]"}##

CAMBIOS: "¡Hola! En este momento tu pedido ya está en preparación 👨‍🍳 Con mucho gusto vamos a revisar si aún alcanzamos a hacer el cambio. ¿Cuéntame qué deseas modificar?"

QUEJAS: "Entiendo tu situación y quiero que quedes 100% satisfecho(a). 📞 Escríbele a nuestra administradora: 316 721 9321"

REGLAS: No inventes productos/precios. Calcula totales correctamente. Solo habla del restaurante."""

HTML_CHAT = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Maria - Taz Bot</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;background:#ECE5DD;height:100vh;display:flex;flex-direction:column}
.header{background:#075E54;color:white;padding:12px 20px;display:flex;align-items:center;gap:12px}
.avatar{width:42px;height:42px;background:#25D366;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:22px}
.header-info h2{font-size:16px}
.header-info p{font-size:12px;color:#ccc}
.badge{background:#FF6B35;color:white;font-size:10px;padding:2px 8px;border-radius:10px;margin-left:6px}
.reset-btn{margin-left:auto;background:rgba(255,255,255,0.2);color:white;border:none;border-radius:15px;padding:6px 14px;font-size:12px;cursor:pointer}
.reset-btn:hover{background:rgba(255,255,255,0.3)}
.messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:6px}
.msg{max-width:75%;padding:8px 12px;border-radius:8px;font-size:14px;line-height:1.5;word-wrap:break-word;white-space:pre-wrap}
.bot{background:white;align-self:flex-start;border-top-left-radius:0}
.user{background:#DCF8C6;align-self:flex-end;border-top-right-radius:0}
.typing{background:white;align-self:flex-start;color:#999;font-style:italic}
.input-area{background:#F0F0F0;padding:10px 15px;display:flex;gap:10px;align-items:center}
#userInput{flex:1;padding:10px 15px;border-radius:25px;border:none;outline:none;font-size:14px}
#sendBtn{background:#075E54;color:white;border:none;border-radius:50%;width:44px;height:44px;cursor:pointer;font-size:18px}
#sendBtn:hover{background:#128C7E}
#sendBtn:disabled{background:#ccc}
</style>
</head>
<body>
<div class="header">
  <div class="avatar">🍔</div>
  <div class="header-info">
    <h2>Maria <span class="badge">MODO PRUEBAS</span></h2>
    <p>Taz Comidas Rápidas · Buenaventura</p>
  </div>
  <button class="reset-btn" onclick="resetChat()">🔄 Nueva conv.</button>
</div>
<div class="messages" id="messages"></div>
<div class="input-area">
  <input type="text" id="userInput" placeholder="Escribe como si fueras un cliente..." onkeypress="if(event.key==='Enter')sendMessage()">
  <button id="sendBtn" onclick="sendMessage()">➤</button>
</div>
<script>
const sid='prueba_'+Math.random().toString(36).substr(2,9);
window.onload=()=>addMsg('bot','¡Hola! Soy Maria de Taz 🍔\nEstoy aquí para ayudarte con tu pedido.\n¿Qué delicia quieres hoy? 😄');
function addMsg(t,txt){
  const m=document.getElementById('messages');
  const d=document.createElement('div');
  d.className='msg '+t;
  d.textContent=txt;
  m.appendChild(d);
  m.scrollTop=m.scrollHeight;
  return d;
}
async function sendMessage(){
  const inp=document.getElementById('userInput');
  const btn=document.getElementById('sendBtn');
  const txt=inp.value.trim();
  if(!txt)return;
  inp.value='';
  btn.disabled=true;
  addMsg('user',txt);
  const typing=addMsg('typing','Maria está escribiendo...');
  try{
    const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:txt,session_id:sid})});
    const d=await r.json();
    typing.remove();
    addMsg('bot',d.response);
  }catch(e){
    typing.remove();
    addMsg('bot','Error de conexión. Intenta de nuevo.');
  }
  btn.disabled=false;
  inp.focus();
}
function resetChat(){
  fetch('/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sid})});
  document.getElementById('messages').innerHTML='';
  addMsg('bot','¡Hola! Soy Maria de Taz 🍔\nEstoy aquí para ayudarte con tu pedido.\n¿Qué delicia quieres hoy? 😄');
}
</script>
</body>
</html>"""


def procesar_con_claude(session_id: str, mensaje_usuario: str) -> str:
    if session_id not in conversaciones:
        conversaciones[session_id] = []
    conversaciones[session_id].append({"role": "user", "content": mensaje_usuario})
    historial = conversaciones[session_id][-20:]
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
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
    return texto_limpio


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
        print(f"❌ Error Google: {e}")
        return None


def registrar_en_sheets(datos_pedido: dict):
    try:
        gc = get_google_client()
        if not gc:
            return
        sheet = gc.open_by_key(os.environ.get("GOOGLE_SHEET_ID"))
        ws = sheet.sheet1
        if ws.row_count == 0 or ws.cell(1, 1).value != "Fecha":
            ws.append_row(["Fecha","Hora","Nombre","Teléfono","Dirección","Barrio","Productos","Total","Método Pago","Estado"])
        ahora = datetime.now()
        ws.append_row([ahora.strftime("%d/%m/%Y"),ahora.strftime("%H:%M"),datos_pedido.get("nombre",""),datos_pedido.get("telefono",""),datos_pedido.get("direccion",""),datos_pedido.get("barrio",""),datos_pedido.get("productos",""),datos_pedido.get("total",""),datos_pedido.get("pago",""),"PENDIENTE"])
        print(f"✅ Pedido: {datos_pedido.get('nombre')}")
    except Exception as e:
        print(f"❌ Sheets: {e}")


def extraer_pedido_confirmado(texto: str):
    if "##PEDIDO_CONFIRMADO##" in texto:
        try:
            inicio = texto.index("##PEDIDO_CONFIRMADO##") + len("##PEDIDO_CONFIRMADO##")
            fin = texto.index("##", inicio)
            return json.loads(texto[inicio:fin])
        except:
            pass
    return None


def limpiar_respuesta(texto: str) -> str:
    if "##PEDIDO_CONFIRMADO##" in texto:
        texto = texto[:texto.index("##PEDIDO_CONFIRMADO##")].strip()
    return texto


def enviar_whatsapp(numero: str, mensaje: str):
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("PHONE_NUMBER_ID")
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": mensaje}}
    resp = requests.post(url, headers=headers, json=data)
    print(f"WhatsApp → {resp.status_code}")


def transcribir_audio(audio_id: str):
    try:
        token = os.environ.get("WHATSAPP_TOKEN")
        headers = {"Authorization": f"Bearer {token}"}
        url_info = requests.get(f"https://graph.facebook.com/v18.0/{audio_id}", headers=headers).json()
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
        print(f"Audio error: {e}")
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
    return jsonify({"response": respuesta})


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
                enviar_whatsapp(numero, "No pude escuchar bien 😅 ¿Puedes escribirlo?")
                return jsonify({"status": "ok"}), 200
        elif tipo == "image":
            texto_cliente = "[El cliente envió una imagen, probablemente comprobante de pago]"
        else:
            enviar_whatsapp(numero, "Solo puedo leer mensajes de texto, notas de voz e imágenes 😊")
            return jsonify({"status": "ok"}), 200
        respuesta = procesar_con_claude(numero, texto_cliente)
        enviar_whatsapp(numero, respuesta)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"status": "error", "detail": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
