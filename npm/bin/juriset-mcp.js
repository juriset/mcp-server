#!/usr/bin/env node
// A thin wrapper for reach (PRD 7.1): `npx -y juriset-mcp` runs the PyPI package of the same
// version with uvx, so there is one implementation and nothing to drift. The server speaks
// MCP over stdio; this process only hands over stdin, stdout, stderr and the environment.
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";

const { version } = JSON.parse(
  readFileSync(new URL("../package.json", import.meta.url), "utf8"),
);

const runners = [
  ["uvx", [`juriset-mcp==${version}`]],
  ["uv", ["tool", "run", `juriset-mcp==${version}`]],
  ["pipx", ["run", `juriset-mcp==${version}`]],
];

function start(index) {
  if (index >= runners.length) {
    process.stderr.write(
      "juriset-mcp needs uv (https://docs.astral.sh/uv/) or pipx to run the Juriset MCP server.\n" +
        "Install uv, then retry; or run the Python package directly: uvx juriset-mcp\n",
    );
    process.exit(127);
  }
  const [command, args] = runners[index];
  const child = spawn(command, [...args, ...process.argv.slice(2)], { stdio: "inherit" });
  child.on("error", (error) => {
    if (error.code === "ENOENT") start(index + 1);
    else {
      process.stderr.write(`juriset-mcp: ${error.message}\n`);
      process.exit(1);
    }
  });
  child.on("exit", (code, signal) => process.exit(signal ? 1 : (code ?? 0)));
}

start(0);
