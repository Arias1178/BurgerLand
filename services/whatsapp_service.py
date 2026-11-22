import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from html import escape
from io import BytesIO
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_ENVIADO = "ENVIADO"
ESTADO_ERROR = "ERROR"


class WhatsAppError(ValueError):
    """Error de configuración o entrega del comprobante por WhatsApp."""


class FacturaElectronicaProvider(Protocol):
    def emitir(self, venta_id: int, datos: dict) -> str:
        """TODO: implementar con un proveedor tecnológico autorizado por DIAN."""


@dataclass(frozen=True)
class ResultadoEnvio:
    estado: str
    url: str | None = None
    message_id: str | None = None


def validar_numero_colombiano(numero: str) -> str:
    """Valida un celular colombiano y lo devuelve en formato internacional."""
    if not isinstance(numero, str):
        raise ValueError("Ingresa un número celular colombiano válido.")
    limpio = re.sub(r"[\s().-]", "", numero.strip())
    if limpio.startswith("+57"):
        celular = limpio[3:]
    elif limpio.startswith("57") and len(limpio) == 12:
        celular = limpio[2:]
    else:
        celular = limpio
    if not re.fullmatch(r"3\d{9}", celular):
        raise ValueError(
            "El celular debe tener 10 dígitos e iniciar en 3. "
            "El prefijo +57 se agrega automáticamente."
        )
    return f"+57{celular}"


def formatear_pesos(valor: float) -> str:
    return f"${valor:,.0f}".replace(",", ".")


def generar_mensaje_comprobante(
    *,
    negocio: str,
    consecutivo: str,
    fecha_hora: datetime,
    mesa: str,
    items: list[dict],
    subtotal: float,
    total: float,
    metodo_pago: str,
    pendiente_pago: bool = False,
) -> str:
    lineas = [
        "Comprobante de venta",
        negocio,
        f"Consecutivo: {consecutivo}",
        f"Fecha y hora: {fecha_hora.strftime('%d/%m/%Y %H:%M')}",
        f"Mesa: {mesa}",
    ]
    if pendiente_pago:
        lineas.append("Estado: Pendiente de pago (precuenta)")
    lineas.append("")
    lineas.append("Productos:")
    for item in items:
        nombre = str(item.get("nombre") or "Producto")
        cantidad = int(item.get("cantidad", 0))
        precio = float(item.get("precio", item.get("precio_unitario", 0)))
        lineas.append(
            f"- {nombre} x{cantidad}: {formatear_pesos(precio * cantidad)}"
        )
        personalizacion = item.get("personalizacion")
        if personalizacion:
            lineas.append(f"  Nota: {personalizacion}")
    lineas.extend(
        [
            "",
            f"Subtotal: {formatear_pesos(subtotal)}",
            f"Total: {formatear_pesos(total)}",
            f"Método de pago: {metodo_pago}",
            "",
            "¡Gracias por tu compra! Te esperamos pronto.",
        ]
    )
    return "\n".join(lineas)


