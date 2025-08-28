"use client";
import { useState, useEffect } from "react";
import { API_BASE, authHeaders } from "../../../lib/api";

type PresetRow = { id:string; name:string; version:string; source:string; counts:{pillars:number;capabilities:number;questions:number}};

export default function AdminPresets() {
  const [items, setItems] = useState<PresetRow[]>([]);
  const [msg, setMsg] = useState<string>("");

  async function load() {
    try {
      const r = await fetch(`${API_BASE}/presets`, { headers: authHeaders() });
      if (!r.ok) {
        setMsg(`Failed to load presets: ${r.status}`);
        return;
      }
      setItems(await r.json());
    } catch (error) {
      setMsg(`Error loading presets: ${error}`);
    }
  }

  useEffect(()=>{ load(); },[]);

  async function onUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      const r = await fetch(`${API_BASE}/presets/upload`, {
        method: "POST",
        headers: { ...authHeaders() }, // do NOT set content-type here
        body: fd
      });
      if (!r.ok) { 
        const errorText = await r.text();
        setMsg(`Upload failed: ${r.status} - ${errorText}`); 
        return; 
      }
      const data = await r.json();
      setMsg(`Uploaded: ${data.name} (${data.id})`);
      await load();
      e.currentTarget.reset();
    } catch (error) {
      setMsg(`Upload error: ${error}`);
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Admin · Presets</h1>
      <form onSubmit={onUpload} className="border rounded p-4 space-y-3">
        <div className="text-sm text-gray-600">Upload a preset JSON</div>
        <input name="file" type="file" accept="application/json" className="border rounded p-2" required />
        <button className="px-3 py-1 border rounded bg-blue-500 text-white hover:bg-blue-600" type="submit">Upload</button>
        {msg && <div className="text-sm">{msg}</div>}
      </form>
      <div className="border rounded p-4">
        <div className="font-medium mb-2">Available Presets</div>
        <table className="w-full text-sm">
          <thead><tr className="border-b">
            <th className="text-left py-2">Name</th>
            <th className="text-left py-2">ID</th>
            <th className="text-left py-2">Version</th>
            <th className="text-left py-2">Counts (P/C/Q)</th>
            <th className="text-left py-2">Source</th>
            <th className="text-left py-2">Actions</th>
          </tr></thead>
          <tbody>
            {items.map(it=>(
              <tr key={it.id} className="border-t">
                <td className="py-2">{it.name}</td>
                <td className="py-2 font-mono text-xs">{it.id}</td>
                <td className="py-2">{it.version}</td>
                <td className="py-2">{it.counts.pillars}/{it.counts.capabilities}/{it.counts.questions}</td>
                <td className="py-2">
                  <span className={`px-2 py-1 rounded text-xs ${it.source === 'bundled' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'}`}>
                    {it.source}
                  </span>
                </td>
                <td className="py-2 space-x-2">
                  <a className="underline text-blue-600 hover:text-blue-800" href={`${API_BASE}/presets/${it.id}`} target="_blank" rel="noopener noreferrer">Preview</a>
                  <button 
                    className="underline text-gray-600 hover:text-gray-800"
                    onClick={() => navigator.clipboard.writeText(it.id)}
                  >
                    Copy ID
                  </button>
                </td>
              </tr>
           ))}
          </tbody>
        </table>
        {items.length === 0 && (
          <div className="text-gray-500 text-center py-4">No presets available</div>
        )}
      </div>
    </div>
  );
}
