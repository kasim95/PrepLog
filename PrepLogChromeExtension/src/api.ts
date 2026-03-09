import { ProblemData, SubmissionData } from "./types";

const DEFAULT_SERVER_URL = "http://localhost:8000";

/** Get the configured server URL from chrome storage. */
async function getServerUrl(): Promise<string> {
  const result = await chrome.storage.local.get("serverUrl");
  return (result.serverUrl as string) || DEFAULT_SERVER_URL;
}

/** Track a LeetCode problem in PrepLogServer. */
export async function trackProblem(problem: ProblemData): Promise<Response> {
  const serverUrl = await getServerUrl();
  return fetch(`${serverUrl}/api/leetcode/problem`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: problem.title,
      description: problem.description,
      difficulty: problem.difficulty,
      leetcode_slug: problem.slug,
    }),
  });
}

/** Send a code submission to PrepLogServer. */
export async function sendSubmission(submission: SubmissionData): Promise<Response> {
  const serverUrl = await getServerUrl();
  return fetch(`${serverUrl}/api/leetcode/submission`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      leetcode_slug: submission.slug,
      code: submission.code,
      language: submission.language,
    }),
  });
}

/** Check server connectivity. */
export async function checkHealth(): Promise<boolean> {
  try {
    const serverUrl = await getServerUrl();
    const resp = await fetch(`${serverUrl}/health`, { method: "GET" });
    return resp.ok;
  } catch {
    return false;
  }
}
