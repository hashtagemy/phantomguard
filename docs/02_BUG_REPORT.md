# Norn — Bug Raporu & Kritik Sorunlar

> **Rapor Tarihi:** 2026-02-28  
> **İnceleme Kapsamı:** Backend (Python) + Frontend (TypeScript/React)

---

## 🚨 KRİTİK BUGLAR (Severity: HIGH)

### ~~BUG-001: `asyncio.create_task()` Çalışan Event Loop Olmadan Çağrılıyor~~ ✅ ÇÖZÜLDÜ

**Dosya:** `norn/core/interceptor.py`, satır 455-461
**Etki:** Runtime crash — `RuntimeError: no running event loop`

```python
# _on_after_tool() metodu — senkron bir callback'ten çağrılıyor
if self.enable_ai_eval and self.task:
    eval_task = asyncio.create_task(self._evaluate_step_relevance(step, result_str_full))
    self._pending_tasks.append(eval_task)

if self.enable_shadow_browser:
    verify_task = asyncio.create_task(self._verify_with_shadow_browser(...))
    self._pending_tasks.append(verify_task)
```

**Problem:** `_on_after_tool()` bir Strands hook callback'idir ve senkron olarak çağrılır. `asyncio.create_task()` yalnızca çalışan bir asyncio event loop'u varsa çalışır. Strands hook sistemi senkron çalıştığından bu satırlar **hemen `RuntimeError` fırlatır**.

**Düzeltme Önerisi:**
```python
# Seçenek 1: Thread pool kullan
import concurrent.futures
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

def _on_after_tool(self, event):
    ...
    if self.enable_ai_eval and self.task:
        future = executor.submit(asyncio.run, self._evaluate_step_relevance(step, result_str_full))
        self._pending_futures.append(future)

# Seçenek 2: asyncio.run_coroutine_threadsafe kullan
```

---

### ~~BUG-002: `os.chdir()` Thread-Safety Problemi~~ ✅ ÇÖZÜLDÜ

**Dosya:** `norn/api.py`, satır 1510-1587
**Etki:** Birden fazla agent aynı anda çalıştığında çapraz kirlenme (cross-contamination)

```python
os.chdir(workspace_dir)       # Satır 1511
try:
    result = agent_instance(task)
    ...
finally:
    os.chdir(_original_cwd)   # Satır 1587
```

**Problem:** `os.chdir()` **process-global** bir işlemdir. `_execute_agent_background()` bir thread'de çalışır. İki agent aynı anda çalıştırılırsa, birinin `os.chdir()` çağrısı diğerinin çalışma dizinini etkiler.

**Düzeltme Önerisi:**
```python
# os.chdir() yerine subprocess kullan veya agent'a cwd bilgisini
# ortam değişkeni olarak geç (zaten NORN_WORKSPACE olarak yapılıyor)
# os.chdir() çağrısını tamamen kaldırmak en güvenli yaklaşım.
```

---

### ~~BUG-003: `sys.path.insert(0, ...)` Temizlenmiyor~~ ✅ ÇÖZÜLDÜ

**Dosya:** `norn/api.py`, satır 1359, 1362, 1376
**Etki:** Bellek sızıntısı + modül karışması

```python
if package_root not in sys.path:
    sys.path.insert(0, package_root)
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))
```

**Problem:** Her agent çalıştırıldığında `sys.path`'e yeni yollar ekleniyor ama **asla temizlenmiyor**. Birden fazla agent çalıştırmak:
1. `sys.path`'i sürekli büyütür
2. Farklı agent'ların modülleri birbirine karışabilir (aynı isimli modüller)
3. `importlib.import_module` yanlış modülü yükleyebilir

**Düzeltme Önerisi:**
```python
original_path = sys.path.copy()
try:
    sys.path.insert(0, package_root)
    # ... agent yükleme
finally:
    sys.path[:] = original_path
```

---

### ~~BUG-004: `pip install --break-system-packages` Güvenlik Riski~~ ✅ ÇÖZÜLDÜ (hiç kullanılmıyordu)

**Dosya:** `norn/api.py`, satır 1320
**Etki:** Sistem Python paketlerini bozma riski

```python
pip_base = [sys.executable, "-m", "pip", "install", "-q", "--break-system-packages"]
```

**Problem:** `--break-system-packages` bayrağı, pip'in sistem dizinine yazmasına izin verir. Bir agent kötü niyetli bir `requirements.txt` ile gelirse, **sistem Python paketlerini bozabilir** veya zararlı paket kurabilir.

**Düzeltme Önerisi:**
- `--break-system-packages` bayrağını kaldırın
- Agent bağımlılıklarını izole bir virtual environment'a kurun
- Veya en azından `--user` bayrağı kullanın

