import { Tour } from './tour.js?v=8';

const $ = (id) => document.getElementById(id);
const SVG_NS = 'http://www.w3.org/2000/svg';

const ACTION_NAME = { intense: 'Intense', focused: 'Focused', light: 'Light', rest: 'Rest' };
const ACTION_TITLE = { intense: 'Intense study block', focused: 'Focused session', light: 'Light review', rest: 'Rest day' };
const ACTION_PHRASE = { intense: 'an intense study block', focused: 'a focused session', light: 'a light review', rest: 'a rest day' };
const ACTION_LEAD = {
  intense: (p) => `Do an intense ${p.hours}-hour study block today.`,
  focused: (p) => `Do a focused ${p.hours}-hour session on Concept ${conceptNumber(p.target_concept)}.`,
  light: (p) => `Do a light ${p.hours}-hour review today.`,
  rest: () => 'Take a rest day today.',
};
const ACTION_MEANING = {
  intense: () => 'a long session is worth the extra stress and the hours it takes',
  focused: (p) => `putting the time into Concept ${conceptNumber(p.target_concept)}, the weakest one, pays off more than spreading it across everything`,
  light: () => 'a short review is the best balance, keeping things moving without adding much stress',
  rest: () => 'more study would cost more in stress and time than it earns, so the best move is to rest',
};
const PROFILE_LABEL = {
  struggling: 'Struggling student',
  advanced: 'Well-prepared student',
  one_weak_spot: 'One weak concept',
  average_early: 'Average, early',
  burnt_out: 'Burnt out',
};

/* The three guided examples. Their explanations are generated from the planner's real result. */
const ACTION_ICON = {
  intense: 'bolt',
  focused: 'target',
  light: 'leaf',
  rest: 'moon',
};
const GUIDED = ['struggling', 'advanced', 'one_weak_spot'];

const DIFFICULTY = [['easy', 'Easy'], ['medium', 'Medium'], ['hard', 'Hard']];
const QUIZ = [['', 'Unknown'], ['low', 'Low'], ['high', 'High']];
const SLEEP = [['', 'Unknown'], ['poor', 'Poor'], ['good', 'Good']];
const MODEL = [['learned', 'Learned'], ['handcrafted', 'Hand-crafted']];
const SECTIONS = ['overview', 'planner', 'week', 'model'];

let meta;
let scenarios = [];
let plan = null;
let busy = false;
let tour;
const networkCache = new Map();

/* ---------- small helpers ---------- */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function svgNode(tag, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, tag);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  if (text !== undefined) node.textContent = text;
  return node;
}

const pct = (value) => `${Math.round(value * 100)}%`;
const hoursText = (hours) => `${hours} h`;
const conceptNumber = (concept) => meta.concepts.indexOf(concept) + 1;
const dayDate = (iso) => new Date(`${iso}T12:00:00Z`);
const dateLabel = (iso, options) => new Intl.DateTimeFormat('en-US', { timeZone: 'UTC', ...options }).format(dayDate(iso));
const timeLabel = (iso) => new Intl.DateTimeFormat('en-GB', { timeZone: meta.timezone, hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(iso));
const timeRange = (event) => `${timeLabel(event.start)}–${timeLabel(event.end)}`;
const examDateText = (iso) => dateLabel(iso, { weekday: 'long', month: 'long', day: 'numeric' });

async function request(url, payload) {
  const response = await fetch(url, payload
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }
    : {});
  if (!response.ok) {
    let message = `Request failed (${response.status}). Please try again.`;
    try {
      const data = await response.json();
      message = typeof data.detail === 'string' ? data.detail : data.detail.map((item) => item.msg).join('; ');
    } catch { /* keep the generic message */ }
    throw new Error(message);
  }
  return response.json();
}

async function getNetwork(learned) {
  const key = learned ? 'learned' : 'handcrafted';
  if (!networkCache.has(key)) networkCache.set(key, await request(`/api/network?use_learned=${learned}`));
  return networkCache.get(key);
}

/* ---------- form ---------- */

function segmented(name, label, options, selected) {
  const group = el('div', 'segmented');
  group.setAttribute('role', 'radiogroup');
  group.setAttribute('aria-label', label);
  const thumb = el('span', 'thumb');
  thumb.setAttribute('aria-hidden', 'true');
  group.append(thumb);
  options.forEach(([value, text]) => {
    const input = el('input');
    input.type = 'radio';
    input.name = name;
    input.value = value;
    input.id = `${name}-${value || 'unknown'}`;
    input.checked = value === selected;
    const labelEl = el('label', '', text);
    labelEl.htmlFor = input.id;
    group.append(input, labelEl);
  });
  return group;
}

