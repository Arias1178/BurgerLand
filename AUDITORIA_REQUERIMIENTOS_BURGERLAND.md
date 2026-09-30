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

### 4. Validaciones de datos
- `services/venta_service.py`: rechaza cantidades no enteras, menores o iguales a cero, precios negativos y productos sin inventario asociado.

## Pruebas ejecutadas
Se ejecutó la validación real con:

```bash
cd C:\Users\dvacc\OneDrive\Desktop\PdG\BurgerLand
C:\Users\dvacc\OneDrive\Desktop\PdG\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Resultado verificado:
- 6 pruebas ejecutadas.
- 6 pruebas pasadas.
- Evidencia en la salida: `Ran 6 tests in ...` y `OK`.

### Casos cubiertos
- venta exitosa descuenta inventario y agrega movimiento de caja
- venta rechaza stock insuficiente sin modificar inventario
- venta rechaza cantidad negativa
- contabilidad mensual con saldo mínimo
- cierre contable usa ventas y costos
- cash flow y utilidad neta con deuda principal

## Estado final de la auditoría
- Integridad transaccional del flujo venta → detalle de venta → descuento de inventario → movimiento de caja: reforzada y validada.
- Stock insuficiente: rechazado con error explícito sin cambios parciales.
- Apertura/cierre de caja: presentes en la lógica principal del sistema.
- Autenticación: corregida y segura con PBKDF2.
- Validaciones: reforzadas para cantidades, precios y stock.
- Pruebas automatizadas: ejecutadas con éxito en el entorno real del proyecto.
