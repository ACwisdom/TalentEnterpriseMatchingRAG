import sys

# Windows 常见 GBK 控制台：业务代码里 print 含 emoji 会触发 UnicodeEncodeError，表现为 Web 500
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import asyncio
import json
import os
import re
import secrets
import shutil
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from web.deps import browser_must_send_api_key, require_api_key

from src.config import OUTPUT_DIR
from src.match_constraints import constraints_from_optional_form
from src.pipeline import iter_match_stream_events, run_match_single_pass
from src.resume_processor import read_resume_file

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_STATIC_DIR = _PROJECT_ROOT / "web" / "static"

_DEFAULT_DEMO_ROOT = _PROJECT_ROOT / "data" / "default"
_DEFAULT_DEMO_INPUT = _DEFAULT_DEMO_ROOT / "input"
_DEFAULT_DEMO_OUTPUT = _DEFAULT_DEMO_ROOT / "output"
_DEFAULT_DEMO_HTML = _DEFAULT_DEMO_ROOT / "demo.html"
_DEMO_READ_MAX_BYTES = int(os.getenv("WEB_DEMO_READ_MAX_BYTES", str(512 * 1024)))

_DOWNLOAD_TTL_SEC = int(os.getenv("WEB_DOWNLOAD_TTL_SEC", "3600"))
_download_lock = threading.Lock()
_download_registry: dict[str, tuple[str, float, str]] = {}
# download_id -> (absolute_path, expires_epoch, suggested_filename)


def _downloads_dir() -> Path:
    d = Path(OUTPUT_DIR) / "web_downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _prune_expired_unlocked() -> None:
    now = time.time()
    dead: list[str] = []
    for did, (path, exp, _) in _download_registry.items():
        if exp < now:
            dead.append(did)
    for did in dead:
        path, _, _ = _download_registry.pop(did, ("", 0, ""))
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def _register_download(abs_path: str, suggested_basename: str) -> str:
    download_id = secrets.token_urlsafe(24)
    exp = time.time() + _DOWNLOAD_TTL_SEC
    with _download_lock:
        _prune_expired_unlocked()
        _download_registry[download_id] = (abs_path, exp, suggested_basename)
    return download_id


def _parse_bool(v: Any, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "on")


def _safe_stem(filename: str | None) -> str:
    if not filename:
        return "resume"
    stem = Path(filename).stem
    stem = re.sub(r"[^\w\u4e00-\u9fff.-]", "_", stem)[:120]
    return stem or "resume"


def _ensure_default_demo_dirs() -> None:
    _DEFAULT_DEMO_INPUT.mkdir(parents=True, exist_ok=True)
    _DEFAULT_DEMO_OUTPUT.mkdir(parents=True, exist_ok=True)


def _demo_safe_name(name: str) -> str:
    if not name or name.strip() != name:
        raise HTTPException(status_code=400, detail="invalid file name")
    if "/" in name or "\\" in name or name in (".", "..") or ".." in name:
        raise HTTPException(status_code=400, detail="invalid file name")
    base = Path(name).name
    if base != name:
        raise HTTPException(status_code=400, detail="invalid file name")
    return base


def _demo_base_for_side(side: str) -> Path:
    if side == "input":
        return _DEFAULT_DEMO_INPUT
    if side == "output":
        return _DEFAULT_DEMO_OUTPUT
    raise HTTPException(status_code=400, detail='side must be "input" or "output"')


def _demo_list_files() -> dict[str, list[str]]:
    _ensure_default_demo_dirs()

    def names(d: Path) -> list[str]:
        if not d.is_dir():
            return []
        return sorted(p.name for p in d.iterdir() if p.is_file())

    return {"input": names(_DEFAULT_DEMO_INPUT), "output": names(_DEFAULT_DEMO_OUTPUT)}


def _demo_read_text(side: str, file: str) -> dict[str, str]:
    base = _demo_base_for_side(side).resolve()
    safe = _demo_safe_name(file)
    path = (base / safe).resolve()
    try:
        path.relative_to(base)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="path outside demo directory") from e
    if not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    suf = path.suffix.lower()
    if suf in (".docx", ".pdf", ".xlsx", ".xlsm", ".zip"):
        return {
            "content": f"[此文件为二进制类型 {suf}，请在服务器目录 {path.parent} 中直接打开]",
            "file": safe,
        }
    raw = path.read_bytes()[:_DEMO_READ_MAX_BYTES]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gbk", errors="replace")
        except Exception:
            text = raw.decode("utf-8", errors="replace")
    if path.stat().st_size > _DEMO_READ_MAX_BYTES:
        text += f"\n\n…（仅展示前 {_DEMO_READ_MAX_BYTES} 字节）"
    return {"content": text, "file": safe}


