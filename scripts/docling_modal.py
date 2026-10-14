"""Docling on a Modal GPU: a chapter PDF's lines in ~1 s/page instead of ~36 s/page on a CPU PC.

prior-art-checked: scripts/section_reader.docling_lines is the local version (same options and same output shape);
services/modal_inference.py is the existing Modal app (auth via the `modal` CLI token). Nothing else in
scripts/ services/ src/ enrichment/ runs a layout model remotely.

Use:  SECTION_READER_LINES=docling_modal python scripts/section_reader.py ...
      python scripts/docling_modal.py some.pdf        (timing + line count)
The PDF is cut into CHUNK_PAGES-page pieces, converted in parallel (.map), pages re-numbered to the original.
Model weights are baked into the image at build time, so a cold container does not download them.
"""
from __future__ import annotations

import sys

import modal

CHUNK_PAGES = 50
GPU = "T4"

app = modal.App("plotdetect-docling")


def _bake_models() -> None:
    from docling.utils.model_downloader import download_models
    download_models()


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("docling", "pymupdf")
    .run_function(_bake_models)
)


@app.function(image=image, gpu=GPU, timeout=1800, scaledown_window=120)
def docling_chunk(pdf_bytes: bytes) -> list[list]:
    """[[page, text], ...] for one PDF, same rules as section_reader.docling_lines."""
    import tempfile
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        path = f.name
    opts = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    doc = conv.convert(path).document
    out: list[list] = []
    for item, _level in doc.iterate_items():
        prov = getattr(item, "prov", None) or []
        page = prov[0].page_no if prov else (out[-1][0] if out else 1)
        label = str(getattr(item, "label", "")).lower()
        if "page_header" in label or "page_footer" in label:
            continue
        if "table" in label and hasattr(item, "data"):
            for row in item.data.grid or []:
                cells = [c.text.strip() for c in row if c.text and c.text.strip()]
                if cells:
                    out.append([page, " | ".join(dict.fromkeys(cells))])
            continue
        text = (getattr(item, "text", "") or "").strip()
        if text:
            marker = (getattr(item, "marker", "") or "").strip()
            out.append([page, f"{marker} {text}".strip() if marker and not text.startswith(marker) else text])
    return out


def _split(pdf_path: str) -> list[tuple[int, bytes]]:
    """[(page offset, bytes of that chunk)] -- fitz runs locally."""
    import fitz
    chunks = []
    with fitz.open(pdf_path) as doc:
        for a in range(0, doc.page_count, CHUNK_PAGES):
            sub = fitz.open()
            sub.insert_pdf(doc, from_page=a, to_page=min(doc.page_count, a + CHUNK_PAGES) - 1)
            chunks.append((a, sub.tobytes(garbage=3, deflate=True)))
            sub.close()
    return chunks


def remote_docling_lines(pdf_path: str) -> list[tuple[int, str]]:
    """(page, text) like section_reader.docling_lines, converted on a Modal GPU in parallel chunks."""
    chunks = _split(str(pdf_path))
    out: list[tuple[int, str]] = []
    with app.run():
        for n, ((offset, _b), lines) in enumerate(zip(chunks, docling_chunk.map([b for _o, b in chunks])), 1):
            out.extend((int(p) + offset, t) for p, t in lines)
            # progress after every chunk, never only at the end
            print(f"    [docling-modal] chunk {n}/{len(chunks)} (from p{offset + 1}): {len(lines)} lines", flush=True)
    return out


if __name__ == "__main__":
    import time
    t0 = time.time()
    res = remote_docling_lines(sys.argv[1])
    print(f"{len(res)} lines in {time.time() - t0:.0f}s")
    if len(sys.argv) > 2:
        pg = int(sys.argv[2])
        for p, t in [x for x in res if x[0] == pg][:10]:
            print(p, t[:160])
