from database.database import engine, Base
from database.models import Usuario, rol, estado_usuarios, estados_productos, estados_caja, metodos_pago, estado_ventas, ventas, detalle_ventas, productos
from services.auth_service import hash_password
from database.database import SessionLocal

# Inicializa la base de datos y deja cargados los datos básicos para que la app pueda funcionar desde cero.
def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Crea los roles iniciales del sistema para diferenciar niveles de acceso.
    roles = ["ADMIN", "VENDEDOR", "CAJERO"]
    for nombre in roles:
        if not db.query(rol).filter(rol.nombre == nombre).first():
            db.add(rol(nombre=nombre))
    db.commit()

    # Inserta los estados posibles para los productos.
    estados = ["ACTIVO", "INACTIVO"]
    for nombre in estados:
        if not db.query(estados_productos).filter(estados_productos.nombre == nombre).first():
            db.add(estados_productos(nombre=nombre))
    db.commit()

    # Define los estados con los que se identifican los usuarios del sistema.
    estados = ["ACTIVO", "INACTIVO"]
    for nombre in estados:
        if not db.query(estado_usuarios).filter(estado_usuarios.nombre == nombre).first():
            db.add(estado_usuarios(nombre=nombre))
    db.commit()

    # Registra los estados de apertura o cierre que puede tener la caja.
    estados = ["ABIERTA", "CERRADA"]
    for nombre in estados:
        if not db.query(estados_caja).filter(estados_caja.nombre == nombre).first():
            db.add(estados_caja(nombre=nombre))
    db.commit()

    # Agrega los métodos de pago disponibles para las ventas.
    metodos = ["EFECTIVO", "TARJETA", "NEQUI"]
    for nombre in metodos:
        if not db.query(metodos_pago).filter(metodos_pago.nombre == nombre).first():
            db.add(metodos_pago(nombre=nombre))
    db.commit()

    # Añade los estados posibles para controlar el ciclo de una venta.
    estados = ["COMPLETADA", "ANULADA"]
    for nombre in estados:
        if not db.query(estado_ventas).filter(estado_ventas.nombre == nombre).first():
            db.add(estado_ventas(nombre=nombre))
    db.commit()


    # Busca los IDs necesarios para vincular el usuario administrador con su rol y estado inicial.
    rol_admin = db.query(rol).filter(rol.nombre == "ADMIN").first()
    estado_activo = db.query(estado_usuarios).filter(estado_usuarios.nombre == "ACTIVO").first()

    # Crea el usuario administrador por defecto si aún no existe.
    if not db.query(Usuario).filter(Usuario.correo == "admin@burgerland.com").first():
        admin = Usuario(
            nombre="Administrador",
            correo="admin@burgerland.com",
            contraseña=hash_password("admin123"),
            id_rol=rol_admin.id_rol,
            id_estado=estado_activo.id_estado
        )
        db.add(admin)
        db.commit()

    db.close()
    print("Base de datos creada exitosamente")

if __name__ == "__main__":
    init_db()

