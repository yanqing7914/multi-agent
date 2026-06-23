#!/usr/bin/env node
// @ts-check
/**
 * run_workers.mjs — reference `@cursor/sdk` launcher for the cursor-sdk path.
 *
 * WHAT THIS IS
 *   The programmatic (Node / TypeScript SDK) sibling of the deterministic
 *   `agent` CLI bridge (adapters/cursor/scripts/launch_cursor_worker.py). It
 *   reads the `run-spec.json` produced by `prepare_cursor_sdk.py` and starts one
 *   Cursor Agent per write-permission Worker, streaming each Run's events.
 *
 * THIS IS A NODE PATH — NOT PART OF THE PYTHON CORE OR CI
 *   - Requires Node 18+ and `npm install` in this folder (pulls `@cursor/sdk`).
 *   - Requires Cursor auth: `export CURSOR_API_KEY=cursor_...` (or `cursor login`).
 *   - It ACTUALLY drives Cursor agents and edits files. Never run it unattended
 *     or in CI without sandboxing. `scripts/validate_all_adapters.py` does NOT
 *     run this file; the Python `prepare_cursor_sdk.py --self-check` is the
 *     dependency-free gate.
 *
 * CONTRACT THIS PRESERVES (identical to every other adapter)
 *   - Each Worker is scoped to its task card's `allowed_paths` (baked into the
 *     prompt by build_worker_prompt / the fallback prompt).
 *   - Each Worker MUST write BOTH result reports (JSON + Markdown) before it is
 *     considered complete. The exact paths live in `worker.result_report_paths`.
 *   - Main still owns gate sync + scope audit AFTER Workers finish. This script
 *     only runs Workers; it does not mark gates or deliver.
 *
 * USAGE
 *   cd adapters/cursor/sdk
 *   npm install
 *   export CURSOR_API_KEY=cursor_...
 *   node run_workers.mjs [path/to/run-spec.json]
 *     # or, equivalently, via the package script:
 *   CURSOR_SDK_RUN_SPEC=/abs/.codex-multi-agent/cursor-sdk/run-spec.json npm start
 *
 * ENVIRONMENT KNOBS
 *   CURSOR_API_KEY        Cursor API key (required). User or service-account key.
 *   CURSOR_SDK_RUN_SPEC   run-spec.json path (else argv[2], else default below).
 *   CURSOR_SDK_RUNTIME    "local" (default) or "cloud".
 *   CURSOR_SDK_MODEL      model id (default "composer-2.5").
 *   CURSOR_SDK_CLOUD_REPO git URL to clone (REQUIRED when runtime=cloud).
 *   CURSOR_SDK_CLOUD_REF  branch/ref for the cloud checkout (optional).
 *
 * local vs cloud, and what it means for the result-report contract
 *   - local: the agent runs on THIS machine against `worker.cwd`
 *     (= workspace_root), so it can write the local `.codex-multi-agent/results`
 *     files the contract expects. This is the right default for the file-based
 *     mission-control flow.
 *   - cloud: the agent runs on a Cursor-hosted VM against a freshly cloned repo
 *     and (with autoCreatePR) opens a PR that shows up in the Agents Window. The
 *     local result-report files will NOT appear on your disk in this mode —
 *     collect outcomes from the PR / Agents Window instead, or have the Worker
 *     commit its result reports into the repo.
 */

import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import process from "node:process";

const DEFAULT_RUN_SPEC = ".codex-multi-agent/cursor-sdk/run-spec.json";
const DEFAULT_MODEL = "composer-2.5";

/** Read CLI/env configuration once. */
function readConfig() {
  const runSpecPath = resolve(
    process.env.CURSOR_SDK_RUN_SPEC || process.argv[2] || DEFAULT_RUN_SPEC,
  );
  return {
    runSpecPath,
    runtime: (process.env.CURSOR_SDK_RUNTIME || "local").toLowerCase(),
    model: process.env.CURSOR_SDK_MODEL || DEFAULT_MODEL,
    apiKey: process.env.CURSOR_API_KEY,
    cloudRepo: process.env.CURSOR_SDK_CLOUD_REPO,
    cloudRef: process.env.CURSOR_SDK_CLOUD_REF,
  };
}

