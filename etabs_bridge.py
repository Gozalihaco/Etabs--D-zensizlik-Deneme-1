# -*- coding: utf-8 -*-
"""
ETABS <-> HTML köprüsü
----------------------
Açık ve analiz edilmiş ETABS modeline COM API ile bağlanır, deprem
case'lerine ait tabloları okur ve HTML arayüzüne JSON olarak gönderir.

Çalıştırma (geliştirici):
    pip install comtypes
    python etabs_bridge.py
Dağıtım: build_exe.bat ile ETABS-Duzensizlik.exe ve kurulum dosyası üretilir.
Program tarayıcıda http://127.0.0.1:8765 adresini açar.

Gereksinimler:
    - Windows, ETABS v19 / v20 / v23 (API kayıtlı)
    - 64-bit Python 3.8+
"""
import json
import os
import socket
import sys
import tempfile
import threading
import urllib.request
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

APP_NAME = "ETABS Duzensizlik Kontrolu"
APP_VERSION = "1.0.0"
HOST = "127.0.0.1"
PORT = 8765
FROZEN = getattr(sys, "frozen", False)
# exe içinde gömülü dosyalar sys._MEIPASS altında, geliştirmede script klasöründe
BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
HTML_FILE = os.path.join(BASE, "etabs_duzensizlik.html")
LIB_DIR = os.path.join(BASE, "lib")
DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(), "ETABS-Duzensizlik")

KN_M_C = 6  # eUnits.kN_m_C
CASE_FINISHED = 4  # Analyze.GetCaseStatus -> 4 = Finished
QUAKE_DESIGN_TYPE = 5  # eLoadPatternType.Quake

_state = {"etabs": None, "model": None}


class BridgeError(Exception):
    pass


# ----------------------------------------------------------------- yardımcılar
def _seqs(res):
    return [list(x) for x in res if isinstance(x, (tuple, list))]


def _str_seqs(res):
    return [s for s in _seqs(res) if s and all(isinstance(v, str) for v in s)]


def _same_path(a, b):
    def n(p):
        return os.path.normcase(os.path.normpath(p.strip().strip('"')))
    na, nb = n(a), n(b)
    return na == nb or os.path.splitext(na)[0] == os.path.splitext(nb)[0]


def _prepare_comtypes_cache():
    """exe içinde comtypes.gen yazılamaz; ETABS arayüz sarmalayıcıları kullanıcı klasörüne üretilir."""
    import comtypes.client
    if not FROZEN:
        return
    gen_dir = os.path.join(DATA_DIR, "comtypes_gen")
    os.makedirs(gen_dir, exist_ok=True)
    import comtypes.gen
    if gen_dir not in comtypes.gen.__path__:
        comtypes.gen.__path__.insert(0, gen_dir)
    comtypes.client.gen_dir = gen_dir


def _attach():
    try:
        _prepare_comtypes_cache()
        import comtypes.client
    except ImportError:
        raise BridgeError("Python 'comtypes' paketi yüklü değil. Komut satırında çalıştırın: pip install comtypes")
    try:
        helper = comtypes.client.CreateObject("ETABSv1.Helper")
        from comtypes.gen import ETABSv1
        helper = helper.QueryInterface(ETABSv1.cHelper)
    except Exception as e:
        raise BridgeError(
            "ETABS API bulunamadı (ETABSv1.Helper). ETABS kurulum klasöründeki "
            "RegisterETABS.exe dosyasını yönetici olarak bir kez çalıştırın. "
            "Ayrıntı: %s" % e)
    try:
        etabs = helper.GetObject("CSI.ETABS.API.ETABSObject")
    except Exception as e:
        raise BridgeError("Çalışan bir ETABS bulunamadı. ETABS'i açıp modeli yükleyin. Ayrıntı: %s" % e)
    if etabs is None:
        raise BridgeError("Çalışan bir ETABS bulunamadı. ETABS'i açıp modeli yükleyin.")
    _state["etabs"] = etabs
    _state["model"] = etabs.SapModel
    return etabs.SapModel


def _model():
    m = _state.get("model")
    if m is None:
        raise BridgeError("Önce ETABS modeline bağlanın.")
    try:
        m.GetModelFilename(True)
    except Exception:
        m = _attach()
    return m


def _version(model):
    try:
        res = model.GetVersion()
        return next((x for x in res if isinstance(x, str)), "")
    except Exception:
        return ""


