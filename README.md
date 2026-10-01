# Sistema de Presupuesto: Categorías, Cuentas y Gastos Mensuales

Sistema enfocado y ligero para:
1. **Crear Categorías**.
2. **Crear Cuentas dentro de las Categorías**.
3. **Registrar Gastos Mensuales** (meses 1 al 12).
4. **Cálculo automático de los 6 totales** en tiempo real.

---

## 1. Reglas de Cálculo Implementadas

1. **Total mensual de cada cuenta**: importe asignado al mes.
2. **Total anual de cada cuenta**: $\sum_{m=1}^{12} V(cuenta, m)$.
3. **Total mensual de cada categoría**: suma de todas sus cuentas en dicho mes.
4. **Total anual de cada categoría**: suma de todos los meses de la categoría.
5. **Total mensual general**: suma de todas las categorías en cada mes.
6. **Total anual general**: consolidado anual con verificación de cuadre cruzado.

---

## 2. Estructura del Proyecto

```
Planificador/
├── backend/
│   ├── database.py             # Modelos SQLAlchemy (Category, Account, MonthlyExpense)
│   ├── schemas.py              # Esquemas Pydantic con validación de montos >= 0.00
│   ├── calculator.py           # Motor de cálculo exacto de los 6 totales
│   ├── main.py                 # Endpoints REST FastAPI y montaje de interfaz
│   ├── static/
│   │   └── index.html          # Interfaz web interactiva React
│   ├── run.py                  # Script para iniciar el servidor
│   ├── test_calculations.py    # Pruebas matemáticas de los 6 totales
│   └── requirements.txt        # Dependencias Python
└── README.md
```

---

## 3. Endpoints REST

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/categories` | Lista todas las categorías con sus cuentas. |
| `POST` | `/api/categories` | Crea una nueva categoría. |
| `PUT` | `/api/categories/{id}` | Modifica el nombre de una categoría. |
| `DELETE` | `/api/categories/{id}` | Elimina una categoría y sus cuentas asociadas. |
| `POST` | `/api/categories/{id}/accounts` | Crea una cuenta dentro de la categoría. |
| `PUT` | `/api/accounts/{id}` | Modifica una cuenta (nombre, proveedor, categoría). |
| `DELETE` | `/api/accounts/{id}` | Elimina una cuenta. |
| `PUT` | `/api/expenses` | Registra o actualiza gastos mensuales por cuenta. |
| `GET` | `/api/budget-summary` | Devuelve la jerarquía completa y los 6 totales calculados. |

---

## 4. Cómo Ejecutar

En la terminal:

```bash
cd c:\Planificador\backend
pip install -r requirements.txt
python run.py
```

Abre en tu navegador:
- **Aplicación Web**: [http://localhost:8000](http://localhost:8000)
- **Documentación Swagger API**: [http://localhost:8000/docs](http://localhost:8000/docs)
