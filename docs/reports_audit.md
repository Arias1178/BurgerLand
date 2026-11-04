# Auditoría de reportes y visualización

## 1. Archivos y responsabilidades

- `views/informes.py`: pantalla principal de Reportes y Estadísticas. Construye los informes general y comparativo, además de exportar PDFs con `reportlab`.
- `views/contabilidad.py`: pantalla de Operatividad contable y estado financiero; integra la lógica de cierre, flujo y validaciones de transacciones.
- `services/financial_engine.py`: motor financiero central para P&L y flujo de caja. Es la fuente de verdad para ingresos, costos, gastos y utilidad.
- `services/contabilidad_service.py`: valida estado de caja, genera cierres contables y consolida ventas/gastos para la contabilidad.
- `services/cierre_caja_service.py`: calcula cierre de caja, diferencia de efectivo y observaciones de arqueo.
- `database/models.py`: modelos de ventas, ventas por detalle, caja, gastos y consolidación contable.
- `main.py`: vista principal que conecta navegación y apertura de informes.

## 2. Librerías utilizadas

- `flet`: UI del escritorio y componentes visuales de pantalla.
- `reportlab`: biblioteca actual para generar PDFs en `views/informes.py`.
- `matplotlib` no está integrado todavía en la pipeline de reportes, aunque el proyecto ya usa `reportlab` para diagramas y tablas.
- `SQLAlchemy`: persistencia y agregados por fecha/caja/producto.

## 3. Flujo de datos real (arquitectura de 3 capas)

La arquitectura actual ya tiene una separación clara:

1. Persistencia: `database/models.py` + `database/database.py`.
2. Lógica de negocio: `services/financial_engine.py`, `services/contabilidad_service.py`, `services/cierre_caja_service.py`.
3. Presentación: `views/informes.py`, `views/contabilidad.py`.

Sin embargo, el problema principal del round 1 es que la capa de reportes no tenía una única fuente de verdad para los periodos y variaciones, y muchos cálculos de formato, validación y fechas se mezclaban en la vista. El ajuste correcto es centralizar el cálculo de periodos y formato en servicios reutilizables y mantener la UI y el PDF como consumidores, no como generadores de lógica.

## 4. Defectos confirmados

Los defectos observados en el round 1 fueron confirmados por la revisión del código y por la lógica del comparativo:

- `views/informes.py` calculaba periodos de quincena sin validar `start <= end` ni fechas futuras.
- El comparativo de quincena se habilitaba solo en fechas convencionales de cierre, sin tener un modo de vista previa.
- Las variaciones se calculaban como porcentajes absolutos sin distinguir entre período con datos previos, período vacío o “nuevo”.
- El PDF usa una plantilla ligera pero sin una estrategia robusta de header/body frame, por lo que la parte superior puede solaparse con el contenido y tables/charts pueden quedar cortados.

## 5. Decisión de implementación

Para cumplir el prompt, se introduce la capa `services/reporting_service.py` con:

- `get_fortnight_periods(reference_date, mode)` para cálculos de periodo válidos.
- `format_currency_es_co(value)` para número monetario en es-CO.
- `format_percentage_es_co(value)` cuando se requiera mostrar valores porcentuales.

Con esto se corrige la causa raíz de D4/D5 y se deja una base reutilizable para los informes que se construyan en fases posteriores, sin romper la current UI ni la lógica de contabilidad existente.
