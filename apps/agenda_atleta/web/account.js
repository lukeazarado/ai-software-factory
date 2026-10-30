"use strict";
const $ = (id) => document.getElementById(id);
let csrf = "";
const message = (text) => { $("message").textContent = text; };
async function getJson(url, opts) {
  const response = await fetch(url, {credentials:"same-origin", cache:"no-store", ...opts});
  if (!response.ok) throw new Error("HTTP " + response.status);
  return response.json();
}
async function init() {
  try {
    const auth = await getJson("/api/auth/me");
    csrf = auth.csrfToken;
    $("accountId").textContent = auth.ownerId || "Indisponível";
    if(auth.isAdmin) $("adminSettingsLink").hidden=false;
    const notice = await getJson("/api/privacy");
    $("notice").textContent = notice.purpose + " Dados: " + notice.data_categories.join(", ") + ". Login Google; sem compartilhamento público.";
    $("supplierName").textContent = "Fornecedor: " + (notice.supplier || "Não informado — pendente de configuração");
    $("privacyCopy").textContent = notice.privacy_notice || "Política de privacidade ainda não fornecida pelo responsável.";
    $("termsCopy").textContent = notice.terms_of_service || "Termos de uso ainda não fornecidos pelo responsável.";
    const ack = await getJson("/api/privacy/ack");
    $("noticeStatus").textContent = ack.acknowledged ? "Declaração registrada na versão " + ack.notice_version : "Declaração ainda não registrada.";
  } catch(e) { message("Não foi possível carregar a conta. Faça login novamente."); }
}
$("accept").addEventListener("click", async () => {
  if (!$("readNotice").checked || !$("adult").checked) return message("Marque as duas declarações para continuar.");
  try {
    const body = {read_notice:true,responsible_adult:true};
    await getJson("/api/privacy/ack", {method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":csrf},body:JSON.stringify(body)});
    message("Declaração registrada. Ela não constitui comprovação de guarda ou consentimento legal.");
    const ack = await getJson("/api/privacy/ack");
    $("noticeStatus").textContent = "Declaração registrada na versão " + ack.notice_version;
  } catch(e) { message("Erro ao registrar declaração: " + e.message); }
});
$("export").addEventListener("click", async () => {
  try {
    const data = await getJson("/api/account/export");
    const blob = new Blob([JSON.stringify(data,null,2)], {type:"application/json"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "agenda-atleta-minha-conta.json";
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
    message("Exportação realizada. Guarde o arquivo fora de pastas compartilhadas.");
  } catch(e) { message("Falha ao exportar dados: " + e.message); }
});
$("delete").addEventListener("click", async () => {
  const confirmation = $("confirmation").value;
  if (confirmation !== "EXCLUIR_MINHA_CONTA_E_ATLETAS") return message("Confirmação inválida.");
  if (!window.confirm("Excluir sua conta e TODOS os atletas deste usuário?")) return;
  try {
    const r = await fetch("/api/account", {method:"DELETE",credentials:"same-origin",headers:{"Content-Type":"application/json","X-CSRF-Token":csrf},body:JSON.stringify({confirmation})});
    if (r.status === 403) throw new Error("Faça logout, entre novamente com Google e tente novamente.");
    if (!r.ok) throw new Error("HTTP " + r.status);
    window.location.assign("/login");
  } catch(e) { message("Falha ao excluir conta: " + e.message); }
});
init();