---

### ~~BUG-005: Zipfile Path Traversal Güvenlik Açığı~~ ✅ ÇÖZÜLDÜ (`_safe_extract()` mevcuttu)

**Dosya:** `norn/api.py`, satır 1049-1050
**Etki:** ZIP dosyası ile dizin geçiş saldırısı (directory traversal)

```python
with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
    zip_ref.extractall(extract_path)
```

**Problem:** `extractall()` kötü niyetli ZIP dosyalarının `../../etc/passwd` gibi yollarla dosya sisteminize yazmasına izin verir. Bu bilinen bir güvenlik açığıdır (CVE geçmişi var).

**Düzeltme Önerisi:**
```python
import zipfile

def safe_extract(zip_ref, extract_path):
    for member in zip_ref.namelist():
        # Normalize ve path traversal kontrolü
        member_path = Path(extract_path) / member
        if not str(member_path.resolve()).startswith(str(extract_path.resolve())):
            raise ValueError(f"Path traversal detected: {member}")
    zip_ref.extractall(extract_path)
```

---

## ⚠️ ORTA SEVİYE BUGLAR (Severity: MEDIUM)

### ~~BUG-006: Session JSON Dosyalarında Race Condition~~ ✅ ÇÖZÜLDÜ

**Dosya:** `norn/api.py`, çeşitli yerler  
**Etki:** Veri kaybı veya bozulması

**Durum:** Tüm session yazma işlemleri artık `_atomic_write_json()` kullanıyor. Hiçbir yerde doğrudan `json.dump(session, ...)` kalmadı.

---

### ~~BUG-007: Agent Registry Dosyasında Lock Mekanizması Yok~~ ✅ ÇÖZÜLDÜ

**Dosya:** `norn/api.py`, çeşitli endpoint'ler  
**Etki:** Aynı anda iki agent import edildiğinde veri kaybı

**Durum:** `_registry_lock = threading.Lock()` eklendi. Tüm registry read-modify-write blokları (`import_github_agent`, `import_zip_agent`, `run_agent`, `delete_agent`, `register_hook_agent`, `_reset_agent_status`) artık `_registry_lock` altında çalışıyor. Salt okunur erişimler `_read_registry()` helper'ı ile yapılıyor.

---

### ~~BUG-008: Agent Discovery'de `_find_functions()` AsyncFunctionDef'i Yakalamıyor~~ ✅ ÇÖZÜLDÜ

**Dosya:** `norn/utils/agent_discovery.py`, satır 210  
**Etki:** Async fonksiyonlar "is_async: False" olarak raporlanıyordu

**Durum:** Kod zaten `isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))` kullanıyor. `is_async` alanı doğru şekilde `isinstance(node, ast.AsyncFunctionDef)` ile hesaplanıyor.

---

### BUG-009: `_detect_agent_type()` Case-Sensitive Sorun

**Dosya:** `norn/utils/agent_discovery.py`, satır 256-278  
**Etki:** `from strands import Agent` yerine `from Strands import Agent` yazılırsa algılanmıyor — ama aslında daha büyük sorun var:

```python
code_lower = code.lower()
if 'from strands import agent' in code_lower:
    return "Strands Agent"
```

**Problem:** `from strands import Agent` doğru yakalansa da, `import strands` ya da `from strands.agents import Agent` gibi varyasyonlar kaçırılıyor. İmport kontrolü AST tabanlı olmalı (zaten `_find_imports()` bunu yapıyor, ama `_detect_agent_type()` kullanmıyor).

---

### ~~BUG-010: `_extract_tool_name()` None Dönebilir Ama Type Hint String~~ ✅ ÇÖZÜLDÜ

**Dosya:** `norn/utils/agent_discovery.py`, satır 196  
**Etki:** Tip anotasyonu yanlıştı

**Durum:** Tip anotasyonu `Optional[str]` olarak düzeltilmiş. Fonksiyon imzası artık `def _extract_tool_name(self, node: ast.AST) -> Optional[str]`.

---

### BUG-011: Temp Dizinleri Temizlenmiyor (Git Clone)

**Dosya:** `norn/api.py`, satır 908  
**Etki:** Disk alanı dolması

```python
temp_dir = Path(tempfile.mkdtemp())
clone_path = temp_dir / "agent_repo"
```

`clone_path` agent registry'de saklanıyor, ama agent silindiğinde `temp_dir` (üst dizin) değil, `clone_path` (alt dizin) siliniyor. `temp_dir` boş dizin olarak kalır. Ayrıca import başarısız olduğunda (exception durumunda) `temp_dir` hiç temizlenmiyor.

---