/* Slide the raised pill under the checked option. The first placement and any resize are instant. */
function placeThumb(group, animate = true) {
  const thumb = group.querySelector('.thumb');
  const checked = group.querySelector('input:checked');
  const label = checked && checked.nextElementSibling;
  if (!thumb || !label || !label.offsetWidth) return;
  const instant = !animate || !group.dataset.ready;
  if (instant) group.classList.add('is-instant');
  thumb.style.width = `${label.offsetWidth}px`;
  thumb.style.transform = `translateX(${label.offsetLeft}px)`;
  group.dataset.ready = '1';
  if (instant) {
    void thumb.offsetWidth;
    group.classList.remove('is-instant');
  }
}

function initSegmented() {
  const groups = [...document.querySelectorAll('.segmented')];
  const observer = new ResizeObserver((entries) => entries.forEach((entry) => placeThumb(entry.target, false)));
  groups.forEach((group) => observer.observe(group));
  requestAnimationFrame(() => groups.forEach((group) => placeThumb(group, false)));
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => groups.forEach((group) => placeThumb(group, false)));
}

function field(label, control) {
  const wrap = el('div', 'field');
  const caption = el('span', 'label', label);
  caption.setAttribute('aria-hidden', 'true');
  wrap.append(caption, control);
  return wrap;
}

function conceptRow(label, control) {
  const row = el('div', 'row');
  row.append(el('span', '', label), control);
  return row;
}

function buildForm() {
  const concepts = $('concept-fields');
  concepts.replaceChildren();
  meta.concepts.forEach((concept, index) => {
    const name = `Concept ${index + 1}`;
    const card = el('div', 'concept');
    card.setAttribute('role', 'group');
    card.setAttribute('aria-label', name);
    card.append(
      el('h3', 'concept-title', name),
      conceptRow('Difficulty', segmented(`difficulty_${concept}`, `${name} difficulty`, DIFFICULTY, 'medium')),
      conceptRow('Quiz', segmented(`quiz_${concept}`, `${name} latest quiz`, QUIZ, '')),
    );
    concepts.append(card);
  });
  $('sleep-field').replaceChildren(...field('Sleep last night', segmented('sleep', 'Sleep last night', SLEEP, '')).childNodes);
  $('model-field').replaceChildren(...field('Model', segmented('model', 'Probability model', MODEL, 'learned')).childNodes);
  $('exam-date').min = meta.today;
  Object.keys(PROFILE_LABEL).forEach((name) => {
    if (!scenarios.some((s) => s.name === name)) return;
    const option = el('option', '', PROFILE_LABEL[name]);
    option.value = name;
    $('profile').append(option);
  });
}

const checkedValue = (name) => $('plan-form').querySelector(`input[name="${name}"]:checked`)?.value ?? '';

function setChoice(name, value) {
  const input = $('plan-form').querySelector(`input[name="${name}"][value="${value ?? ''}"]`);
  if (!input) return;
  input.checked = true;
  placeThumb(input.closest('.segmented'));
}

function readForm() {
  const difficulty = {};
  const quiz = {};
  meta.concepts.forEach((concept) => {
    difficulty[concept] = checkedValue(`difficulty_${concept}`);
    quiz[concept] = checkedValue(`quiz_${concept}`) || null;
  });
  return {
    difficulty,
    quiz,
    sleep: checkedValue('sleep') || null,
    exam_date: $('exam-date').value,
    use_learned: checkedValue('model') === 'learned',
  };
}

function applyProfile(name) {
  const scenario = scenarios.find((s) => s.name === name);
  if (!scenario) return null;
  meta.concepts.forEach((concept) => {
    setChoice(`difficulty_${concept}`, scenario.difficulty[concept]);
    setChoice(`quiz_${concept}`, scenario.quiz[concept]);
  });
  setChoice('sleep', scenario.sleep);
  $('exam-date').value = scenario.exam_date;
  $('profile').value = name;
  return scenario;
}

function markStale() {
  if (plan) $('stale').hidden = false;
}

/* ---------- rendering ---------- */

const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* Run `apply` after the next paint so CSS transitions start from the old value. The timer is a
   fallback for hidden tabs, where animation frames are paused. */
function afterPaint(apply) {
  let done = false;
  const once = () => { if (!done) { done = true; apply(); } };
  requestAnimationFrame(() => requestAnimationFrame(once));
  setTimeout(once, 250);
}

function growAfterPaint(node, property, value) {
  afterPaint(() => { node.style[property] = value; });
}

function setRing(id, fraction) {
  afterPaint(() => $(id).style.setProperty('--pct', String(Math.round(Math.max(0, Math.min(1, fraction)) * 100))));
}

