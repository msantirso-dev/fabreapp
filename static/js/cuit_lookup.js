(function () {
  const cuitInput = document.getElementById("id_cuit");
  const nameInput = document.getElementById("id_name");
  const statusEl = document.getElementById("cuit-status");
  if (!cuitInput || !nameInput || !statusEl) return;

  let timer = null;
  let lastLookup = "";

  function digitsOnly(value) {
    return (value || "").replace(/\D/g, "");
  }

  function formatCuit(value) {
    const d = digitsOnly(value);
    if (d.length !== 11) return value;
    return d.slice(0, 2) + "-" + d.slice(2, 10) + "-" + d.slice(10);
  }

  function setStatus(text, kind) {
    statusEl.textContent = text || "";
    statusEl.classList.remove("field-error", "muted", "notice-inline");
    if (kind === "error") statusEl.classList.add("field-error");
    else if (kind === "info") statusEl.classList.add("notice-inline");
    else statusEl.classList.add("muted");
  }

  async function lookup() {
    const cuit = digitsOnly(cuitInput.value);
    if (cuit.length !== 11) {
      setStatus("Ingresá los 11 dígitos del CUIT.", "muted");
      return;
    }
    if (cuit === lastLookup) return;
    lastLookup = cuit;
    cuitInput.value = formatCuit(cuit);
    setStatus("Buscando empresa…", "muted");
    try {
      const res = await fetch("/api/v1/clients/lookup-cuit/?cuit=" + encodeURIComponent(cuit), {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      const data = await res.json();
      if (!data.ok) {
        if (data.code === "needs_config") {
          setStatus(
            (data.error || "Falta configurar consulta CUIT.") +
              " Configurar → /integraciones/cuit/",
            "info"
          );
          return;
        }
        setStatus(data.error || "No se pudo consultar el CUIT.", "error");
        return;
      }
      if (data.cuit) cuitInput.value = data.cuit;
      if (data.name) {
        nameInput.value = data.name;
        nameInput.dispatchEvent(new Event("input", { bubbles: true }));
      }
      setStatus("Datos cargados automáticamente.", "muted");
    } catch (err) {
      setStatus("Error de red al consultar el CUIT.", "error");
    }
  }

  function scheduleLookup() {
    clearTimeout(timer);
    timer = setTimeout(lookup, 450);
  }

  cuitInput.addEventListener("input", scheduleLookup);
  cuitInput.addEventListener("blur", lookup);
})();
