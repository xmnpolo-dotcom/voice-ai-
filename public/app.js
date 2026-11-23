const API_BASE = (window.VOICE_AI_API_URL || "https://voice-ai-api.onrender.com").replace(/\/$/, "");
const fileInput=document.querySelector("#videoFile");
const preview=document.querySelector("#preview");
const fileInfo=document.querySelector("#fileInfo");
const scriptBox=document.querySelector("#script");
const statusBox=document.querySelector("#status");
const processBtn=document.querySelector("#processBtn");
let selectedFile=null;
let previewUrl=null;

document.querySelectorAll('input[name="mode"]').forEach(input=>input.addEventListener("change",()=>{
  document.querySelectorAll(".choice").forEach(card=>card.classList.toggle("selected",card.querySelector("input").checked));
  scriptBox.hidden=document.querySelector('input[name="mode"]:checked').value!=="script";
}));

fileInput.addEventListener("change",()=>{
  selectedFile=fileInput.files?.[0]||null;
  if(previewUrl)URL.revokeObjectURL(previewUrl);
  preview.hidden=!selectedFile;
  if(!selectedFile){fileInfo.textContent="Selecciona un vídeo para empezar.";return;}
  if(!selectedFile.type.startsWith("video/")){selectedFile=null;fileInfo.textContent="El archivo seleccionado no parece ser un vídeo.";return;}
  previewUrl=URL.createObjectURL(selectedFile);
  preview.src=previewUrl;
  fileInfo.textContent=selectedFile.name+" · "+(selectedFile.size/1024/1024).toFixed(1)+" MB";
});

const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));

async function watchJob(jobId){
  for(let attempt=0;attempt<1080;attempt++){
    await sleep(10000);
    const response=await fetch(`${API_BASE}/api/jobs/${jobId}`);
    const job=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(job.detail||"No se pudo consultar el estado del doblaje.");
    statusBox.textContent=job.message||"Procesando vídeo…";
    if(job.status==="failed")throw new Error(job.message||"El doblaje ha fallado.");
    if(job.status==="completed"&&job.download_url){
      const link=document.createElement("a");
      link.href=API_BASE+job.download_url;
      link.textContent="Descargar vídeo doblado";
      link.className="download-link";
      link.download="";
      statusBox.replaceChildren(document.createTextNode("¡Doblaje terminado! "),link);
      return;
    }
  }
  throw new Error("El procesamiento está tardando demasiado. Comprueba el estado más tarde.");
}

processBtn.addEventListener("click",async()=>{
  if(!selectedFile){statusBox.textContent="Primero selecciona un vídeo.";return;}
  const mode=document.querySelector('input[name="mode"]:checked').value;
  if(mode==="script"){statusBox.textContent="El modo con guion personalizado todavía no está disponible. Selecciona Automático.";return;}
  statusBox.textContent="Subiendo vídeo al motor de doblaje…";
  processBtn.disabled=true;
  try{
    const data=new FormData();
    data.append("file",selectedFile);
    data.append("mode","automatic");
    data.append("script","");
    data.append("language","es");
    data.append("voice",document.querySelector("#voice").value);
    data.append("resolution",document.querySelector("#resolution").value);
    data.append("keep_audio",document.querySelector("#keepAudio").checked?"true":"false");
    data.append("translate_audio","true");
    data.append("target_language","es");
    data.append("translate_screen_text",document.querySelector("#translateScreenText").checked?"true":"false");
    const response=await fetch(`${API_BASE}/api/jobs`,{method:"POST",body:data});
    const job=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(job.detail||"No se pudo enviar el vídeo. Comprueba que el servidor esté desplegado.");
    statusBox.textContent=job.message||"Vídeo recibido. Iniciando doblaje…";
    await watchJob(job.id);
  }catch(error){
    statusBox.textContent=error.message||"No se pudo conectar con el servidor de doblaje.";
  }finally{processBtn.disabled=false;}
});

if("serviceWorker" in navigator)window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(()=>{}));