### ~~BUG-012: WebSocket'te Auth Kontrolü Yok~~ ✅ ÇÖZÜLDÜ (API_KEY kontrolü mevcuttu)

**Dosya:** `norn/api.py`, satır 1883-1926
**Etki:** API anahtarı ayarlanmış olsa bile WebSocket'e kimlik doğrulama olmadan bağlanılabilir

```python
@app.websocket("/ws/sessions")
async def websocket_sessions(websocket: WebSocket):
    await manager.connect(websocket)  # ← API key kontrolü yok!
```

REST endpoint'ler `Depends(verify_api_key)` ile korunan ama WebSocket bağlantısı açık.

---

### ~~BUG-013: `_save_config()` Atomik Değil~~ ✅ ÇÖZÜLDÜ

**Dosya:** `norn/api.py`, satır 170-172  
**Etki:** Konfigürasyon dosyası bozulabiliyordu

**Durum:** `_save_config()` artık `_atomic_write_json(CONFIG_FILE, config)` kullanıyor.

---

## 📋 DÜŞÜK SEVİYE BUGLAR (Severity: LOW)

### ~~BUG-014: `.env` Dosyası Git'te~~ ✅ ÇÖZÜLDÜ (dosya kaldırıldı)

**Dosya:** `.gitignore` satır 28  
**Etki:** git geçmişinde credential sızıntısı riski

**Durum:** `.env` dosyası proje kökünde artık mevcut değil.

---

### ~~BUG-015: `appointments.db` ve `result.txt` Proje Kökünde~~ ✅ ÇÖZÜLDÜ (dosyalar kaldırıldı)

**Dosya:** Proje kök dizini  
**Etki:** Çalışma alanı izolasyonu ihlali

**Durum:** `appointments.db` ve `result.txt` artık proje kökünde mevcut değil.

---

### ~~BUG-016: `import_zip_agent` Aynı Anda İki ZIP Yüklendiğinde ID Çakışması~~ ✅ ÇÖZÜLDÜ

**Dosya:** `norn/api.py`, satır 1110  
**Etki:** Aynı saniyede iki ZIP yüklendiğinde aynı ID üretiliyordu

**Durum:** ZIP agent ID'si artık `f"zip-{uuid.uuid4().hex[:12]}"` kullanarak UUID tabanlı benzersiz ID üretiyor.

---

### BUG-017: `agent_runner.py` Hook Enjeksiyonunda Eski API Kullanıyor

**Dosya:** `norn/utils/agent_runner.py`, satır 172-175  
**Etki:** Hook eklenmesi çalışmıyor

```python
if not hasattr(agent_or_func, '_hooks'):
    agent_or_func._hooks = []
agent_or_func._hooks.append(guard)
```

Bu, Strands'ın eski dahili API'sini kullanıyor. Yeni Strands sürümlerinde `HookRegistry` ve `add_hook()` kullanılıyor (`api.py`'deki satır 1504'te doğru yapılıyor). Bu dosya muhtemelen eski ve güncellenmemiş.

---

### BUG-018: `quality_evaluator.py` Boş Step Listesinde Division by Zero

**Dosya:** `norn/agents/quality_evaluator.py`, satır 207  
**Etki:** Edge case crash (korunuyor ama riskli)

```python
avg_security = sum(evaluated_scores) / len(evaluated_scores) if evaluated_scores else 0
```

`evaluated_scores` boş ise 0 döner. Ama sonraki `len(steps) == 0` kontrolü (satır 187) bu durumu önceden yakalıyor, bu yüzden pratikte tetiklenmez. Yine de defensif kodlama açısından not edilmelidir.

---

### BUG-019: Frontend'de `tool_analysis`, `decision_observations`, `efficiency_explanation` Type Cast

**Dosya:** `norn-dashboard/App.tsx`, satır 242-244  
**Etki:** Type-safety bypass

```typescript
toolAnalysis: (s as any).tool_analysis,
decisionObservations: (s as any).decision_observations,
efficiencyExplanation: (s as any).efficiency_explanation,
```

`SessionData` interface'i bu alanları tanımlamıyor, bu yüzden `as any` ile cast ediliyor. Bu alanlar `SessionData` interface'ine eklenmeli.

---

### BUG-020: Frontend `types.ts` ile `services/api.ts` Arasında Tip Uyumsuzluğu

**Dosya:** `norn-dashboard/types.ts` ve `norn-dashboard/services/api.ts`  
**Etki:** Çift tip tanımlama, bakım zorluğu

