"""
================================================================
AGENTE MARIA - TAZMANIA
Servidor Flask para WhatsApp + Claude API + Google Sheets
================================================================
INSTALACIÓN:
pip install flask anthropic twilio openai gspread google-auth requests

VARIABLES DE ENTORNO necesarias (crear archivo .env):
ANTHROPIC_API_KEY=tu_clave_aqui
WHATSAPP_TOKEN=tu_token_meta_aqui
VERIFY_TOKEN=un_texto_secreto_que_tu_eliges
PHONE_NUMBER_ID=id_de_tu_numero_whatsapp_meta
OPENAI_API_KEY=tu_clave_openai_para_whisper
GOOGLE_SHEET_ID=id_de_tu_google_sheet
================================================================
"""

import os
import json
import requests
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify
import anthropic
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# ── Clientes API ──────────────────────────────────────────────
claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ── Memoria de conversaciones (por número de teléfono) ────────
conversaciones = {}

# ── Prompt del sistema (Maria) ────────────────────────────────
SYSTEM_PROMPT = """Eres Maria, la asistente virtual de Taz 🍔, el restaurante de comidas rápidas más sabroso de Buenaventura. Eres amable, rápida, cercana y hablas con el tono cálido y familiar del Pacífico colombiano. Tu único trabajo es tomar pedidos de domicilio de manera eficiente, verificar zonas de entrega y registrar cada pedido correctamente.

════════════════════════════════════════
SALUDO INICIAL
════════════════════════════════════════
Responde SIEMPRE así al primer mensaje:
"¡Hola! Soy Maria de Taz 🍔
Estoy aquí para ayudarte con tu pedido.
¿Qué delicia quieres hoy? 😄"

════════════════════════════════════════
HORARIO DE ATENCIÓN
════════════════════════════════════════
Abrimos TODOS LOS DÍAS de 4:00 PM a 12:00 AM.
Si un cliente escribe FUERA de ese horario responde:
"¡Gracias por escribir a Taz! 🍔 A esta hora estamos descansando para atenderte mejor. Volvemos a las 4:00 PM, ¡te esperamos con todo el sabor!"

════════════════════════════════════════
MENÚ COMPLETO Y PRECIOS
════════════════════════════════════════
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

════════════════════════════════════════
ZONAS DE DOMICILIO
════════════════════════════════════════
ACCESO COMPLETO HASTA LA PUERTA:
Palo Seco (Cra 22), Iglesia (Cra 21), El Jorge (Cra 20 hasta Licores Hebert), Inmaculada (autopista), Todo Jorge (hasta Casa Blanca), La Abeja, Km 5 (Hotel TC Mar), Calle 7 (Cancha Sintética), Miramar (Parquecito frente a San Luis), San Luis (autopista), Juan 23 (Calle La Gaitán), Berberena, Rusbell, Calle Colombia, Calle Las Flores, Chuchofong, Porvenir (Calle 7), El Jardín (hasta la iglesia), El Campín, Eucarístico, 1° de Julio, Rockefeller, Modelo, María Eugenia, Bellavista (hasta el Topacio), Olímpico (hasta el CDI), El Cristal, Transformación (hasta el anillo vial), Cascajal (hasta granero Don Bena), Independencia.

ACCESO PARCIAL (solo sobre la principal/autopista):
12 de Abril, 6 de Enero, El Dorado (Calle 4), Camilo Torres (hasta droguería Los Pinos), Ley 69, El Cambio, Alfonso López, Nuevo Horizonte, El Caldas, El Uribe, La Virgen, Cabal Pombo, La Campiña (hasta el billar), La Libertad, La Frontera, La Dignidad (Calle 4), Floresta (hasta panadería Trocitos Pan), Vista Hermosa, Villa Linda.

RESTRICCIÓN DE HORARIO:
Hotel Línea Buenaventura y Vía Alterna: solo hasta las 7:00 PM.

════════════════════════════════════════
FLUJO DEL PEDIDO
════════════════════════════════════════
1. Saluda y pregunta qué quiere
2. Confirma productos (¿combo o unitario?, ¿bebida?, ¿salsa si aplica?, ¿adicionales?)
3. Pide nombre y dirección
4. Verifica zona de entrega
5. Presenta resumen con total calculado correctamente
6. Informa tiempos: Entre semana 30-45 min | Fines de semana 50-60 min
7. Pregunta método de pago (Efectivo / Datáfono / QR Transferencia BBVA - Chef Fast llave: 0091626861)
8. Si paga por transferencia: pide comprobante de pago antes de confirmar
9. Confirma el pedido

Cuando el pedido esté COMPLETAMENTE confirmado (tienes nombre, dirección, productos y pago), incluye al final de tu mensaje esta línea especial exactamente así:
##PEDIDO_CONFIRMADO##{"nombre":"[nombre]","telefono":"[numero]","direccion":"[direccion]","barrio":"[barrio]","productos":"[lista de productos]","total":"[total]","pago":"[metodo]"}##

════════════════════════════════════════
CAMBIOS Y CANCELACIONES
════════════════════════════════════════
"¡Hola! En este momento tu pedido ya está en preparación 👨‍🍳 Con mucho gusto vamos a revisar si aún alcanzamos a hacer el cambio. ¿Cuéntame qué deseas modificar?"

════════════════════════════════════════
QUEJAS / TRANSFERENCIA HUMANA
════════════════════════════════════════
"Entiendo tu situación y quiero que quedes 100% satisfecho(a). Voy a comunicarte con nuestra administradora. 📞 Escríbele directamente al: 316 721 9321"

════════════════════════════════════════
REGLAS
════════════════════════════════════════
1. NUNCA inventes productos o precios
2. NUNCA confirmes sin comprobante si paga por transferencia
3. SIEMPRE calcula el total correctamente
4. Solo habla de temas del restaurante
5. Sé amable y usa emojis con moderación"""


