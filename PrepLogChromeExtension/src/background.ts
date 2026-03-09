/**
 * PrepLog Background Service Worker
 * Handles messages from content script and popup, forwards data to PrepLogServer.
 */

import { ProblemData, ExtensionMessage } from "./types";
import { trackProblem, sendSubmission } from "./api";

// Store current problem data in memory
let currentProblem: ProblemData | null = null;

// Listen for messages from content scripts and popup
chrome.runtime.onMessage.addListener(
  (message: ExtensionMessage, sender, sendResponse) => {
    handleMessage(message, sendResponse);
    return true; // Keep message channel open for async response
  }
);

async function handleMessage(
  message: ExtensionMessage,
  sendResponse: (response: any) => void
): Promise<void> {
  switch (message.type) {
    case "PROBLEM_DETECTED": {
      currentProblem = message.data;
      console.log("[PrepLog] Problem detected:", currentProblem.title);
      sendResponse({ ok: true });
      break;
    }

    case "SUBMISSION_DETECTED": {
      console.log("[PrepLog] Submission detected for:", message.data.slug);
      try {
        // First ensure the problem is tracked
        if (currentProblem && currentProblem.slug === message.data.slug) {
          await trackProblem(currentProblem);
        }
        // Then send the submission
        const resp = await sendSubmission(message.data);
        if (resp.ok) {
          console.log("[PrepLog] Submission tracked successfully");
        } else {
          console.error("[PrepLog] Failed to track submission:", resp.status);
        }
        sendResponse({ ok: resp.ok });
      } catch (error) {
        console.error("[PrepLog] Error tracking submission:", error);
        sendResponse({ ok: false, error: String(error) });
      }
      break;
    }

    case "GET_CURRENT_PROBLEM": {
      sendResponse({ problem: currentProblem });
      break;
    }

    case "TRACK_PROBLEM": {
      if (!currentProblem) {
        sendResponse({ ok: false, error: "No problem detected" });
        return;
      }
      try {
        const resp = await trackProblem(currentProblem);
        sendResponse({ ok: resp.ok });
      } catch (error) {
        sendResponse({ ok: false, error: String(error) });
      }
      break;
    }

    case "SEND_SUBMISSION": {
      // Request code from the active tab's content script
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id) {
        sendResponse({ ok: false, error: "No active tab" });
        return;
      }

      chrome.tabs.sendMessage(
        tab.id,
        { type: "GET_CURRENT_CODE" },
        async (codeResp) => {
          if (!codeResp?.code) {
            sendResponse({ ok: false, error: "Could not extract code" });
            return;
          }
          try {
            // Ensure problem is tracked first
            if (currentProblem) {
              await trackProblem(currentProblem);
            }
            const resp = await sendSubmission({
              slug: codeResp.slug || currentProblem?.slug || "",
              code: codeResp.code,
              language: codeResp.language || "unknown",
            });
            sendResponse({ ok: resp.ok });
          } catch (error) {
            sendResponse({ ok: false, error: String(error) });
          }
        }
      );
      break;
    }
  }
}
