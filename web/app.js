import { Tour } from './tour.js';

const $ = (id) => document.getElementById(id);
const SVG_NS = 'http://www.w3.org/2000/svg';

const ACTION_NAME = { intense: 'Intense', focused: 'Focused', light: 'Light', rest: 'Rest' };
const ACTION_PHRASE = { intense: 'an intense study block', focused: 'a focused session', light: 'a light review', rest: 'a rest day' };
const PROFILE_LABEL = {
  struggling: 'Struggling student',
  advanced: 'Well-prepared student',
  one_weak_spot: 'One weak concept',
  average_early: 'Average, early',
  burnt_out: 'Burnt out',
};

/* The three guided examples. The takeaway is only shown when the planner picks the
   action the example is meant to illustrate, so it can never contradict the result. */
const GUIDED = [
  { name: 'struggling', takeaway: 'Almost nothing is mastered and the exam is close, so a long session is worth its stress and time cost.' },
  { name: 'advanced', takeaway: 'Already prepared with time to spare: extra study would add stress and cost more than it earns, so the planner clears the day.' },
  { name: 'one_weak_spot', takeaway: 'Only one concept is weak, so a single focused session on it beats reviewing everything.' },
];

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
  if (input) input.checked = true;
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

function renderStats(result) {
  $('stat-action').textContent = ACTION_NAME[result.best_action];
  $('stat-action-sub').textContent = result.best_action === 'focused' ? `Concept ${conceptNumber(result.target_concept)}` : '';
  $('stat-hours').textContent = hoursText(result.hours);
  $('stat-session').textContent = result.events.length ? timeRange(result.events[0]) : 'No session';
  $('stat-pass').textContent = pct(result.posteriors.p_pass);
  $('stat-stress').textContent = pct(result.posteriors.p_stress_high);
  $('stat-days').textContent = String(result.days_until_exam);
  $('stat-exam').textContent = dateLabel(result.exam_date, { weekday: 'short', month: 'short', day: 'numeric' });
}

function growAfterPaint(node, property, value) {
  requestAnimationFrame(() => requestAnimationFrame(() => { node.style[property] = value; }));
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

function initTheme() {
  setTheme(document.documentElement.dataset.theme, false);
  $('theme-toggle').addEventListener('click', () => {
    setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark', true);
  });
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

function difficultySentence(scenario) {
  return meta.concepts.map((concept, index) => `Concept ${index + 1} is ${scenario.difficulty[concept]}`).join(', ') + '.';
}

function quizSentence(scenario) {
  const given = meta.concepts.map((concept, index) => [index + 1, scenario.quiz[concept]]).filter(([, result]) => result);
  if (!given.length) return 'There are no quiz results yet.';
  if (given.length === meta.concepts.length && given.every(([, result]) => result === given[0][1])) {
    return `All three quizzes came back ${given[0][1]}.`;
  }
  const text = given.map(([number, result]) => `the Concept ${number} quiz came back ${result}`).join(', ');
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}${given.length < meta.concepts.length ? '; the others have no quiz yet' : ''}.`;
}

function guideSteps(name) {
  const scenario = scenarios.find((s) => s.name === name);
  const label = PROFILE_LABEL[name];
  const ranked = () => Object.entries(plan.expected_utility).sort((a, b) => b[1] - a[1]);
  const guided = GUIDED.find((g) => g.name === name);
  return [
    {
      title: label,
      body: `${scenario.description}\n\nWe will fill in the evidence, run the planner and explain what it decides.`,
      nextLabel: 'Start',
    },
    {
      target: '#profile-field',
      title: 'Load the student',
      before: () => {
        applyProfile(name);
        markStale();
      },
      body: `${label} is selected. That fills in all the evidence below.`,
    },
    {
      target: '#concept-fields',
      title: 'Difficulty and quizzes',
      body: () => `${difficultySentence(scenario)}\n\n${quizSentence(scenario)}`,
    },
    {
      target: '#context-fields',
      title: 'Sleep and exam date',
      body: () => `${scenario.sleep ? `Last night's sleep was ${scenario.sleep}.` : 'Sleep is not recorded.'}\n\nThe exam is on ${examDateText(scenario.exam_date)}, ${scenario.days_until_exam} days away.`,
    },
    {
      target: '#calculate',
      title: 'Run the planner',
      body: 'Calculate asks the model how well each concept is known, how stressed the student is and how likely they are to pass, then scores each study option.',
      nextLabel: 'Calculate',
      after: async () => {
        if (!(await calculate())) tour.close(false);
      },
    },
    {
      target: '#beliefs',
      title: 'What the model believes',
      body: () => {
        const m = plan.posteriors.p_mastery_high;
        const mastery = meta.concepts.map((concept, index) => `Concept ${index + 1} ${pct(m[concept])}`).join(', ');
        return `Mastery: ${mastery}.\n\nStress risk is ${pct(plan.posteriors.p_stress_high)}, and the chance of passing if nothing changes is ${pct(plan.posteriors.p_pass)}.`;
      },
    },
    {
      target: '#scores',
      title: 'Scoring the options',
      body: () => `${ranked().map(([key, value]) => `${ACTION_NAME[key]} ${value.toFixed(1)}`).join(', ')}.\n\nEach score weighs the chance of passing against stress and takes off one point per study hour. The highest wins.`,
    },
    {
      target: '#overview',
      title: 'The decision',
      placement: 'bottom',
      body: () => {
        const focus = plan.best_action === 'focused' ? ` on Concept ${conceptNumber(plan.target_concept)}` : '';
        const when = plan.events.length ? ` It is placed today at ${timeRange(plan.events[0])}.` : ' No study session is scheduled today.';
        return `Recommended: ${ACTION_PHRASE[plan.best_action]}${focus} (${hoursText(plan.hours)}).${when}`;
      },
    },
    {
      target: '#week',
      title: 'On the calendar',
      placement: 'top',
      body: () => (plan.events.length
        ? "Today's session appears here. Future days stay empty because the planner decides one day at a time."
        : 'A rest day adds no session. Any planner sessions already on today would be cleared.'),
    },
    {
      title: 'Summary',
      rows: () => {
        const [first, second] = ranked();
        const m = plan.posteriors.p_mastery_high;
        return [
          ['Student', scenario.description],
          ['Beliefs', `Mastery ${meta.concepts.map((concept) => pct(m[concept])).join(' / ')}; stress risk ${pct(plan.posteriors.p_stress_high)}; pass chance ${pct(plan.posteriors.p_pass)}`],
          ['Decision', `${ACTION_NAME[plan.best_action]} (${hoursText(plan.hours)})`],
          ['Why', `${ACTION_NAME[first[0]]} scores ${first[1].toFixed(1)}, ahead of ${ACTION_NAME[second[0]]} at ${second[1].toFixed(1)}.`],
        ];
      },
      body: () => `${plan.best_action === scenario.expected_action ? `${guided.takeaway}\n\n` : ''}The form now shows this student. Change anything and press Calculate to explore.`,
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

  GUIDED.forEach(({ name }) => {
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
    if (event.target.id === 'profile') applyProfile(event.target.value);
    else if (event.target.name !== 'model') $('profile').value = '';
    markStale();
  });

  try {
    [meta, scenarios] = await Promise.all([getNetwork(false), request('/api/scenarios')]);
    $('today-label').textContent = dateLabel(meta.today, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    $('today-label').dateTime = meta.today;
    buildForm();
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