def _stories(model):
    try:
        res = list(model.Story.GetStories(0.0, 0, [], [], [], [], [], [], []))
    except Exception:
        return []
    names = None
    idx = -1
    for i, x in enumerate(res):
        if isinstance(x, (tuple, list)) and x and all(isinstance(v, str) for v in x):
            names, idx = list(x), i
            break
    if not names:
        return []
    elevs = list(res[idx + 1]) if idx + 1 < len(res) and isinstance(res[idx + 1], (tuple, list)) else [None] * len(names)
    heights = list(res[idx + 2]) if idx + 2 < len(res) and isinstance(res[idx + 2], (tuple, list)) else [None] * len(names)
    out = []
    for i, n in enumerate(names):
        out.append({"name": n,
                    "elev": float(elevs[i]) if i < len(elevs) and elevs[i] is not None else float(i),
                    "height": float(heights[i]) if i < len(heights) and heights[i] is not None else None})
    out.sort(key=lambda s: s["elev"])
    return out


def _load_cases(model):
    res = list(model.LoadCases.GetNameList(0, []))
    seqs = _str_seqs(res)
    names = seqs[0] if seqs else []
    status = {}
    try:
        st = list(model.Analyze.GetCaseStatus(0, [], []))
        s_names = _str_seqs(st)
        s_names = s_names[0] if s_names else []
        s_vals = [list(x) for x in st if isinstance(x, (tuple, list)) and x and not isinstance(x[0], str)]
        s_vals = s_vals[0] if s_vals else []
        status = {n: int(v) for n, v in zip(s_names, s_vals)}
    except Exception:
        pass
    cases = []
    for n in names:
        ctype, dtype = None, None
        try:
            r = list(model.LoadCases.GetTypeOAPI_1(n, 0, 0, 0, 0, 0))
            ctype, dtype = int(r[0]), int(r[2])
        except Exception:
            try:
                r = list(model.LoadCases.GetTypeOAPI(n, 0, 0))
                ctype = int(r[0])
            except Exception:
                pass
        cases.append({"name": n, "caseType": ctype, "designType": dtype,
                      "seismic": dtype == QUAKE_DESIGN_TYPE, "status": status.get(n)})
    return cases


def _get_table(model, key):
    for field_keys in ([], [""]):
        try:
            res = list(model.DatabaseTables.GetTableForDisplayArray(key, field_keys, "All", 0, [], 0, []))
        except Exception:
            continue
        if not res or res[-1] != 0:
            continue
        seqs = _seqs(res[:-1])
        if len(seqs) < 2:
            continue
        data, fields = seqs[-1], seqs[-2]
        if not fields or len(data) % len(fields) != 0:
            # yedek: veri en uzun dizi, alanlar onu tam bölen son metin dizisi
            data = max(seqs, key=len)
            fields = next((s for s in reversed(seqs)
                           if s is not data and s and all(isinstance(v, str) for v in s)
                           and len(data) % len(s) == 0), None)
            if not fields:
                continue
        nf = len(fields)
        rows = [[str(v) for v in data[i:i + nf]] for i in range(0, len(data), nf)]
        return {"key": key, "fields": [str(f) for f in fields], "rows": rows}
    return None


def _available_tables(model):
    try:
        res = list(model.DatabaseTables.GetAvailableTables(0, [], [], []))
        seqs = _str_seqs(res[:-1])
        return seqs[0] if seqs else []
    except Exception:
        return []


def _find_table(model, candidates, tokens=None, avail=None):
    avail = avail if avail is not None else _available_tables(model)
    low = {k.lower(): k for k in avail}
    ordered = [low.get(c.lower(), c) for c in candidates]
    if tokens:
        for k in avail:
            if all(t in k.lower() for t in tokens) and k not in ordered:
                ordered.append(k)
    for k in ordered:
        t = _get_table(model, k)
        if t is not None and t["rows"]:
            return t
    return None


# ----------------------------------------------------------------- API uçları
def api_connect(body):
    path = (body.get("path") or "").strip()
    version = body.get("version") or ""
    if not path:
        raise BridgeError("Model dosya yolunu girin.")
    model = _attach()
    fname = ""
    try:
        fname = model.GetModelFilename(True) or ""
    except Exception:
        pass
    if not fname:
        raise BridgeError("ETABS açık ama kayıtlı bir model yüklü değil.")
    if not _same_path(fname, path):
        raise BridgeError("Açık ETABS modeli girilen dosya değil.\nETABS'te açık: %s\nGirilen: %s" % (fname, path))

    warnings = []
    ver = _version(model)
    major = ver.split(".")[0] if ver else ""
    expected = {"19-20": ("19", "20"), "23": ("23",)}.get(version, ())
    if major and expected and major not in expected:
        warnings.append("Seçilen ETABS sürümü (%s) ile çalışan sürüm (%s) farklı." % (version, ver))
    try:
        if not model.GetModelIsLocked():
            warnings.append("Model kilitli değil; analiz yapılmamış olabilir.")
    except Exception:
        pass

    return {"ok": True, "filename": fname, "etabsVersion": ver, "warnings": warnings,
            "stories": _stories(model), "cases": _load_cases(model)}


