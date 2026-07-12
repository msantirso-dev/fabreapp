# Instrucciones distintas (no es lo mismo de antes)

## Por qué fallaba
Coolify pone PORT=3000 y chequea ese puerto.
Nosotros forzábamos gunicorn en 8000 → healthcheck/proxy fallan.

## Fix en el código (ya pusheado)
La app ahora escucha en $PORT de Coolify (3000).

## Qué hacer VOS en Coolify (panel de Coolify, NO app.fabregad.com.ar)

La app puede estar caída y igual entrás a Coolify:
- http://IP-DEL-SERVIDOR:8000
- o el dominio de tu panel Coolify

1. Abrí el recurso fabreapp
2. Advanced → si existe "Disable Healthchecks", NO lo hace falta ahora (hay healthcheck OK)
3. Ports Exposes / Port = **3000** (el default de Coolify)
4. Deploy → **Rebuild without cache**
5. En el log buscá: `Starting gunicorn on 0.0.0.0:3000`
6. Si dice 8000, todavía hay una variable PORT=8000 en Coolify: borrala o poné PORT=3000

## Si no ves el build
En Coolify: Deployments (historial a la izquierda/arriba del recurso), no la URL pública.
Ahí están los logs aunque la web dé Bad Gateway.