app = FastAPI(title="Talent-Enterprise Matching API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/client-options")
def client_options(request: Request) -> dict:
    return {"require_api_key": browser_must_send_api_key(request)}


@app.get("/demo")
def demo_fixed_page() -> FileResponse:
    """固定 Demo 页：磁盘上 data/default/demo.html，数据来自 data/default/input 与 output。"""
    _ensure_default_demo_dirs()
    if not _DEFAULT_DEMO_HTML.is_file():
        raise HTTPException(
            status_code=404,
            detail="缺少 data/default/demo.html",
        )
    return FileResponse(str(_DEFAULT_DEMO_HTML), media_type="text/html; charset=utf-8")


@app.get("/demo/api/list")
def demo_api_list() -> dict[str, list[str]]:
    return _demo_list_files()


@app.get("/demo/api/read")
def demo_api_read(side: str, file: str) -> JSONResponse:
    return JSONResponse(_demo_read_text(side, file))


@app.get("/")
def root_index() -> FileResponse:
    index = _STATIC_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="index.html missing")
    return FileResponse(str(index), media_type="text/html; charset=utf-8")


@app.post("/api/match")
async def api_match(
    _: None = Depends(require_api_key),
    file: UploadFile = File(...),
    top_k: int = Form(15),
    use_llm: str = Form("false"),
    use_llm_for_profile: str = Form("false"),
    preferred_provinces: str = Form(""),
    preferred_cities: str = Form(""),
    required_field_keywords: str = Form(""),
    exclude_enterprise_ids: str = Form(""),
    hard_region: str = Form("false"),
    hard_field: str = Form("false"),
    constraints_json: str = Form(""),
    min_recall_score: str = Form(""),
    salary_max_wan: str = Form(""),
    expected_salary_text: str = Form(""),
) -> JSONResponse:
    if top_k < 1 or top_k > 200:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 200")

    orig_name = file.filename or "resume.pdf"
    suffix = Path(orig_name).suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported format; use .pdf, .docx, or .txt",
        )

    ul_llm = _parse_bool(use_llm)
    ul_profile = _parse_bool(use_llm_for_profile)
    constraints = constraints_from_optional_form(
        provinces_csv=preferred_provinces,
        cities_csv=preferred_cities,
        field_keywords_csv=required_field_keywords,
        exclude_ids_csv=exclude_enterprise_ids,
        hard_region=hard_region,
        hard_field=hard_field,
        constraints_json=constraints_json or None,
        min_recall_score=min_recall_score,
        salary_max_wan=salary_max_wan,
        expected_salary_text=expected_salary_text or None,
    )

    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="match_upload_")
    os.close(fd)
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        max_bytes = int(os.getenv("WEB_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
        if len(content) > max_bytes:
            raise HTTPException(status_code=400, detail="File too large")
        with open(tmp_path, "wb") as out:
            out.write(content)

        resume_text = read_resume_file(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    tag = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    stem = _safe_stem(orig_name)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    word_out = os.path.join(OUTPUT_DIR, f"{stem}_匹配报告_{tag}.docx")

    try:
        single = run_match_single_pass(
            resume_text=resume_text,
            top_k=top_k,
            output_file=word_out,
            use_llm=ul_llm,
            use_llm_for_profile=ul_profile,
            constraints=constraints,
        )
        word_abs = single.word_path
        report_text = single.report_preview_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e!s}") from e

    word_basename = os.path.basename(word_abs)
    dest_dir = _downloads_dir()
    dest_path = dest_dir / f"{secrets.token_urlsafe(16)}.docx"
    try:
        shutil.move(word_abs, dest_path)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Could not stage download: {e!s}") from e

    json_sidecar = single.json_path
    if os.path.isfile(json_sidecar):
        try:
            os.remove(json_sidecar)
        except OSError:
            pass

    download_id = _register_download(str(dest_path), word_basename)

    payload: dict[str, Any] = {
        "report_text": report_text,
        "word_path": word_basename,
        "download_id": download_id,
        "ranking_meta": single.ranking_meta,
        "download_note": (
            "MVP: download tokens are stored in process memory and expire after "
            f"{_DOWNLOAD_TTL_SEC}s; multi-instance deployments need a shared store."
        ),
    }
    return JSONResponse(payload)


def _sse_line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/api/match/stream")
async def api_match_stream(
    _: None = Depends(require_api_key),
    file: UploadFile = File(...),
    top_k: int = Form(15),
    use_llm: str = Form("false"),
    use_llm_for_profile: str = Form("false"),
    preferred_provinces: str = Form(""),
    preferred_cities: str = Form(""),
    required_field_keywords: str = Form(""),
    exclude_enterprise_ids: str = Form(""),
    hard_region: str = Form("false"),
    hard_field: str = Form("false"),
    constraints_json: str = Form(""),
    min_recall_score: str = Form(""),
    salary_max_wan: str = Form(""),
    expected_salary_text: str = Form(""),
) -> StreamingResponse:
    if top_k < 1 or top_k > 200:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 200")

    orig_name = file.filename or "resume.pdf"
    suffix = Path(orig_name).suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported format; use .pdf, .docx, or .txt",
        )

    ul_llm = _parse_bool(use_llm)
    ul_profile = _parse_bool(use_llm_for_profile)
    constraints = constraints_from_optional_form(
        provinces_csv=preferred_provinces,
        cities_csv=preferred_cities,
        field_keywords_csv=required_field_keywords,
        exclude_ids_csv=exclude_enterprise_ids,
        hard_region=hard_region,
        hard_field=hard_field,
        constraints_json=constraints_json or None,
        min_recall_score=min_recall_score,
        salary_max_wan=salary_max_wan,
        expected_salary_text=expected_salary_text or None,
    )

    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="match_upload_")
    os.close(fd)
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        max_bytes = int(os.getenv("WEB_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
        if len(content) > max_bytes:
            raise HTTPException(status_code=400, detail="File too large")
        with open(tmp_path, "wb") as out:
            out.write(content)

        resume_text = read_resume_file(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    tag = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    stem = _safe_stem(orig_name)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    word_out = os.path.join(OUTPUT_DIR, f"{stem}_匹配报告_{tag}.docx")

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Any] = asyncio.Queue()
    sentinel = object()

    def worker() -> None:
        try:
            for ev in iter_match_stream_events(
                resume_text=resume_text,
                top_k=top_k,
                output_file=word_out,
                use_llm=ul_llm,
                use_llm_for_profile=ul_profile,
                constraints=constraints,
            ):
                fut = asyncio.run_coroutine_threadsafe(queue.put(ev), loop)
                fut.result()
        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                queue.put({"type": "error", "message": str(e)}),
                loop,
            ).result()
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(sentinel), loop).result()

    threading.Thread(target=worker, daemon=True).start()

    async def gen_bytes():
        while True:
            item = await queue.get()
            if item is sentinel:
                break
            if isinstance(item, dict) and item.get("type") == "done":
                word_abs = item.get("word_abs") or word_out
                report_text = item.get("report_text") or ""
                if not word_abs or not os.path.isfile(word_abs):
                    yield _sse_line({"type": "error", "message": "Word export missing"}).encode(
                        "utf-8"
                    )
                    break
                word_basename = os.path.basename(word_abs)
                dest_dir = _downloads_dir()
                dest_path = dest_dir / f"{secrets.token_urlsafe(16)}.docx"
                try:
                    shutil.move(word_abs, dest_path)
                except OSError as e:
                    yield _sse_line(
                        {"type": "error", "message": f"Could not stage download: {e!s}"}
                    ).encode("utf-8")
                    break
                json_sidecar = item.get("json_path") or str(Path(word_abs).with_suffix(".json"))
                if os.path.isfile(json_sidecar):
                    try:
                        os.remove(json_sidecar)
                    except OSError:
                        pass
                download_id = _register_download(str(dest_path), word_basename)
                done_payload = {
                    "type": "done",
                    "download_id": download_id,
                    "word_path": word_basename,
                    "report_text": report_text,
                    "download_note": (
                        "MVP: download tokens are stored in process memory and expire after "
                        f"{_DOWNLOAD_TTL_SEC}s; multi-instance deployments need a shared store."
                    ),
                }
                yield _sse_line(done_payload).encode("utf-8")
                continue
            yield _sse_line(item).encode("utf-8")

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        gen_bytes(),
        media_type="text/event-stream; charset=utf-8",
        headers=headers,
    )


@app.get("/api/download/{download_id}")
def api_download(
    download_id: str,
    _: None = Depends(require_api_key),
) -> FileResponse:
    with _download_lock:
        _prune_expired_unlocked()
        entry = _download_registry.get(download_id)

    if not entry:
        raise HTTPException(status_code=404, detail="Unknown or expired download")

    path, _exp, suggested = entry
    if not os.path.isfile(path):
        with _download_lock:
            _download_registry.pop(download_id, None)
        raise HTTPException(status_code=404, detail="File no longer available")

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=suggested or "report.docx",
    )


if _STATIC_DIR.is_dir():
    app.mount(
        "/static",
        StaticFiles(directory=str(_STATIC_DIR)),
        name="static",
    )
