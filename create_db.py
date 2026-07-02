from database.database import engine, Base
from database.models import Usuario, rol, estado_usuarios, estados_productos , estados_caja , metodos_pago , estado_ventas
from services.auth_service import hash_password
from database.database import SessionLocal

def init_db():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # crear roles
    roles = ["ADMIN", "VENDEDOR", "CAJERO"]
    for nombre in roles:
        if not db.query(rol).filter(rol.nombre == nombre).first():
            db.add(rol(nombre=nombre))
    db.commit()

    # estados productos
    estados = ["ACTIVO", "INACTIVO"]
    for nombre in estados:
        if not db.query(estados_productos).filter(estados_productos.nombre == nombre).first():
            db.add(estados_productos(nombre=nombre))
    db.commit()

    # crear estados de usuario
    estados = ["ACTIVO", "INACTIVO"]
    for nombre in estados:
        if not db.query(estado_usuarios).filter(estado_usuarios.nombre == nombre).first():
            db.add(estado_usuarios(nombre=nombre))
    db.commit()

    # estado de caja
    estados = ["ABIERTA", "CERRADA"]
    for nombre in estados:
        if not db.query(estados_caja).filter(estados_caja.nombre == nombre).first():
            db.add(estados_caja(nombre=nombre))
    db.commit()

    # metodos de pago
    metodos = ["EFECTIVO", "TARJETA", "NEQUI"]
    for nombre in metodos:
        if not db.query(metodos_pago).filter(metodos_pago.nombre == nombre).first():
            db.add(metodos_pago(nombre=nombre))
    db.commit()

    # estado ventas
    estados = ["COMPLETADA", "ANULADA"]
    for nombre in estados:
        if not db.query(estado_ventas).filter(estado_ventas.nombre == nombre).first():
            db.add(estado_ventas(nombre=nombre))
    db.commit()


    # buscar el id del rol ADMIN y el estado ACTIVO
    rol_admin = db.query(rol).filter(rol.nombre == "ADMIN").first()
    estado_activo = db.query(estado_usuarios).filter(estado_usuarios.nombre == "ACTIVO").first()

    # crear usuario admin
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
    
    # buscar rol vendedor y estado activo
    rol_vendedor = db.query(rol).filter(rol.nombre == "VENDEDOR").first()

# crear usuario vendedor
    if not db.query(Usuario).filter(Usuario.correo == "vendedor@burgerland.com").first():
        vendedor = Usuario(
            nombre="Vendedor1",
            correo="vendedor@burgerland.com",
            contraseña=hash_password("vendedor123"),
            id_rol=rol_vendedor.id_rol,
            id_estado=estado_activo.id_estado
        )
        db.add(vendedor)
        db.commit()

    db.close()
    print("Base de datos creada exitosamente")

if __name__ == "__main__":
    init_db()

