# BurgerLand

BurgerLand es un POS para la gestión básica de un negocio de hamburguesas.

## Stack

- Python
- Flet
- SQLAlchemy
- SQLite

## Instalación

```bash
pip install -r requirements.txt
```

## Inicializar la base de datos

```bash
python create_db.py
```

## Ejecutar la aplicación

```bash
python main.py
```

Credenciales rápidas:

- Correo: `admin@burguerland.com`
- Contraseña: `admin123`

## Compras e inventario

Las compras se registran contra la tabla `inventario`, que contiene los insumos
gestionados por la aplicación. Cada línea de compra aumenta `inventario.cantidad`;
la tabla `productos` se mantiene como catálogo del menú y no se modifica al
registrar compras.

## Selección de mesa

El número de mesas se configura en `services/mesa_service.py` (`NUMERO_MESAS`).
La inicialización de la aplicación crea las mesas faltantes sin cambiar el
estado de las que ya existen. En una nueva venta se puede elegir una mesa libre
o "Para llevar / Mostrador"; la mesa elegida queda asociada a la venta pagada.

### Domicilios

En Nueva Venta se puede elegir **Domicilio** e ingresar cliente, teléfono,
dirección, barrio o referencia, costo de envío y domiciliario opcional. El costo
se suma al total y al movimiento de caja. Historial permite filtrar domicilios,
ver sus datos y actualizar el estado de los pedidos activos. Una cancelación
requiere motivo, revierte el inventario vendido y registra el reembolso; los
pagos que no sean en efectivo quedan como devolución pendiente de ejecutar por
el canal de pago original.

Los campos de domicilios y el tipo de pedido se agregan de forma aditiva al
inicializar la aplicación. Para actualizar una base existente, ejecuta
`python create_db.py` o reinicia la aplicación; no se reemplazan las ventas
históricas. Los informes distinguen ventas por tipo de pedido y muestran los
domicilios e ingresos por envío.

## Cuentas abiertas

En Nueva Venta, usa **Guardar cuenta abierta** para conservar el carrito sin
registrar una venta ni afectar caja o inventario. La mesa queda ocupada. Desde
**Cuentas abiertas** se puede reabrir, seguir editando y guardar la cuenta, o
anularla con confirmación. **Cobrar** convierte el carrito guardado en una venta,
registra el pago en caja y libera la mesa. Las modificaciones usan una versión
optimista para detectar si otro cajero guardó o cobró la cuenta primero.
Desde una cuenta abierta también se puede elegir **Cambiar mesa**; el traslado
se guarda inmediatamente y libera la mesa anterior, siempre que la mesa destino
siga libre.

### Roles de usuario

Los administradores tienen la sección **Usuarios** para asignar el rol
**Administrador** o **Trabajador / Vendedor** a otros usuarios. No se puede
cambiar el propio rol ni quitar el último administrador del sistema. Los cambios
se guardan en la base de datos y se aplican al usuario en su siguiente acceso.

### División de cuenta

Desde una cuenta abierta con al menos dos unidades, **Dividir cuenta** permite
repartirla por productos (incluidas unidades individuales de una misma línea) o
en partes iguales. El redondeo se hace en pesos enteros y cualquier residuo se
asigna a la última subcuenta. Cada subcuenta tiene método de pago y cobro
independientes; la cuenta y su mesa permanecen abiertas hasta cobrar la última.

Los cobros por productos descuentan del inventario únicamente las unidades
asignadas a esa subcuenta. En partes iguales, el inventario completo se valida y
descuenta en el primer cobro, y no vuelve a descontarse en los siguientes. Para
mantener la suma y asignaciones consistentes, después de dividir una cuenta sus
productos quedan bloqueados para edición. Si una subcuenta ya se pagó, no se
puede anular el resto como si no hubiera habido cobros.

Verificación de mesas, cuentas y división:

```bash
python -m unittest tests.test_mesa_service tests.test_venta_service tests.test_cuenta_service
```

### Comprobantes por WhatsApp

En Nueva Venta puedes ingresar un celular colombiano de 10 dígitos que inicie
en 3, preparar el comprobante por WhatsApp y activar **Enviar al confirmar el
pago**. El envío manual previo al cobro se identifica como **precuenta pendiente
de pago**; después de pagar, el comprobante incluye el consecutivo de venta. En
cuentas divididas, cada subcuenta tiene su propio celular y opción de envío.
Los comprobantes se titulan **Comprobante de venta** y no reemplazan la factura
electrónica DIAN.

El proveedor `wa_me` abre WhatsApp con el mensaje preparado. El estado permanece
**PENDIENTE** hasta que una integración confirme el envío; el cliente debe
presionar Enviar en WhatsApp. Para el envío automático configura estas
variables de entorno antes de iniciar la aplicación. Cloud API recibe el
comprobante como PDF y una copia de texto en el pie del documento:

```text
WHATSAPP_PROVIDER=cloud_api
WHATSAPP_ACCESS_TOKEN=<token de WhatsApp Business Cloud API>
WHATSAPP_PHONE_NUMBER_ID=<identificador del número de empresa>
WHATSAPP_GRAPH_API_VERSION=<versión de Graph API habilitada en Meta>
BUSINESS_NAME=BurgerLand
```

Sin esas variables, el proveedor por defecto es `wa_me`. Cloud API requiere
credenciales vigentes y que el destinatario haya dado su consentimiento; Meta
puede restringir mensajes iniciados por la empresa según la ventana de atención
y las plantillas aprobadas. Los estados de WhatsApp y el celular quedan
asociados a cada venta, con opción para reintentar desde Historial. No guardes
tokens en el código ni en el repositorio. La interfaz
`FacturaElectronicaProvider` deja preparado el punto de integración DIAN, sin
emitir facturas electrónicas.

Pruebas del comprobante y validación del celular:

```bash
python -m unittest tests.test_whatsapp_service tests.test_cuenta_service
```
