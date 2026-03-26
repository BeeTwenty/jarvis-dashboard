# LinkedIn Post — Jarvis Dashboard

## What to post

**Format:** Text post with images (NOT article, NOT link post — text posts get 3-5x more reach)

**Images to attach (in this order):**
1. `docs/screenshots/linkedin-discover.png` — Trending movies/series with posters (best visual hook — colorful, content-rich)
2. `docs/screenshots/linkedin-detail.png` — Inception detail page with cast, ratings, backdrop
3. `docs/screenshots/linkedin-media.png` — Media library with continue watching, unwatched, stats
4. `docs/screenshots/linkedin-overview.png` — Main dashboard overview with system/docker/torrents/weather

All are 2160x2700 (4:5 ratio @2x retina) — optimal LinkedIn carousel size. No cropping.

**Do NOT include:** The library screenshots showing your personal movie collection.

---

## Post text

```
I built a full-stack dashboard — FastAPI backend, Next.js frontend, 30+ API endpoints, 5 service integrations — without writing a single line of code.

Every function, every component, every route — written by Claude Opus 4.6. I described what I wanted. The AI built it. I tested, gave feedback, iterated.

What it does:
→ System monitoring, Docker management, live logs
→ Movie & series discovery via TMDB — mood-based, library-aware, trending
→ Automated media acquisition with season/episode-level awareness
→ Media library with continue watching, watch history, Jellyfin integration
→ File explorer, dark/light mode

I started this to test the limits of vibe coding. Could a real, multi-service application be built entirely through conversation?

Yes. And that raises uncomfortable questions.

If someone who didn't write the code can ship a product that handles auth cookies, proxies images, auto-detects content types, manages file routing, and refactors itself from a 1,600-line monolith to a proper project structure because I said "I don't want to look like a fool on GitHub"... what's the moat for a developer who does the same but takes 3 weeks?

But it breaks down too. We spent an hour trying to change Jellyfin's subtitle font size — server API, custom CSS, JS injection, patching webpack chunks inside Docker. Nothing worked. The setting was in browser localStorage. A human dev would've found it in 5 minutes using dev tools. The AI couldn't observe the browser.

Carl Sagan: "If you wish to make an apple pie from scratch, you must first invent the universe."

The universe of software already exists. The AI has consumed it. Now someone can point at it and say "make me an apple pie" and get one. A real one.

So what's left for us? Maybe the value was never writing code. Maybe it was always knowing what to build, knowing when something feels wrong, what questions to ask. The taste. The judgment.

Or maybe that's just what we tell ourselves as the machines get better.

This post was also written by Claude.

But every feature decision was mine. Every "this feels wrong" was mine. The vision, the workflow, the product — that was human. The AI was the hands. I was the eye.

Whether that distinction matters in 2 years, I don't know.

Open source. Link in comments.

@Anthropic @NVIDIA @Microsoft

#vibecoding #claudecode #ai #fullstack #buildinpublic #futureofwork #homelab #selfhosted
```

---

## Comment to post immediately after

Post this as the FIRST comment within 30 seconds of publishing:

```
GitHub: https://github.com/Animesh98/jarvis-dashboard

Built entirely through conversation with Claude Code (Opus 4.6). Not a line of code was written manually.

If you run a homelab with Jellyfin + qBittorrent, this might actually be useful. PRs welcome.
```

---

## Second comment (post 5 minutes later to boost engagement):

```
For those asking about the process — it was roughly:

1. Describe a feature in plain English
2. AI writes the code
3. I test it (browser, phone, Tailscale)
4. "This doesn't work" or "make it better"
5. Repeat

Total build time: ~2 days of conversation across multiple sessions.
The AI handled architecture decisions, dependency choices, error handling, and edge cases I never thought of.
```

---

## Tips for maximum reach

1. **Post timing:** Tuesday-Thursday, 8-10 AM IST
2. **First 2 lines are everything** — the hook "built production-grade full-stack... without writing a single line of code" is designed to stop the scroll
3. **Reply to every comment** in the first 2 hours
4. **Don't edit the post** after publishing
5. **GitHub link in comments only** — LinkedIn kills reach for posts with external links
6. **Tag Anthropic, NVIDIA, Microsoft** — their social teams monitor tags, reshares = massive reach
7. **The 4-image carousel** gets 2x engagement vs single image
8. **The Carl Sagan quote** and the philosophical turn is what makes this shareable beyond tech LinkedIn — it reaches the "future of work" crowd too
9. **The reveal that the post itself was written by Claude** is the mic drop — people will screenshot and reshare that alone
10. **"The AI was the hands. I was the eye."** — this is the quotable line. If anything goes viral from this post, it's this sentence.
