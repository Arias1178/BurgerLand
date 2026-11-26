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
- Asociar productos del menú con recetas de varios insumos y descontar cada
  ingrediente al vender. Un administrador puede revisar o ajustar las cantidades
  desde **Receta** en la tarjeta del producto.
- Al iniciar, crear proveedores genéricos editables, vincular a su catálogo los
  insumos/categorías que ofrecen y preparar las recetas del menú. Las existencias
  iniciales quedan en cero; registra una compra antes de vender platos que
  requieran esos insumos. Las cantidades de receta iniciales son estimadas y
  deben verificarse con las porciones reales.
- Administrar categorías, cantidades, unidades, costos y niveles mínimos de
  inventario.
- Mantener proveedores y su catálogo de suministros.
- Sincronizar los artículos del catálogo de proveedores con inventario y
  secciones del menú. Los artículos sin precio de venta se crean inactivos
  hasta que un administrador configure su precio.
- Registrar compras y sus líneas; estas aumentan la cantidad y actualizan el
  costo promedio del insumo en inventario.
- El menú de productos y el inventario de insumos son catálogos diferentes.
  Registrar una compra actualiza inventario, no los productos del menú.
- La sección **Compras** está disponible para usuarios ADMIN.

### Domicilios

En una venta a domicilio se pueden guardar los datos de entrega, cliente,
teléfono, barrio o referencia, costo de envío y domiciliario opcional. El costo
de envío se suma a la venta y al movimiento de caja. En **Historial** se pueden
consultar pedidos y actualizar su estado. Una cancelación pide el motivo,
revierte las unidades vendidas y registra el reembolso; un pago no efectivo
queda pendiente de devolución por su canal original.

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
python -m unittest tests.test_cuenta_service
```