# ══════════════════════════════════════════════════════════════
# GOOGLE SHEETS
# ══════════════════════════════════════════════════════════════

def registrar_en_sheets(datos_pedido: dict):
    """Registra el pedido confirmado en Google Sheets."""
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(
            "google_credentials.json", scopes=scopes
        )
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(os.environ.get("GOOGLE_SHEET_ID"))
        worksheet = sheet.sheet1

        # Si es la primera fila, agrega encabezados
        if worksheet.row_count == 0 or worksheet.cell(1, 1).value != "Fecha":
            worksheet.append_row([
                "Fecha", "Hora", "Nombre", "Teléfono",
                "Dirección", "Barrio", "Productos",
                "Total", "Método Pago", "Estado"
            ])

        ahora = datetime.now()
        worksheet.append_row([
            ahora.strftime("%d/%m/%Y"),
            ahora.strftime("%H:%M"),
            datos_pedido.get("nombre", ""),
            datos_pedido.get("telefono", ""),
            datos_pedido.get("direccion", ""),
            datos_pedido.get("barrio", ""),
            datos_pedido.get("productos", ""),
            datos_pedido.get("total", ""),
            datos_pedido.get("pago", ""),
            "PENDIENTE"
        ])
        print(f"✅ Pedido registrado en Google Sheets: {datos_pedido.get('nombre')}")
    except Exception as e:
        print(f"❌ Error al registrar en Sheets: {e}")


def extraer_pedido_confirmado(texto: str) -> dict | None:
    """Busca el marcador de pedido confirmado en la respuesta de Claude."""
    if "##PEDIDO_CONFIRMADO##" in texto:
        try:
            inicio = texto.index("##PEDIDO_CONFIRMADO##") + len("##PEDIDO_CONFIRMADO##")
            fin = texto.index("##", inicio)
            json_str = texto[inicio:fin]
            return json.loads(json_str)
        except Exception as e:
            print(f"Error extrayendo pedido: {e}")
    return None


def limpiar_respuesta(texto: str) -> str:
    """Elimina el marcador técnico de la respuesta antes de enviarla al cliente."""
    if "##PEDIDO_CONFIRMADO##" in texto:
        inicio = texto.index("##PEDIDO_CONFIRMADO##")
        texto = texto[:inicio].strip()
    return texto


# ══════════════════════════════════════════════════════════════
# TRANSCRIPCIÓN DE NOTAS DE VOZ
# ══════════════════════════════════════════════════════════════

