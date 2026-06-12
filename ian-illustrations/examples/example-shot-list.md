# Example — Xiaohei shot list for an article

> A worked example for a generic article, *"How a rate limiter works."* It shows
> the output shape: a shot list mapping cognitive anchors to structure types, then
> one image-gen prompt per illustration. (Prompts are the deliverable; feed them to
> any image-generation tool. Illustrations not included here.)

## Shot list
1. [The Bucket That Refills] — requests spend tokens; the bucket drips back up — Conceptual metaphor
2. [Allowed vs. Throttled] — same client, two outcomes either side of the limit — Before/after
3. [The Bouncer at the Door] — limiter decides who passes, per window — Character state

---

### Illustration 1: The Bucket That Refills
**Cognitive anchor:** A token bucket grants requests until it's empty, then refills at a fixed rate
**Structure type:** Conceptual metaphor
**Metaphor:** A leaky bucket on a stand — coins (tokens) drop in slowly from above; each request scoops one out

**Image generation prompt:**
```
Pure white background. Minimalist black hand-drawn line art. Large empty white space (at least 35% as a quiet zone).

Central character: small solid-black creature (Xiaohei) with white dot eyes, tiny thin legs, blank deadpan serious expression — reaching up to scoop a single coin out of a bucket. Not decorative. Not cute. Not a mascot.

Scene: A bucket on a stand drawn in thick black lines, center-left. From above, coins labelled "tokens" drip in one at a time on a slow dotted path (orange). Xiaohei takes one coin out per request. A small queue of waiting requests sketched to the right. The bucket is hand-drawn imperfect.

Sparse English handwritten-style annotations (max 6 labels):
- "1 token = 1 request" (near the coin, red)
- "refills slowly" (near the drip path, orange)
- "bucket empty → wait" (near the bucket bottom, blue)
- "burst up to capacity" (near the queue)

Color rules: orange for the refill drip path only; red for the key rule; blue for the wait state; black for all linework.

No gradients. No shadows. No background texture. No realistic UI. No PPT infographic style. No title label in top-left corner. No Chinese text.

Format: 16:9 horizontal. Style: sketch, eccentric, memorable, hand-drawn product diagram feel.
```

---

### Illustration 2: Allowed vs. Throttled
**Cognitive anchor:** Below the limit a request passes; above it, the same request is rejected with a retry hint
**Structure type:** Before/after
**Metaphor:** A turnstile — green pass on the left, an arm drops down on the right

**Image generation prompt:**
```
Pure white background. Minimalist black hand-drawn line art. Large empty white space splitting the two halves.

Central character: small solid-black creature (Xiaohei) with white dot eyes, tiny thin legs, blank deadpan expression — shown twice, once on each side of a vertical divider. Left: walking through an open turnstile. Right: stopped by a lowered turnstile arm, holding a small ticket stub. Not cute.

Scene: A vertical hairline divides the canvas. Left half labelled "under limit", turnstile open. Right half labelled "over limit", turnstile arm down with a small "429" sign and a clock showing a wait. Both turnstiles hand-drawn, slightly uneven.

Sparse English handwritten-style annotations (max 6 labels):
- "under limit" (left, small)
- "200 OK" (left, near the open gate)
- "over limit" (right, small)
- "429 — try later" (right, red)
- "retry-after: 30s" (right, near the clock, blue)

Color rules: orange for the gate-open flow arrow on the left; red for the rejection sign; blue for the retry hint; black for all linework and Xiaohei.

No gradients. No shadows. No realistic UI. No PPT style. No Chinese text. No title label.

Format: 16:9 horizontal. Style: sketch, deadpan, hand-drawn.
```