def api_run(body):
    model = _model()
    x_cases = body.get("xCases") or []
    y_cases = body.get("yCases") or []
    cases = list(dict.fromkeys(x_cases + y_cases))
    if not cases:
        raise BridgeError("En az bir deprem case'i seçin.")

    status = {c["name"]: c["status"] for c in _load_cases(model)}
    not_run = [c for c in cases if status.get(c) not in (None, CASE_FINISHED)]
    if not_run:
        raise BridgeError("Şu case'ler için analiz tamamlanmamış: %s. ETABS'te analizi çalıştırıp tekrar deneyin."
                          % ", ".join(not_run))

    prev_units = None
    try:
        prev_units = model.GetPresentUnits()
    except Exception:
        pass
    model.SetPresentUnits(KN_M_C)
    try:
        dt = model.DatabaseTables
        dt.SetLoadCasesSelectedForDisplay(cases)
        try:
            dt.SetLoadCombinationsSelectedForDisplay([])
        except Exception:
            pass
        avail = _available_tables(model)
        tables = {
            "drift": _find_table(model, ["Story Drifts"], None, avail),
            "maxavg": _find_table(model, ["Story Max Over Avg Drifts", "Diaphragm Max Over Avg Drifts",
                                          "Story Max/Avg Drifts"], ["max", "avg", "drift"], avail),
            "stiff": _find_table(model, ["Story Stiffness"], ["story", "stiff"], avail),
            "mass": _find_table(model, ["Mass Summary by Story"], ["mass", "story"], avail),
        }
    finally:
        if isinstance(prev_units, int):
            try:
                model.SetPresentUnits(prev_units)
            except Exception:
                pass

    return {"ok": True, "units": "kN, m", "stories": _stories(model), "tables": tables,
            "missing": [k for k, v in tables.items() if v is None]}


# ----------------------------------------------------------------- HTTP sunucu
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, b"")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(HTML_FILE, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "etabs_duzensizlik.html bu dosyayla aynı klasörde olmalı.", "text/plain; charset=utf-8")
        elif self.path == "/api/ping":
            self._send(200, {"ok": True, "app": APP_NAME, "version": APP_VERSION})
        elif self.path.startswith("/lib/"):
            name = os.path.basename(self.path.split("?")[0])
            fp = os.path.join(LIB_DIR, name)
            if name.endswith(".js") and os.path.isfile(fp):
                with open(fp, "rb") as f:
                    self._send(200, f.read(), "application/javascript; charset=utf-8")
            else:
                self._send(404, "", "text/plain")
        else:
            self._send(404, {"ok": False, "error": "Bulunamadı"})

    def do_POST(self):
        routes = {"/api/connect": api_connect, "/api/run": api_run}
        fn = routes.get(self.path)
        if not fn:
            return self._send(404, {"ok": False, "error": "Bulunamadı"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            self._send(200, fn(body))
        except BridgeError as e:
            self._send(200, {"ok": False, "error": str(e)})
        except Exception as e:
            traceback.print_exc()
            self._send(200, {"ok": False, "error": "Beklenmeyen hata: %s" % e})


def _already_running(port):
    try:
        with urllib.request.urlopen("http://%s:%d/api/ping" % (HOST, port), timeout=1.5) as r:
            return json.loads(r.read().decode("utf-8")).get("app") == APP_NAME
    except Exception:
        return False


def _bind():
    for port in range(PORT, PORT + 10):
        if _already_running(port):
            return None, port
        try:
            return HTTPServer((HOST, port), Handler), port  # tek thread: COM çağrıları aynı thread'de
        except (OSError, socket.error):
            continue
    raise SystemExit("Boş port bulunamadı (%d-%d)." % (PORT, PORT + 9))


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    if os.name == "nt":
        os.system("title %s" % APP_NAME)
    srv, port = _bind()
    url = "http://%s:%d/" % (HOST, port)
    if srv is None:
        print("Program zaten açık, tarayıcı açılıyor: " + url)
        webbrowser.open(url)
        return
    print("=" * 60)
    print(" %s  v%s" % (APP_NAME, APP_VERSION))
    print(" Adres: %s" % url)
    print(" Bu pencere açık kaldığı sürece program çalışır.")
    print(" Kapatmak için bu pencereyi kapatın.")
    print("=" * 60)
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