Aynı konseptler (Session, Issue, Step) her iki dosyada da tanımlanıyor:
- `api.ts`: `SessionData`, `SessionIssue`, `SessionStep` (backend'e yakın)
- `types.ts`: `Session`, `SessionIssueDetail`, `AgentStep` (frontend'e yakın)

`App.tsx`'de sürekli `convertSessionData()` ile dönüştürme yapılıyor. Bu çift yapı hataya açık.

---

### ~~BUG-021: `_find_entry_points()` 'da `ast.Eq` Kontrolü Çok Geniş~~ ✅ ÇÖZÜLDÜ

**Dosya:** `norn/utils/agent_discovery.py`, satır 290-298  
**Etki:** False positive entry point tespiti

**Durum:** `_find_entry_points()` artık tam doğrulama yapıyor: `isinstance(node.test.left, ast.Name)`, `node.test.left.id == "__name__"`, `isinstance(node.test.comparators[0], ast.Constant)`, ve `node.test.comparators[0].value == "__main__"` kontrolleri mevcut.

---

## 📊 Bug Özet Tablosu

| ID | Severity | Dosya | Kısa Açıklama | Durum |
|---|---|---|---|---|
| ~~BUG-001~~ | ~~🔴 HIGH~~ | interceptor.py | ~~asyncio.create_task() event loop olmadan~~ | ✅ Çözüldü |
| ~~BUG-002~~ | ~~🔴 HIGH~~ | api.py | ~~os.chdir() thread-safety sorunu~~ | ✅ Çözüldü |
| ~~BUG-003~~ | ~~🔴 HIGH~~ | api.py | ~~sys.path kirlenmesi~~ | ✅ Çözüldü |
| ~~BUG-004~~ | ~~🔴 HIGH~~ | api.py | ~~--break-system-packages güvenlik riski~~ | ✅ Çözüldü |
| ~~BUG-005~~ | ~~🔴 HIGH~~ | api.py | ~~ZIP path traversal güvenlik açığı~~ | ✅ Çözüldü |
| ~~BUG-006~~ | ~~🟡 MEDIUM~~ | api.py | ~~Session yazma race condition~~ | ✅ Çözüldü |
| ~~BUG-007~~ | ~~🟡 MEDIUM~~ | api.py | ~~Registry dosya kilidi eksik~~ | ✅ Çözüldü |
| ~~BUG-008~~ | ~~🟡 MEDIUM~~ | agent_discovery.py | ~~AsyncFunctionDef yakalanmıyor~~ | ✅ Çözüldü |
| BUG-009 | 🟡 MEDIUM | agent_discovery.py | Agent tipi algılama eksiklikleri | ⚠️ Açık |
| ~~BUG-010~~ | ~~🟡 MEDIUM~~ | agent_discovery.py | ~~Yanlış tip anotasyonu~~ | ✅ Çözüldü |
| BUG-011 | 🟡 MEDIUM | api.py | Temp dizin temizleme eksik | ⚠️ Açık |
| ~~BUG-012~~ | ~~🟡 MEDIUM~~ | api.py | ~~WebSocket auth bypass~~ | ✅ Çözüldü |
| ~~BUG-013~~ | ~~🟡 MEDIUM~~ | api.py | ~~Config yazma atomik değil~~ | ✅ Çözüldü |
| ~~BUG-014~~ | ~~🟢 LOW~~ | .env | ~~Olası credential sızıntısı~~ | ✅ Dosya kaldırıldı |
| ~~BUG-015~~ | ~~🟢 LOW~~ | root/ | ~~Workspace izolasyon ihlali~~ | ✅ Dosyalar kaldırıldı |
| ~~BUG-016~~ | ~~🟢 LOW~~ | api.py | ~~ZIP agent ID çakışması~~ | ✅ Çözüldü |
| BUG-017 | 🟢 LOW | agent_runner.py | Eski Hook API kullanımı | ⚠️ Açık |
| BUG-018 | 🟢 LOW | quality_evaluator.py | Division by zero edge case | 🔵 Korumalı |
| BUG-019 | 🟢 LOW | App.tsx | Type-safety bypass | ⚠️ Açık |
| BUG-020 | 🟢 LOW | types.ts / api.ts | Çift tip tanımlama | ⚠️ Açık |
| ~~BUG-021~~ | ~~🟢 LOW~~ | agent_discovery.py | ~~Entry point false positive~~ | ✅ Çözüldü |

---

## 📈 Genel Durum

- **Toplam:** 21 bug
- **Çözülen:** 16 (BUG-001–008, 010, 012–016, 021)
- **Açık kalan:** 5 (BUG-009, 011, 017, 019, 020)
  - **Gerçek bug:** BUG-009 (agent tipi algılama), BUG-011 (temp dizin temizleme)
  - **Eski/bakım:** BUG-017 (eski Hook API), BUG-019/020 (frontend tip sorunları)
- **Korumalı edge case:** BUG-018 (pratikte tetiklenmez)
