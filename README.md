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