def transcribir_audio(audio_id: str) -> str | None:
    """Descarga y transcribe una nota de voz de WhatsApp con Whisper."""
    try:
        token = os.environ.get("WHATSAPP_TOKEN")
        headers = {"Authorization": f"Bearer {token}"}

        # Obtener URL del audio
        url_info = requests.get(
            f"https://graph.facebook.com/v18.0/{audio_id}",
            headers=headers
        ).json()
        audio_url = url_info.get("url")

        # Descargar el audio
        audio_resp = requests.get(audio_url, headers=headers)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio_resp.content)
            temp_path = f.name

        # Transcribir con Whisper
        from openai import OpenAI
        openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        with open(temp_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es"
            )
        os.unlink(temp_path)
        return transcript.text

    except Exception as e:
        print(f"Error transcribiendo audio: {e}")
        return None


# ══════════════════════════════════════════════════════════════
# CLAUDE - PROCESAR MENSAJE
# ══════════════════════════════════════════════════════════════

def procesar_con_claude(numero: str, mensaje_usuario: str) -> str:
    """Envía el mensaje a Claude manteniendo el historial de conversación."""
    if numero not in conversaciones:
        conversaciones[numero] = []

    conversaciones[numero].append({
        "role": "user",
        "content": mensaje_usuario
    })

    # Mantener máximo 20 turnos para controlar costos
    historial = conversaciones[numero][-20:]

    respuesta = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=historial
    )

    texto_respuesta = respuesta.content[0].text

    conversaciones[numero].append({
        "role": "assistant",
        "content": texto_respuesta
    })

    return texto_respuesta


# ══════════════════════════════════════════════════════════════
# WHATSAPP - ENVIAR MENSAJE
# ══════════════════════════════════════════════════════════════

def enviar_whatsapp(numero: str, mensaje: str):
    """Envía un mensaje de texto por WhatsApp."""
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_id = os.environ.get("PHONE_NUMBER_ID")

    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    resp = requests.post(url, headers=headers, json=data)
    print(f"WhatsApp send → {resp.status_code}: {resp.text}")


# ══════════════════════════════════════════════════════════════
# WEBHOOK - VERIFICACIÓN (Meta requiere esto al configurar)
# ══════════════════════════════════════════════════════════════

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    """Meta llama a esto una sola vez para verificar que el servidor es tuyo."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == os.environ.get("VERIFY_TOKEN"):
        print("✅ Webhook verificado correctamente")
        return challenge, 200
    else:
        return "Token incorrecto", 403


# ══════════════════════════════════════════════════════════════
# WEBHOOK - RECIBIR MENSAJES
# ══════════════════════════════════════════════════════════════

@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    """Recibe todos los mensajes entrantes de WhatsApp."""
    try:
        data = request.get_json()
        print(f"Mensaje recibido: {json.dumps(data, indent=2)}")

        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return jsonify({"status": "ok"}), 200

        msg = messages[0]
        numero = msg.get("from")
        tipo = msg.get("type")

        # ── Procesar según tipo de mensaje ────────────────────
        if tipo == "text":
            texto_cliente = msg["text"]["body"]

        elif tipo == "audio":
            audio_id = msg["audio"]["id"]
            texto_cliente = transcribir_audio(audio_id)
            if not texto_cliente:
                enviar_whatsapp(numero, "No pude escuchar bien tu mensaje 😅 ¿Puedes escribirlo?")
                return jsonify({"status": "ok"}), 200

        elif tipo == "image":
            # El cliente envió una foto (ej. comprobante de pago)
            texto_cliente = "[El cliente envió una imagen, probablemente el comprobante de pago]"

        else:
            # Tipo no soportado
            enviar_whatsapp(numero, "Por ahora solo puedo leer mensajes de texto, notas de voz e imágenes 😊")
            return jsonify({"status": "ok"}), 200

        # ── Enviar a Claude ───────────────────────────────────
        respuesta_claude = procesar_con_claude(numero, texto_cliente)

        # ── Verificar si hay pedido confirmado ────────────────
        pedido = extraer_pedido_confirmado(respuesta_claude)
        if pedido:
            pedido["telefono"] = numero
            registrar_en_sheets(pedido)

        # ── Limpiar y enviar respuesta al cliente ─────────────
        respuesta_limpia = limpiar_respuesta(respuesta_claude)
        enviar_whatsapp(numero, respuesta_limpia)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        return jsonify({"status": "error", "detail": str(e)}), 500


# ══════════════════════════════════════════════════════════════
# INICIO
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)