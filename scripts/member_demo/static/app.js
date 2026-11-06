'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state, selectedId = null, activeView = 'student';
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '操作失败，请重试');
  return result;
}
function notice(text, error=false) {
  $('message').hidden = false; $('message').className = error ? 'error' : ''; $('message').textContent = text;
}
function action(fn) { return async event => { try { await fn(event); } catch(error) { notice(error.message, true); } }; }
function statusText(r) { return r.appliedAt ? '已应用' : state.reviews[r.review]; }
function statusClass(r) { return r.appliedAt ? 'applied' : r.review; }
function summary(r) { const p=r.payload; return `${p.name} · ${p.entryYear || '年份未填'} · ${state.roles[p.role]}`; }
function switchView(view) {
  activeView=view;
  for(const button of document.querySelectorAll('[data-view]')) { if(button.dataset.view===view) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current'); }
  for(const panel of document.querySelectorAll('.view')) panel.hidden=panel.id!==`view-${view}`;
  if(view==='members') $('members-frame').src='/members?refresh='+Date.now();
}
function selectedDirections(container) { return [...$(container).querySelectorAll('input:checked')].map(input=>input.value); }
function kindChanged() {
  const kind=$('kind').value;
  for(const name of ['graduate','add','update']) $(`${name}-fields`).hidden=kind!==name;
  $('graduationAcknowledged').required=kind==='graduate';
  $('graduationAcknowledged').checked=false;
  $('receipt').hidden=true;
  yearChanged();
  syncControls();
}
function yearChanged() {
  const postdoc=$('role').value==='postdoc';
  $('year-label').textContent=postdoc ? '入站年份（可暂缺）' : '入学年份';
  $('entryYear').required=!postdoc;
}
function changeFieldChanged() {
  const field=$('change-field').value;
  $('change-text-label').hidden=['researchIds','role'].includes(field);
  $('change-role-label').hidden=field!=='role';
  $('change-directions-field').hidden=field!=='researchIds';
  $('clear-label').hidden=!['url','researchIds','entryYear'].includes(field);
  $('clear-field').checked=false;
  $('change-value').type=field==='url'?'url':field==='entryYear'?'number':'text';
  $('change-value').value='';
  syncControls();
}
function syncControls() {
  const kind=$('kind').value, field=$('change-field').value, clear=$('clear-field').checked;
  for(const name of ['graduate','add','update']) for(const control of $(`${name}-fields`).querySelectorAll('input,select,textarea')) control.disabled=kind!==name;
  $('change-value').disabled=kind!=='update'||['researchIds','role'].includes(field)||clear;
  $('change-role').disabled=kind!=='update'||field!=='role';
  for(const input of $('change-directions').querySelectorAll('input'))input.disabled=kind!=='update'||field!=='researchIds'||clear;
}
function fillExample() {
  kindChanged();
  $('name').value='示例同学甲'; $('role').value='master'; $('entryYear').value='2021';
  for(const box of document.querySelectorAll('.checks input')) box.checked=false;
  if($('kind').value==='add') {
    $('name').value='示例同学乙'; $('role').value='phd'; $('entryYear').value='2026'; $('add-url').value='';
    $('add-directions').querySelector('input[value="ts"]').checked=true;
  } else if($('kind').value==='update') {
    $('name').value='示例同学乙'; $('entryYear').value='2025'; $('change-field').value='url'; changeFieldChanged();
    $('change-value').value='https://example.org/student-b';
  }
  yearChanged();
}
async function load() {
  state=await api('/api/state');
  if(!state.requests.some(r=>r.id===selectedId))selectedId=state.requests.at(-1)?.id || null;
  $('pending-count').textContent=state.requests.filter(r=>!r.appliedAt && r.review==='pending').length || '';
  $('student-requests').innerHTML=state.requests.length ? '<ul class="compact-list">'+[...state.requests].reverse().map(r=>`<li><span>${esc(r.id)} · ${esc(state.kinds[r.payload.kind])}<br><span class="muted">${esc(summary(r))}${r.review==='rejected' && r.reviewNote ? ' · 退回说明：'+esc(r.reviewNote) : ''}</span></span><span class="status ${statusClass(r)}">${statusText(r)}</span></li>`).join('')+'</ul>' : '<p class="empty">还没有申请。可以直接使用上方预填示例开始。</p>';
  $('review-list').innerHTML=state.requests.length ? [...state.requests].reverse().map(r=>`<button class="request-item${selectedId===r.id?' active':''}" data-request="${esc(r.id)}"><strong>${esc(state.kinds[r.payload.kind])} · ${esc(r.payload.name)}</strong><span class="request-meta">${esc(r.id)} · ${esc(r.payload.entryYear || '年份未填')} · ${esc(state.roles[r.payload.role])} · ${statusText(r)}</span></button>`).join('') : '<p class="empty">尚无待处理申请。</p>';
  for(const button of document.querySelectorAll('[data-request]')) button.onclick=()=>{selectedId=button.dataset.request; renderDetail(); for(const b of document.querySelectorAll('[data-request]')) b.classList.toggle('active',b===button);};
  renderDetail();
}
function describePayload(p) {
  if(p.kind==='graduate') return '确认上述硕博经历已毕业；同一人的其他经历保持不变。';
  if(p.kind==='add') return '新增方向：'+(p.researchIds.map(id=>state.directions.find(g=>g.id===id).title).join('、') || '暂不归属')+(p.url?'；主页：'+p.url:'');
  const labels={name:'姓名',url:'个人主页',role:'身份',entryYear:'年份',researchIds:'研究方向'};
  const values=Object.entries(p.changes).map(([key,value])=>labels[key]+'：'+(key==='role'?state.roles[value]:key==='researchIds'?value.map(id=>state.directions.find(g=>g.id===id).title).join('、'):value));
  values.push(...p.clearFields.map(key=>'明确清空'+labels[key]));
  return values.join('；');
}
function existingDescription(option) {
  if(!option) return '<p class="empty">请先确认匹配对象。</p>';
  if(option.memberId==='new') return '<p class="muted">将建立一位新成员及其第一段经历。</p>';
  const m=option.member || state.members.find(m=>m.id===option.memberId);
  const e=option.experience;
  return `<dl class="definition"><div><dt>现有姓名</dt><dd>${esc(m.name)}</dd></div><div><dt>现有主页</dt><dd>${esc(m.url || '未填写')}</dd></div>${e?`<div><dt>现有经历</dt><dd>${esc(e.entryYear || '年份未填')} · ${esc(state.roles[e.role])} · ${e.graduationConfirmed?'已确认毕业':e.status==='current'?'当前':'往届，未确认毕业'}</dd></div><div><dt>现有方向</dt><dd>${esc(e.researchIds.map(id=>state.directions.find(g=>g.id===id).title).join('、') || '未归属')}</dd></div>`:'<div><dt>现有经历</dt><dd>'+esc(state.experiences.filter(e=>e.memberId===m.id).map(e=>(e.entryYear || '年份未填')+' '+state.roles[e.role]).join('；'))+'</dd></div>'}</dl>`;
}
function renderDetail() {
  const r=state.requests.find(r=>r.id===selectedId);
  if(!r){$('review-detail').innerHTML='<p class="empty">提交申请后，可在这里查看和审核。</p>';return;}
  const options=r.candidates;
  let chosen=-1;
  if(r.target) chosen=options.findIndex(o=>o.memberId===r.target.memberId && o.experienceId===r.target.experienceId);
  if(chosen<0) {const existing=options.map((o,i)=>[o,i]).filter(([o])=>o.memberId!=='new');if(existing.length===1)chosen=existing[0][1];else if(!existing.length && r.payload.kind==='add')chosen=options.findIndex(o=>o.memberId==='new');}
  $('review-detail').innerHTML=`<div class="review-detail-head"><h3>${esc(r.id)} · ${esc(state.kinds[r.payload.kind])}</h3><span class="status ${statusClass(r)}">${statusText(r)}</span></div><dl class="definition"><div><dt>申请人</dt><dd>${esc(summary(r))}</dd></div><div><dt>申请内容</dt><dd>${esc(describePayload(r.payload))}</dd></div></dl><form id="review-form" class="review-controls"><label>确认匹配的人员与经历<select id="target" ${r.appliedAt?'disabled':''}><option value="">${options.length?'请选择；同名时请仔细核对':'没有匹配记录，可先标记待核对或退回'}</option>${options.map((o,i)=>`<option value="${i}" ${chosen===i?'selected':''}>${esc(o.label)}</option>`).join('')}</select></label><div id="existing-data">${existingDescription(options[chosen])}</div><label>审核结果<select id="decision" ${r.appliedAt?'disabled':''}>${Object.entries(state.reviews).map(([key,value])=>`<option value="${key}" ${r.review===key?'selected':''}>${value}</option>`).join('')}</select></label><label>审核备注（选填）<textarea id="review-note" rows="2" maxlength="500" ${r.appliedAt?'disabled':''}>${esc(r.reviewNote)}</textarea></label><div class="button-row"><button type="submit" ${r.appliedAt?'disabled':''}>保存审核结果</button><button type="button" class="primary" id="preview" ${r.review!=='approved'||r.appliedAt?'disabled':''}>查看修改预览</button></div><p class="apply-note">“通过”仅表示审核完成。查看修改预览并应用后，成员展示才会改变。</p></form><section id="diff" class="diff-area" hidden></section>${r.appliedAt?'<p class="receipt">这份申请已应用。<button class="text-button" id="after-apply-view">查看成员展示结果 →</button></p>':''}`;
  let previewToken=null;
  const dirty=()=>{previewToken=null;$('diff').hidden=true;$('preview').disabled=true;};
  $('target').onchange=()=>{$('existing-data').innerHTML=existingDescription($('target').value===''?null:options[Number($('target').value)]);dirty();};
  $('decision').onchange=dirty;
  $('review-note').oninput=dirty;
  $('review-form').onsubmit=action(async event=>{
    event.preventDefault();
    const index=$('target').value;
    const target=index===''?null:{memberId:options[Number(index)].memberId,experienceId:options[Number(index)].experienceId};
    await api('/api/review',{requestId:r.id,decision:$('decision').value,note:$('review-note').value,target});
    await load();notice('审核结果已保存。通过后，请继续查看修改预览。');
  });
  $('preview').onclick=action(async()=>{
    const result=await api('/api/preview',{requestId:r.id});previewToken=result.token;
    $('diff').hidden=false;
    $('diff').innerHTML='<h3>应用前，请核对这些变化</h3><table><thead><tr><th>修改项</th><th>当前</th><th>应用后</th></tr></thead><tbody>'+result.changes.map(c=>`<tr><td>${esc(c.label)}</td><td>${esc(c.before)}</td><td>${esc(c.after)}</td></tr>`).join('')+'</tbody></table><p class="apply-note">只更新这份申请涉及的资料；毕业确认不会改变同一人的其他经历。</p><button class="primary" id="apply">应用到测试数据</button>';
    $('diff').scrollIntoView({behavior:'smooth',block:'nearest'});
    $('apply').onclick=action(async()=>{
      const button=$('apply');button.disabled=true;
      try {await api('/api/apply',{requestId:r.id,token:previewToken});await load();notice('已应用到测试数据。现在可在“成员展示预览”查看结果。');}
      catch(error){previewToken=null;$('diff').hidden=true;notice(error.message,true);}
    });
  });
  if($('after-apply-view'))$('after-apply-view').onclick=()=>switchView('members');
}
async function init() {
  await load();
  for(const container of ['add-directions','change-directions']) $(container).innerHTML=state.directions.map(g=>`<label><input type="checkbox" value="${esc(g.id)}"> ${esc(g.title)}</label>`).join('');
  for(const button of document.querySelectorAll('[data-view]')) button.onclick=()=>switchView(button.dataset.view);
  $('kind').onchange=kindChanged;$('role').onchange=yearChanged;$('change-field').onchange=changeFieldChanged;
  $('clear-field').onchange=syncControls;
  $('fill-example').onclick=fillExample;$('go-review').onclick=()=>switchView('review');
  $('request-form').onsubmit=action(async event=>{
    event.preventDefault();
    const p={kind:$('kind').value,name:$('name').value,role:$('role').value,entryYear:$('entryYear').value};
    if(p.kind==='graduate')p.graduationAcknowledged=$('graduationAcknowledged').checked;
    else if(p.kind==='add'){p.url=$('add-url').value;p.researchIds=selectedDirections('add-directions');}
    else {const field=$('change-field').value;const value=field==='researchIds'?selectedDirections('change-directions'):field==='role'?$('change-role').value:$('change-value').value;p.changes=$('clear-field').checked?{}:{[field]:value};p.clearFields=$('clear-field').checked?[field]:[];}
    const button=$('request-form').querySelector('[type="submit"]');button.disabled=true;
    try{const result=await api('/api/submit',p);selectedId=result.id;await load();$('receipt').hidden=false;$('receipt-text').textContent=`${result.id} · 待核对。你可以切换到维护者，继续体验审核。`;$('receipt').focus();notice('申请已提交，成员资料暂未改变。');}
    finally{button.disabled=false;}
  });
  $('reset').onclick=action(async()=>{
    if(!confirm('重置后将恢复初始虚构成员，并清空当前申请列表。原状态会保留在本地备份。确定重置吗？'))return;
    await api('/api/reset',{confirmed:true});selectedId=null;await load();$('receipt').hidden=true;fillExample();switchView('student');notice('演示数据已恢复初始状态。');
  });
  for(const [id,reviewed] of [['export-requests',false],['export-reviews',true]]) $(id).onclick=action(async()=>{
    const result=await api('/api/export',{reviewed});
    $('message').hidden=false;$('message').className='';$('message').innerHTML=`CSV 已保存到项目内：<code>${esc(result.path)}</code>　<a href="${esc(result.url)}" target="_blank" rel="noopener">查看导出内容 ↗</a>`;
  });
  kindChanged();changeFieldChanged();
}
init().catch(error=>notice('页面加载失败：'+error.message,true));
