# BurgerLand

BurgerLand es una aplicación de escritorio para administrar la operación de un
restaurante: ventas, caja, inventario, compras, cuentas, informes y contabilidad.

## Tecnologías

- Python
- Flet
- SQLAlchemy
- SQLite
- ReportLab para exportar informes PDF

## Requisitos e instalación

Instala una versión de Python compatible con las dependencias del proyecto.
Desde la carpeta del repositorio, crea un entorno virtual e instala los
paquetes:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Inicializa la base de datos si es una instalación nueva:

```powershell
python create_db.py
```

Inicia la aplicación:

```powershell
python main.py
```

La aplicación también inicializa y actualiza de forma aditiva su esquema al
arrancar. La base SQLite está en `burguerland.db`, en la carpeta raíz del
proyecto. Conserva una copia de seguridad antes de reemplazar o mover esa base.

## Acceso y roles

En la pantalla de acceso, el campo **Usuario o correo** acepta el correo
completo o el nombre corto **Admin**. El alias no elimina la contraseña ni
otorga permisos por sí mismo: se autentica contra la cuenta inicial
`admin@burguerland.com` y solo funciona mientras esa cuenta tenga el rol
`ADMIN`.

Credenciales creadas por defecto por `create_db.py`:

- Administrador: `Admin` (o `admin@burguerland.com`) / `admin123`
- Vendedor: `vendedor@burgerland.com` / `vendedor123`

Son credenciales iniciales de desarrollo. Cámbialas y protege el acceso a la
base de datos antes de usar el sistema con información real. Un administrador
puede asignar los roles **Administrador** y **Trabajador / Vendedor** desde
**Usuarios**. No se puede cambiar el propio rol ni retirar el último
administrador.

## Funcionalidades

### Ventas y caja

- Abrir caja y registrar ventas con los medios de pago configurados.
- Elegir mesa, mostrador/para llevar o domicilio para una venta.
- Consultar las ventas del día y el historial con filtros.
- Registrar retiros de caja pendientes de justificar y movimientos de egreso.
- Cerrar caja y consultar el saldo final calculado y el resumen del turno.
- Mantener cuentas abiertas, reabrirlas, trasladarlas de mesa, anularlas o
  cobrarlas después. La aplicación valida cambios concurrentes para evitar
  sobrescribir un cobro o una edición reciente.
- Dividir una cuenta por productos o en partes iguales, y cobrar cada subcuenta
  por separado.

El cierre disponible en la aplicación calcula el saldo final esperado con el
saldo inicial, las ventas en efectivo y los egresos registrados. El servicio
contable también contiene una rutina de arqueo con conteo físico, pero no forma
parte del flujo de cierre conectado a la interfaz actual.

### Menú, inventario, proveedores y compras

- Administrar secciones y productos del menú.
- Asociar productos del menú con insumos y descontar inventario al vender.
- Administrar categorías, cantidades, unidades, costos y niveles mínimos de
  inventario.
- Mantener proveedores y su catálogo de suministros.
- Registrar compras y sus líneas; estas aumentan la cantidad y actualizan el
  costo promedio del insumo en inventario.
- El menú de productos y el inventario de insumos son catálogos diferentes.
  Registrar una compra actualiza inventario, no los productos del menú.
- La sección **Compras** está disponible para usuarios ADMIN.

### Domicilios y comprobantes

En una venta a domicilio se pueden guardar los datos de entrega, cliente,
teléfono, barrio o referencia, costo de envío y domiciliario opcional. El costo
de envío se suma a la venta y al movimiento de caja. En **Historial** se pueden
consultar pedidos y actualizar su estado. Una cancelación pide el motivo,
revierte las unidades vendidas y registra el reembolso; un pago no efectivo
queda pendiente de devolución por su canal original.

Los comprobantes por WhatsApp admiten celulares colombianos de 10 dígitos que
inicien en 3. El proveedor `wa_me` abre WhatsApp con el mensaje preparado y el
cliente debe enviarlo. También existe un proveedor opcional de WhatsApp Business
Cloud API, que envía el comprobante PDF y un mensaje de texto. Configura estas
variables antes de iniciar la aplicación para usarlo:

```text
WHATSAPP_PROVIDER=cloud_api
WHATSAPP_ACCESS_TOKEN=<token de WhatsApp Business Cloud API>
WHATSAPP_PHONE_NUMBER_ID=<identificador del número de empresa>
WHATSAPP_GRAPH_API_VERSION=<versión de Graph API habilitada en Meta>
BUSINESS_NAME=BurgerLand
```

Sin esas variables se usa `wa_me`. No guardes tokens en el código ni en el
repositorio. El estado queda pendiente hasta que el proveedor confirme el envío.
Los comprobantes de venta no son facturas electrónicas DIAN; la interfaz
`FacturaElectronicaProvider` no emite facturas.

### Informes y contabilidad

- Ver informes de ventas, productos vendidos, métodos de pago, tipos de pedido,
  egresos y resultados comparativos.
- Usar **Contabilidad y Operatividad** para consolidar una caja cerrada,
  desglosar ventas brutas/netas e impuestos, registrar propinas y costo de
  ventas.
- Consultar el panel de análisis financiero por periodos predeterminados o por
  fechas personalizadas. Permite registrar ingresos y gastos, y administrar
  nómina, servicios y deudas; los registros se pueden excluir de los cálculos.
- Consultar utilidad, flujo de caja, valores pendientes por cobrar/pagar y punto
  de equilibrio.
- Exportar el estado de resultados a PDF desde el servicio de contabilidad.

La operatividad de una caja solo puede procesarse después de cerrarla. Las tasas
predeterminadas y parámetros laborales deben revisarse y mantenerse conforme a
la normativa aplicable; los resultados son cálculos del sistema, no asesoría
contable ni tributaria.

El documento [FORMULAS_CONTABILIDAD.txt](./FORMULAS_CONTABILIDAD.txt) explica
cada fórmula, dónde se aplica y qué resultado produce.

## Pruebas

Ejecuta todas las pruebas unitarias desde la raíz:

```powershell
python -m unittest discover -s tests
```

Para validar áreas específicas:

```powershell
python -m unittest tests.test_auth_service
python -m unittest tests.test_contabilidad_service tests.test_financial_engine tests.test_contabilidad_financial_view
python -m unittest tests.test_mesa_service tests.test_venta_service tests.test_cuenta_service
python -m unittest tests.test_whatsapp_service tests.test_cuenta_service
```
