function doGet(e) {
  const palletId = e.parameter.palletId || "";
  const vendorEncoded = e.parameter.vendor || "";
  const productEncoded = e.parameter.product || "";

  // Base64 decode + decodeURIComponent
  const vendor = decodeURIComponent(Utilities.newBlob(Utilities.base64Decode(vendorEncoded)).getDataAsString());
  const product = decodeURIComponent(Utilities.newBlob(Utilities.base64Decode(productEncoded)).getDataAsString());

  const formUrl = "https://docs.google.com/forms/d/e/1FAIpQLSdDmnWcW27tfDptUvuSjEgN8K7nNNQWecdpeMMhwftTtbiyIQ/viewform";
  const redirectUrl = `${formUrl}?usp=pp_url` +
    `&entry.419411235=${encodeURIComponent(palletId)}` +
    `&entry.427884801=보관종료` +
    `&entry.2110345042=${encodeURIComponent(vendor)}` +
    `&entry.306824944=${encodeURIComponent(product)}`;

  return HtmlService.createHtmlOutput(
    `<html>
       <head><base target="_top"></head>
       <body>
         <script>
           window.location.href = "${redirectUrl}";
         </script>
       </body>
     </html>`
  );
}
