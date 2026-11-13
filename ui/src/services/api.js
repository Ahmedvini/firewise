// ============================================================
// BACKEND CONNECTION POINT
// The RAG backend does not exist yet. To connect it later:
//   1. Create a file named .env in the project root containing:
//        VITE_API_BASE_URL=http://localhost:8000
//   2. Restart `npm run dev`.
// Until then, askQuestion() makes no network request.
// ============================================================

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

/**
 * Sends a question to POST {API_BASE_URL}/ask.
 * Expected response JSON:
 *   { answer, key_findings: [], sources: [{title, experiment, year, url}], related_experiments: [] }
 * Returns { status: "not_connected" } when no backend URL is configured.
 */
export async function askQuestion(question) {
  if (!API_BASE_URL) return { status: "not_connected" };

  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) throw new Error(`The server responded with status ${response.status}.`);

  const data = await response.json();
  return { status: "ok", ...data };
}
