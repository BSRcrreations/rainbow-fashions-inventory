/** Print a rendered document. This function never creates a sale or changes stock. */
export function printDocument(html: string, width: number, margin: number, copies = 1, height?: number) {
  const popup = window.open("", "rainbow-print", "width=600,height=700");
  if (!popup) throw new Error("Allow pop-up windows for this shop to print, then try again.");
  popup.opener = null;
  popup.document.write(`<!doctype html><html><head><title>Rainbow Fashions • Print</title><style>@page{size:${width}mm ${height ? `${height}mm` : 'auto'};margin:0}*{box-sizing:border-box}body{margin:0;color:#000;background:#fff;font-family:Arial,sans-serif;font-size:10pt}.print-copy{width:${width}mm;padding:${margin}mm;${height ? `height:${height}mm;overflow:hidden;` : ''}break-after:page}.print-copy:last-child{break-after:auto}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:3px 0;vertical-align:top;overflow-wrap:anywhere}td:last-child,th:last-child{text-align:right}hr{border:0;border-top:1px dashed #000}h2,p{margin:5px 0}small{font-size:8pt}img{max-width:45mm;max-height:20mm}.receipt-title{text-align:center}.receipt-total{font-size:13pt;font-weight:bold}.receipt-line{border-bottom:1px dotted #999}.barcode{display:block;max-width:100%;height:9mm;margin:auto}.label-name{font-size:9pt;font-weight:bold}.label-meta{font-size:7pt}.label-code{font-family:monospace;text-align:center;font-size:7pt}</style></head><body>${Array.from({ length: copies }, () => `<article class="print-copy">${html}</article>`).join('')}</body></html>`);
  popup.document.close();
  const run = () => { popup.focus(); popup.print(); };
  const images = Array.from(popup.document.images).filter((image) => !image.complete);
  if (images.length) Promise.all(images.map((image) => new Promise<void>((resolve) => { image.onload = () => resolve(); image.onerror = () => resolve(); }))).then(run);
  else run();
}
