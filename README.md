# Campus Lab

Plataforma web ficticia para un laboratorio de seguridad **autorizado y local**. Incluye cuatro desafíos intencionales: dos de nivel inicial, uno intermedio y uno avanzado. Los códigos de cada reto se generan al iniciar una base de datos nueva.

## Requisitos

- Docker Desktop o Docker Engine con Compose.
- Puerto 8080 libre en el equipo.

## Inicio rápido

```bash
docker compose up --build -d
```

Abre <http://localhost:8080>. Comprueba el servicio con:

```bash
docker compose ps
curl http://localhost:8080/api/health
```

Para detenerlo: `docker compose down`. Para comenzar una sesión limpia: `docker compose down -v` y luego `docker compose up --build -d`. **La opción `-v` elimina el progreso y genera nuevos códigos.**

También funciona sin Docker con Python 3.10 o superior: `python app.py`. No requiere paquetes externos. En este caso escucha en el puerto 8080 y crea `data/` en el directorio del proyecto.

## Misión del estudiante

Actúas como Lucía Rojas en un campus de prueba. Encuentra cuatro códigos con formato `CAMPUS{...}` usando únicamente esta aplicación. Hay pistas en la interfaz y en las respuestas HTTP. Los retos abarcan la biblioteca, los comprobantes, los informes y el archivo de investigación.

Trabaja contra tu instancia local. Puedes utilizar el navegador, sus herramientas de desarrollo, `curl` o un proxy de pruebas. No ataques servicios ajenos. Puedes leer el código para aprender, aunque el ejercicio está pensado para investigar primero desde la interfaz. Los códigos se guardan en la base de datos generada al iniciar el servicio; no están fijados en el repositorio.

## Para docentes

La guía docente con soluciones se entrega como archivo separado del proyecto. No la añadas al repositorio que compartirás con estudiantes.

## Publicación en GitHub

El proyecto está listo para versionarse. Desde esta carpeta:

```bash
git init
git add .
git commit -m "Add Campus Lab security exercise"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/TU-REPOSITORIO.git
git push -u origin main
```

`data/` queda excluido por `.gitignore`. El contenedor solo publica el puerto en `127.0.0.1`. Si un docente lo adapta para una red de clase, debe aislarlo en una red de laboratorio y no exponerlo a Internet.

## Estructura

| Archivo | Función |
| --- | --- |
| `app.py` | Servidor HTTP, SQLite y retos. |
| `static/` | Interfaz web. |
| `compose.yaml`, `Dockerfile` | Ejecución en contenedor. |
