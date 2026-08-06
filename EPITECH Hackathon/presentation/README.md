# LINKFORGE - MED & AI

## Run

```bash
npm start
```

Then open http://localhost:8000. That's it — the start script is a tiny built-in
Node static server with no dependencies to install.

You can also open `index.html` directly in a browser, but serving over http is
recommended so the speaker-notes window and demo iframes behave.

Optional: `npm install` refreshes the vendored `reveal.js` from the version pinned in
`package.json`.

### Controls

Arrow keys to move, `F` fullscreen, `S` speaker notes (notes are on the key slides),
`Esc` slide overview, `B` blank screen.

## Fill in the placeholders

Search `index.html` for `[` to find everything to replace:

- `[Team name]`, `[Event / Date]` on the title and closing slides.
- `[Teammate 1..3]` and `[Role — ...]` on the five team slides (same auto-animate
  morph as the Zappy deck).
- The working title `IN THE LOOP` — rename if you like.

## Embed the two live demos

The Editorial Guard and Document Graph slides have a browser mock with a placeholder.
Replace the placeholder block with a live iframe:

```html
<iframe class="demo-iframe" src="http://localhost:8000"></iframe>
```

(Serve the deck on a different port than a demo, e.g. `PORT=9000 npm start`, so they
don't collide.) For a full-screen live demo, instead put this on the slide's
`<section>` and drop the inner content:

```html
<section data-background-iframe="http://localhost:8000" data-preload>
```

## Structure

```
in-the-loop/
  index.html        the deck
  css/custom.css    deck-specific styles
  dist/             reveal.js core + themes (vendored)
  plugin/           reveal.js plugins: notes, markdown, highlight (vendored)
  server.js         zero-dependency static server
  package.json
```

The deck is in English to match the prototypes' UI. Translating to French is a
slide-by-slide text edit.