/** Load and lightly validate the run-spec emitted by prepare_cursor_sdk.py. */
function loadRunSpec(runSpecPath) {
  if (!existsSync(runSpecPath)) {
    throw new Error(
      `run-spec not found: ${runSpecPath}\n` +
        "Generate it first:\n" +
        "  python adapters/cursor/scripts/prepare_cursor_sdk.py --ownership .codex-multi-agent/ownership.json",
    );
  }
  const spec = JSON.parse(readFileSync(runSpecPath, "utf8"));
  if (!Array.isArray(spec.workers)) {
    throw new Error(`run-spec missing a "workers" array: ${runSpecPath}`);
  }
  return spec;
}

/**
 * Build the per-Worker Agent options. We ALWAYS set exactly one of local/cloud
 * explicitly — the SDK silently defaults to local otherwise, which is an easy
 * way to think you launched a cloud agent when you did not.
 */
function buildAgentOptions(worker, cfg) {
  const base = { apiKey: cfg.apiKey, model: { id: cfg.model } };
  if (cfg.runtime === "cloud") {
    if (!cfg.cloudRepo) {
      throw new Error("CURSOR_SDK_RUNTIME=cloud requires CURSOR_SDK_CLOUD_REPO=<git url>");
    }
    return {
      ...base,
      cloud: {
        repos: [
          {
            repository: cfg.cloudRepo,
            ...(cfg.cloudRef ? { ref: cfg.cloudRef } : {}),
          },
        ],
        autoCreatePR: true,
        // CI-friendly: don't page a human reviewer just to launch the run.
        skipReviewerRequest: true,
      },
    };
  }
  // Local default: run against the Worker's workspace_root so the agent can
  // write the local result-report files named in the prompt.
  return { ...base, local: { cwd: worker.cwd } };
}

/** Print a single Run stream event compactly. */
function logEvent(taskId, event) {
  const tag = `[${taskId}] ${event.type}`;
  switch (event.type) {
    case "assistant": {
      // Assistant messages carry content blocks; stream the text ones inline.
      const blocks = event.message?.content ?? [];
      const text = blocks
        .filter((block) => block.type === "text")
        .map((block) => block.text)
        .join("");
      if (text) process.stdout.write(text);
      return;
    }
    case "tool_call": {
      const name = event.tool_call?.name ?? event.name ?? "tool";
      console.log(`\n${tag}: ${name}`);
      return;
    }
    case "thinking":
      // Reasoning tokens are noisy; surface only the type. Flip to print
      // event.thinking?.text when you need to debug a stuck Worker.
      return;
    case "status":
      console.log(`\n${tag}: ${event.status ?? ""}`.trimEnd());
      return;
    default:
      // system / user / request / task and anything new the SDK adds later.
      console.log(`\n${tag}`);
  }
}

/** Report whether the Worker actually produced its two result-report files. */
function reportArtifacts(worker) {
  const reports = worker.result_report_paths || {};
  for (const kind of ["json", "markdown"]) {
    const path = reports[kind];
    if (!path) continue;
    const present = existsSync(path) ? "WROTE" : "MISSING";
    console.log(`  result ${kind}: [${present}] ${path}`);
  }
}

/** Dispose the agent without masking the original error path. */
async function disposeAgent(agent) {
  if (!agent) return;
  try {
    // `await using agent = await Agent.create(...)` is the idiomatic form in
    // TypeScript; in plain .mjs we dispose explicitly for broad Node support.
    if (typeof agent[Symbol.asyncDispose] === "function") {
      await agent[Symbol.asyncDispose]();
    } else if (typeof agent.close === "function") {
      await agent.close();
    }
  } catch (err) {
    console.error(`  (dispose warning) ${err?.message ?? err}`);
  }
}

/**
 * Run a single Worker end to end. Returns an exit-code-style outcome:
 *   "finished" -> 0, "error" -> 2 (ran but failed), "startup" -> 1 (never ran).
 */
