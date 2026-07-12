# Script / prompt para Claude (extensión Chrome) — arreglar Bad Gateway en Coolify
# Dominio: https://app.fabregad.com.ar
# Repo: https://github.com/msantirso-dev/fabreapp
#
# Pegá TODO lo de abajo en Claude (Chrome) con Coolify abierto.

---

## OBJETIVO
Hacer que https://app.fabregad.com.ar deje de mostrar "Bad Gateway" y cargue el login de Django.

## CONTEXTO TÉCNICO (importante)
- Stack: Docker Compose en Coolify (`web` + `db` Postgres).
- El contenedor `web` corre gunicorn.
- Coolify normalmente inyecta la variable de entorno `PORT` (suele ser **3000**).
- Gunicorn DEBE escuchar en el mismo puerto que Coolify usa para el proxy del dominio.
- En logs ya vimos: `Listening at: http://0.0.0.0:3000` → el proxy del dominio NO puede estar en 8000.
- Si el dominio apunta a 8000 y gunicorn está en 3000 → Bad Gateway.
- Repo GitHub: msantirso-dev/fabreapp (rama main). Compose file: `docker-compose.yml`. Servicio HTTP: **web**.

## PASOS QUE DEBÉS HACER EN COOLIFY (en orden)

1. Abrí el proyecto/aplicación de **fabreapp** / **app.fabregad.com.ar** en Coolify.
2. Identificá el recurso Docker Compose y el servicio llamado **web** (no `db`).
3. Abrí la configuración de **Domains / FQDN / Proxy** del servicio **web**:
   - Dominio debe ser: `app.fabregad.com.ar`
   - HTTPS / SSL: habilitado si ya está.
   - **Port / Ports Exposes / Container Port**: debe ser **3000** (NO 8000), salvo que en los logs gunicorn diga otro puerto.
4. Revisá variables de entorno del servicio/compose. Deben existir al menos:
   - `SECRET_KEY` (no vacío)
   - `ALLOWED_HOSTS=app.fabregad.com.ar`
   - `CSRF_TRUSTED_ORIGINS=https://app.fabregad.com.ar`
   - `APP_BASE_URL=https://app.fabregad.com.ar`
   - `DATABASE_URL=postgres://fabreapp:<PASSWORD>@db:5432/fabreapp`
   - `POSTGRES_PASSWORD` igual a la password de `DATABASE_URL`
   - Si existe `PORT`, dejalo en **3000** (o alineado al Ports Exposes).
5. Si hay un campo "Ports Exposes" a nivel servicio, poné **3000**.
6. Guardá cambios.
7. Hacé **Redeploy** / Restart del compose (rebuild si hace falta).
8. Abrí **Logs** del servicio **web** y verificá que aparezca:
   - `Database is ready.`
   - `Listening at: http://0.0.0.0:XXXX`
   - Anotá el XXXX. Ese número DEBE coincidir con el puerto del dominio en Coolify.
9. Si el log dice Listening en 3000 y el dominio sigue en 8000, cambiá el dominio a 3000 y redeploy/restart del proxy.
10. Abrí https://app.fabregad.com.ar/accounts/login/ y confirmá HTTP 200 (formulario de login), no Bad Gateway.

## SI SIGUE FALLANDO
- Pegá/leé las últimas 80 líneas de logs de `web`.
- Confirmá que `db` está healthy.
- Confirmá que el dominio está asignado al servicio **web**, no a `db`.
- No cambies el código de la app; solo Coolify (puerto, dominio, env, redeploy).

## RESULTADO ESPERADO
Reportame al final:
1. Puerto configurado en Coolify para el dominio
2. Puerto que muestra gunicorn en logs (`Listening at...`)
3. URL de login: ¿200 OK o sigue Bad Gateway?
4. Qué cambiaste exactamente

Empezá ahora navegando Coolify y aplicando estos cambios.
