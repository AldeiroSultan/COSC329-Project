/* Spotlight walkthrough: dims the page, highlights one element at a time and points a
   card at it. It knows nothing about the planner; app.js supplies the steps.

   step = {
     target:   CSS selector, element or function returning one (omit for a centred card),
     title:    string,
     body:     string (blank lines split paragraphs) or function returning one,
     rows:     optional function returning [[label, value], ...] (summary list),
     before:   optional async hook run before the step is shown,
     after:    optional async hook run when the user presses Next,
     placement: optional preferred side: right | left | bottom | top,
     nextLabel, extra: { label, onClick }   optional button overrides
   } */

const SVG_NS = 'http://www.w3.org/2000/svg';
const clamp = (value, low, high) => Math.min(Math.max(value, low), high);

function icon(name) {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', 'icon');
  const use = document.createElementNS(SVG_NS, 'use');
  use.setAttribute('href', `#i-${name}`);
  svg.append(use);
  return svg;
}

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

export class Tour {
  constructor({ onClose, topInset = () => 96 } = {}) {
    this.onClose = onClose;
    this.topInset = topInset;
    this.steps = [];
    this.index = -1;
    this.active = false;
    this.busy = false;
    this.token = 0;
    this.frame = 0;
    this.current = null;
    this.build();
    this.onKey = this.onKey.bind(this);
    this.onReflow = this.onReflow.bind(this);
  }

  get reducedMotion() { return matchMedia('(prefers-reduced-motion: reduce)').matches; }
  get mobile() { return matchMedia('(max-width: 720px)').matches; }

  build() {
    this.root = node('div', 'tour');
    this.root.hidden = true;
    this.blocker = node('div', 'tour-blocker');
    this.spot = node('div', 'tour-spot is-empty');
    this.card = node('div', 'tour-card');
    this.card.setAttribute('role', 'dialog');
    this.card.setAttribute('aria-modal', 'true');
    this.card.setAttribute('aria-labelledby', 'tour-title');

    this.arrow = node('span', 'tour-arrow');
    this.closeBtn = node('button', 'btn icon-btn tour-close');
    this.closeBtn.type = 'button';
    this.closeBtn.setAttribute('aria-label', 'Close guide');
    this.closeBtn.append(icon('x'));

    this.text = node('div', 'tour-text');
    this.text.setAttribute('aria-live', 'polite');
    this.stepLabel = node('p', 'tour-step');
    this.titleEl = node('h3');
    this.titleEl.id = 'tour-title';
    this.bodyEl = node('div', 'tour-body');
    this.text.append(this.stepLabel, this.titleEl, this.bodyEl);

    this.progress = node('div', 'tour-progress');
    this.progress.setAttribute('aria-hidden', 'true');
    this.progressBar = node('span');
    this.progress.append(this.progressBar);

    this.actions = node('div', 'tour-actions');
    this.backBtn = node('button', 'btn small', 'Back');
    this.backBtn.type = 'button';
    this.extraBtn = node('button', 'btn small');
    this.extraBtn.type = 'button';
    this.nextBtn = node('button', 'btn small primary');
    this.nextBtn.type = 'button';
    this.actions.append(this.backBtn, this.extraBtn, this.nextBtn);

    this.card.append(this.arrow, this.closeBtn, this.text, this.progress, this.actions);
    this.root.append(this.blocker, this.spot, this.card);
    document.body.append(this.root);

    this.closeBtn.addEventListener('click', () => this.close(false));
    this.backBtn.addEventListener('click', () => this.prev());
    this.nextBtn.addEventListener('click', () => this.next());
  }

  get isOpen() { return this.active; }

  async start(steps, opener = document.activeElement) {
    if (this.active) this.teardown(false);
    this.steps = steps;
    this.opener = opener;
    this.active = true;
    this.root.hidden = false;
    document.addEventListener('keydown', this.onKey, true);
    window.addEventListener('resize', this.onReflow);
    window.addEventListener('scroll', this.onReflow, { passive: true });
    await this.show(0);
  }

