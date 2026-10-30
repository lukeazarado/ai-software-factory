"use strict";
const byId = id => document.getElementById(id);
const create = (tag, cls, content) => { const el = document.createElement(tag); if(cls) el.className=cls; if(content!==undefined) el.textContent=String(content); return el; };
let csrf = "";
let toastTimer;
const statuses = {pending:"Pendente", in_review:"Em análise", evidence_recorded:"Evidência registrada"};
function notify(text, error=false) {
  const node = byId("message"); node.textContent=text;node.className="toast show"+(error?" error":"");
  clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.className="toast",7000);
}
async function api(url, options={}) {
  const method = (options.method||"GET").toUpperCase();
  const response = await fetch(url,{credentials:"same-origin",cache:"no-store",...options,
     headers:{...(method!=="GET"?{"X-CSRF-Token":csrf,"Content-Type":"application/json"}:{}),...(options.headers||{})}});
  if(response.status===401){location.assign("/login");throw Error("Sessão encerrada");}
  if(response.status===403)throw Error("Você não possui autorização administrativa");
  let data;try{data=await response.json();}catch(_){data={};}
  if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:"HTTP "+response.status);
  return data;
}
function field(label,kind,value,limit){
 const box=create("label");const name=create("span","fieldlabel",label);box.append(name);
 let control;
 if(kind==="textarea")control=create("textarea");
 else if(kind==="choice") {
   control=create("select");const option=create("option",null,"Administrador adulto (acesso sem login de menores)");option.value="adult_administrator";control.append(option);
 } else {
   control=create("input");control.type=({email:"email",url:"url",integer:"number"})[kind]||"text";
 }
 if(kind==="integer"){control.min="30";control.max="3650";}else if(kind!=="choice")control.maxLength=limit;
 control.value=value;box.append(control);return {box,control};
}
async function saveItem(item,value,button){
 button.disabled=true;const oldLabel=button.textContent;button.textContent="Salvando...";
 try {
   const saved=await api("/api/admin/settings/"+encodeURIComponent(item.key),{method:"PUT",body:JSON.stringify({revision:item.revision,value})});
   item.value=saved.value;item.revision=saved.revision;
   notify("Parâmetro atualizado e auditado: "+item.label);
   await loadSettings();
 } catch(e) {notify(e.message,true);button.disabled=false;button.textContent=oldLabel;}
}
function renderSetting(item){
 const card=create("article","settings-card");const group=create("span","group",item.group);
 const {box,control}=field(item.label,item.kind,item.value,item.max_length);
 const controls=create("div","card-actions");const revision=create("span","revision","Revisão #"+item.revision);
 const save=create("button","save","Salvar alteração");save.type="button";
 save.addEventListener("click",()=>saveItem(item,item.kind==="integer"?Number(control.value):control.value,save));
 controls.append(revision,save);card.append(group,box,controls);return card;
}
function obligationField(caption,type,value,options){
 const label=create("label");label.append(create("span",null,caption));let el;
 if(options){el=create("select");for(const [key,text] of Object.entries(options)){const op=create("option",null,text);op.value=key;el.append(op);}}
 else {el=create("input");el.type=type||"text";el.maxLength=type==="date"?10:600;}
 el.value=value;label.append(el);return {label,control:el};
}
function renderObligation(item){
 const card=create("article","obligation");const top=create("div","obligation-head");
 const title=create("strong",null,item.label);const badge=create("span","status "+item.value.status,statuses[item.value.status]);top.append(title,badge);
 const fields=create("div","obligation-fields");
 const status=obligationField("Situação","text",item.value.status,statuses);
 const owner=obligationField("Responsável","text",item.value.owner);
 const reference=obligationField("Referência da evidência","text",item.value.evidence_reference);
 const reviewed=obligationField("Data da revisão","date",item.value.reviewed_on);
 for(const x of [status,owner,reference,reviewed])fields.append(x.label);
 const actions=create("div","obligation-save");const save=create("button","save","Registrar andamento");save.type="button";
 save.addEventListener("click",()=>saveItem(item,{status:status.control.value,owner:owner.control.value,
   evidence_reference:reference.control.value,reviewed_on:reviewed.control.value},save));
 actions.append(save);card.append(top,fields,actions);return card;
}
function renderHistory(audit){
 const node=byId("history");node.replaceChildren();
 if(!audit.length){node.append(create("div","loading","Nenhuma alteração registrada."));return;}
 for(const entry of audit){
   const row=create("div","history-row");row.append(create("span",null,entry.key),
     create("span",null,"Revisão #"+entry.revision),
     create("span",null,new Date(entry.updated_at*1000).toLocaleString("pt-BR")));
   node.append(row);
 }
}
async function loadSettings(){
 const data=await api("/api/admin/settings");
 byId("totalCount").textContent=data.obligations.total;
 byId("reviewCount").textContent=data.obligations.inReview;
 byId("recordedCount").textContent=data.obligations.recorded;
 const settings=byId("settings"),obligations=byId("obligationsList");settings.replaceChildren();obligations.replaceChildren();
 const items=data.settings.filter(s=>s.kind!=="obligation").sort((a,b)=>a.group.localeCompare(b.group,"pt-BR")||a.label.localeCompare(b.label,"pt-BR"));
 for(const item of items)settings.append(renderSetting(item));
 for(const item of data.settings.filter(s=>s.kind==="obligation"))obligations.append(renderObligation(item));
 renderHistory(data.recentChanges);
}
(async function(){try {csrf=(await api("/api/auth/me")).csrfToken;await loadSettings();}
catch(e){byId("settings").replaceChildren(create("div","loading",e.message));byId("obligationsList").replaceChildren();notify(e.message,true);}})();