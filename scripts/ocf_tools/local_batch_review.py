"""Stage and serve a loopback-only review site from verified native batch output."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import tempfile
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from .bulk_render import verified_output
from .listening_portal import PrivateServer, byte_range, file_signature, open_regular
from .paths import work_path
from .utils import OCFError, read_json_object, sha256_of_file

FUNCTION = re.compile(r"OCF-[A-Z]{3}-[0-9]{3}")
SHA = re.compile(r"[a-f0-9]{64}")
EDITION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
KINDS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".txt": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".xml": "application/xml",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".vtt": "text/vtt",
}
CSS = """body{font:1.1rem/1.5 system-ui,sans-serif;margin:0;background:#0d1725;color:#f2f4ff}
main{max-width:46rem;margin:auto;padding:1rem 1.25rem}a{color:#afe9ff}li{margin:.55rem 0}
audio{display:block;width:100%;margin:1rem 0}article{border-top:1px solid #617187;padding-bottom:1rem}
.notice{color:#d4def1}"""


def _need(ok, message):
    if not ok:
        raise OCFError(message)


def _page(title, body):
    title = html.escape(title)
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='robots' content='noindex,nofollow'>"
        f"<title>{title}</title><style>{CSS}</style><main><h1>{title}</h1>"
        "<p class='notice'>Local listening review. This is not a published release.</p>"
        f"{body}</main></html>"
    )


def _native_records(batch, locale, marker_root):
    _need(
        not batch.get("dry_run") and not batch.get("failed") and not batch.get("blocked"),
        "local review requires a successful full requested batch",
    )
    rows = batch["results"]
    _need(
        rows
        and all(
            FUNCTION.fullmatch(r["function_id"]) and r["status"] in {"rendered", "skipped-verified"}
            for r in rows
        ),
        "a requested recording is still held",
    )
    _need(len({r["function_id"] for r in rows}) == len(rows), "duplicate review function")
    wanted = {str(Path(r["output_directory"]).resolve()): r for r in rows}
    records = {}
    for path in marker_root.glob("*.json"):
        if path.is_symlink() or not SHA.fullmatch(path.stem):
            continue
        marker = read_json_object(path)
        key = marker.get("output_directory")
        if key not in wanted:
            continue
        row = wanted[key]
        fid = row["function_id"]
        root = Path(key)
        speech = root / "speech-verification.json"
        _need(
            fid not in records
            and verified_output(marker, path.stem)
            and sha256_of_file(speech) == marker.get("speech_verification_sha256"),
            f"{fid}: native artifact or speech proof no longer matches",
        )
        proof = read_json_object(speech)
        segments = proof.get("segments", [])
        _need(
            bool(proof.get("verifier"))
            and bool(segments)
            and all(
                part.get("locale") == locale
                and all(
                    SHA.fullmatch(part.get(k, ""))
                    for k in ("text_sha256", "wav_sha256", "recognized_sha256")
                )
                for part in segments
            ),
            f"{fid}: exact speech proof is incomplete",
        )
        report = read_json_object(root / "session-report.json")
        _need(
            report.get("function_id") == fid and report.get("requested_locale") == locale,
            f"{fid}: native locale or function does not match",
        )
        records[fid] = (root, report, marker)
    _need(len(records) == len(rows), "a native checksum receipt is missing; no site was staged")
    return records


def _copy_pages(pages, site, functions):
    """Add only local playback links to a separately built production Pages artifact."""
    pages = Path(pages).resolve(strict=True)
    _need(pages.is_dir(), "Pages input is not a built static site")
    index = read_json_object(pages / "documentation-index.json")
    hrefs = {}
    for item in index["functions"]:
        fid = item.get("function_id")
        if fid not in functions:
            continue
        _need(
            fid not in hrefs and item["href"] == f"functions/{fid}/",
            "Pages guide is not bound to the exact function ID",
        )
        hrefs[fid] = item["href"] + "index.html"
    _need(set(hrefs) == set(functions), "Pages artifact is missing a requested guide")
    for src in pages.rglob("*"):
        _need(not src.is_symlink(), "Pages artifact contains a symlink")
        if not src.is_file() or src.suffix not in KINDS:
            continue
        dst = site / src.relative_to(pages)
        _need(
            not dst.exists()
            and dst.relative_to(site).parts[0] not in {"_local-audition", "local-review.json"},
            "Pages artifact conflicts with the local audition path",
        )
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.suffix != ".html":
            shutil.copyfile(src, dst)
            continue
        markup = src.read_text(encoding="utf-8")
        _need(markup.count("</head>") == 1, "Pages artifact contains unrecognized markup")
        markup = markup.replace("</head>", '<meta name="robots" content="noindex,nofollow"></head>')
        dst.write_text(markup, encoding="utf-8")
    for rel, slug in {"index.html": "", **{v: k for k, v in hrefs.items()}}.items():
        page = site / rel
        raw = page.read_text(encoding="utf-8")
        _need(
            raw.count("</main>") == 1 and "data-local-batch-review" not in raw,
            "Pages artifact is missing the review insertion point",
        )
        target = "index.html" if not slug else slug + ".html"
        notice = (
            '<section class="guide-section" data-local-batch-review>'
            "<h2>Private listening review</h2><p>"
            f'<a href="/_local-audition/{target}">Open local candidate recordings</a>'
            "</p><p>This does not modify the published edition.</p></section>"
        )
        page.write_text(raw.replace("</main>", notice + "</main>"), encoding="utf-8")


def build_review(batch, destination, *, locale, edition_version, pages=None):
    """Only stage reviewed batch inputs. Never starts a server or pushes a release."""
    from .audition_exports import export_audition

    out = Path(destination).expanduser().absolute()
    _need(
        out.parent.is_dir()
        and out.parent.resolve() == out.parent
        and not out.exists()
        and not out.is_symlink(),
        "audition site needs a new local directory",
    )
    _need(
        len(edition_version) <= 30 and EDITION.fullmatch(edition_version),
        "invalid local edition version",
    )
    records = _native_records(batch, locale, work_path("cache", "bulk-renders"))
    exports_root = work_path("renders")
    exports_root.mkdir(parents=True, exist_ok=True)
    output = {}
    if pages is not None:
        source_pages = Path(pages).resolve(strict=True)
        _need(not out.is_relative_to(source_pages), "output cannot be inside the Pages artifact")
    with (
        tempfile.TemporaryDirectory(prefix=".ocf-local-audition-", dir=out.parent) as temporary,
        tempfile.TemporaryDirectory(prefix=".ocf-local-exports-", dir=exports_root) as export_temp,
    ):
        top = Path(temporary)
        site = top / "site"
        site.mkdir(mode=0o700)
        catalog = site
        if pages is not None:
            _copy_pages(source_pages, site, records)
            catalog = site / "_local-audition"
            catalog.mkdir()
        (catalog / "audio").mkdir()
        rows = []
        for fid, (source, report, marker) in sorted(records.items()):
            candidate = Path(export_temp) / fid
            export_audition(
                source, edition_version=edition_version, output=candidate, no_artwork=True
            )
            exported = read_json_object(candidate / "manifest.json")
            formats = {}
            for ext in ("mp3", "flac"):
                encoded = exported["artifacts"][ext]
                target = catalog / "audio" / f"{fid}.{ext}"
                _need(Path(encoded["path"]).name == encoded["path"], "invalid private export path")
                shutil.copyfile(candidate / encoded["path"], target)
                _need(
                    sha256_of_file(target) == encoded["sha256"], "private audio checksum mismatch"
                )
                formats[ext] = encoded["sha256"]
            title = report.get("title") or fid
            vtt = report.get("artifacts", {}).get("listener_vtt")
            subtitles = ""
            if vtt:
                name = "audio/" + fid + ".vtt"
                shutil.copyfile(source / vtt["path"], catalog / name)
                _need(
                    sha256_of_file(catalog / name) == vtt["sha256"],
                    "private subtitle checksum mismatch",
                )
                subtitles = f'<track kind="subtitles" srclang="{html.escape(locale)}" label="Timed transcript" src="{name}">'
            body = (
                '<p><a href="index.html">All recordings</a></p>'
                f'<audio controls preload="none" src="audio/{fid}.mp3">{subtitles}</audio>'
                f'<p><a href="audio/{fid}.mp3" download>Download MP3</a> · '
                f'<a href="audio/{fid}.flac" download>Download FLAC</a></p>'
            )
            (catalog / (fid + ".html")).write_text(_page(title, body), encoding="utf-8")
            rows.append(f'<li><a href="{fid}.html">{html.escape(title)}</a></li>')
            output[fid] = {
                "native_report_sha256": marker["manifest_sha256"],
                "speech_verification_sha256": marker["speech_verification_sha256"],
                "delivery_sha256": formats,
            }
            shutil.rmtree(candidate)  # temporary verified export copy, not the native source
        (catalog / "index.html").write_text(
            _page("OCF local audition", "<ul>" + "".join(rows) + "</ul>"), encoding="utf-8"
        )
        sealed = {
            "schema": 1,
            "kind": "private-local-review",
            "publication_approval": False,
            "locale": locale,
            "edition": edition_version,
            "recordings": output,
            "routes": {
                f.relative_to(site).as_posix(): sha256_of_file(f)
                for f in site.rglob("*")
                if f.is_file()
            },
        }
        (site / "local-review.json").write_text(
            json.dumps(sealed, indent=2) + "\n", encoding="utf-8"
        )
        site.rename(out)
    return {"directory": str(out), "recordings": len(output), "publication_approval": False}


def serve(root, port=8765):
    """Serve only the sealed route set on loopback, with seekable audio ranges."""
    root = Path(root).resolve(strict=True)
    receipt = read_json_object(root / "local-review.json")
    _need(
        receipt.get("kind") == "private-local-review"
        and receipt.get("publication_approval") is False,
        "not a private local review directory",
    )
    routes = {}
    for rel, digest in receipt["routes"].items():
        path = root / rel
        _need(
            path.resolve(strict=True) == path
            and path.is_relative_to(root)
            and path.suffix in KINDS
            and sha256_of_file(path) == digest,
            "local review route changed",
        )
        stat = path.stat()
        routes["/" + rel] = (path, file_signature(stat), stat.st_size, digest)
        if rel.endswith("/index.html"):
            routes["/" + rel[: -len("index.html")]] = routes["/" + rel]
    routes["/"] = routes["/index.html"]

    class ReviewHandler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            if self.headers.get_all("Host", []) != [f"127.0.0.1:{self.server.server_port}"]:
                return self.send_error(403)
            from urllib.parse import urlsplit

            row = routes.get(urlsplit(self.path).path)
            if row is None:
                return self.send_error(404)
            path, signature, size, digest = row

            try:
                with os.fdopen(open_regular(path), "rb") as payload:
                    current = os.fstat(payload.fileno())
                    if file_signature(current) != signature:
                        return self.send_error(404)
                    etag = f'"{digest}"'
                    requested = self.headers.get("Range")
                    if self.headers.get("If-Range") not in (None, etag):
                        requested = None
                    try:
                        start, stop, code = byte_range(requested, size)
                    except ValueError:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{size}")
                        self.end_headers()
                        return
                    self.send_response(code)
                    self.send_header("Content-Type", KINDS[path.suffix])
                    self.send_header("Content-Length", str(stop - start + 1))
                    self.send_header("ETag", etag)
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Cache-Control", "private, no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.send_header(
                        "Content-Security-Policy",
                        "default-src 'none'; script-src 'self'; connect-src 'self'; media-src 'self' https:; "
                        "style-src 'self' 'unsafe-inline'; img-src 'self' https:; font-src 'self'; frame-ancestors 'none'",
                    )
                    if code == 206:
                        self.send_header("Content-Range", f"bytes {start}-{stop}/{size}")
                    self.end_headers()
                    if self.command == "GET":
                        payload.seek(start)
                        while start <= stop:
                            block = payload.read(min(128 * 1024, stop - start + 1))
                            if not block:
                                break
                            self.wfile.write(block)
                            start += len(block)
            except OSError:
                self.close_connection = True

    with PrivateServer(("127.0.0.1", port), ReviewHandler) as server:
        print(f"Review at http://127.0.0.1:{server.server_port}/", flush=True)
        server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(args.site, args.port)


if __name__ == "__main__":
    main()