  async show(index) {
    const token = ++this.token;
    this.busy = true;
    this.card.classList.add('is-busy');
    this.index = index;
    const step = this.steps[index];
    try {
      if (step.before) await step.before();
      if (token !== this.token) return;
      this.render(step, index);
      const target = this.resolve(step.target);
      if (target) await this.scrollTo(target);
      if (token !== this.token) return;
      this.current = { step, target };
      this.place();
      this.nextBtn.focus({ preventScroll: true });
    } finally {
      if (token === this.token) {
        this.busy = false;
        this.card.classList.remove('is-busy');
      }
    }
  }

  async next() {
    if (this.busy || !this.active) return;
    const step = this.steps[this.index];
    if (step.after) {
      this.busy = true;
      this.card.classList.add('is-busy');
      try { await step.after(); } finally { this.busy = false; }
      if (!this.active) return;
    }
    if (this.index >= this.steps.length - 1) this.close(true);
    else await this.show(this.index + 1);
  }

  async prev() {
    if (this.busy || !this.active || this.index === 0) return;
    await this.show(this.index - 1);
  }

  close(completed) {
    if (!this.active) return;
    this.teardown(true, completed);
  }

  teardown(notify, completed = false) {
    this.token += 1;
    this.active = false;
    this.busy = false;
    this.root.hidden = true;
    this.spot.classList.add('is-empty');
    document.removeEventListener('keydown', this.onKey, true);
    window.removeEventListener('resize', this.onReflow);
    window.removeEventListener('scroll', this.onReflow);
    const opener = this.opener;
    this.opener = null;
    if (opener && opener.isConnected && typeof opener.focus === 'function') opener.focus({ preventScroll: true });
    if (notify && this.onClose) this.onClose({ completed, index: this.index });
  }

  resolve(target) {
    if (!target) return null;
    if (typeof target === 'function') return target();
    if (typeof target === 'string') return document.querySelector(target);
    return target;
  }

  render(step, index) {
    const total = this.steps.length;
    this.stepLabel.textContent = step.rows ? 'Summary' : `Step ${index + 1} of ${total}`;
    this.titleEl.textContent = step.title;
    const raw = typeof step.body === 'function' ? step.body() : step.body || '';
    const paragraphs = String(raw).split(/\n\s*\n/).filter(Boolean).map((text) => node('p', '', text));
    const rows = step.rows ? step.rows() : null;
    if (rows) {
      const list = node('dl', 'tour-rows');
      rows.forEach(([label, value]) => {
        const row = node('div');
        row.append(node('dt', '', label), node('dd', '', value));
        list.append(row);
      });
      this.bodyEl.replaceChildren(list, ...paragraphs);
    } else {
      this.bodyEl.replaceChildren(...paragraphs);
    }
    this.progressBar.style.width = `${((index + 1) / total) * 100}%`;
    this.backBtn.style.visibility = index === 0 ? 'hidden' : 'visible';
    const last = index === total - 1;
    this.nextBtn.replaceChildren(document.createTextNode(step.nextLabel || (last ? 'Done' : 'Next')), icon(last ? 'check' : 'arrow-right'));
    if (step.extra) {
      this.extraBtn.hidden = false;
      this.extraBtn.textContent = step.extra.label;
      this.extraBtn.onclick = () => step.extra.onClick();
    } else {
      this.extraBtn.hidden = true;
      this.extraBtn.onclick = null;
    }
  }

  async scrollTo(element) {
    const rect = element.getBoundingClientRect();
    const viewport = window.innerHeight;
    const top = this.topInset();
    const bottomLimit = this.mobile ? viewport * 0.5 : viewport - 24;
    if (rect.top >= top && rect.bottom <= bottomLimit) return;
    let desired;
    if (this.mobile || rect.height > viewport - top - 40) desired = window.scrollY + rect.top - top - 8;
    else desired = window.scrollY + rect.top - (viewport - rect.height) / 2;
    window.scrollTo({ top: Math.max(0, desired), behavior: this.reducedMotion ? 'auto' : 'smooth' });
    await this.settle();
  }

