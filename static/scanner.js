const codeReader = new ZXing.BrowserMultiFormatReader();

window.onload = async () => {
  const videoElement = document.getElementById("video");
  const status = document.getElementById("status");

  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cams = devices.filter(d => d.kind === "videoinput");

    if (cams.length === 0) {
      status.innerText = "Nessuna fotocamera trovata!";
      return;
    }

    const backCamera = cams[cams.length - 1].deviceId;

    await codeReader.decodeFromVideoDevice(backCamera, videoElement, (result, err) => {
      if (result) {
        const barcode = result.text;
        status.innerText = "Letto: " + barcode;

        // Fermiamo lo scanner
        codeReader.reset();

        // INVIA il barcode al backend
        fetch("/api/barcode_lookup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ barcode: barcode })
        })
        .then(r => r.json())
        .then(data => {
          if (data.found) {
            // Precompila il form add_product
            const query = new URLSearchParams(data.product).toString();
            window.location.href = "/add?" + query;
          } else {
            alert("Prodotto non trovato nel database OpenFoodFacts");
            window.location.href = "/add?barcode=" + barcode;
          }
        });
      }
    });

  } catch (e) {
    console.error(e);
    status.innerText = "Errore: " + e;
  }
};
