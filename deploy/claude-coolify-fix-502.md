# Claude Chrome — Coolify fabreapp

El último error fue:
- Coolify esperaba healthcheck Docker
- La imagen no tenía Health → "map has no entry for key Health"
- Además a veces salta el build ("Build step skipped")

En Coolify ahora:
1. Deploy del commit nuevo
2. Activá "Rebuild without cache" / Force rebuild (NO aceptar skip)
3. Servicio web:
   - Ports Exposes = 8000
   - Domain port = 8000
4. Healthcheck habilitado, path=/accounts/login/, port=8000
5. Confirmá en logs:
   - Listening at: http://0.0.0.0:8000
   - Healthcheck curl a 8000 (NO 3000)
6. Abrí https://app.fabregad.com.ar/accounts/login/