async function runWorker(sdk, worker, cfg) {
  const { Agent, CursorAgentError } = sdk;
  console.log(`\n=== Worker ${worker.task_id} (${worker.session_name}) ===`);
  console.log(`  runtime=${cfg.runtime} cwd=${worker.cwd}`);
  console.log(`  allowed_paths=${(worker.allowed_paths || []).join(", ") || "(none)"}`);

  let agent;
  try {
    agent = await Agent.create(buildAgentOptions(worker, cfg));
  } catch (err) {
    // Thrown before/at startup => the run never executed (auth/config/network).
    if (CursorAgentError && err instanceof CursorAgentError) {
      console.error(`  startup failed (retryable=${err.isRetryable}): ${err.message}`);
    } else {
      console.error(`  startup failed: ${err?.message ?? err}`);
    }
    return "startup";
  }

  try {
    // We send the FULL scoped prompt (preflight + allowed_paths + dual
    // result-report contract) that prepare_cursor_sdk.py baked into the spec.
    const run = await agent.send(worker.prompt);
    // Log ids immediately so a hung stream is still traceable in the dashboard.
    console.log(`  agentId=${agent.agentId ?? "?"} runId=${run.id ?? "?"}`);

    for await (const event of run.stream()) {
      logEvent(worker.task_id, event);
    }
    // wait() is the only reliable way to learn the terminal status.
    const result = await run.wait();
    console.log(`\n  run status: ${result.status}`);
    reportArtifacts(worker);

    if (result.status === "error") {
      // Ran but failed mid-flight: inspect transcript / git state / tool output.
      return "error";
    }
    return "finished";
  } catch (err) {
    if (CursorAgentError && err instanceof CursorAgentError) {
      console.error(`  run startup failed (retryable=${err.isRetryable}): ${err.message}`);
      return "startup";
    }
    console.error(`  run failed: ${err?.message ?? err}`);
    return "error";
  } finally {
    await disposeAgent(agent);
  }
}

async function main() {
  const cfg = readConfig();
  const spec = loadRunSpec(cfg.runSpecPath);

  console.log(`run-spec: ${cfg.runSpecPath}`);
  console.log(`workers:  ${spec.workers.length}`);
  console.log(`runtime:  ${cfg.runtime} | model: ${cfg.model}`);
  if (!cfg.apiKey) {
    console.warn(
      "warning: CURSOR_API_KEY is not set. Export it (or run `cursor login`) before launching real agents.",
    );
  }

  // Dynamic import so a missing dependency yields a clear, actionable message
  // instead of an opaque module-resolution stack trace.
  let sdk;
  try {
    sdk = await import("@cursor/sdk");
  } catch (err) {
    console.error(
      "\nCould not load @cursor/sdk. Install it first:\n" +
        "  cd adapters/cursor/sdk && npm install\n" +
        `(${err?.message ?? err})`,
    );
    process.exit(1);
    return;
  }

  // Sequential keeps the streamed output readable. For true parallelism (the
  // shape Cursor's in-App `/multitask` uses), give each Worker its own git
  // worktree via `python tools/worktree_tool.py --action plan --create
  // --ownership .codex-multi-agent/ownership.json`, point each worker.cwd at its
  // worktree, then wrap these calls in `Promise.all(...)`.
  const outcomes = [];
  for (const worker of spec.workers) {
    outcomes.push(await runWorker(sdk, worker, cfg));
  }

  const counts = outcomes.reduce((acc, status) => {
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {});
  console.log(
    `\nSummary: finished=${counts.finished || 0} error=${counts.error || 0} startup=${counts.startup || 0}`,
  );
  console.log("Next: collect result reports, then run gate sync + scope audit before delivery.");

  // 0 = all finished, 2 = a run executed and errored, 1 = a run never started.
  if (counts.error) process.exit(2);
  if (counts.startup) process.exit(1);
  process.exit(0);
}

main().catch((err) => {
  console.error(err?.stack ?? err?.message ?? err);
  process.exit(1);
});
