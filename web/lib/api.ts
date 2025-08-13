const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function fetchPreset(id: string) {
  try {
    const res = await fetch(`${BASE}/presets/${id}`, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`Preset ${id} not found`);
    }
    return res.json();
  } catch (error) {
    console.error("Error fetching preset:", error);
    throw error;
  }
}
