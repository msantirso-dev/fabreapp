# Pegá esto en Claude (Chrome) con Coolify abierto

Arreglá el deploy de fabreapp (Bad Gateway / healthcheck fail).

PROBLEMA REAL (de los logs):
- Gunicorn escucha en: 0.0.0.0:8000
- Healthcheck de Coolify/Dockerfile intenta: 127.0.0.1:3000
- Por eso falla y hace rollback

QUÉ HACER EN COOLIFY:
1. Abrí el recurso Docker Compose de msantirso-dev/fabreapp
2. Servicio WEB (no db):
   - Ports Exposes / Container Port / Domain port = **8000**
   - Path healthcheck (si existe) = `/accounts/login/`
3. Si hay toggle de Healthcheck custom del Dockerfile: desactivalo o asegurate puerto 8000
4. Variables: PORT=8000 y APP_PORT=8000 (si existen)
5. IMPORTANTE: hacé **Force Rebuild** (no redeploy normal).
   El log anterior dijo "Build step skipped" por mismo SHA; hace falta rebuild forzado tras el nuevo commit.
6. Esperá que el healthcheck pase
7. Verificá logs: debe decir `Listening at: http://0.0.0.0:8000`
8. Abrí https://app.fabregad.com.ar/accounts/login/

Reportá resultado final.