/* Count a figure up (or down) to its new value. The final text is always set exactly. */
function countTo(node, target, render, duration = 900) {
  const from = node._value ?? 0;
  node._value = target;
  const token = (node._token = (node._token || 0) + 1);
  if (reducedMotion() || from === target) {
    node.textContent = render(target);
    return;
  }
  const start = performance.now();
  const step = (now) => {
    if (node._token !== token) return;
    const t = Math.min(1, (now - start) / duration);
    node.textContent = render(t < 1 ? from + (target - from) * (1 - (1 - t) ** 3) : target);
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
  setTimeout(() => { if (node._token === token) node.textContent = render(target); }, duration + 150);
}

function renderStats(result) {
  $('stat-action').textContent = ACTION_TITLE[result.best_action];
  $('stat-action-sub').textContent = result.best_action === 'focused' ? `On Concept ${conceptNumber(result.target_concept)}` : '';
  countTo($('stat-hours'), result.hours, (value) => hoursText(Math.round(value * 2) / 2));
  $('stat-session').textContent = result.events.length ? timeRange(result.events[0]) : 'No session';
  countTo($('stat-pass'), result.posteriors.p_pass * 100, (value) => `${Math.round(value)}%`);
  countTo($('stat-stress'), result.posteriors.p_stress_high * 100, (value) => `${Math.round(value)}%`);
  countTo($('stat-days'), result.days_until_exam, (value) => String(Math.round(value)));
  $('stat-exam').textContent = dateLabel(result.exam_date, { weekday: 'short', month: 'short', day: 'numeric' });
  setRing('ring-pass', result.posteriors.p_pass);
  setRing('ring-stress', result.posteriors.p_stress_high);
}

function renderScores(result) {
  const chart = $('score-chart');
  const table = $('score-table');
  chart.replaceChildren();
  table.replaceChildren();
  const values = meta.actions.map((action) => result.expected_utility[action.key]);
  const max = Math.max(...values, 1);
  meta.actions.forEach((action, index) => {
    const best = action.key === result.best_action;
    const fill = el('div', 'bar-fill');
    const track = el('div', 'bar-track');
    track.append(fill);
    const column = el('div', best ? 'bar-col is-best' : 'bar-col');
    column.append(el('span', 'bar-value', values[index].toFixed(1)), track, el('span', 'bar-name', ACTION_NAME[action.key]), el('span', 'bar-hours', hoursText(action.hours)));
    chart.append(column);
    growAfterPaint(fill, 'height', `${(Math.max(0, values[index]) / max) * 100}%`);

    const row = el('tr');
    row.append(el('td', '', ACTION_NAME[action.key] + (best ? ' (recommended)' : '')), el('td', '', hoursText(action.hours)), el('td', '', values[index].toFixed(1)));
    table.append(row);
  });
}

function renderBeliefs(result) {
  const rows = [
    ...meta.concepts.map((concept, index) => [`Concept ${index + 1}`, result.posteriors.p_mastery_high[concept]]),
    ['Stress risk', result.posteriors.p_stress_high],
    ['Pass chance', result.posteriors.p_pass],
  ];
  const list = $('belief-bars');
  list.replaceChildren();
  rows.forEach(([label, value]) => {
    const fill = el('span', 'fill');
    const track = el('div', 'track');
    track.setAttribute('aria-hidden', 'true');
    track.append(fill);
    const row = el('div', 'belief');
    row.append(el('span', '', label), track, el('span', '', pct(value)));
    list.append(row);
    growAfterPaint(fill, 'width', `${Math.max(0, Math.min(100, value * 100))}%`);
  });
}

function renderWeek(result) {
  const calendar = $('calendar');
  calendar.replaceChildren();
  for (let offset = 0; offset < 7; offset += 1) {
    const date = dayDate(result.today);
    date.setUTCDate(date.getUTCDate() + offset);
    const iso = date.toISOString().slice(0, 10);
    const day = el('div', offset === 0 ? 'day is-today' : 'day');
    const head = el('div', 'day-head');
    head.append(el('span', '', offset === 0 ? 'Today' : dateLabel(iso, { weekday: 'short' })), el('b', '', String(date.getUTCDate())));
    day.append(head);
    result.events.filter((event) => event.start.slice(0, 10) === iso).forEach((event) => {
      const session = el('div', 'session');
      const name = result.best_action === 'focused' ? `Focused · Concept ${conceptNumber(result.target_concept)}` : ACTION_NAME[result.best_action];
      session.append(el('span', '', name), el('small', '', timeRange(event)));
      day.append(session);
    });
    if (offset === 0 && !result.events.length) day.append(el('p', 'day-note', 'Rest day'));
    if (iso === result.exam_date) day.append(el('span', 'exam-tag', 'Exam'));
    calendar.append(day);
  }
}

function renderNetwork(network) {
  const svg = svgNode('svg', {
    viewBox: '0 0 1000 380',
    role: 'img',
    'aria-label': '13-node Bayesian network: difficulty affects mastery, mastery affects quizzes and exam success, days left affects stress, and stress affects sleep and exam success',
  });
  const marker = svgNode('marker', { id: 'net-arrow', viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: 'auto' });
  marker.append(svgNode('path', { d: 'M 0 0 L 10 5 L 0 10 z', class: 'net-arrow' }));
  svg.append(svgNode('defs', {}), marker);

  const positions = {};
  meta.concepts.forEach((concept, index) => {
    positions[`Difficulty_${concept}`] = [80 + index * 240, 40];
    positions[`Mastery_${concept}`] = [80 + index * 240, 150];
    positions[`Quiz_${concept}`] = [180 + index * 240, 220];
  });
  Object.assign(positions, { DaysLeft: [820, 40], Stress: [820, 150], Sleep: [920, 220], ExamSuccess: [440, 330] });

  network.edges.forEach((edge) => {
    const [x1, y1] = positions[edge.source];
    const [x2, y2] = positions[edge.target];
    const dx = x2 - x1;
    const dy = y2 - y1;
    const boundary = Math.min(64 / Math.abs(dx), 22 / Math.abs(dy));
    const end = boundary + 5 / Math.hypot(dx, dy);
    svg.append(svgNode('line', {
      x1: x1 + dx * boundary, y1: y1 + dy * boundary, x2: x2 - dx * end, y2: y2 - dy * end,
      class: 'net-edge', 'marker-end': 'url(#net-arrow)',
    }));
  });
  network.nodes.forEach((node) => {
    const [x, y] = positions[node.id];
    const group = svgNode('g', { class: node.role === 'query' ? 'net-node query' : 'net-node' });
    group.append(svgNode('rect', { x: x - 64, y: y - 22, width: 128, height: 44, rx: 10 }), svgNode('text', { x, y: y + 4 }, node.id.replaceAll('_', ' ')));
    svg.append(group);
  });
  $('network-graph').replaceChildren(svg);

  const select = $('node-select');
  const previous = select.value;
  select.replaceChildren(...network.nodes.map((node) => {
    const option = el('option', '', node.id.replaceAll('_', ' '));
    option.value = node.id;
    return option;
  }));
  if (network.cpds[previous]) select.value = previous;
  select.onchange = () => renderCpd(network);
  renderCpd(network);
}

function renderCpd(network) {
  const cpd = network.cpds[$('node-select').value];
  const table = el('table');
  const head = el('tr');
  [...cpd.parents, ...cpd.states.map((state) => `P(${state})`)].forEach((text) => {
    const th = el('th', '', text.replaceAll('_', ' '));
    th.scope = 'col';
    head.append(th);
  });
  const thead = el('thead');
  thead.append(head);
  let combinations = [[]];
  cpd.parents.forEach((parent) => {
    combinations = combinations.flatMap((previous) => cpd.parent_states[parent].map((state) => [...previous, state]));
  });
  const body = el('tbody');
  combinations.forEach((combo, index) => {
    const row = el('tr');
    [...combo, ...cpd.values.map((values) => `${(values[index] * 100).toFixed(1)}%`)].forEach((value) => row.append(el('td', '', value)));
    body.append(row);
  });
  table.append(thead, body);
  $('cpd-table').replaceChildren(table);
}

/* ---------- calculating ---------- */

function setBusy(state) {
  busy = state;
  $('main').setAttribute('aria-busy', String(state));
  $('calculate').classList.toggle('is-busy', state);
  $('plan-form').querySelectorAll('input, select, button').forEach((control) => { control.disabled = state; });
}

async function calculate() {
  if (busy) return plan;
  if (!$('exam-date').value) {
    $('exam-date').focus();
    showError('Choose an exam date.');
    return null;
  }
  const payload = readForm();
  hideError();
  setBusy(true);
  try {
    const [result, network] = await Promise.all([request('/api/plan', payload), getNetwork(payload.use_learned)]);
    plan = result;
    renderStats(result);
    renderScores(result);
    renderBeliefs(result);
    renderWeek(result);
    renderNetwork(network);
    $('stale').hidden = true;
    $('status').textContent = `Plan updated: ${ACTION_NAME[result.best_action]}, ${hoursText(result.hours)}.`;
    return result;
  } catch (error) {
    showError(error.message || 'Could not calculate the plan. Check that the server is running and try again.');
    return null;
  } finally {
    setBusy(false);
  }
}

function showError(message) {
  $('error').textContent = message;
  $('error').hidden = false;
}

function hideError() {
  $('error').hidden = true;
}

/* ---------- theme ---------- */

function setTheme(theme, persist) {
  document.documentElement.dataset.theme = theme;
  $('theme-toggle').setAttribute('aria-checked', String(theme === 'dark'));
  if (!persist) return;
  try { localStorage.setItem('theme', theme); } catch { /* storage unavailable */ }
}

/* The switch reveals the new theme as a circle growing from the switch itself. Browsers without
   view transitions, and people who prefer reduced motion, get a plain colour fade instead. */
function toggleTheme() {
  const root = document.documentElement;
  const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
  if (reducedMotion() || !document.startViewTransition) {
    root.classList.add('theme-fade');
    setTheme(next, true);
    setTimeout(() => root.classList.remove('theme-fade'), 500);
    return;
  }
  const box = $('theme-toggle').getBoundingClientRect();
  const x = box.left + box.width / 2;
  const y = box.top + box.height / 2;
  const radius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
  const transition = document.startViewTransition(() => setTheme(next, true));
  transition.ready.then(() => root.animate(
    { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
    { duration: 650, easing: 'cubic-bezier(0.4, 0, 0.2, 1)', pseudoElement: '::view-transition-new(root)' },
  )).catch(() => {});
}

function initTheme() {
  setTheme(document.documentElement.dataset.theme, false);
  $('theme-toggle').addEventListener('click', toggleTheme);
}

/* ---------- navigation highlight ---------- */

function initScrollSpy() {
  const links = [...document.querySelectorAll('.rail-nav a')];
  const activate = (id) => links.forEach((link) => link.classList.toggle('is-active', link.dataset.section === id));
  const update = () => {
    const line = topInset() + 130;
    let current = SECTIONS[0];
    SECTIONS.forEach((id) => { if ($(id).getBoundingClientRect().top <= line) current = id; });
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) current = SECTIONS[SECTIONS.length - 1];
    activate(current);
  };
  let frame = 0;
  window.addEventListener('scroll', () => {
    if (frame) return;
    frame = requestAnimationFrame(() => { frame = 0; update(); });
  }, { passive: true });
  window.addEventListener('resize', update);
  update();
}

/* ---------- guided tours ---------- */

function topInset() {
  return window.matchMedia('(max-width: 720px)').matches ? $('rail').offsetHeight + 24 : document.querySelector('.topbar').offsetHeight + 16;
}

function seenTour() {
  try { return localStorage.getItem('tour-seen') === '1'; } catch { return false; }
}

function rememberTour() {
  try { localStorage.setItem('tour-seen', '1'); } catch { /* storage unavailable */ }
}

function appTourSteps() {
  return [
    {
      title: 'Welcome to the study planner',
      body: 'This quick tour shows where everything is. It takes about a minute.\n\nUse Next, or the arrow keys. Press Esc to leave at any time.',
      nextLabel: 'Start',
    },
    { target: '#rail', title: 'Navigation', placement: 'right', body: 'Jump to any section. The highlighted item follows you as you scroll.' },
    { target: '#profile-field', title: 'Pick a student', body: 'Start from a ready-made student, or leave this on Custom and enter your own evidence.' },
    { target: '#concept-fields', title: 'Difficulty and quizzes', body: 'For each concept, set how hard it is and the latest quiz result. Leave the quiz on Unknown if there is none.' },
    { target: '#context-fields', title: 'Sleep and exam date', body: 'Poor sleep raises the stress estimate. The exam date sets how many days are left.' },
    { target: '#model-field', title: 'Choose a model', body: 'Learned uses probabilities estimated from 5,000 simulated students. Hand-crafted uses our original estimates.' },
    { target: '#calculate', title: 'Calculate', body: 'Runs the model on your evidence. Nothing is saved to your calendar.' },
    { target: '#overview', title: 'The result at a glance', placement: 'bottom', body: 'The recommended action, study time, pass chance, stress risk and days left.', before: ensurePlan },
    { target: '#scores', title: 'Action scores', body: 'Each study option gets a score that weighs the chance of passing against stress and study hours. The tallest bar is recommended.', before: ensurePlan },
    { target: '#beliefs', title: 'Beliefs', body: 'What the model thinks before you act: how well each concept is known, your stress risk and your chance of passing.' },
    { target: '#week', title: 'This week', placement: 'top', body: "Today's session is placed on the calendar. Only today is planned, so run it again each day with fresh evidence." },
    { target: '#network-graph', title: 'Inside the model', placement: 'top', body: 'The network behind the numbers. Arrows show what influences what, and the table below it shows every probability.' },
    { target: '#theme-toggle', title: 'Light or dark', body: 'Switch themes here. Your choice is remembered.' },
    { target: '#help-button', title: 'Need this again?', body: 'Replay this tour, or watch the planner work through a guided example, from here.' },
  ];
}

async function ensurePlan() {
  if (!plan) await calculate();
}

const joinList = (items) => (items.length < 2 ? items.join('') : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`);
const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);
/* "an 87%", "an 11%", "a 9%": percentages read aloud as eight-, eleven- and eighteen- start with a vowel sound */
const withArticle = (percent) => `${/^(8|11|18)/.test(percent) ? 'an' : 'a'} ${percent}`;

function difficultyClause(scenario) {
  const levels = meta.concepts.map((concept) => scenario.difficulty[concept]);
  if (levels.every((level) => level === levels[0])) return `every concept is ${levels[0]}`;
  return joinList(meta.concepts.map((concept, index) => `Concept ${index + 1} is ${scenario.difficulty[concept]}`));
}

/* What the practice quizzes say, in words, and what that does to the model's view. */
function quizReading(scenario) {
  const given = meta.concepts.map((concept, index) => [index + 1, scenario.quiz[concept]]).filter(([, result]) => result);
  if (!given.length) return { clause: 'no quiz results are in yet', simple: true, effect: 'so for now the model relies on difficulty alone' };
  if (given.length === meta.concepts.length && given.every(([, result]) => result === given[0][1])) {
    return {
      clause: `every practice quiz came back ${given[0][1]}`,
      simple: true,
      effect: given[0][1] === 'low' ? 'which pulls those estimates down even further' : 'which lifts those estimates',
    };
  }
  const partial = given.length < meta.concepts.length;
  const text = joinList(given.map(([number, result]) => `the Concept ${number} quiz came back ${result}`));
  const which = given.length === 1 ? 'that concept' : 'those concepts';
  return {
    clause: `${text}${partial ? ', and the others have no quiz yet' : ''}`,
    simple: false,
    effect: partial ? `so the model adjusts ${which}, while the rest rely on difficulty alone` : 'so the model adjusts each concept to match its quiz',
  };
}

function examClause(scenario) {
  const days = scenario.days_until_exam;
  if (days === 0) return 'the exam is today';
  if (days === 1) return 'the exam is only 1 day away';
  if (days <= 3) return `the exam is only ${days} days away`;
  if (days > 10) return `the exam is still ${days} days away`;
  return `the exam is ${days} days away`;
}

function pressureNote(days) {
  if (days <= 3) return 'which tends to push stress up';
  if (days <= 10) return 'so there is some time pressure';
  return 'so there is less pressure for now';
}

function sleepSentence(scenario) {
  if (scenario.sleep === 'poor') return 'Poor sleep last night points to higher stress.';
  if (scenario.sleep === 'good') return 'Good sleep last night points to lower stress.';
  return "Sleep isn't recorded, so it plays no part in the estimate.";
}

const stressWord = (value) => (value >= 0.6 ? 'high' : value <= 0.3 ? 'low' : 'moderate');

function passMeaning(value) {
  if (value < 0.25) return 'there is a lot of ground to cover';
  if (value < 0.6) return 'it is a real chance, but far from safe';
  return 'they are in decent shape';
}

const masteryList = (posteriors) => joinList(meta.concepts.map((concept, index) => `${pct(posteriors.p_mastery_high[concept])} for Concept ${index + 1}`));

/* The evidence in one or two plain sentences, e.g. "Every concept is hard, and every practice quiz came back low. The exam is only 2 days away." */
function situationSentence(scenario) {
  const reading = quizReading(scenario);
  const difficulty = capitalize(difficultyClause(scenario));
  const evidence = reading.simple ? `${difficulty}, and ${reading.clause}.` : `${difficulty}. ${capitalize(reading.clause)}.`;
  return `${evidence} ${capitalize(examClause(scenario))}.`;
}

/* The summary's wording: the situation, what the scores mean, and what to do next. */
function summaryParts(scenario, [first, second]) {
  const post = plan.posteriors;
  const gap = first[1] - second[1];
  const situation = `${situationSentence(scenario)} Because of that, the model estimates mastery at ${masteryList(post)}, `
    + `with ${withArticle(pct(post.p_pass))} chance of passing and ${withArticle(pct(post.p_stress_high))} risk of high stress.`;
  const meaning = `${ACTION_NAME[first[0]]} scores ${first[1].toFixed(1)}, ahead of ${ACTION_NAME[second[0]].toLowerCase()} at ${second[1].toFixed(1)}, `
    + `which means ${ACTION_MEANING[first[0]](plan)}.`
    + (gap < 2 ? ` That said, it is a close call, so ${ACTION_PHRASE[second[0]]} would also be a reasonable choice.` : ' That lead is clear enough to act on.');
  return { gap, situation, meaning, next: 'The form now shows this student, so change anything and press Calculate to see how the advice shifts.' };
}

function svgIcon(name) {
  const svg = svgNode('svg', { class: 'icon' });
  svg.append(svgNode('use', { href: `#i-${name}` }));
  return svg;
}

/* Bold the figures (percentages and one-decimal scores) so the eye lands on them first. */
function richText(text) {
  const fragment = document.createDocumentFragment();
  text.split(/(\b\d+(?:\.\d+)?%|\b\d+\.\d\b)/).forEach((part, index) => {
    fragment.append(index % 2 ? el('strong', '', part) : document.createTextNode(part));
  });
  return fragment;
}

function gauge(label, value, tone) {
  const ring = el('span', `ring lg ${tone}`);
  ring.append(el('span', 'ring-value', pct(value)));
  afterPaint(() => ring.style.setProperty('--pct', String(Math.round(value * 100))));
  const wrap = el('div', 'gauge');
  wrap.append(ring, el('span', 'gauge-label', label));
  return wrap;
}

function scoreRows(ranked) {
  const max = Math.max(...ranked.map(([, value]) => value), 1);
  const list = el('div', 'score-rows');
  ranked.forEach(([key, value], index) => {
    const fill = el('span', 'fill');
    const track = el('div', 'track');
    track.append(fill);
    const row = el('div', index === 0 ? 'score-row is-best' : 'score-row');
    row.append(el('span', 'score-name', ACTION_NAME[key]), track, el('span', 'score-value', value.toFixed(1)));
    list.append(row);
    growAfterPaint(fill, 'width', `${(Math.max(0, value) / max) * 100}%`);
  });
  return list;
}

/* The guided example's closing card: a headline recommendation and short, spaced paragraphs on the
   left; the numbers as graphics (two gauges, the study time and the four scores) on the right. */
function summaryView(scenario, ranked) {
  const parts = summaryParts(scenario, ranked);
  const best = plan.best_action;

  const icon = el('span', 'summary-icon');
  icon.append(svgIcon(ACTION_ICON[best]));
  const head = el('div', 'summary-head');
  head.append(icon, el('span', 'summary-label', 'Summary'));
  const title = el('h3', 'summary-title', ACTION_LEAD[best](plan));
  title.id = 'tour-title';

  const section = (heading, text) => {
    const wrap = el('section', 'summary-section');
    const paragraph = el('p');
    paragraph.append(richText(text));
    wrap.append(el('h4', '', heading), paragraph);
    return wrap;
  };
  const intro = el('div', 'summary-intro');
  intro.append(head, title);
  const body = el('div', 'summary-body');
  body.append(section('The situation', parts.situation), section('What it means', parts.meaning), el('p', 'summary-next', parts.next));

  const gauges = el('div', 'gauges');
  gauges.append(gauge('Pass chance', plan.posteriors.p_pass, 'good'), gauge('Stress risk', plan.posteriors.p_stress_high, 'warn'));
  const time = el('div', 'time-chip');
  time.append(el('strong', '', hoursText(plan.hours)), el('span', '', plan.events.length ? `${ACTION_NAME[best]} \u00b7 ${timeRange(plan.events[0])}` : 'No session today'));
  const verdict = el('span', parts.gap < 2 ? 'chip is-close' : 'chip is-clear', `${parts.gap < 2 ? 'Close call' : 'Clear winner'} \u00b7 ${parts.gap.toFixed(1)} points ahead`);
  const scores = el('div', 'summary-scores');
  scores.append(el('span', 'visual-label', 'Action scores'), scoreRows(ranked), verdict);
  const visual = el('aside', 'summary-visual');
  visual.append(gauges, time, scores);

  const wrap = el('div', 'summary');
  wrap.append(intro, visual, body);
  return wrap;
}

function guideSteps(name) {
  const scenario = scenarios.find((s) => s.name === name);
  const label = PROFILE_LABEL[name];
  const ranked = () => Object.entries(plan.expected_utility).sort((a, b) => b[1] - a[1]);
  return [
    {
      title: label,
      body: () => `${situationSentence(scenario)}\n\nWe will fill in the evidence, run the planner and talk through what it decides and why.`,
      nextLabel: 'Start',
    },
    {
      target: '#profile-field',
      title: 'Load the student',
      before: () => {
        applyProfile(name);
        markStale();
      },
      body: `We have loaded the ${label.toLowerCase()} profile, which fills in all of the evidence below.`,
    },
    {
      target: '#concept-fields',
      title: 'Difficulty and quizzes',
      body: () => {
        const reading = quizReading(scenario);
        return `${capitalize(difficultyClause(scenario))}, so the model starts out with a view on how likely each one is to be mastered.\n\n`
          + `${capitalize(reading.clause)}, ${reading.effect}.`;
      },
    },
    {
      target: '#context-fields',
      title: 'Sleep and exam date',
      body: () => `${sleepSentence(scenario)}\n\n${capitalize(examClause(scenario))} (${examDateText(scenario.exam_date)}), ${pressureNote(scenario.days_until_exam)}.`,
    },
    {
      target: '#calculate',
      title: 'Run the planner',
      body: 'Now the planner pulls everything together: how well each concept is probably known, how stressed the student is likely to be, and how likely they are to pass. It then scores every study option.',
      nextLabel: 'Calculate',
      after: async () => {
        if (!(await calculate())) tour.close(false);
      },
    },
    {
      target: '#beliefs',
      title: 'What the model believes',
      body: () => {
        const post = plan.posteriors;
        return `From that evidence, the model estimates mastery at ${masteryList(post)}.\n\n`
          + `Stress risk comes out ${stressWord(post.p_stress_high)}, at ${pct(post.p_stress_high)}, and the chance of passing if nothing changes is ${pct(post.p_pass)}, which means ${passMeaning(post.p_pass)}.`;
      },
    },
    {
      target: '#scores',
      title: 'Scoring the options',
      body: () => `Each option gets a score that weighs the chance of passing against stress, then takes off a point for every hour of study. Here, ${joinList(ranked().map(([key, value]) => `${ACTION_NAME[key].toLowerCase()} scores ${value.toFixed(1)}`))}.\n\nThe highest score wins, so that is what the planner recommends.`,
    },
    {
      target: '#overview',
      title: 'The decision',
      placement: 'bottom',
      body: () => {
        const [first, second] = ranked();
        const gap = first[1] - second[1];
        const rival = ACTION_PHRASE[second[0]];
        const focus = plan.best_action === 'focused' ? ` on Concept ${conceptNumber(plan.target_concept)}` : '';
        const when = plan.events.length ? ` It is placed today at ${timeRange(plan.events[0])}.` : ' Nothing is scheduled today.';
        let margin = `It leads ${rival} by ${gap.toFixed(1)} points, a clear gap.`;
        if (gap < 2) margin = `It is only ${gap.toFixed(1)} points ahead of ${rival}, so this is a close call, and ${rival} would not be a bad choice either.`;
        else if (gap < 8) margin = `It leads ${rival} by ${gap.toFixed(1)} points, which is a fairly clear preference.`;
        return `That makes the recommendation ${ACTION_PHRASE[plan.best_action]}${focus} (${hoursText(plan.hours)}).${when}\n\n${margin}`;
      },
    },
    {
      target: '#week',
      title: 'On the calendar',
      placement: 'top',
      body: () => (plan.events.length
        ? "Today's session shows up here, and the other days stay empty because the planner decides one day at a time."
        : 'A rest day adds nothing to the calendar, and any planner sessions already on today would be cleared.'),
    },
    {
      view: () => summaryView(scenario, ranked()),
      nextLabel: 'Done',
      extra: { label: 'Replay', onClick: () => startGuide(name) },
    },
  ];
}

async function startTour(opener) {
  await ensurePlan();
  tour.start(appTourSteps(), opener);
}

async function startGuide(name, opener) {
  if (!plan) await ensurePlan();
  tour.start(guideSteps(name), opener || $('help-button'));
}

/* ---------- help menu ---------- */

function initHelp() {
  const button = $('help-button');
  const menu = $('help-menu');
  const items = () => [...menu.querySelectorAll('.menu-item')];

  GUIDED.forEach((name) => {
    const scenario = scenarios.find((s) => s.name === name);
    if (!scenario) return;
    const item = el('button', 'menu-item');
    item.type = 'button';
    item.setAttribute('role', 'menuitem');
    item.dataset.guide = name;
    const icon = svgNode('svg', { class: 'icon' });
    icon.append(svgNode('use', { href: '#i-play' }));
    const text = el('span');
    text.append(el('strong', '', PROFILE_LABEL[name]), el('small', '', `Exam in ${scenario.days_until_exam} days`));
    item.append(icon, text);
    $('guide-items').append(item);
  });

  const open = () => {
    menu.hidden = false;
    button.setAttribute('aria-expanded', 'true');
    items()[0]?.focus();
  };
  const close = (returnFocus) => {
    if (menu.hidden) return;
    menu.hidden = true;
    button.setAttribute('aria-expanded', 'false');
    if (returnFocus) button.focus();
  };

  button.addEventListener('click', () => (menu.hidden ? open() : close(false)));
  document.addEventListener('click', (event) => {
    if (!menu.hidden && !menu.contains(event.target) && !button.contains(event.target)) close(false);
  });
  menu.addEventListener('keydown', (event) => {
    const list = items();
    const index = list.indexOf(document.activeElement);
    if (event.key === 'Escape') { event.preventDefault(); close(true); }
    else if (event.key === 'ArrowDown') { event.preventDefault(); list[(index + 1) % list.length].focus(); }
    else if (event.key === 'ArrowUp') { event.preventDefault(); list[(index - 1 + list.length) % list.length].focus(); }
    else if (event.key === 'Home') { event.preventDefault(); list[0].focus(); }
    else if (event.key === 'End') { event.preventDefault(); list[list.length - 1].focus(); }
    else if (event.key === 'Tab') close(false);
  });
  menu.addEventListener('click', (event) => {
    const item = event.target.closest('.menu-item');
    if (!item) return;
    close(false);
    if (item.dataset.guide === 'tour') startTour(button);
    else startGuide(item.dataset.guide, button);
  });
}

/* ---------- start-up ---------- */

document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  tour = new Tour({ topInset, onClose: rememberTour });

  $('plan-form').addEventListener('submit', (event) => { event.preventDefault(); calculate(); });
  $('plan-form').addEventListener('change', (event) => {
    if (event.target.matches('.segmented input')) placeThumb(event.target.closest('.segmented'));
    if (event.target.id === 'profile') applyProfile(event.target.value);
    else if (event.target.name !== 'model') $('profile').value = '';
    markStale();
  });

  try {
    [meta, scenarios] = await Promise.all([getNetwork(false), request('/api/scenarios')]);
    $('today-label').textContent = dateLabel(meta.today, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    $('today-label').dateTime = meta.today;
    buildForm();
    initSegmented();
    applyProfile('one_weak_spot');
    $('calculate').disabled = false;
    initScrollSpy();
    initHelp();
    await calculate();
    if (!seenTour()) setTimeout(() => startTour($('help-button')), 700);
  } catch (error) {
    showError(`Could not load the planner. Make sure the local server is running, then reload. ${error.message}`);
  }
});
