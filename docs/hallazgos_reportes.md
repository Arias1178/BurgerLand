# Hallazgos del módulo de reportes y contabilidad

## 1. Ubicación de las pantallas y PDFs
- La pantalla principal de informes se define en `views/informes.py`.
- El módulo de contabilidad se encuentra en `views/contabilidad.py`.
- Los servicios de cálculo de resultados financieros se centralizan en `services/financial_engine.py`.
- La persistencia de caja e informes y la consolidación contable están en `services/contabilidad_service.py` y `main.py`.

## 2. Librería usada para PDF y gráficos
- El PDF actual usa `reportlab` con `SimpleDocTemplate`, `Table`, `Paragraph`, `Pie`, `VerticalBarChart`, etc.
- Las gráficas en pantalla se construyen con componentes nativos de Flet (`flet.canvas` y `ft.Container`/`Row`).
- El proyecto no está aún usando una capa de servicios dedicada exclusivamente a reportería visual; los cálculos se mezclan con la vista en varios puntos.

## 3. Servicios que alimentan los informes
- `views/informes.py` llama a funciones como `_obtener_analisis_negocio` y `_obtener_resumen_contabilidad_periodo`.
- `services/financial_engine.py` calcula P&L y flujo de caja a partir de ventas, gastos y deuda.
- `services/contabilidad_service.py` valida cierre de caja y genera la consolidación contable.

## 4. Hallazgo importante del bug de ventas/ingresos
- El motor financiero sí suma `ventas.total` al P&L, así que la inconsistencia no es por un bug trivial del cálculo; puede deberse a filtros de fechas o a que la caja aún no está cerrada/procesada.
- La capa de reportes debe dejar explícito si la información aún no está consolidada y mostrar un aviso claro cuando la caja no haya sido procesada en contabilidad.

## 5. Objetivo del ajuste actual
- Mantener la arquitectura existente.
- Separar la lógica de autorización/preview del comparativo del flujo oficial de exportación.
- Evitar errores de división por cero y mostrar una vista previa legible incluso fuera de la fecha oficial.
