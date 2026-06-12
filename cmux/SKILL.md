---
name: cmux
description: Control the cmux terminal multiplexer via its CLI. Use when the user wants to manage cmux workspaces, windows, panes, or surfaces; send input to terminals; read terminal screens; drive the built-in browser (navigate, click, fill, snapshot, screenshot); or script any cmux automation. Trigger on mentions of cmux, or when the user asks to open a workspace, split a pane, read a terminal, automate a browser tab inside cmux, or send keys/text to another pane.
---

# cmux

`cmux` is a terminal multiplexer with workspaces, windows, panes, surfaces (tabs), and an integrated Playwright-style browser. You control it via the `cmux` CLI, which talks to a running cmux app over a Unix socket.

Binary: `/Applications/cmux.app/Contents/Resources/bin/cmux` (already on PATH as `cmux`).

## Context autodiscovery

Inside a cmux-spawned terminal, these env vars are set and used as defaults:

- `CMUX_WORKSPACE_ID` → default `--workspace`
- `CMUX_SURFACE_ID` → default `--surface`
- `CMUX_TAB_ID` → default `--tab`

So `cmux send "ls"` sends to the *current* surface. Pass `--workspace`/`--surface` with a UUID, short ref (`workspace:2`, `surface:4`, `pane:3`, `window:1`), or index to target elsewhere.

Run `cmux ping` first if unsure the app is running. Run `cmux tree --all` to inspect the full hierarchy.

## Object model

- **window** → OS window. Contains workspaces.
- **workspace** → a tabbed session. Contains panes and panels.
- **pane** → a split region inside a workspace. Contains surfaces.
- **surface** → a single terminal or browser tab inside a pane.

## Common workflows

### Inspect state
```bash
cmux tree --all              # full hierarchy, all windows
cmux list-workspaces
cmux list-panes --workspace workspace:1
cmux list-pane-surfaces
cmux current-workspace
```

### Create / open
```bash
cmux /path/to/dir                                 # open dir in new workspace
cmux new-workspace --name "api" --cwd ~/code/api --command "make start-server"
cmux new-window
cmux new-split right --workspace workspace:1      # split pane to the right
cmux new-surface --type terminal                  # new tab in current pane
cmux new-surface --type browser --url https://...
```

### Send input & read output
```bash
cmux send "poetry install"                 # types text into current surface (no Enter)
cmux send-key Enter                        # send a specific key
cmux send --surface surface:3 "clear"
cmux read-screen                           # current visible screen
cmux read-screen --scrollback --lines 500  # include scrollback
```
To run a command: `cmux send "…" && cmux send-key Enter`.

### Focus / navigation
```bash
cmux focus-pane --pane pane:2
cmux select-workspace --workspace workspace:3
cmux next-window / previous-window / last-window
```

### Browser automation (Playwright-like)
Operates on a browser surface. If `--surface` is omitted, cmux targets the active browser surface in the caller's workspace.

```bash
cmux browser open https://example.com            # open browser split
cmux browser goto https://example.com --snapshot-after
cmux browser snapshot --compact                  # accessibility snapshot
cmux browser click "button#submit" --snapshot-after
cmux browser fill "input[name=q]" "hello"
cmux browser type "textarea" "some text"
cmux browser press Enter
cmux browser wait --selector ".result" --timeout-ms 5000
cmux browser get url | title | text <sel> | html <sel> | value <sel> | attr <sel> <name>
cmux browser eval "document.title"
cmux browser screenshot --out /tmp/page.png
cmux browser find role button "Submit"           # query by role/text/label/etc
cmux browser console list                        # captured console logs
cmux browser errors list
cmux browser cookies get | set | clear
cmux browser tab new | list | switch <n> | close
```
Use `--snapshot-after` on actions to get the updated page snapshot in one round-trip.

### Notifications & misc
```bash
cmux notify --title "Build done" --body "OK"
cmux markdown open /path/to/file.md        # live-reload markdown viewer
cmux rename-tab "tests"
cmux close-surface --surface surface:4
cmux rpc <method> '<json-params>'          # low-level RPC; see `cmux capabilities`
```

## Identifiers

Commands accept three forms for any `window`/`workspace`/`pane`/`surface` arg:
1. UUID (e.g. `a1b2c3…`)
2. Short ref: `workspace:2`, `surface:4`, `pane:3`, `window:1`, or `tab:<n>` for `tab-action`/`rename-tab`
3. Index (integer; position in parent)

Pass `--id-format uuids` or `--id-format both` to include UUIDs in outputs when you need stable handles.

## Patterns

- **Run a command in another workspace and capture output**:
  ```bash
  cmux send --workspace workspace:2 "pytest -x" && cmux send-key --workspace workspace:2 Enter
  sleep 3
  cmux read-screen --workspace workspace:2 --scrollback --lines 200
  ```
- **Spin up a dev env**: `cmux new-workspace --name dev --cwd ~/proj --command "npm run dev"`, then `cmux new-split right` + `cmux send "npm test -- --watch"`.
- **Drive a webpage**: `cmux browser open <url>` → `cmux browser snapshot --compact` to see structure → interact with `click`/`fill` using selectors from the snapshot.
- **Debug a flaky UI**: after an action, use `cmux browser console list` and `cmux browser errors list`.

## Discovery

- `cmux help` → full command list
- `cmux capabilities` → JSON list of all RPC methods (for advanced `cmux rpc`)
- `cmux shortcuts` → keyboard shortcuts reference

## Gotchas

- `cmux send` does NOT press Enter. Follow with `cmux send-key Enter` (or include `\n` via `send-key`).
- Without `CMUX_WORKSPACE_ID` (i.e. not running inside cmux), you must pass `--workspace` explicitly.
- Socket auth: set `CMUX_SOCKET_PASSWORD` or use `--password` if the app has a password configured.
- Override socket path with `CMUX_SOCKET_PATH` if connecting to a non-default instance.