  settle() {
    return new Promise((resolve) => {
      let last = window.scrollY;
      let still = 0;
      let frames = 0;
      const tick = () => {
        frames += 1;
        still = Math.abs(window.scrollY - last) < 0.5 ? still + 1 : 0;
        last = window.scrollY;
        if (still >= 4 || frames > 80) resolve();
        else requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }

  place() {
    if (!this.current) return;
    const { step, target } = this.current;
    const card = this.card;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const margin = 12;
    card.classList.toggle('is-centered', !target);

    if (!target) {
      // A zero-size spotlight in the middle keeps the whole page dimmed behind the card.
      Object.assign(this.spot.style, { left: `${vw / 2}px`, top: `${vh / 2}px`, width: '0px', height: '0px', borderRadius: '0px' });
      this.spot.classList.add('is-empty');
      card.dataset.placement = 'none';
      card.style.left = `${Math.max(margin, (vw - card.offsetWidth) / 2)}px`;
      card.style.top = `${Math.max(margin, (vh - card.offsetHeight) / 2)}px`;
      return;
    }

    const pad = 10;
    const raw = target.getBoundingClientRect();
    const rect = {
      left: Math.max(raw.left - pad, 4),
      top: Math.max(raw.top - pad, 4),
      right: Math.min(raw.right + pad, vw - 4),
      bottom: Math.min(raw.bottom + pad, vh - 4),
    };
    const radius = parseFloat(getComputedStyle(target).borderTopLeftRadius) || 0;
    Object.assign(this.spot.style, {
      left: `${rect.left}px`,
      top: `${rect.top}px`,
      width: `${rect.right - rect.left}px`,
      height: `${rect.bottom - rect.top}px`,
      borderRadius: `${Math.min(radius + pad, 34)}px`,
    });
    this.spot.classList.remove('is-empty');

    if (this.mobile) {
      card.dataset.placement = 'none';
      card.style.left = '';
      card.style.top = '';
      return;
    }

    const cw = card.offsetWidth;
    const ch = card.offsetHeight;
    const gap = 20;
    const fits = {
      right: vw - rect.right >= cw + gap + margin,
      left: rect.left >= cw + gap + margin,
      bottom: vh - rect.bottom >= ch + gap + margin,
      top: rect.top >= ch + gap + margin,
    };
    const order = step.placement ? [step.placement, 'right', 'bottom', 'left', 'top'] : ['right', 'bottom', 'left', 'top'];
    const side = order.find((candidate) => fits[candidate]);
    const centerX = (rect.left + rect.right) / 2;
    const centerY = (rect.top + rect.bottom) / 2;
    let x;
    let y;
    if (side === 'right' || side === 'left') {
      x = side === 'right' ? rect.right + gap : rect.left - gap - cw;
      y = clamp(centerY - ch / 2, margin, vh - ch - margin);
      this.arrow.style.top = `${clamp(centerY - y, 24, ch - 24) - 9}px`;
      this.arrow.style.left = '';
    } else if (side === 'bottom' || side === 'top') {
      y = side === 'bottom' ? rect.bottom + gap : rect.top - gap - ch;
      x = clamp(centerX - cw / 2, margin, vw - cw - margin);
      this.arrow.style.left = `${clamp(centerX - x, 24, cw - 24) - 9}px`;
      this.arrow.style.top = '';
    } else {
      x = vw - cw - 24;
      y = vh - ch - 24;
    }
    card.dataset.placement = side || 'none';
    card.style.left = `${x}px`;
    card.style.top = `${y}px`;
  }

  onReflow() {
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      if (this.active) this.place();
    });
  }

  onKey(event) {
    if (!this.active) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      this.close(false);
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      this.next();
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      this.prev();
    } else if (event.key === 'Tab') {
      const buttons = [...this.card.querySelectorAll('button')].filter((button) => !button.hidden && button.style.visibility !== 'hidden');
      if (!buttons.length) return;
      const first = buttons[0];
      const last = buttons[buttons.length - 1];
      if (!this.card.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }
}
