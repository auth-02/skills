# Component snippets

Copy-pasteable building blocks. These are the signature components — every project should include at least a few of them.

## Meta-row (section header)

```html
<div class="meta-row">
  <span>// 02 — Typography</span>
  <span>3 FAMILIES</span>
</div>
```

```css
.meta-row {
  display: flex; justify-content: space-between;
  border-bottom: 1px solid var(--line);
  padding-bottom: 6px;
  margin-bottom: var(--r-3);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--ink-mute);
}
```

## Section title with italic accent

```html
<h2 class="sec-title">A serif for <em>voice.</em> A mono for <em>truth.</em></h2>
```

```css
.sec-title {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: clamp(32px, 4.2vw, 48px);
  line-height: 1.05;
  letter-spacing: -0.025em;
  margin-bottom: var(--r-5);
  max-width: 720px;
}
.sec-title em {
  font-style: italic;
  color: var(--accent);
  font-weight: 500;
}
```

## Schematic card (with corner ticks + index)

```html
<div class="card">
  <span class="num">001</span>
  <code>grep "GDPR" ~/legal/</code>
  <h3>Legal search</h3>
  <p>Description text here.</p>
</div>
```

```css
.card {
  background: var(--bg-alt);
  border: 1px solid var(--line);
  padding: var(--r-4);
  position: relative;
}
.card::before {
  content: '';
  position: absolute;
  top: -1px; left: -1px;
  width: 10px; height: 10px;
  border-top: 1px solid var(--accent);
  border-left: 1px solid var(--accent);
}
.card::after {
  content: '';
  position: absolute;
  bottom: -1px; right: -1px;
  width: 10px; height: 10px;
  border-bottom: 1px solid var(--accent);
  border-right: 1px solid var(--accent);
}
.card .num {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.15em;
  color: var(--accent);
  position: absolute;
  top: var(--r-3); right: var(--r-3);
}
.card code {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 11px;
  background: var(--bg-deep);
  color: var(--accent-deep);
  padding: 3px 8px;
  margin-bottom: var(--r-2);
}
```

## Terminal block

```html
<div class="terminal">
  <div class="term-head">
    <span><span class="dot"></span>READY</span>
    <span>INSTALL.SH</span>
  </div>
  <div><span class="prompt">$</span>curl -fsSL example.com/install | sh</div>
  <div><span class="comment"># → and you're done.</span></div>
</div>
```

```css
.terminal {
  background: var(--bg-alt);
  border: 1px solid var(--line);
  padding: var(--r-4);
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.7;
}
.terminal .term-head {
  display: flex; justify-content: space-between;
  margin-bottom: var(--r-3);
  font-size: 10px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--ink-mute);
}
.terminal .term-head .dot {
  display: inline-block;
  width: 6px; height: 6px;
  background: var(--accent);
  border-radius: 50%;
  margin-right: 6px;
}
.terminal .prompt { color: var(--accent); margin-right: 8px; }
.terminal .comment { color: var(--ink-mute); font-style: italic; }
```

## Button pair (ghost + solid)

```html
<button class="btn solid">Primary action</button>
<button class="btn">Secondary action</button>
```

```css
.btn {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  padding: 12px 20px;
  background: transparent;
  color: var(--accent);
  border: 1px solid var(--accent);
  cursor: pointer;
  transition: all 180ms ease;
}
.btn:hover {
  background: var(--accent);
  color: var(--bg);
}
.btn.solid {
  background: var(--ink);
  color: var(--bg);
  border-color: var(--ink);
}
.btn.solid:hover {
  background: var(--accent);
  border-color: var(--accent);
}
```

## Mono label (inline)

```html
<span class="label accent">// VIRTUAL FILE — 01</span>
```

```css
.label {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ink-mute);
  display: block;
}
.label.accent { color: var(--accent); }
```

## Spec-sheet grid (label + content)

```html
<div class="type-grid">
  <div class="spec-label">Display<small>Fraunces · 500</small></div>
  <div>
    <div class="spec-display">Headline <em>here.</em></div>
  </div>
</div>
```

```css
.type-grid {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: var(--r-5) var(--r-4);
  align-items: baseline;
}
.spec-label {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-mute);
  border-top: 1px solid var(--line);
  padding-top: var(--r-2);
}
.spec-label small {
  display: block;
  text-transform: none;
  letter-spacing: 0.05em;
  margin-top: 6px;
  font-size: 10px;
}
```
