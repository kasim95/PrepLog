/**
 * PrepLog Extension Popup
 * Shows current problem, connection status, and manual tracking controls.
 */

import { ProblemData } from "./types";
import { checkHealth } from "./api";

// DOM elements
const serverUrlInput = document.getElementById("server-url") as HTMLInputElement;
const saveUrlBtn = document.getElementById("save-url") as HTMLButtonElement;
const statusDiv = document.getElementById("status") as HTMLDivElement;
const problemInfoDiv = document.getElementById("problem-info") as HTMLDivElement;
const trackBtn = document.getElementById("track-btn") as HTMLButtonElement;
const submitBtn = document.getElementById("submit-btn") as HTMLButtonElement;
const messageDiv = document.getElementById("message") as HTMLDivElement;

let currentProblem: ProblemData | null = null;

/** Initialize the popup. */
async function init(): Promise<void> {
  // Load saved server URL
  const result = await chrome.storage.local.get("serverUrl");
  if (result.serverUrl) {
    serverUrlInput.value = result.serverUrl as string;
  }

  // Set up event listeners
  saveUrlBtn.addEventListener("click", saveServerUrl);
  trackBtn.addEventListener("click", trackProblem);
  submitBtn.addEventListener("click", sendSubmission);

  // Check server connection
  await checkConnection();

  // Get current problem from background
  chrome.runtime.sendMessage({ type: "GET_CURRENT_PROBLEM" }, (response) => {
    if (response?.problem) {
      currentProblem = response.problem;
      displayProblem(currentProblem);
    }
  });

  // Also try to get problem directly from content script
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id && tab.url?.includes("leetcode.com/problems/")) {
    chrome.tabs.sendMessage(tab.id, { type: "GET_CURRENT_PROBLEM" }, (response) => {
      if (chrome.runtime.lastError) return;
      if (response?.problem) {
        currentProblem = response.problem;
        displayProblem(currentProblem);
      }
    });
  }
}

/** Save the server URL to chrome storage. */
async function saveServerUrl(): Promise<void> {
  const url = serverUrlInput.value.trim().replace(/\/$/, "");
  await chrome.storage.local.set({ serverUrl: url });
  showMessage("Server URL saved", "success");
  await checkConnection();
}

/** Check server connection and update status. */
async function checkConnection(): Promise<void> {
  statusDiv.textContent = "Status: Checking...";
  statusDiv.className = "status status-disconnected";

  const connected = await checkHealth();
  if (connected) {
    statusDiv.textContent = "Status: Connected ✓";
    statusDiv.className = "status status-connected";
  } else {
    statusDiv.textContent = "Status: Disconnected ✗";
    statusDiv.className = "status status-disconnected";
  }
}

/** Display problem information. */
function displayProblem(problem: ProblemData | null): void {
  if (!problem) {
    problemInfoDiv.innerHTML = '<span class="muted">No problem detected</span>';
    trackBtn.disabled = true;
    submitBtn.disabled = true;
    return;
  }

  const diffClass = problem.difficulty
    ? `difficulty-${problem.difficulty.toLowerCase()}`
    : "";

  problemInfoDiv.innerHTML = `
    <span class="problem-title">${escapeHtml(problem.title)}</span>
    ${
      problem.difficulty
        ? `<span class="problem-difficulty ${diffClass}">${problem.difficulty}</span>`
        : ""
    }
  `;

  trackBtn.disabled = false;
  submitBtn.disabled = false;
}

/** Track the current problem. */
async function trackProblem(): Promise<void> {
  trackBtn.disabled = true;
  try {
    const response = await new Promise<any>((resolve) => {
      chrome.runtime.sendMessage({ type: "TRACK_PROBLEM" }, resolve);
    });

    if (response?.ok) {
      showMessage("Problem tracked successfully!", "success");
    } else {
      showMessage(response?.error || "Failed to track problem", "error");
    }
  } catch (error) {
    showMessage(`Error: ${error}`, "error");
  } finally {
    trackBtn.disabled = false;
  }
}

/** Send the current code as a submission. */
async function sendSubmission(): Promise<void> {
  submitBtn.disabled = true;
  try {
    const response = await new Promise<any>((resolve) => {
      chrome.runtime.sendMessage({ type: "SEND_SUBMISSION" }, resolve);
    });

    if (response?.ok) {
      showMessage("Submission sent successfully!", "success");
    } else {
      showMessage(response?.error || "Failed to send submission", "error");
    }
  } catch (error) {
    showMessage(`Error: ${error}`, "error");
  } finally {
    submitBtn.disabled = false;
  }
}

/** Show a temporary message. */
function showMessage(text: string, type: "success" | "error"): void {
  messageDiv.textContent = text;
  messageDiv.className = `message ${type}`;
  setTimeout(() => {
    messageDiv.className = "message hidden";
  }, 3000);
}

/** Escape HTML to prevent XSS. */
function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Initialize
document.addEventListener("DOMContentLoaded", init);
