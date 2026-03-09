/** Data about a detected LeetCode problem. */
export interface ProblemData {
  title: string;
  description: string;
  difficulty: string;
  slug: string;
}

/** Data about a LeetCode code submission. */
export interface SubmissionData {
  slug: string;
  code: string;
  language: string;
}

/** Messages sent between content script and background service worker. */
export type ExtensionMessage =
  | { type: "PROBLEM_DETECTED"; data: ProblemData }
  | { type: "SUBMISSION_DETECTED"; data: SubmissionData }
  | { type: "GET_CURRENT_PROBLEM" }
  | { type: "TRACK_PROBLEM" }
  | { type: "SEND_SUBMISSION" };

/** Response from the background to popup. */
export interface PopupState {
  currentProblem: ProblemData | null;
  serverUrl: string;
  connected: boolean;
  lastError: string | null;
}