def generar_comprobante_pdf(
    *,
    negocio: str,
    consecutivo: str,
    fecha_hora: datetime,
    mesa: str,
    items: list[dict],
    subtotal: float,
    total: float,
    metodo_pago: str,
    pendiente_pago: bool = False,
) -> bytes:
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Comprobante de venta {consecutivo}",
        author=negocio,
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "ComprobanteTitulo",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#2C2F3E"),
    )
    derecha = ParagraphStyle(
        "ComprobanteDerecha",
        parent=estilos["Normal"],
        alignment=TA_RIGHT,
    )
    elementos = [
        Paragraph("Comprobante de venta", titulo),
        Paragraph(escape(negocio), estilos["Heading2"]),
        Paragraph(f"Consecutivo: {escape(str(consecutivo))}", estilos["Normal"]),
        Paragraph(
            f"Fecha y hora: {fecha_hora.strftime('%d/%m/%Y %H:%M')}",
            estilos["Normal"],
        ),
        Paragraph(f"Mesa: {escape(str(mesa))}", estilos["Normal"]),
    ]
    if pendiente_pago:
        elementos.append(
            Paragraph(
                "<b>Estado: Pendiente de pago (precuenta)</b>",
                estilos["Normal"],
            )
        )
    elementos.append(Spacer(1, 8 * mm))

    filas = [["Cant.", "Producto", "Precio", "Subtotal"]]
    for item in items:
        cantidad = int(item.get("cantidad", 0))
        precio = float(item.get("precio", item.get("precio_unitario", 0)))
        nombre = escape(str(item.get("nombre") or "Producto"))
        personalizacion = item.get("personalizacion")
        if personalizacion:
            nombre += f"<br/><font size='8'>{escape(str(personalizacion))}</font>"
        filas.append(
            [
                str(cantidad),
                Paragraph(nombre, estilos["Normal"]),
                Paragraph(formatear_pesos(precio), derecha),
                Paragraph(formatear_pesos(precio * cantidad), derecha),
            ]
        )

    tabla = Table(
        filas,
        colWidths=[18 * mm, 88 * mm, 34 * mm, 34 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3A3F52")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9CEDB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elementos.extend(
        [
            tabla,
            Spacer(1, 8 * mm),
            Paragraph(f"Subtotal: {formatear_pesos(subtotal)}", derecha),
            Paragraph(
                f"<b>Total: {formatear_pesos(total)}</b>",
                derecha,
            ),
            Paragraph(
                f"Método de pago: {escape(str(metodo_pago))}",
                derecha,
            ),
            Spacer(1, 8 * mm),
            Paragraph(
                "¡Gracias por tu compra! Te esperamos pronto.",
                titulo,
            ),
        ]
    )
    documento.build(elementos)
    return buffer.getvalue()


def crear_url_wa_me(numero: str, mensaje: str) -> str:
    internacional = validar_numero_colombiano(numero)
    destinatario = internacional.removeprefix("+")
    return f"https://wa.me/{destinatario}?{urlencode({'text': mensaje})}"


def _enviar_cloud_api(
    numero: str,
    mensaje: str,
    pdf_bytes: bytes | None = None,
    nombre_pdf: str = "comprobante-venta.pdf",
) -> ResultadoEnvio:
    token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "").strip()
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    api_version = os.environ.get("WHATSAPP_GRAPH_API_VERSION", "").strip()
    if not token or not phone_number_id or not api_version:
        raise WhatsAppError(
            "El modo Cloud API requiere WHATSAPP_ACCESS_TOKEN, "
            "WHATSAPP_PHONE_NUMBER_ID y WHATSAPP_GRAPH_API_VERSION."
        )

    internacional = validar_numero_colombiano(numero).removeprefix("+")
    url = (
        f"https://graph.facebook.com/{api_version}/"
        f"{phone_number_id}/messages"
    )
    tipo_mensaje = "text"
    contenido_mensaje = {"preview_url": False, "body": mensaje}
    if pdf_bytes:
        boundary = "----BurgerLandWhatsAppBoundary"
        multipart = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="messaging_product"\r\n\r\n'
            "whatsapp\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="type"\r\n\r\n'
            "application/pdf\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; '
            f'filename="{nombre_pdf}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8") + pdf_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
        media_request = Request(
            f"https://graph.facebook.com/{api_version}/"
            f"{phone_number_id}/media",
            data=multipart,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        media_request.add_header("Authorization", "Bearer " + token)
        try:
            with urlopen(media_request, timeout=20) as response:
                media_response = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detalle = error.read().decode("utf-8", errors="replace")
            raise WhatsAppError(
                f"WhatsApp no aceptó el PDF (HTTP {error.code}): {detalle}"
            ) from error
        except (TimeoutError, URLError, OSError) as error:
            raise WhatsAppError(
                f"No se pudo cargar el PDF a WhatsApp: {error}"
            ) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise WhatsAppError(
                "WhatsApp devolvió una respuesta inválida al cargar el PDF."
            ) from error
        media_id = media_response.get("id")
        if not media_id:
            raise WhatsAppError("WhatsApp no confirmó la carga del PDF.")
        tipo_mensaje = "document"
        contenido_mensaje = {
            "id": media_id,
            "caption": mensaje[:1024],
            "filename": nombre_pdf,
        }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": internacional,
        "type": tipo_mensaje,
        tipo_mensaje: contenido_mensaje,
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    request.add_header("Authorization", "Bearer " + token)
    try:
        with urlopen(request, timeout=15) as response:
            respuesta = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detalle = error.read().decode("utf-8", errors="replace")
        raise WhatsAppError(
            f"WhatsApp Cloud API rechazó el envío (HTTP {error.code}): {detalle}"
        ) from error
    except (TimeoutError, URLError, OSError) as error:
        raise WhatsAppError(f"No se pudo conectar con WhatsApp: {error}") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WhatsAppError("WhatsApp devolvió una respuesta inválida.") from error

    message_id = None
    mensajes = respuesta.get("messages") or []
    if mensajes:
        message_id = mensajes[0].get("id")
    if not message_id:
        raise WhatsAppError(
            "WhatsApp no confirmó la aceptación del mensaje. "
            "Revisa la configuración y vuelve a intentar."
        )
    return ResultadoEnvio(estado=ESTADO_ENVIADO, message_id=message_id)


def enviar_comprobante(
    numero: str,
    mensaje: str,
    pdf_bytes: bytes | None = None,
    nombre_pdf: str = "comprobante-venta.pdf",
) -> ResultadoEnvio:
    internacional = validar_numero_colombiano(numero)
    proveedor = os.environ.get("WHATSAPP_PROVIDER", "wa_me").strip().lower()
    if proveedor == "wa_me":
        return ResultadoEnvio(
            estado=ESTADO_PENDIENTE,
            url=crear_url_wa_me(internacional, mensaje),
        )
    if proveedor == "cloud_api":
        return _enviar_cloud_api(
            internacional,
            mensaje,
            pdf_bytes,
            nombre_pdf,
        )
    raise WhatsAppError(
        "WHATSAPP_PROVIDER debe ser 'wa_me' o 'cloud_api'."
    )


def actualizar_estado_envio_venta(
    db,
    venta_id: int,
    estado: str,
    error: str | None = None,
) -> None:
    from database.models import ventas

    if estado not in {ESTADO_PENDIENTE, ESTADO_ENVIADO, ESTADO_ERROR}:
        raise ValueError("El estado de WhatsApp no es válido.")
    venta = db.get(ventas, venta_id)
    if venta is None:
        raise ValueError("No se encontró la venta para actualizar WhatsApp.")
    venta.whatsapp_estado_envio = estado
    venta.whatsapp_error = error
    db.commit()
