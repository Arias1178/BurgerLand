# Auditoría de requisitos - BurgerLand

## Objetivo
Verificar el estado real del sistema frente a los requisitos críticos del negocio: integridad transaccional del flujo de venta, control de inventario, control de caja, autenticación y validaciones ante datos inválidos.

## Credenciales verificadas
- `admin@burguerland.com` / `admin123`
- `vendedor@burgerland.com` / `vendedor123`

Estas credenciales se validan en la semilla de base de datos generada por `create_db.py` y en la lógica de autenticación real de `services/auth_service.py`.

## Evidencia real
### 1. Autenticación y control de acceso
- `create_db.py`: crea usuarios semilla con `hash_password()` usando PBKDF2-HMAC-SHA256.
- `services/auth_service.py`: valida credenciales con compatibilidad para hashes previos y rechaza entradas vacías.
- `views/login.py`: el campo de contraseña queda definido con `password=True` y `can_reveal_password=True` para permitir el login en la vista real.

### 2. Flujo de venta, inventario y transacción
- `services/venta_service.py`: valida cada producto del carrito, agrega cantidades por producto, comprueba stock disponible y descuenta inventario solamente si la venta es válida.
- `views/nueva_venta_view.py`: bloquea ventas sin caja abierta, cantidades no válidas y stock insuficiente antes de confirmar la venta.
- El flujo realiza `commit` sólo al finalizar la operación; cualquier error provoca `rollback` para evitar artefactos parciales.

### 3. Apertura y cierre de caja
- `main.py`: `abrir_caja` y `cerrar_caja` implementan la apertura, cierre y cálculo del resumen de caja.

### 4. Contabilidad y análisis financiero
- `views/contabilidad.py` permite consultar P&L y flujo de caja por un rango de fechas, registrar transacciones y administrar nómina, deudas y servicios.
- `services/financial_engine.py` separa utilidad neta y flujo de caja: el capital de deuda no reduce utilidad, los pagos pendientes no se restan del efectivo disponible, y los intereses pagados sí se incluyen en las salidas de caja.
- El punto de equilibrio usa el mismo rango seleccionado para el análisis. Los pagos pendientes se muestran aparte e incluyen transacciones, servicios y cuotas de deuda marcadas como pendientes.
- Las cuotas de deuda pagadas se descuentan del flujo de caja; las impagas se suman a cuentas pendientes y quedan identificadas en el panel. Las deudas nuevas se crean como pendientes de forma predeterminada. Si se registra el valor de cuota, se usa como pago total para evitar duplicar capital e interés; si no, se suman esos dos componentes.
- `services/contabilidad_service.py` separa gastos fijos y variables según su categoría, y filtra nóminas mensuales por los meses que se cruzan con el rango, incluso cuando este cambia de año.
- La consolidación diaria sigue bloqueada hasta que la caja esté cerrada. Los cálculos de tasas e impuestos se revisaron como lógica de la aplicación; no constituyen una certificación de cumplimiento tributario.

### 5. Validaciones de datos
- `services/venta_service.py`: rechaza cantidades no enteras, menores o iguales a cero, precios negativos y productos sin inventario asociado.

## Pruebas ejecutadas
Se ejecutó la validación real con:

```bash
cd C:\Users\dvacc\OneDrive\Desktop\PdG\BurgerLand
C:\Users\dvacc\OneDrive\Desktop\PdG\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Resultado verificado:
- 13 pruebas ejecutadas.
- 13 pruebas pasadas.
- Evidencia en la salida: `Ran 13 tests in ...` y `OK`.

### Casos cubiertos
- venta exitosa descuenta inventario y agrega movimiento de caja
- venta rechaza stock insuficiente sin modificar inventario
- venta rechaza cantidad negativa
- contabilidad mensual con saldo mínimo
- cierre contable usa ventas y costos
- nómina mensual en rangos que cruzan el cambio de año
- estado de resultados separa gastos fijos y variables
- flujo de caja distingue pagos realizados de obligaciones pendientes e incluye interés y capital pagados
- cuotas de deuda pagadas y pendientes se incluyen en el flujo y cuentas por pagar
- punto de equilibrio calculado para el rango seleccionado
- utilidad neta excluye abonos a capital

## Estado final de la auditoría
- Integridad transaccional del flujo venta → detalle de venta → descuento de inventario → movimiento de caja: reforzada y validada.
- Stock insuficiente: rechazado con error explícito sin cambios parciales.
- Apertura/cierre de caja: presentes en la lógica principal del sistema.
- Análisis contable: flujo de caja y punto de equilibrio corregidos para respetar pagos y rango seleccionado; cuotas de deuda reflejadas y destacadas como pendientes; gastos y nómina mensual clasificados en su periodo correspondiente.
- Autenticación: corregida y segura con PBKDF2.
- Validaciones: reforzadas para cantidades, precios y stock.
- Pruebas automatizadas: ejecutadas con éxito en el entorno real del proyecto.
