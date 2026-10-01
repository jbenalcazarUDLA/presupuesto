import os
import sys
import uvicorn

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    print("Iniciando Sistema de Presupuesto en http://localhost:8000 ...")
    print("Swagger interactivo en: http://localhost:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, app_dir=script_dir)
