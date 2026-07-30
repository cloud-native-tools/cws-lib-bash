# Extraction Scripts

Browser-side JavaScript snippets to run **in the target page** via the `browser-utils` skill (Tier 1 built-in eval, Tier 2 MCP `evaluate_script`, or Tier 3 Playwright `page.evaluate`). Each returns a JSON string — capture the full output, don't hand-measure.

## 1. Asset Discovery

Enumerate every asset on the page before writing the download script. Detects layered compositions via parent/sibling info.

```javascript
JSON.stringify({
  images: [...document.querySelectorAll('img')].map(img => ({
    src: img.src || img.currentSrc,
    alt: img.alt,
    width: img.naturalWidth,
    height: img.naturalHeight,
    // parent info reveals layered compositions (bg + overlay stacked in one container)
    parentClasses: img.parentElement?.className,
    siblings: img.parentElement ? [...img.parentElement.querySelectorAll('img')].length : 0,
    position: getComputedStyle(img).position,
    zIndex: getComputedStyle(img).zIndex
  })),
  videos: [...document.querySelectorAll('video')].map(v => ({
    src: v.src || v.querySelector('source')?.src,
    poster: v.poster,
    autoplay: v.autoplay,
    loop: v.loop,
    muted: v.muted
  })),
  backgroundImages: [...document.querySelectorAll('*')].filter(el => {
    const bg = getComputedStyle(el).backgroundImage;
    return bg && bg !== 'none';
  }).map(el => ({
    url: getComputedStyle(el).backgroundImage,
    element: el.tagName + '.' + el.className?.split(' ')[0]
  })),
  svgCount: document.querySelectorAll('svg').length,
  fonts: [...new Set([...document.querySelectorAll('*')].slice(0, 200).map(el => getComputedStyle(el).fontFamily))],
  favicons: [...document.querySelectorAll('link[rel*="icon"]')].map(l => ({ href: l.href, sizes: l.sizes?.toString() }))
});
```

Then write a download script (Node or Python) that fetches everything to the static dir, preserving meaningful structure. Batch ~4 parallel downloads with error handling.

## 2. Per-Component CSS Walker

Extract exact computed styles for a section's full subtree. Replace `SELECTOR` with the section's container selector. Filters out default/empty values to keep output focused.

```javascript
(function(selector) {
  const el = document.querySelector(selector);
  if (!el) return JSON.stringify({ error: 'Element not found: ' + selector });
  const props = [
    'fontSize','fontWeight','fontFamily','lineHeight','letterSpacing','color',
    'textTransform','textDecoration','backgroundColor','background',
    'padding','paddingTop','paddingRight','paddingBottom','paddingLeft',
    'margin','marginTop','marginRight','marginBottom','marginLeft',
    'width','height','maxWidth','minWidth','maxHeight','minHeight',
    'display','flexDirection','justifyContent','alignItems','gap',
    'gridTemplateColumns','gridTemplateRows',
    'borderRadius','border','borderTop','borderBottom','borderLeft','borderRight',
    'boxShadow','overflow','overflowX','overflowY',
    'position','top','right','bottom','left','zIndex',
    'opacity','transform','transition','cursor',
    'objectFit','objectPosition','mixBlendMode','filter','backdropFilter',
    'whiteSpace','textOverflow','WebkitLineClamp'
  ];
  function extractStyles(element) {
    const cs = getComputedStyle(element);
    const styles = {};
    props.forEach(p => { const v = cs[p]; if (v && v !== 'none' && v !== 'normal' && v !== 'auto' && v !== '0px' && v !== 'rgba(0, 0, 0, 0)') styles[p] = v; });
    return styles;
  }
  function walk(element, depth) {
    if (depth > 4) return null;
    const children = [...element.children];
    return {
      tag: element.tagName.toLowerCase(),
      classes: element.className?.toString().split(' ').slice(0, 5).join(' '),
      text: element.childNodes.length === 1 && element.childNodes[0].nodeType === 3 ? element.textContent.trim().slice(0, 200) : null,
      styles: extractStyles(element),
      images: element.tagName === 'IMG' ? { src: element.src, alt: element.alt, naturalWidth: element.naturalWidth, naturalHeight: element.naturalHeight } : null,
      childCount: children.length,
      children: children.slice(0, 20).map(c => walk(c, depth + 1)).filter(Boolean)
    };
  }
  return JSON.stringify(walk(el, 0), null, 2);
})('SELECTOR');
```

## 3. Multi-State Diffing

For any element with more than one state (scroll-triggered, hover, active tab), the **diff between states IS the behavior spec**.

```
// State A: run the walker (#2) on the element at its current state (e.g. scroll position 0)
// Trigger the change via browser-utils (scroll past the threshold, click the tab, hover the element)
// State B: re-run the walker on the SAME element
// Record explicitly: "Property X: VALUE_A → VALUE_B, triggered by TRIGGER, transition: TRANSITION_CSS"
```

Capture the exact trigger (scroll position in px, or IntersectionObserver ratio/rootMargin) and the transition (duration, easing, which properties, CSS-transition vs. JS-driven vs. `animation-timeline`).

## 4. Per-State Content (tabbed / stateful)

For tabbed or cycling content, click each control via browser-utils and extract that state's content:

```javascript
// After clicking a tab, run this scoped to the content container:
(function(selector) {
  const el = document.querySelector(selector);
  if (!el) return JSON.stringify({ error: 'not found' });
  return JSON.stringify({
    texts: [...el.querySelectorAll('h1,h2,h3,h4,p,span,a,button,li')]
      .map(n => n.textContent.trim()).filter(Boolean),
    images: [...el.querySelectorAll('img')].map(i => ({ src: i.src, alt: i.alt })),
    links: [...el.querySelectorAll('a')].map(a => ({ text: a.textContent.trim(), href: a.href }))
  }, null, 2);
})('SELECTOR');
```

Record which content belongs to which state and the transition between states (opacity, slide, fade).
