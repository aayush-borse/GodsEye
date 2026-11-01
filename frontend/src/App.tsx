import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity, ArrowDownToLine, ArrowUpRight, Check, ChevronRight, CircleHelp,
  Database, FileUp, Globe2, Layers3, LoaderCircle, Menu, RadioTower,
  RefreshCw, ShieldCheck, Waves, X,
} from 'lucide-react';
import './styles.css';

type Variable = { name: string; dimensions: string[]; dtype: string; units?: string | null };
type Coordinate = { name: string; dimensions: string[]; dtype: string; size: number; min_value?: number | null; max_value?: number | null };
type DatasetMetadata = { dataset_id: string; filename: string; variables: Variable[]; coordinates: Coordinate[]; dimensions: Record<string, number> };
type UploadResponse = { dataset_id: string; filename: string; metadata: DatasetMetadata };
type ApiState = 'checking' | 'online' | 'offline';

const DATASET_KEY = 'godseye.datasetId';
const DATASET_NAME_KEY = 'godseye.datasetName';
const MAX_UPLOAD_BYTES = 1_000_000_000;

function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    let frame = 0;
    let animationFrame = 0;
    let width = 0;
    let height = 0;
    let points: Array<{ a: number; b: number; r: number; hue: number }> = [];
    let pointerX = 0;
    let pointerY = 0;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const ratio = Math.min(window.devicePixelRatio || 1, 1.6);
      width = rect.width; height = rect.height;
      canvas.width = Math.floor(width * ratio); canvas.height = Math.floor(height * ratio);
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      const count = Math.min(1500, Math.max(650, Math.floor(width * height / 350)));
      points = Array.from({ length: count }, () => ({
        a: Math.random() * Math.PI * 2,
        b: Math.random() * Math.PI * 2,
        r: 0.72 + Math.random() * 0.55,
        hue: Math.random(),
      }));
    };
    const onMove = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointerX = (event.clientX - rect.left) / rect.width - 0.5;
      pointerY = (event.clientY - rect.top) / rect.height - 0.5;
    };
    const draw = () => {
      if (!ctx) return;
      ctx.clearRect(0, 0, width, height);
      const cx = width * 0.52 + pointerX * 12;
      const cy = height * 0.49 + pointerY * 8;
      const radius = Math.min(width * 0.24, height * 0.43, 230);
      const rotation = reduced ? 0.18 : frame * 0.0017;
      for (const p of points) {
        const u = p.a + rotation;
        const v = p.b;
        const tube = radius * 0.31 * p.r;
        const ring = radius + tube * Math.cos(v);
        const x = Math.cos(u) * ring;
        const y = Math.sin(u) * ring * 0.72;
        const z = tube * Math.sin(v) + Math.sin(u * 2 + v) * 5;
        const perspective = 1 / (1.15 + z / (radius * 2.6));
        const px = cx + x * perspective;
        const py = cy + y * perspective;
        const depth = (z + tube) / (tube * 2);
        const alpha = 0.14 + depth * 0.58;
        const hue = p.hue < 0.48 ? 34 + p.hue * 35 : 245 + p.hue * 50;
        ctx.fillStyle = `hsla(${hue}, 95%, ${58 + depth * 20}%, ${alpha})`;
        const size = 0.55 + depth * 1.05;
        ctx.fillRect(px, py, size, size);
      }
      frame += 1;
      if (!reduced) animationFrame = requestAnimationFrame(draw);
    };
    resize(); draw();
    window.addEventListener('resize', resize);
    canvas.addEventListener('pointermove', onMove);
    return () => { cancelAnimationFrame(animationFrame); window.removeEventListener('resize', resize); canvas.removeEventListener('pointermove', onMove); };
  }, []);
  return <canvas className="particle-field" ref={canvasRef} aria-hidden="true" />;
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function App() {
  const [apiState, setApiState] = useState<ApiState>('checking');
  const [datasetId, setDatasetId] = useState(() => localStorage.getItem(DATASET_KEY) || 'io-model-4d');
  const [datasetName, setDatasetName] = useState(() => localStorage.getItem(DATASET_NAME_KEY) || 'Synthetic demonstration model');
  const [metadata, setMetadata] = useState<DatasetMetadata | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [dragging, setDragging] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const checkBackend = useCallback(async () => {
    try {
      const response = await fetch('/health', { signal: AbortSignal.timeout(5000) });
      if (!response.ok) throw new Error('Backend health check failed');
      setApiState('online');
    } catch { setApiState('offline'); }
  }, []);

  const loadMetadata = useCallback(async (id: string) => {
    if (!id) return;
    try {
      const response = await fetch(`/datasets/${encodeURIComponent(id)}`);
      if (!response.ok) { setMetadata(null); return; }
      setMetadata(await response.json() as DatasetMetadata);
    } catch { setMetadata(null); }
  }, []);

  useEffect(() => { void checkBackend(); const timer = window.setInterval(checkBackend, 30000); return () => window.clearInterval(timer); }, [checkBackend]);
  useEffect(() => { void loadMetadata(datasetId); }, [datasetId, loadMetadata]);

  function chooseFile(candidate?: File) {
    setError(''); setNotice('');
    if (!candidate) return;
    if (!/\.(nc|nc4|cdf)$/i.test(candidate.name)) { setFile(null); setError('Choose a NetCDF file (.nc, .nc4 or .cdf).'); return; }
    if (candidate.size > MAX_UPLOAD_BYTES) { setFile(null); setError('This file exceeds the 1 GB upload limit.'); return; }
    setFile(candidate);
  }

  async function upload() {
    if (!file || busy) return;
    setBusy(true); setError(''); setNotice('Validating and indexing your dataset…');
    try {
      const body = new FormData(); body.append('file', file);
      const response = await fetch('/datasets/upload', { method: 'POST', body });
      const payload = await response.json().catch(() => ({})) as { detail?: string } & Partial<UploadResponse>;
      if (!response.ok) throw new Error(payload.detail || `Upload failed (${response.status}).`);
      if (!payload.dataset_id || !payload.metadata) throw new Error('The server returned an incomplete dataset response.');
      localStorage.setItem(DATASET_KEY, payload.dataset_id);
      localStorage.setItem(DATASET_NAME_KEY, payload.filename || file.name);
      setDatasetId(payload.dataset_id); setDatasetName(payload.filename || file.name);
      setMetadata(payload.metadata); setFile(null);
      if (inputRef.current) inputRef.current.value = '';
      setNotice('Dataset indexed. Your scientific workspace is ready.');
    } catch (err) {
      setNotice(''); setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
    } finally { setBusy(false); }
  }

  function openExplorer() {
    if (!datasetId) return;
    localStorage.setItem(DATASET_KEY, datasetId);
    window.location.assign('/ocean.html');
  }

  const variableCount = metadata?.variables?.length ?? 0;
  const dimensionCount = Object.keys(metadata?.dimensions ?? {}).length;
  const coordinateCount = metadata?.coordinates?.length ?? 0;

  return (
    <div className="site-shell">
      <header className="nav-bar">
        <a className="wordmark" href="/" aria-label="God's Eye home"><span className="mark"><Waves size={18} /></span><span>GOD'S EYE<small>OCEAN INTELLIGENCE</small></span></a>
        <nav className="nav-links" aria-label="Main navigation"><a href="#workspace">Workspace</a><a href="#workflow">Method</a><a href="/docs" target="_blank" rel="noreferrer">API reference <ArrowUpRight size={12}/></a></nav>
        <div className="nav-actions"><span className={`connection ${apiState}`}><i />{apiState === 'online' ? 'SYSTEM ONLINE' : apiState === 'offline' ? 'API UNAVAILABLE' : 'CONNECTING'}</span><button className="icon-button" onClick={() => setShowHelp(true)} aria-label="Help"><CircleHelp size={17}/></button><a className="nav-cta" href="#workspace">Start a session <ArrowUpRight size={13}/></a></div>
      </header>

      <main>
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy"><p className="eyebrow"><span /> OCEAN DATA · MODEL INTELLIGENCE · SCIENTIFIC EVIDENCE</p><h1 id="hero-title">See the ocean<br/><em>beneath the surface.</em></h1><p className="hero-description">Explore ocean model fields, inspect in-situ observations, and test where simulated conditions meet the real ocean — with transparent scientific evidence at every step.</p><div className="hero-actions"><a className="button-primary" href="#workspace">Enter workspace <ChevronRight size={16}/></a><a className="text-link" href="#workflow">How it works <ArrowUpRight size={14}/></a></div><div className="hero-meta"><span><b>01</b> INGEST</span><span><b>02</b> EXPLORE</span><span><b>03</b> VALIDATE</span></div></div>
          <div className="hero-visual"><ParticleField/><div className="visual-label label-top"><span>GLOBAL OCEAN SYSTEM</span><b>4D</b></div><div className="visual-label label-bottom"><span>MODEL × OBSERVATION</span><b>LIVE WORKSPACE</b></div><div className="visual-coordinate">18° 32' N&nbsp;&nbsp; 64° 12' E<br/>0.0 — 5,000 M DEPTH</div></div>
          <div className="hero-side-note">A clearer view of complex ocean systems.<br/>Built for exploration, grounded in evidence.</div>
        </section>

        <section className="workspace-section" id="workspace">
          <div className="section-heading"><div><p className="eyebrow">YOUR SCIENTIFIC WORKSPACE</p><h2>Start with the data.</h2></div><p>Bring a NetCDF model into the workspace, or continue with a dataset already loaded in this browser.</p></div>
          <div className="workspace-grid">
            <section className={`upload-panel ${dragging ? 'dragging' : ''}`} onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(e) => { e.preventDefault(); setDragging(false); chooseFile(e.dataTransfer.files[0]); }}>
              <div className="panel-topline"><span>01 / DATA INGESTION</span><FileUp size={17}/></div><h3>Load an ocean model</h3><p className="panel-description">Upload a CF-aware NetCDF dataset to inspect its variables, coordinates and dimensions before opening the 3D explorer.</p>
              <button className="dropzone" onClick={() => inputRef.current?.click()} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}><input ref={inputRef} type="file" accept=".nc,.nc4,.cdf,application/x-netcdf" onChange={(e) => chooseFile(e.target.files?.[0])}/><span className="upload-symbol"><ArrowDownToLine size={20}/></span><strong>{file ? file.name : 'Drop your dataset here'}</strong><small>{file ? `${formatBytes(file.size)} · ready to inspect` : 'or browse files · .nc, .nc4, .cdf · up to 1 GB'}</small></button>
              {error && <div className="feedback error" role="alert"><X size={14}/>{error}</div>}{notice && <div className="feedback success" role="status"><Check size={14}/>{notice}</div>}
              <button className="button-primary upload-button" disabled={!file || busy || apiState !== 'online'} onClick={upload}>{busy ? <><LoaderCircle className="spin" size={15}/> Processing dataset</> : <>Upload & inspect <ChevronRight size={15}/></>}</button>
              {apiState === 'offline' && <p className="inline-warning">The API is unreachable. Start the backend to upload a dataset.</p>}
            </section>

            <section className="dataset-panel">
              <div className="panel-topline"><span>02 / ACTIVE DATA SESSION</span><Database size={17}/></div><div className="dataset-title-row"><div><h3>{datasetName}</h3><p>{metadata ? 'Indexed and available in this browser session' : datasetId ? 'Saved session reference · reconnect to inspect metadata' : 'No dataset loaded yet'}</p></div><span className={`dataset-state ${metadata ? 'ready' : 'idle'}`}><i/>{metadata ? 'READY' : 'IDLE'}</span></div>
              {metadata ? <><div className="dataset-id"><span>SESSION ID</span><code>{datasetId}</code></div><div className="data-stats"><div><b>{dimensionCount}</b><span>DIMENSIONS</span></div><div><b>{variableCount}</b><span>VARIABLES</span></div><div><b>{coordinateCount}</b><span>COORDINATES</span></div></div><div className="variable-preview"><div className="list-heading">AVAILABLE VARIABLES <span>{variableCount} FOUND</span></div>{metadata.variables.slice(0, 5).map((v) => <div className="variable-row" key={v.name}><span>{v.name}</span><small>{v.units || v.dtype}</small></div>)}{variableCount > 5 && <p className="more-vars">+ {variableCount - 5} more variables in explorer</p>}</div></> : <div className="empty-session"><div className="empty-icon"><Layers3 size={21}/></div><div><strong>{datasetId ? 'Session metadata unavailable' : 'Your workspace is waiting'}</strong><p>{datasetId ? 'The server may have restarted and cleared its in-memory dataset session. Upload the file again to restore it.' : 'Upload a NetCDF file to see its scientific structure and open the explorer.'}</p></div></div>}
              <button className="button-secondary" onClick={openExplorer} disabled={!datasetId || !metadata}>Open scientific explorer <ArrowUpRight size={14}/></button>
              {datasetId && !metadata && <button className="subtle-button" onClick={() => void loadMetadata(datasetId)}><RefreshCw size={13}/> Retry session lookup</button>}
            </section>
          </div>
        </section>

        <section className="method-section" id="workflow"><div className="method-heading"><p className="eyebrow">FROM RAW DATA TO SCIENTIFIC CONTEXT</p><h2>One connected workflow.<br/><em>No black boxes.</em></h2></div><div className="method-steps"><article><span>01</span><Database size={18}/><h3>Ingest</h3><p>Read NetCDF structure, coordinates, variables and metadata on the server.</p></article><article><span>02</span><Globe2 size={18}/><h3>Explore</h3><p>Navigate spatial, depth and time dimensions through the 3D field explorer.</p></article><article><span>03</span><RadioTower size={18}/><h3>Collocate</h3><p>Find nearby in-situ profiles and compare observations with model output.</p></article><article><span>04</span><ShieldCheck size={18}/><h3>Validate</h3><p>Review interpolation, quality flags, distance and confidence evidence.</p></article></div></section>
      </main>

      <footer className="site-footer"><a className="wordmark" href="/"><span className="mark"><Waves size={17}/></span><span>GOD'S EYE<small>OCEAN INTELLIGENCE</small></span></a><span>SCIENTIFIC VISUALIZATION · MODEL VALIDATION · EVIDENCE</span><span>SIH26067</span></footer>
      {showHelp && <div className="modal-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setShowHelp(false); }}><section className="help-modal" role="dialog" aria-modal="true" aria-labelledby="help-title"><button className="modal-close" onClick={() => setShowHelp(false)} aria-label="Close help"><X size={18}/></button><p className="eyebrow">QUICK GUIDE</p><h2 id="help-title">Working with GOD'S EYE</h2><ol><li><b>Prepare your data.</b><span>Use a NetCDF file containing ocean variables and usable geographic/depth/time coordinates.</span></li><li><b>Upload and inspect.</b><span>The backend validates and opens the dataset, then returns its metadata.</span></li><li><b>Explore the model.</b><span>Open the scientific explorer to inspect slices, volumes and vectors.</span></li><li><b>Validate against observations.</b><span>Use available Argo profiles for collocation and comparison. Observation availability depends on the configured profile dataset.</span></li></ol><p className="help-note">GOD'S EYE reports the evidence available in the selected dataset. A missing observation or unsupported variable is not treated as a successful scientific comparison.</p></section></div>}
    </div>
  );
}

export default App;
