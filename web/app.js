// Original interface; design guidance: Unslop by Damir Sokolovsky, CC BY 4.0.
const $ = (id) => document.getElementById(id);
let metadata, scenarios = [], chart, currentPlan, busy = false;
const networkCache = new Map();
const title = (value) => value.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
const el = (tag, text, className) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; };
const option = (value, label) => { const node = el('option', label); node.value = value; return node; };
const dayDate = (iso) => new Date(`${iso}T12:00:00Z`);
const dateLabel = (iso, options) => new Intl.DateTimeFormat('en-CA', {timeZone: 'UTC', ...options}).format(dayDate(iso));
const timeLabel = (iso) => new Intl.DateTimeFormat('en-CA', {timeZone: metadata.timezone, hour:'numeric', minute:'2-digit'}).format(new Date(iso));

async function request(url, payload) {
  const response = await fetch(url, payload ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)} : {});
  if (!response.ok) {
    let message = `Request failed (${response.status}). Please try again.`;
    try { const data = await response.json(); message = typeof data.detail === 'string' ? data.detail : data.detail.map(item => item.msg).join('; '); } catch {}
    throw new Error(message);
  }
  return response.json();
}
async function getNetwork(learned) {
  const key = learned ? 'learned' : 'handcrafted';
  if (!networkCache.has(key)) networkCache.set(key, await request(`/api/network?use_learned=${learned}`));
  return networkCache.get(key);
}
function renderConceptInputs() {
  $('concept-inputs').replaceChildren();
  for (const concept of metadata.concepts) {
    const row = el('div', undefined, 'concept-row');
    row.append(el('span', concept, 'concept-index'));
    for (const [kind, states] of [['difficulty',metadata.difficulty_states],['quiz',metadata.quiz_states]]) {
      const select = el('select'); select.name = `${kind}_${concept}`; select.id = select.name;
      select.setAttribute('aria-label', `${concept} ${kind === 'quiz' ? 'quiz result' : kind}`);
      if (kind === 'quiz') select.append(option('', 'Unknown'));
      states.forEach(state => select.append(option(state, title(state)))); row.append(select);
    }
    $('concept-inputs').append(row);
  }
  metadata.sleep_states.forEach(state => $('sleep').append(option(state,title(state))));
}
function readForm() {
  const difficulty = {}, quiz = {};
  metadata.concepts.forEach(c => {difficulty[c] = $(`difficulty_${c}`).value; quiz[c] = $(`quiz_${c}`).value || null;});
  return {difficulty, quiz, sleep:$('sleep').value || null, exam_date:$('exam-date').value, use_learned:$('model-select').value === 'learned'};
}
function loadScenario(name) {
  const scenario = scenarios.find(s => s.name === name);
  if (!scenario) { $('scenario-description').textContent = 'Your own inputs. Unknown quiz results are left unobserved.'; return; }
  metadata.concepts.forEach(c => {$(`difficulty_${c}`).value = scenario.difficulty[c]; $(`quiz_${c}`).value = scenario.quiz[c] || '';});
  $('sleep').value = scenario.sleep || ''; $('exam-date').value = scenario.exam_date;
  $('scenario-description').textContent = scenario.description;
}
function markStale() {
  if (!currentPlan) return;
  $('plan-status').textContent = 'Inputs changed — calculate again to update this plan';
  $('recommendation-label').textContent = 'Previous calculation';
}
function renderPosteriors(plan) {
  const values = [...metadata.concepts.map(c => [c + ' mastery',plan.posteriors.p_mastery_high[c]]),['High stress',plan.posteriors.p_stress_high],['Exam pass',plan.posteriors.p_pass]];
  $('posterior-bars').replaceChildren();
  for (const [label,value] of values) {
    const item = el('div', undefined, 'posterior-item');
    item.append(el('span',label,'posterior-label'),el('span',`${Math.round(value*100)}%`,'posterior-value'));
    const track = el('div', undefined, 'posterior-track'), fill = el('span', undefined, 'posterior-fill');
    fill.style.width = `${Math.max(0,Math.min(100,value*100))}%`; track.setAttribute('aria-hidden','true'); track.append(fill); item.append(track); $('posterior-bars').append(item);
  }
}
function renderExpectedUtility(plan) {
  const actions = metadata.actions;
  $('utility-values').replaceChildren();
  for (const action of actions) {
    const row = el('tr',undefined,action.key === plan.best_action ? 'chosen' : '');
    const label = el('td',title(action.key));
    if (action.key === plan.best_action) label.append(el('span','Recommended','chosen-marker'));
    row.append(label,el('td',`${action.hours} h`),el('td',plan.expected_utility[action.key].toFixed(1))); $('utility-values').append(row);
  }
  if (!window.Chart) { $('eu-chart').parentElement.hidden = true; return; }
  const values = actions.map(a => plan.expected_utility[a.key]);
  const colors = actions.map(a => a.key === plan.best_action ? '#315d45' : '#c5cbc2');
  if (chart) chart.destroy();
  chart = new Chart($('eu-chart'), {type:'bar', data:{labels:actions.map(a => title(a.key)),datasets:[{data:values,backgroundColor:colors,borderRadius:3,maxBarThickness:64}]}, options:{responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx => `${ctx.parsed.y.toFixed(1)} utility points`}}},scales:{x:{grid:{display:false},border:{display:false},ticks:{color:'#59605b',font:{size:12}}},y:{beginAtZero:true,grid:{color:'#e5e7e1'},border:{display:false},ticks:{color:'#6d746e',font:{family:'Consolas',size:11}}}}}});
}
function renderCalendar(plan) {
  $('calendar').replaceChildren();
  for (let i=0;i<7;i++) {
    const day = dayDate(plan.today); day.setUTCDate(day.getUTCDate()+i); const iso = day.toISOString().slice(0,10);
    const block = el('div',undefined,`day ${i === 0 ? 'day-today' : ''}`), head = el('div',undefined,'day-header');
    head.append(el('span',i === 0 ? 'Today' : dateLabel(iso,{weekday:'short'})),el('span',String(day.getUTCDate()),'day-date')); block.append(head);
    const events = plan.events.filter(event => event.start.slice(0,10) === iso);
    if (events.length) for (const event of events) {
      const session = el('div',title(plan.best_action) + ' study','calendar-event');
      session.append(el('small',`${timeLabel(event.start)}–${timeLabel(event.end)}`));
      if (plan.best_action === 'focused') session.append(el('small',`Focus: ${plan.target_concept}`));
      block.append(session);
    } else block.append(el('p',i === 0 ? 'Rest day · no session' : 'Not planned','day-note'));
    if (iso === plan.exam_date) block.append(el('p','Exam day','exam-marker'));
    $('calendar').append(block);
  }
  $('week-description').textContent = `${dateLabel(plan.today,{month:'long',day:'numeric'})} onward · a daily plan, not a week-long prediction`;
}
function renderRecommendation(plan) {
  const labels = {intense:'An intensive study block',focused:`Focus on ${plan.target_concept}`,light:'Keep it light',rest:'Make room to rest'};
  $('action-title').textContent = labels[plan.best_action] || title(plan.best_action);
  const ranked = Object.entries(plan.expected_utility).sort((a,b)=>b[1]-a[1]);
  $('action-reason').textContent = `${title(plan.best_action)} has the highest expected utility (${ranked[0][1].toFixed(1)}), ahead of ${ranked[1][0]} (${ranked[1][1].toFixed(1)}), after accounting for stress and time.`;
  $('hours').textContent = String(plan.hours); $('duration-unit').textContent = 'study hours';
  $('days-left').textContent = plan.days_until_exam === 0 ? 'Exam today' : `${plan.days_until_exam} days to your exam`;
  $('session-time').textContent = plan.events.length ? `${timeLabel(plan.events[0].start)}–${timeLabel(plan.events[0].end)}` : 'No session scheduled';
  $('recommendation-label').textContent = "Today's recommendation";
  $('model-label').textContent = plan.model === 'learned' ? 'Learned model' : 'Hand-crafted model';
  $('plan-status').textContent = 'Calculated from your current inputs · preview only';
}
function renderNetwork(network) {
  const ns = 'http://www.w3.org/2000/svg';
  const svgNode = (tag,attrs,text) => {const n = document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text)n.textContent=text;return n;};
  const svg = svgNode('svg',{viewBox:'0 0 1000 380',role:'img','aria-label':'13-node Bayesian network: difficulty affects mastery, mastery affects quizzes and exam success, days left affects stress, and stress affects sleep and exam success'});
  const defs = svgNode('defs',{}), marker = svgNode('marker',{id:'arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto'});
  marker.append(svgNode('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'#8b948b'})); defs.append(marker);svg.append(defs);
  const positions = {};
  metadata.concepts.forEach((c,i)=>{positions[`Difficulty_${c}`]=[80+i*240,40];positions[`Mastery_${c}`]=[80+i*240,150];positions[`Quiz_${c}`]=[180+i*240,220];});
  positions.DaysLeft=[820,40];positions.Stress=[820,150];positions.Sleep=[920,220];positions.ExamSuccess=[440,330];
  for (const edge of network.edges) {
    const [x1,y1]=positions[edge.source], [x2,y2]=positions[edge.target];
    const dx=x2-x1,dy=y2-y1;
    const boundary=Math.min(64/Math.abs(dx),22/Math.abs(dy));
    const start=boundary, end=boundary+5/Math.hypot(dx,dy);
    svg.append(svgNode('line',{x1:x1+dx*start,y1:y1+dy*start,x2:x2-dx*end,y2:y2-dy*end,stroke:'#8b948b','stroke-width':1.5,'marker-end':'url(#arrow)'}));
  }
  for (const node of network.nodes) {
    const [x,y]=positions[node.id];svg.append(svgNode('rect',{x:x-64,y:y-22,width:128,height:44,rx:8,fill:node.role === 'query'?'#e5eee2':'#eeefeb',stroke:'#d4d9d1'}));
    svg.append(svgNode('text',{x,y:y+4,'text-anchor':'middle',fill:'#315d45','font-size':12,'font-family':'Segoe UI, sans-serif'},node.id.replaceAll('_',' ')));
  }
  $('network-graph').replaceChildren(svg);
  const selected = $('node-select').value;
  $('node-select').replaceChildren(...network.nodes.map(n=>option(n.id,n.id.replaceAll('_',' '))));
  if (network.cpds[selected]) $('node-select').value=selected;
  $('node-select').onchange=()=>renderCpd(network);
  renderCpd(network);
}
function renderCpd(network) {
  const cpd=network.cpds[$('node-select').value], table=el('table'), thead=el('thead'), heading=el('tr');
  const headers=[...cpd.parents,...cpd.states.map(s=>`P(${s})`)];
  headers.forEach(h=>{const th=el('th',h.replaceAll('_',' '));th.scope='col';heading.append(th);});thead.append(heading);table.append(thead);
  let combinations=[[]];
  cpd.parents.forEach(p=>{combinations=combinations.flatMap(previous=>cpd.parent_states[p].map(s=>[...previous,s]));});
  const body=el('tbody');
  combinations.forEach((combo,index)=>{const row=el('tr');[...combo,...cpd.values.map(values=>(values[index]*100).toFixed(1)+'%')].forEach(value=>row.append(el('td',value)));body.append(row);});table.append(body);$('cpd-table').replaceChildren(table);
}
async function calculate() {
  if (busy || !$('plan-form').reportValidity()) return;
  const payload=readForm(); busy=true;$('results').setAttribute('aria-busy','true');$('error').hidden=true;
  const controls=[...$('plan-form').querySelectorAll('select,input,button')];controls.forEach(n=>n.disabled=true);
  $('plan-status').textContent='Calculating the four study actions…';
  try {
    const [plan,network]=await Promise.all([request('/api/plan',payload),getNetwork(payload.use_learned)]);
    currentPlan=plan;renderRecommendation(plan);renderPosteriors(plan);renderExpectedUtility(plan);renderCalendar(plan);renderNetwork(network);
  } catch (error) {
    $('error').textContent=error.message || 'Could not calculate the plan. Check the local server and try again.';$('error').hidden=false;
    $('plan-status').textContent=currentPlan?'Calculation failed — previous result remains below':'Calculation failed';
    $('recommendation-label').textContent=currentPlan?'Previous calculation':'No plan calculated';
  } finally {busy=false;controls.forEach(n=>n.disabled=false);$('results').setAttribute('aria-busy','false');}
}
document.addEventListener('DOMContentLoaded',async()=>{
  $('plan-form').addEventListener('submit',event=>{event.preventDefault();calculate();});
  $('plan-form').addEventListener('change',event=>{
    if (event.target.id==='scenario-select') loadScenario(event.target.value);
    else if (event.target.id!=='model-select') {$('scenario-select').value='';loadScenario('');}
    markStale();
  });
  document.querySelectorAll('nav a').forEach(link=>link.addEventListener('click',()=>{document.querySelectorAll('nav a').forEach(a=>a.classList.remove('nav-active'));link.classList.add('nav-active');}));
  try {
    [metadata,scenarios]=await Promise.all([getNetwork(false),request('/api/scenarios')]);
    renderConceptInputs();$('exam-date').min=metadata.today;
    $('today-label').textContent=dateLabel(metadata.today,{weekday:'long',month:'long',day:'numeric',year:'numeric'});
    $('today-label').dateTime=metadata.today;
    scenarios.forEach(s=>$('scenario-select').append(option(s.name,title(s.name))));
    $('scenario-select').value='one_weak_spot';loadScenario('one_weak_spot');$('submit-plan').disabled=false;await calculate();
  } catch(error) {$('error').textContent='Could not load the planner. Make sure the local server is running, then reload. '+error.message;$('error').hidden=false;$('plan-status').textContent='Planner unavailable';$('results').setAttribute('aria-busy','false');}
});
