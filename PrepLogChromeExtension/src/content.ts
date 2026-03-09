/**
 * PrepLog Content Script
 * Runs on LeetCode problem pages to extract problem details and detect submissions.
 */

import { ProblemData, SubmissionData } from "./types";

/** Extract the problem slug from the current URL. */
function getSlugFromUrl(): string | null {
  const match = window.location.pathname.match(/^\/problems\/([^/]+)/);
  return match ? match[1] : null;
}

/** Extract problem details from the page DOM. */
function extractProblemData(): ProblemData | null {
  const slug = getSlugFromUrl();
  if (!slug) return null;

  // Title - LeetCode uses various selectors depending on the version
  const titleEl =
    document.querySelector('[data-cy="question-title"]') ||
    document.querySelector(".text-title-large") ||
    document.querySelector("div[class*='title'] a") ||
    document.querySelector("h4[class*='title']");

  const title = titleEl?.textContent?.trim() || slug.replace(/-/g, " ");

  // Difficulty
  const difficultyEl =
    document.querySelector('[diff]') ||
    document.querySelector("div[class*='difficulty']") ||
    document.querySelector("span[class*='Easy']") ||
    document.querySelector("span[class*='Medium']") ||
    document.querySelector("span[class*='Hard']");

  let difficulty = "";
  if (difficultyEl) {
    const text = difficultyEl.textContent?.trim() || "";
    if (/easy/i.test(text)) difficulty = "Easy";
    else if (/medium/i.test(text)) difficulty = "Medium";
    else if (/hard/i.test(text)) difficulty = "Hard";
  }

  // Description
  const descEl =
    document.querySelector('[data-cy="question-content"]') ||
    document.querySelector("div[class*='description']") ||
    document.querySelector("div.elfjS");

  const description = descEl?.textContent?.trim() || "";

  return { title, description, difficulty, slug };
}

/** Extract code from the Monaco/CodeMirror editor. */
function extractCode(): { code: string; language: string } | null {
  // Try Monaco editor (LeetCode's newer editor)
  const monacoLines = document.querySelectorAll(".view-lines .view-line");
  if (monacoLines.length > 0) {
    const code = Array.from(monacoLines)
      .map((line) => line.textContent || "")
      .join("\n");

    // Try to detect language from UI
    const langBtn =
      document.querySelector("button[id*='lang']") ||
      document.querySelector("div[class*='lang-select']") ||
      document.querySelector("button[class*='lang']");
    const language = langBtn?.textContent?.trim()?.toLowerCase() || "unknown";

    return { code, language };
  }

  // Try CodeMirror
  const cmEl = document.querySelector(".CodeMirror") as any;
  if (cmEl?.CodeMirror) {
    return { code: cmEl.CodeMirror.getValue(), language: "unknown" };
  }

  return null;
}

/** Observe for submission success events. */
function observeSubmissions(): void {
  // Watch for the "Accepted" status that appears after a successful submission
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of Array.from(mutation.addedNodes)) {
        if (node instanceof HTMLElement) {
          const text = node.textContent || "";
          if (/accepted/i.test(text) && node.querySelector?.("span[class*='success']")) {
            handleSubmissionDetected();
          }
        }
      }
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
}

/** Handle when a submission is detected. */
function handleSubmissionDetected(): void {
  const slug = getSlugFromUrl();
  const codeData = extractCode();

  if (slug && codeData) {
    const submission: SubmissionData = {
      slug,
      code: codeData.code,
      language: codeData.language,
    };

    chrome.runtime.sendMessage({
      type: "SUBMISSION_DETECTED",
      data: submission,
    });
  }
}

/** Initialize the content script. */
function init(): void {
  // Wait a bit for the page to fully render
  setTimeout(() => {
    const problem = extractProblemData();
    if (problem) {
      chrome.runtime.sendMessage({
        type: "PROBLEM_DETECTED",
        data: problem,
      });
    }
  }, 2000);

  // Listen for messages from popup
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === "GET_CURRENT_PROBLEM") {
      const problem = extractProblemData();
      sendResponse({ problem });
    } else if (message.type === "GET_CURRENT_CODE") {
      const codeData = extractCode();
      const slug = getSlugFromUrl();
      sendResponse({ slug, ...codeData });
    }
    return true;
  });

  // Watch for submissions
  observeSubmissions();
}

init();
